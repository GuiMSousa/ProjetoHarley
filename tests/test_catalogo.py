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
