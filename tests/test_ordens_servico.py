import json
import os
import unittest
from itertools import product
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from Projeto_HarleyStore.services.ordens_servico import (
    TRANSICOES_OS,
    OrdemServicoCreate,
    OrdemServicoDetalhe,
    OrdemServicoResumo,
    TransicaoStatusOS,
)
from Projeto_HarleyStore.services.xano_client import (
    XanoClient,
    XanoNotFoundError,
    XanoPermissionError,
    XanoValidationError,
)


STATUSES = ("ABERTA", "EM_ANDAMENTO", "CONCLUIDA", "CANCELADA")
VALID_TRANSITIONS = {
    ("ABERTA", "EM_ANDAMENTO"),
    ("ABERTA", "CANCELADA"),
    ("EM_ANDAMENTO", "CONCLUIDA"),
    ("EM_ANDAMENTO", "CANCELADA"),
}

DETAIL_RESPONSE = {
    "id": 31,
    "status": "EM_ANDAMENTO",
    "id_moto_cliente": 12,
    "data_abertura": 1790000000000,
    "data_inicio": 1790000600000,
    "tipo_servico": "CORRETIVA",
    "descricao_problema": "Ruído na embreagem",
    "quilometragem": 18350,
    "id_cliente": 5,
    "nome_cliente": "Ana Souza",
    "placa": "ABC1D23",
    "modelo": "Street Glide",
    "id_funcionario": 2,
    "nome_funcionario": "Carlos",
    "id_mecanico": 4,
    "nome_mecanico": "Bruno",
    "historico": [
        {"id": 1, "status_anterior": None, "status_novo": "ABERTA", "id_funcionario": 2,
         "nome_funcionario": "Carlos", "created_at": 1790000000000, "observacao": None},
        {"id": 2, "status_anterior": "ABERTA", "status_novo": "EM_ANDAMENTO", "id_funcionario": 4,
         "nome_funcionario": "Bruno", "created_at": 1790000600000},
    ],
    "itens": [],
}


def abertura(**overrides):
    data = {
        "id_moto_cliente": 12,
        "id_mecanico": 4,
        "tipo_servico": "CORRETIVA",
        "descricao_problema": "  Ruído na embreagem  ",
        "quilometragem": 18350,
    }
    data.update(overrides)
    return OrdemServicoCreate(**data)


class OrdemServicoDtoTests(unittest.TestCase):
    def test_valid_opening_strips_description(self):
        self.assertEqual(abertura().descricao_problema, "Ruído na embreagem")

    def test_opening_rejects_invalid_fields(self):
        invalid = [
            {"tipo_servico": "REVISAO"},
            {"descricao_problema": "   "},
            {"quilometragem": -1},
            {"id_moto_cliente": 0},
            {"id_mecanico": 0},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                abertura(**overrides)

    def test_mechanic_and_mileage_are_optional(self):
        ordem = abertura(id_mecanico=None, quilometragem=None)
        self.assertIsNone(ordem.id_mecanico)
        self.assertIsNone(ordem.quilometragem)

    def test_transition_table_mirrors_the_state_machine(self):
        for atual, novo in product(STATUSES, STATUSES):
            with self.subTest(atual=atual, novo=novo):
                observacao = "Cliente desistiu" if novo == "CANCELADA" else None
                if (atual, novo) in VALID_TRANSITIONS:
                    TransicaoStatusOS(status_atual=atual, status_novo=novo, observacao=observacao)
                else:
                    with self.assertRaises(ValidationError):
                        TransicaoStatusOS(status_atual=atual, status_novo=novo, observacao=observacao)
        self.assertEqual(
            {(a, n) for a, targets in TRANSICOES_OS.items() for n in targets},
            VALID_TRANSITIONS,
        )

    def test_cancellation_requires_reason(self):
        for observacao in (None, "", "   "):
            with self.subTest(observacao=observacao), self.assertRaises(ValidationError) as context:
                TransicaoStatusOS(status_atual="ABERTA", status_novo="CANCELADA", observacao=observacao)
            self.assertIn("motivo", str(context.exception))

    def test_closed_order_cannot_be_reopened(self):
        with self.assertRaises(ValidationError) as context:
            TransicaoStatusOS(status_atual="CONCLUIDA", status_novo="ABERTA")
        self.assertIn("encerrada", str(context.exception))

    def test_detail_parses_timeline_and_legacy_rows(self):
        detalhe = OrdemServicoDetalhe.model_validate(DETAIL_RESPONSE)
        self.assertEqual(detalhe.historico[0].status_anterior, None)
        self.assertEqual(detalhe.historico[1].status_novo, "EM_ANDAMENTO")
        self.assertEqual(detalhe.data_abertura.year, 2026)
        legacy = OrdemServicoResumo.model_validate(
            {"id": 1, "status": "CONCLUIDA", "id_moto_cliente": 3}
        )
        self.assertIsNone(legacy.tipo_servico)
        self.assertIsNone(legacy.id_mecanico)


class OrdemServicoClientTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {"XANO_API_BASE_URL": "https://xano.test/api:test", "XANO_AUTH_API_BASE_URL": ""},
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    def make_client(self, handler):
        return XanoClient(token="jwt", transport=httpx.MockTransport(handler))

    def test_opening_sends_only_opening_fields(self):
        captured = {}

        def handler(request):
            captured["method"] = request.method
            captured["path"] = request.url.path
            captured["body"] = json.loads(request.read())
            return httpx.Response(200, json=DETAIL_RESPONSE)

        with self.make_client(handler) as client:
            detalhe = client.abrir_ordem_servico(abertura(id_mecanico=None))

        self.assertEqual((captured["method"], captured["path"]), ("POST", "/api:test/ordens_servico"))
        self.assertEqual(
            set(captured["body"]),
            {"id_moto_cliente", "tipo_servico", "descricao_problema", "quilometragem"},
        )
        for forbidden in ("status", "id_funcionario", "id_cliente", "data_abertura", "id_mecanico"):
            self.assertNotIn(forbidden, captured["body"])
        self.assertIsInstance(detalhe, OrdemServicoDetalhe)

    def test_transition_posts_expected_and_new_status(self):
        captured = {}

        def handler(request):
            captured["path"] = request.url.path
            captured["body"] = json.loads(request.read())
            return httpx.Response(200, json=DETAIL_RESPONSE)

        with self.make_client(handler) as client:
            client.transicionar_ordem_servico(
                31, TransicaoStatusOS(status_atual="ABERTA", status_novo="EM_ANDAMENTO")
            )

        self.assertEqual(captured["path"], "/api:test/ordens_servico/31/status")
        self.assertEqual(
            captured["body"],
            {"status_atual": "ABERTA", "status_novo": "EM_ANDAMENTO", "observacao": None},
        )

    def test_list_sends_only_given_filters(self):
        queries = []

        def handler(request):
            queries.append(dict(request.url.params))
            return httpx.Response(200, json=[DETAIL_RESPONSE])

        with self.make_client(handler) as client:
            client.list_ordens_servico()
            client.list_ordens_servico(status="ABERTA")
            ordens = client.list_ordens_servico(id_moto_cliente=12)

        self.assertEqual(queries, [{}, {"status": "ABERTA"}, {"id_moto_cliente": "12"}])
        self.assertEqual(ordens[0].nome_mecanico, "Bruno")

    def test_detail_and_mechanics_use_read_endpoints(self):
        paths = []

        def handler(request):
            paths.append(request.url.path)
            if request.url.path.endswith("mecanicos"):
                return httpx.Response(200, json=[{"id": 4, "nome_funcionario": "Bruno"}])
            return httpx.Response(200, json=DETAIL_RESPONSE)

        with self.make_client(handler) as client:
            client.get_ordem_servico(31)
            mecanicos = client.list_mecanicos()

        self.assertEqual(paths, ["/api:test/ordens_servico/31", "/api:test/oficina/mecanicos"])
        self.assertEqual(mecanicos[0].nome_funcionario, "Bruno")

    def test_errors_are_typed(self):
        cases = {
            400: XanoValidationError,
            403: XanoPermissionError,
            404: XanoNotFoundError,
        }
        for status_code, error_type in cases.items():
            with self.subTest(status_code=status_code):
                def handler(request, status_code=status_code):
                    return httpx.Response(status_code, json={"message": "Transição de status inválida."})

                with self.make_client(handler) as client, self.assertRaises(error_type):
                    client.transicionar_ordem_servico(
                        31, TransicaoStatusOS(status_atual="ABERTA", status_novo="EM_ANDAMENTO")
                    )


if __name__ == "__main__":
    unittest.main()
