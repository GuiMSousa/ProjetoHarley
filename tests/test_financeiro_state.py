"""Change 10: rules and flows of the /financeiro state."""

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from reflex.istate.data import RouterData
from reflex.state import State

from Projeto_HarleyStore.financeiro_state import (
    FILTRO_TODOS,
    MINUS,
    FinanceiroFormError,
    FinanceiroState,
    atalho_periodo,
    build_periodo,
    descricao_operacao,
    filtrar_operacoes,
    operacao_row,
    ordenar_por_tipo,
    periodo_padrao,
    resumo_row,
    tipo_row,
)
from Projeto_HarleyStore.services.financeiro import OperacaoFinanceira, ResumoFinanceiro, TotalPorTipo
from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoPermissionError,
    XanoRateLimitError,
)

from tests.event_runner import run_event
from tests.test_financeiro import RESUMO


def operacao(**overrides):
    data = {
        "origem": "TRANSACAO",
        "id": 41,
        "tipo": "ORDEM_SERVICO",
        "natureza": "RECEITA",
        "data": 1791990000000,
        "valor": "1250.00",
        "contraparte": "Ana Souza",
        "funcionario": "João Mecânico",
        "id_os": 87,
        "modelo": "Street Glide",
        "placa": "ABC1D23",
    }
    data.update(overrides)
    return OperacaoFinanceira(**data)


class PeriodoRulesTests(unittest.TestCase):
    def test_default_period_is_the_current_month_up_to_today(self):
        self.assertEqual(periodo_padrao(date(2026, 10, 9)), (date(2026, 10, 1), date(2026, 10, 9)))

    def test_shortcuts_cross_month_and_year_boundaries(self):
        self.assertEqual(atalho_periodo("MES_ANTERIOR", date(2026, 1, 15)), (date(2025, 12, 1), date(2025, 12, 31)))
        self.assertEqual(atalho_periodo("MES_ANTERIOR", date(2026, 3, 31)), (date(2026, 2, 1), date(2026, 2, 28)))
        self.assertEqual(atalho_periodo("ULTIMOS_30_DIAS", date(2026, 3, 1)), (date(2026, 1, 31), date(2026, 3, 1)))
        self.assertEqual(atalho_periodo("MES_ATUAL", date(2026, 10, 9)), (date(2026, 10, 1), date(2026, 10, 9)))

    def test_build_periodo_gives_readable_messages(self):
        self.assertEqual(build_periodo("2026-10-01", "2026-10-09").fim, date(2026, 10, 9))
        for inicio, fim, message in (
            ("", "2026-10-09", "Informe a data inicial do período."),
            ("2026-10-01", "", "Informe a data final do período."),
            ("2026-10-09", "2026-10-01", "O fim do período deve ser igual ou posterior ao início."),
            ("2025-01-01", "2026-01-02", "O período pode ter no máximo 366 dias."),
        ):
            with self.subTest(inicio=inicio, fim=fim), self.assertRaises(FinanceiroFormError) as context:
                build_periodo(inicio, fim)
            self.assertEqual(str(context.exception), message)


class OperacaoRulesTests(unittest.TestCase):
    def test_description_by_type(self):
        self.assertEqual(descricao_operacao(operacao()), "OS #87 · Street Glide")
        self.assertEqual(
            descricao_operacao(operacao(tipo="MOTO", id_os=None)),
            "Venda de moto · Street Glide · ABC1D23",
        )
        self.assertEqual(
            descricao_operacao(
                operacao(origem="ENTRADA", id=12, tipo="ENTRADA_MERCADORIA", natureza="DESPESA", numero_documento="NF-5521")
            ),
            "Entrada NF-5521",
        )
        # Rows created by the generic CRUD before Change 10 have no business reference.
        self.assertEqual(descricao_operacao(operacao(tipo="BALCAO", id_os=None, id=7)), "Transação #7")
        self.assertEqual(descricao_operacao(operacao(id_os=None, id=8)), "Transação #8")

    def test_rows_sign_expenses_and_keep_revenue_plain(self):
        receita = operacao_row(operacao())
        despesa = operacao_row(operacao(origem="ENTRADA", tipo="ENTRADA_MERCADORIA", natureza="DESPESA", valor="8200"))
        self.assertEqual((receita["valor"], receita["tipo_label"], receita["natureza_label"]), ("R$ 1.250,00", "Serviço de oficina", "Receita"))
        self.assertEqual(despesa["valor"], f"{MINUS} R$ 8.200,00")
        self.assertEqual(operacao_row(operacao(contraparte=None))["contraparte"], "—")

    def test_types_are_ordered_revenue_first_by_amount(self):
        totais = [
            TotalPorTipo(tipo="ENTRADA_MERCADORIA", natureza="DESPESA", quantidade=3, valor=Decimal("18250.5")),
            TotalPorTipo(tipo="ORDEM_SERVICO", natureza="RECEITA", quantidade=12, valor=Decimal("50400")),
            TotalPorTipo(tipo="MOTO", natureza="RECEITA", quantidade=1, valor=Decimal("185000")),
        ]
        self.assertEqual([total.tipo for total in ordenar_por_tipo(totais)], ["MOTO", "ORDEM_SERVICO", "ENTRADA_MERCADORIA"])
        self.assertEqual(tipo_row(totais[0])["valor"], f"{MINUS} R$ 18.250,50")

    def test_summary_flags_negative_balance_and_truncation(self):
        negativo = resumo_row(ResumoFinanceiro.model_validate({**RESUMO, "saldo": -500.0}))
        self.assertEqual((negativo["saldo"], negativo["saldo_negativo"]), (f"{MINUS} R$ 500,00", "true"))
        cheio = resumo_row(ResumoFinanceiro.model_validate({**RESUMO, "total_operacoes": 812, "truncado": True}))
        self.assertIn("2 operações mais recentes de 812", cheio["aviso_truncado"])
        self.assertEqual(resumo_row(ResumoFinanceiro.model_validate(RESUMO))["aviso_truncado"], "")

    def test_local_filter_by_type_and_search(self):
        rows = [
            operacao_row(operacao()),
            operacao_row(operacao(id=2, tipo="MOTO", id_os=None, contraparte="Bruno Lima")),
            operacao_row(operacao(origem="ENTRADA", id=3, tipo="ENTRADA_MERCADORIA", natureza="DESPESA", numero_documento="NF-1", contraparte="Distribuidora São Paulo")),
        ]
        self.assertEqual(len(filtrar_operacoes(rows, FILTRO_TODOS, "")), 3)
        self.assertEqual([row["chave"] for row in filtrar_operacoes(rows, "MOTO", "")], ["TRANSACAO-2"])
        self.assertEqual([row["chave"] for row in filtrar_operacoes(rows, FILTRO_TODOS, "sao paulo")], ["ENTRADA-3"])
        self.assertEqual(filtrar_operacoes(rows, "MOTO", "distribuidora"), [])


class FinanceiroStateTests(unittest.TestCase):
    def make_state(self, role="GERENTE"):
        root = State(_reflex_internal_init=True)
        state = root.get_substate(FinanceiroState.get_full_name().split("."))
        root.router = RouterData.from_router_data({"pathname": "/financeiro", "query": {}, "asPath": "/financeiro", "headers": {}})
        state.auth_token = "token"
        state.is_authenticated = True
        state.employee_role = role
        return state

    def patched_client(self, resumo=RESUMO):
        patcher = patch("Projeto_HarleyStore.financeiro_state.XanoClient")
        client_class = patcher.start()
        self.addCleanup(patcher.stop)
        client = MagicMock()
        client_class.return_value.__enter__.return_value = client
        client.resumo_financeiro.return_value = ResumoFinanceiro.model_validate(resumo)
        return client_class, client

    @patch("Projeto_HarleyStore.financeiro_state.hoje_loja", return_value=date(2026, 10, 9))
    def test_manager_loads_the_current_month(self, _hoje):
        _, client = self.patched_client()
        state = self.make_state()
        run_event(FinanceiroState.load_financeiro, state)
        (periodo,) = client.resumo_financeiro.call_args.args
        self.assertEqual((periodo.inicio, periodo.fim), (date(2026, 10, 1), date(2026, 10, 9)))
        self.assertEqual((state.inicio, state.fim), ("2026-10-01", "2026-10-09"))
        self.assertEqual(state.resumo["receitas"], "R$ 186.250,00")
        self.assertEqual([row["tipo"] for row in state.por_tipo], ["MOTO", "ORDEM_SERVICO", "ENTRADA_MERCADORIA"])
        self.assertEqual(len(state.visible_rows), 2)
        self.assertEqual([option["value"] for option in state.tipo_options], [FILTRO_TODOS, "MOTO", "ORDEM_SERVICO", "ENTRADA_MERCADORIA"])
        self.assertFalse(state.is_loading_resumo)

    def test_other_roles_never_call_xano(self):
        for role in ("VENDEDOR", "MECANICO"):
            client_class, _ = self.patched_client()
            state = self.make_state(role)
            run_event(FinanceiroState.load_financeiro, state)
            with self.subTest(role=role):
                client_class.assert_not_called()

    def test_invalid_period_is_rejected_locally(self):
        client_class, _ = self.patched_client()
        state = self.make_state()
        run_event(FinanceiroState.set_inicio, state, "2026-10-09")
        run_event(FinanceiroState.set_fim, state, "2026-10-01")
        run_event(FinanceiroState.aplicar_periodo, state)
        self.assertEqual(state.periodo_error, "O fim do período deve ser igual ou posterior ao início.")
        client_class.assert_not_called()

    @patch("Projeto_HarleyStore.financeiro_state.hoje_loja", return_value=date(2026, 1, 15))
    def test_shortcut_sets_the_period_and_reloads(self, _hoje):
        _, client = self.patched_client()
        state = self.make_state()
        run_event(FinanceiroState.usar_atalho, state, "MES_ANTERIOR")
        self.assertEqual((state.inicio, state.fim), ("2025-12-01", "2025-12-31"))
        client.resumo_financeiro.assert_called_once()
        run_event(FinanceiroState.usar_atalho, state, "INEXISTENTE")
        client.resumo_financeiro.assert_called_once()

    def test_type_filter_and_search_are_local(self):
        _, client = self.patched_client()
        state = self.make_state()
        state.inicio, state.fim = "2026-10-01", "2026-10-09"
        run_event(FinanceiroState.aplicar_periodo, state)
        run_event(FinanceiroState.set_filtro_tipo, state, "ENTRADA_MERCADORIA")
        self.assertEqual([row["descricao"] for row in state.visible_rows], ["Entrada NF-5521"])
        run_event(FinanceiroState.set_filtro_tipo, state, FILTRO_TODOS)
        run_event(FinanceiroState.set_busca, state, "ana")
        self.assertEqual([row["descricao"] for row in state.visible_rows], ["OS #87 · Street Glide"])
        client.resumo_financeiro.assert_called_once()

    def test_filter_resets_when_the_type_disappears(self):
        _, client = self.patched_client()
        state = self.make_state()
        state.inicio, state.fim = "2026-10-01", "2026-10-09"
        state.filtro_tipo = "BALCAO"
        run_event(FinanceiroState.aplicar_periodo, state)
        self.assertEqual(state.filtro_tipo, FILTRO_TODOS)

    def test_errors_are_visible_and_rate_limit_is_explained(self):
        for error, expected in (
            (XanoRateLimitError("x", status_code=429), "Muitas requisições"),
            (XanoPermissionError("x", status_code=403), "permissão"),
        ):
            _, client = self.patched_client()
            client.resumo_financeiro.side_effect = error
            state = self.make_state()
            state.inicio, state.fim = "2026-10-01", "2026-10-09"
            run_event(FinanceiroState.aplicar_periodo, state)
            with self.subTest(error=type(error).__name__):
                self.assertIn(expected, state.list_error)
                self.assertFalse(state.is_loading_resumo)
                self.assertTrue(state.is_authenticated)

    def test_expired_session_clears_the_session(self):
        _, client = self.patched_client()
        client.resumo_financeiro.side_effect = XanoAuthenticationError("expired", status_code=401)
        state = self.make_state()
        state.inicio, state.fim = "2026-10-01", "2026-10-09"
        run_event(FinanceiroState.aplicar_periodo, state)
        self.assertFalse(state.is_authenticated)

    def test_busy_state_reaches_the_browser_before_xano(self):
        _, client = self.patched_client()
        state = self.make_state()
        state.inicio, state.fim = "2026-10-01", "2026-10-09"
        steps = FinanceiroState.aplicar_periodo.fn(state)
        next(steps)
        self.assertTrue(state.is_loading_resumo)
        client.resumo_financeiro.assert_not_called()
        with self.assertRaises(StopIteration):
            next(steps)
        self.assertFalse(state.is_loading_resumo)


if __name__ == "__main__":
    unittest.main()
