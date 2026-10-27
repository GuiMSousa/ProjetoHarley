import json
import os
import unittest
from decimal import Decimal
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from Projeto_HarleyStore.feedback import error_feedback
from Projeto_HarleyStore.services.catalogo import (
    MAX_CORES,
    ModeloCatalogo,
    ModeloMoto,
    ModeloMotoCreate,
    ModeloMotoUpdate,
    TtlCache,
    VariacaoCorCreate,
)
from Projeto_HarleyStore.services.motos import MotoEstoque, MotoEstoqueDetalhe
from Projeto_HarleyStore.services.xano_client import XanoClient, XanoRateLimitError


COR = {"nome": "Vivid Black", "hex": "#0B0B0B", "imagem_url": "https://img.test/sg-black.jpg"}
VITRINE = {
    "id": 3,
    "nome_modelo": "Street Glide",
    "familia": "TOURING",
    "descricao": "Touring de alto desempenho.",
    "imagem_principal": "https://img.test/sg.jpg",
    "variacoes_cor": [COR],
    "destaque": True,
    "preco_a_partir": 189900.0,
    "disponiveis": 2,
}


def modelo(**overrides):
    data = {
        "nome_modelo": "  Street Glide  ",
        "familia": "TOURING",
        "preco_base": "189900.00",
        "imagem_principal": "https://img.test/sg.jpg",
        "variacoes_cor": [COR],
    }
    data.update(overrides)
    return ModeloMotoCreate(**data)


class CatalogoDtoTests(unittest.TestCase):
    def test_valid_model_strips_text(self):
        self.assertEqual(modelo().nome_modelo, "Street Glide")
        self.assertFalse(modelo().destaque)

    def test_color_requires_hex_and_https_photo(self):
        for invalid in (
            {**COR, "hex": "black"},
            {**COR, "hex": "#0B0B0"},
            {**COR, "imagem_url": "http://img.test/a.jpg"},
            {**COR, "imagem_url": "javascript:alert(1)"},
            {**COR, "nome": ""},
        ):
            with self.subTest(cor=invalid), self.assertRaises(ValidationError):
                VariacaoCorCreate(**invalid)

    def test_model_rejects_invalid_fields(self):
        invalid = (
            {"familia": "SCOOTER"},
            {"preco_base": "0"},
            {"preco_base": "1.999"},
            {"imagem_principal": "http://img.test/sg.jpg"},
            {"nome_modelo": " "},
            {"variacoes_cor": [COR] * (MAX_CORES + 1)},
        )
        for overrides in invalid:
            with self.subTest(overrides=list(overrides)), self.assertRaises(ValidationError):
                modelo(**overrides)

    def test_showroom_and_managed_models_tolerate_null_colors_and_flags(self):
        vitrine = ModeloCatalogo.model_validate({**VITRINE, "variacoes_cor": None, "destaque": None})
        self.assertEqual((vitrine.variacoes_cor, vitrine.destaque), ([], False))
        self.assertEqual(vitrine.preco_a_partir, Decimal("189900.0"))
        gerido = ModeloMoto.model_validate(
            {
                "id": 3,
                "nome_modelo": "Street Glide",
                "familia": "TOURING",
                "preco_base": 189900,
                "imagem_principal": "https://img.test/sg.jpg",
                "variacoes_cor": None,
                "destaque": None,
                "ativo": None,
            }
        )
        self.assertEqual((gerido.variacoes_cor, gerido.destaque, gerido.ativo), ([], False, True))


class GaleriaDoXanoTests(unittest.TestCase):
    """Change 17: Xano sends the gallery as /vault/ paths (or file objects); the DTOs read URLs."""

    def setUp(self):
        environment = patch.dict(os.environ, {"XANO_API_BASE_URL": "https://x8.xano.test/api:Hd3aQ"})
        environment.start()
        self.addCleanup(environment.stop)

    def test_vault_paths_and_file_objects_become_urls_on_the_instance_origin(self):
        galeria = [
            "/vault/abc/fat-boy-1.jpg",
            {"access": "public", "path": "/vault/abc/fat-boy-2.jpg", "mime": "image/jpeg"},
            "https://cdn.loja.test/fat-boy-3.jpg",
        ]
        esperado = [
            "https://x8.xano.test/vault/abc/fat-boy-1.jpg",
            "https://x8.xano.test/vault/abc/fat-boy-2.jpg",
            "https://cdn.loja.test/fat-boy-3.jpg",
        ]
        self.assertEqual(ModeloCatalogo.model_validate({**VITRINE, "galeria": galeria}).galeria, esperado)
        self.assertEqual(MotoEstoqueDetalhe.model_validate({"id": 9, "galeria": galeria}).galeria, esperado)

    def test_local_unsafe_or_unreadable_items_are_dropped(self):
        galeria = ["/motos/fat-boy/1.fat-boy.jpg", "javascript:alert(1)", "data:image/png;base64,AA",
                   {"path": None}, None, 7, "  "]
        self.assertEqual(ModeloCatalogo.model_validate({**VITRINE, "galeria": galeria}).galeria, [])

    def test_a_path_that_climbs_out_of_the_vault_is_refused(self):
        # The browser resolves "..", %2e%2e and backslashes alike: none may leave /vault/.
        for caminho in ("/vault/../api:Hd3aQ/auth/me", "/vault/%2e%2E/api:Hd3aQ", r"/vault/a\..\..\api:Hd3aQ",
                        {"path": "/vault/../api:Hd3aQ"}):
            with self.subTest(caminho=caminho):
                self.assertEqual(ModeloCatalogo.model_validate({**VITRINE, "galeria": [caminho]}).galeria, [])
        # Dots inside a file name are not a climb.
        self.assertEqual(
            ModeloCatalogo.model_validate({**VITRINE, "galeria": ["/vault/abc/fat..boy.jpg"]}).galeria,
            ["https://x8.xano.test/vault/abc/fat..boy.jpg"],
        )

    def test_web_urls_are_read_on_https_whatever_the_scheme_case(self):
        galeria = ["http://cdn.loja.test/1.jpg", "HTTPS://cdn.loja.test/2.JPG", "Http://cdn.loja.test/3.jpg",
                   "https://", "ftp://cdn.loja.test/4.jpg", "//cdn.loja.test/5.jpg"]
        self.assertEqual(
            ModeloCatalogo.model_validate({**VITRINE, "galeria": galeria}).galeria,
            ["https://cdn.loja.test/1.jpg", "https://cdn.loja.test/2.JPG", "https://cdn.loja.test/3.jpg"],
        )

    def test_without_the_xano_url_a_vault_path_cannot_be_resolved(self):
        with patch.dict(os.environ, {"XANO_API_BASE_URL": ""}):
            modelo = ModeloCatalogo.model_validate(
                {**VITRINE, "galeria": ["/vault/abc/1.jpg", "https://cdn.loja.test/2.jpg"]}
            )
        self.assertEqual(modelo.galeria, ["https://cdn.loja.test/2.jpg"])

    def test_stock_units_carry_the_model_photo(self):
        unidade = MotoEstoque.model_validate({"id": 9, "imagem_principal": "https://cdn.loja.test/sg.jpg"})
        self.assertEqual((unidade.imagem_principal, unidade.galeria), ("https://cdn.loja.test/sg.jpg", []))
        self.assertEqual(MotoEstoque.model_validate({"id": 10, "imagem_principal": None}).imagem_principal, "")


class TtlCacheTests(unittest.TestCase):
    def test_value_is_reused_until_the_ttl_expires(self):
        now = [100.0]
        cache = TtlCache(60, clock=lambda: now[0])
        calls = []

        def loader():
            calls.append(1)
            return [len(calls)]

        self.assertEqual(cache.get(loader), [1])
        now[0] += 59
        self.assertEqual(cache.get(loader), [1])
        now[0] += 2
        self.assertEqual(cache.get(loader), [2])
        cache.invalidate()
        self.assertEqual(cache.get(loader), [3])

    def test_failed_load_is_not_cached(self):
        cache = TtlCache(60, clock=lambda: 0.0)

        def failing():
            raise RuntimeError("xano down")

        with self.assertRaises(RuntimeError):
            cache.get(failing)
        self.assertEqual(cache.get(lambda: ["ok"]), ["ok"])


class CatalogoClientTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {"XANO_API_BASE_URL": "https://xano.test/api:test", "XANO_AUTH_API_BASE_URL": ""},
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def make_client(self, handler, token=None):
        return XanoClient(token=token, transport=httpx.MockTransport(handler))

    def test_public_catalog_is_called_without_a_session(self):
        captured = {}

        def handler(request):
            captured["path"] = request.url.path
            captured["params"] = dict(request.url.params)
            captured["auth"] = request.headers.get("Authorization")
            return httpx.Response(200, json=[VITRINE])

        with self.make_client(handler) as client:
            modelos = client.list_catalogo(familia="TOURING", busca="glide")

        self.assertEqual(captured["path"], "/api:test/catalogo")
        self.assertEqual(captured["params"], {"familia": "TOURING", "busca": "glide"})
        self.assertIsNone(captured["auth"])
        self.assertEqual(modelos[0].variacoes_cor[0].nome, "Vivid Black")

    def test_detail_is_public_and_management_uses_the_session(self):
        seen = []

        def handler(request):
            seen.append((request.method, request.url.path, request.headers.get("Authorization")))
            if request.url.path.endswith("/catalogo/3"):
                return httpx.Response(200, json=VITRINE)
            body = {**VITRINE, "preco_base": 189900, "ativo": True}
            return httpx.Response(200, json=[body] if request.method == "GET" else body)

        with self.make_client(handler, token="jwt") as client:
            client.get_modelo_catalogo(3)
            client.list_modelos_moto()
            client.criar_modelo_moto(modelo())
            client.atualizar_modelo_moto(3, ModeloMotoUpdate(ativo=False))

        self.assertEqual(seen[0], ("GET", "/api:test/catalogo/3", None))
        self.assertEqual(
            [entry[:2] for entry in seen[1:]],
            [("GET", "/api:test/modelos_moto"), ("POST", "/api:test/modelos_moto"), ("PATCH", "/api:test/modelos_moto/3")],
        )
        self.assertTrue(all(entry[2] == "Bearer jwt" for entry in seen[1:]))

    def test_update_sends_only_fields_set(self):
        captured = {}

        def handler(request):
            captured["body"] = json.loads(request.read())
            return httpx.Response(200, json={**VITRINE, "preco_base": 1, "ativo": False})

        with self.make_client(handler, token="jwt") as client:
            client.atualizar_modelo_moto(3, ModeloMotoUpdate(ativo=False))

        self.assertEqual(captured["body"], {"ativo": False})

    def test_rate_limit_is_a_typed_error_with_a_wait_message(self):
        def handler(request):
            return httpx.Response(429, json={"message": "Too many requests"})

        with self.make_client(handler) as client, self.assertRaises(XanoRateLimitError) as context:
            client.list_catalogo()
        self.assertEqual(context.exception.status_code, 429)
        self.assertIn("Aguarde alguns segundos", error_feedback(context.exception))


if __name__ == "__main__":
    unittest.main()
