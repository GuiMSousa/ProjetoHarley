"""Change 10: DTOs of the consolidated view and the GET financeiro/resumo request."""

import os
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from Projeto_HarleyStore.services.financeiro import (
    FUSO_LOJA,
    NATUREZA_POR_TIPO,
    PERIODO_MAXIMO_DIAS,
    TIPO_LABELS,
    OperacaoFinanceira,
    PeriodoFinanceiro,
    ResumoFinanceiro,
)
from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoClient,
    XanoPermissionError,
    XanoRateLimitError,
    XanoResponseError,
    XanoValidationError,
)


RESUMO = {
    "inicio": 1790823600000,
    "fim": 1791601199999,
    "receitas": 186250.0,
    "despesas": 8200.0,
    "saldo": 178050.0,
    "por_tipo": [
        {"tipo": "MOTO", "natureza": "RECEITA", "quantidade": 1, "valor": 185000.0},
        {"tipo": "ORDEM_SERVICO", "natureza": "RECEITA", "quantidade": 1, "valor": 1250.0},
        {"tipo": "ENTRADA_MERCADORIA", "natureza": "DESPESA", "quantidade": 1, "valor": 8200.0},
    ],
    "operacoes": [
        {
            "origem": "TRANSACAO", "id": 41, "tipo": "ORDEM_SERVICO", "natureza": "RECEITA",
            "data": 1791990000000, "valor": 1250.0, "contraparte": "Ana Souza", "funcionario": "João",
            "id_os": 87, "id_moto_cliente": 30, "modelo": "Street Glide", "placa": None,
            "id_entrada": None, "numero_documento": None,
        },
        {
            "origem": "ENTRADA", "id": 12, "tipo": "ENTRADA_MERCADORIA", "natureza": "DESPESA",
            "data": 1791900000000, "valor": 8200.0, "contraparte": "Distribuidora", "funcionario": None,
            "id_os": None, "id_moto_cliente": None, "modelo": None, "placa": None,
            "id_entrada": 12, "numero_documento": "NF-5521",
        },
    ],
    "total_operacoes": 2,
    "truncado": False,
}


class PeriodoTests(unittest.TestCase):
    def test_params_cover_whole_days_in_the_store_time_zone(self):
        periodo = PeriodoFinanceiro(inicio=date(2026, 10, 1), fim=date(2026, 10, 9))
        params = periodo.params()
        inicio = datetime.fromtimestamp(params["inicio"] / 1000, FUSO_LOJA)
        fim = datetime.fromtimestamp(params["fim"] / 1000, FUSO_LOJA)
        self.assertEqual(inicio, datetime(2026, 10, 1, 0, 0, tzinfo=FUSO_LOJA))
        self.assertEqual(fim, datetime(2026, 10, 9, 23, 59, 59, 999000, tzinfo=FUSO_LOJA))
        # UTC-3 fixed: 00:00 in the store is 03:00 UTC.
        self.assertEqual(datetime.fromtimestamp(params["inicio"] / 1000, timezone.utc).hour, 3)

    def test_single_day_and_the_366_day_limit(self):
        dia = PeriodoFinanceiro(inicio=date(2026, 2, 28), fim=date(2026, 2, 28)).params()
        self.assertEqual(dia["fim"] - dia["inicio"], 24 * 60 * 60 * 1000 - 1)
        limite = PeriodoFinanceiro(inicio=date(2025, 10, 9), fim=date(2025, 10, 9) + timedelta(days=PERIODO_MAXIMO_DIAS - 1))
        span = limite.params()["fim"] - limite.params()["inicio"]
        # The same rule as Xano: at most 366 days in milliseconds.
        self.assertLessEqual(span, PERIODO_MAXIMO_DIAS * 24 * 60 * 60 * 1000)

    def test_rejects_inverted_or_longer_periods(self):
        for inicio, fim, message in (
            (date(2026, 10, 9), date(2026, 10, 1), "O fim do período deve ser igual ou posterior ao início."),
            (date(2025, 1, 1), date(2026, 1, 2), "O período pode ter no máximo 366 dias."),
        ):
            with self.subTest(inicio=inicio, fim=fim), self.assertRaises(ValidationError) as context:
                PeriodoFinanceiro(inicio=inicio, fim=fim)
            self.assertIn(message, str(context.exception))


class DtoTests(unittest.TestCase):
    def test_summary_parses_millisecond_timestamps_and_decimals(self):
        resumo = ResumoFinanceiro.model_validate(RESUMO)
        self.assertEqual((resumo.receitas, resumo.saldo), (Decimal("186250.0"), Decimal("178050.0")))
        self.assertEqual(resumo.operacoes[0].data.year, 2026)
        self.assertEqual([total.tipo for total in resumo.por_tipo], ["MOTO", "ORDEM_SERVICO", "ENTRADA_MERCADORIA"])

    def test_empty_period_defaults(self):
        resumo = ResumoFinanceiro.model_validate({"inicio": 1790823600000, "fim": 1791601199999})
        self.assertEqual((resumo.receitas, resumo.operacoes, resumo.truncado), (Decimal("0"), [], False))

    def test_operation_accepts_null_references_and_rejects_unknown_types(self):
        operacao = OperacaoFinanceira.model_validate({**RESUMO["operacoes"][1], "contraparte": None})
        self.assertIsNone(operacao.contraparte)
        with self.assertRaises(ValidationError):
            OperacaoFinanceira.model_validate({**RESUMO["operacoes"][1], "tipo": "OUTRO"})

    def test_labels_and_nature_cover_every_type(self):
        self.assertEqual(set(TIPO_LABELS), set(NATUREZA_POR_TIPO))
        self.assertEqual(
            {tipo for tipo, natureza in NATUREZA_POR_TIPO.items() if natureza == "DESPESA"},
            {"COMPRA", "ENTRADA_MERCADORIA"},
        )


class ResumoClientTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {"XANO_API_BASE_URL": "https://xano.test/api:harley", "XANO_AUTH_API_BASE_URL": ""},
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.periodo = PeriodoFinanceiro(inicio=date(2026, 10, 1), fim=date(2026, 10, 9))

    def respond(self, response):
        requests = []

        def handler(request):
            requests.append(request)
            return response

        return requests, XanoClient(token="jwt", transport=httpx.MockTransport(handler))

    def test_get_sends_the_period_as_milliseconds_with_the_token(self):
        requests, client = self.respond(httpx.Response(200, json=RESUMO))
        with client:
            resumo = client.resumo_financeiro(self.periodo)
        (request,) = requests
        self.assertEqual((request.method, request.url.path), ("GET", "/api:harley/financeiro/resumo"))
        self.assertEqual(request.headers["Authorization"], "Bearer jwt")
        self.assertEqual(dict(request.url.params), {key: str(value) for key, value in self.periodo.params().items()})
        self.assertEqual(resumo.total_operacoes, 2)

    def test_status_errors_are_typed(self):
        for response, error in (
            (httpx.Response(400, json={"message": "O período pode ter no máximo 366 dias."}), XanoValidationError),
            (httpx.Response(401, json={}), XanoAuthenticationError),
            (httpx.Response(403, json={}), XanoPermissionError),
            (httpx.Response(429, json={}), XanoRateLimitError),
            (httpx.Response(200, json={"receitas": "x"}), XanoResponseError),
        ):
            _, client = self.respond(response)
            with self.subTest(status=response.status_code), client, self.assertRaises(error):
                client.resumo_financeiro(self.periodo)

    def test_client_has_no_transaction_writer(self):
        writers = [name for name in dir(XanoClient) if "transac" in name.lower()]
        self.assertEqual(writers, [])


if __name__ == "__main__":
    unittest.main()
