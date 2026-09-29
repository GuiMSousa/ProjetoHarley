import json
import os
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from Projeto_HarleyStore.services.motos import (
    CancelamentoReservaMoto,
    MotoEstoque,
    MotoEstoqueCreate,
    MotoEstoqueDetalhe,
    MotoEstoqueUpdate,
    ReservaMotoCreate,
)
from Projeto_HarleyStore.services.xano_client import XanoClient, XanoPermissionError


DETALHE = {
    "id": 9,
    "status": "RESERVADA",
    "id_modelo": 3,
    "nome_modelo": "Street Glide",
    "familia": "TOURING",
    "variacoes_cor": [{"nome": "Vivid Black", "hex": "#0B0B0B", "imagem_url": "https://img.test/a.jpg"}],
    "chassi": "1HD1KTP19RB600001",
    "cor": "Vivid Black",
    "ano_modelo": 2025,
    "preco_venda": 189900,
    "clientes_id": 5,
    "nome_cliente": "Ana Souza",
    "id_vendedor_reserva": 2,
    "nome_vendedor": "Carlos",
    "reservada_ate": 1790600000000,
    "historico": [
        {"id": 1, "status_anterior": None, "status_novo": "DISPONIVEL", "nome_funcionario": "Gerente"},
        {"id": 2, "status_anterior": "DISPONIVEL", "status_novo": "RESERVADA", "id_cliente": 5},
    ],
}


def unidade(**overrides):
    data = {
        "id_modelo": 3,
        "chassi": " 1hd1ktp19rb600001 ",
        "cor": "Vivid Black",
        "ano_modelo": 2025,
        "preco_venda": "189900.00",
    }
    data.update(overrides)
    return MotoEstoqueCreate(**data)


class MotoDtoTests(unittest.TestCase):
    def test_chassi_is_normalized_to_uppercase_vin(self):
        self.assertEqual(unidade().chassi, "1HD1KTP19RB600001")

    def test_unit_rejects_invalid_fields(self):
        invalid = (
            {"chassi": "1HD1KTP19RB60000"},  # 16 chars
            {"chassi": "1HD1KTP19RB60000O"},  # letter O is not allowed in a VIN
            {"ano_modelo": 1989},
            {"ano_modelo": date.today().year + 2},
            {"preco_venda": "0"},
            {"preco_venda": "1.999"},
            {"id_modelo": 0},
            {"cor": ""},
        )
        for overrides in invalid:
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                unidade(**overrides)

    def test_update_carries_no_status_or_customer(self):
        update = MotoEstoqueUpdate(preco_venda=Decimal("185000"))
        self.assertEqual(update.model_dump(mode="json", exclude_unset=True), {"preco_venda": "185000"})
        for forbidden in ("status", "clientes_id", "id_vendedor_reserva", "reservada_ate"):
            self.assertNotIn(forbidden, MotoEstoqueUpdate.model_fields)
            self.assertNotIn(forbidden, MotoEstoqueCreate.model_fields)

    def test_reservation_and_cancellation(self):
        self.assertEqual(ReservaMotoCreate(id_cliente=5).dias_validade, 7)
        for dias in (0, 31):
            with self.subTest(dias=dias), self.assertRaises(ValidationError):
                ReservaMotoCreate(id_cliente=5, dias_validade=dias)
        with self.assertRaises(ValidationError):
            CancelamentoReservaMoto(motivo="   ")
        self.assertEqual(CancelamentoReservaMoto(motivo=" Desistiu ").motivo, "Desistiu")

    def test_legacy_units_read_as_available_without_model(self):
        legado = MotoEstoque.model_validate({"id": 1, "marca": "Harley", "modelo": "Iron", "status": None, "variacoes_cor": None})
        self.assertEqual((legado.status, legado.id_modelo, legado.variacoes_cor), ("DISPONIVEL", None, []))
        detalhe = MotoEstoqueDetalhe.model_validate(DETALHE)
        self.assertEqual([evento.status_novo for evento in detalhe.historico], ["DISPONIVEL", "RESERVADA"])
        self.assertEqual(detalhe.reservada_ate.year, 2026)


class MotoClientTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {"XANO_API_BASE_URL": "https://xano.test/api:test", "XANO_AUTH_API_BASE_URL": ""},
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def make_client(self, handler):
        return XanoClient(token="jwt", transport=httpx.MockTransport(handler))

    def test_routes_and_bodies(self):
        calls = []

        def handler(request):
            body = json.loads(request.read()) if request.content else None
            calls.append((request.method, request.url.path, dict(request.url.params), body))
            if request.method == "GET" and request.url.path.endswith("/motos"):
                return httpx.Response(200, json=[DETALHE])
            return httpx.Response(200, json=DETALHE)

        with self.make_client(handler) as client:
            client.list_motos_estoque(status="RESERVADA", id_modelo=3)
            client.get_moto_estoque(9)
            client.cadastrar_moto_estoque(unidade())
            client.atualizar_moto_estoque(9, MotoEstoqueUpdate(cor="Laranja Harley"))
            client.reservar_moto(9, ReservaMotoCreate(id_cliente=5, dias_validade=10))
            client.cancelar_reserva_moto(9, CancelamentoReservaMoto(motivo="Desistiu"))

        self.assertEqual(
            [(method, path) for method, path, _, _ in calls],
            [
                ("GET", "/api:test/motos"),
                ("GET", "/api:test/motos/9"),
                ("POST", "/api:test/motos"),
                ("PATCH", "/api:test/motos/9"),
                ("POST", "/api:test/motos/9/reserva"),
                ("POST", "/api:test/motos/9/reserva/cancelar"),
            ],
        )
        self.assertEqual(calls[0][2], {"status": "RESERVADA", "id_modelo": "3"})
        self.assertEqual(calls[2][3]["chassi"], "1HD1KTP19RB600001")
        self.assertEqual(calls[3][3], {"cor": "Laranja Harley"})
        self.assertEqual(calls[4][3], {"id_cliente": 5, "dias_validade": 10})
        self.assertEqual(calls[5][3], {"motivo": "Desistiu"})

    def test_forbidden_cancellation_is_a_permission_error(self):
        def handler(request):
            return httpx.Response(403, json={"message": "Somente quem reservou..."})

        with self.make_client(handler) as client, self.assertRaises(XanoPermissionError):
            client.cancelar_reserva_moto(9, CancelamentoReservaMoto(motivo="x"))


if __name__ == "__main__":
    unittest.main()
