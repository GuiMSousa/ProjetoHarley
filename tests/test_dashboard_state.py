"""Change 12: KPI cards of the overview, filtered by role like the Xano permissions."""

import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from reflex.state import State

from Projeto_HarleyStore.dashboard_state import DashboardState, kpis_visiveis, montar_kpis
from Projeto_HarleyStore.services.xano_client import XanoRateLimitError

from tests.event_runner import run_event


ORDENS = [SimpleNamespace(status=status) for status in ("ABERTA", "ABERTA", "EM_ANDAMENTO", "CONCLUIDA", "CANCELADA")]
MOTOS = [SimpleNamespace(status=status) for status in ("DISPONIVEL", "DISPONIVEL", "RESERVADA", "VENDIDA")]
RESUMO = SimpleNamespace(
    receitas=Decimal("236789.70"),
    por_tipo=[
        SimpleNamespace(tipo="MOTO", quantidade=1, valor=Decimal("185000")),
        SimpleNamespace(tipo="BALCAO", quantidade=3, valor=Decimal("389.70")),
    ],
)


class KpiRulesTests(unittest.TestCase):
    def test_financial_kpis_are_the_managers_only(self):
        self.assertEqual(kpis_visiveis("GERENTE"), ["faturamento", "motos", "os", "balcao"])
        self.assertEqual(kpis_visiveis("VENDEDOR"), ["motos", "os"])
        self.assertEqual(kpis_visiveis("MECANICO"), ["os"])
        self.assertEqual(kpis_visiveis(""), [])

    def test_values_and_details(self):
        kpis = montar_kpis(ORDENS, MOTOS, RESUMO)
        self.assertEqual((kpis["os"], kpis["os_detalhe"]), ("3", "2 abertas · 1 em andamento"))
        self.assertEqual((kpis["motos"], kpis["motos_detalhe"]), ("3", "2 disponíveis · 1 reservadas"))
        self.assertEqual(kpis["faturamento"], "R$ 236.789,70")
        self.assertEqual((kpis["balcao"], kpis["balcao_detalhe"]), ("3", "R$ 389,70 no mês"))

    def test_sources_the_role_cannot_read_are_left_out(self):
        self.assertEqual(set(montar_kpis(ORDENS, None, None)), {"os", "os_detalhe"})
        sem_balcao = montar_kpis(None, None, SimpleNamespace(receitas=Decimal("0"), por_tipo=[]))
        self.assertEqual((sem_balcao["balcao"], sem_balcao["balcao_detalhe"]), ("0", "R$ 0,00 no mês"))


class DashboardStateTests(unittest.TestCase):
    def make_state(self, role):
        root = State(_reflex_internal_init=True)
        state = root.get_substate(DashboardState.get_full_name().split("."))
        state.auth_token = "token"
        state.is_authenticated = True
        state.employee_role = role
        return state

    def patched_client(self):
        patcher = patch("Projeto_HarleyStore.dashboard_state.XanoClient")
        client_class = patcher.start()
        self.addCleanup(patcher.stop)
        client = MagicMock()
        client_class.return_value.__enter__.return_value = client
        client.list_ordens_servico.return_value = ORDENS
        client.list_motos_estoque.return_value = MOTOS
        client.resumo_financeiro.return_value = RESUMO
        return client

    def test_each_role_reads_only_what_xano_allows(self):
        for role, chamadas in (
            ("GERENTE", (True, True, True)),
            ("VENDEDOR", (True, True, False)),
            ("MECANICO", (True, False, False)),
        ):
            with self.subTest(role=role):
                client = self.patched_client()
                state = self.make_state(role)
                run_event(DashboardState.load_dashboard, state)
                self.assertEqual(
                    (client.list_ordens_servico.called, client.list_motos_estoque.called, client.resumo_financeiro.called),
                    chamadas,
                )
                self.assertEqual(state.kpis_do_perfil, kpis_visiveis(role))

    def test_loading_state_reaches_the_browser_before_xano(self):
        client = self.patched_client()
        state = self.make_state("GERENTE")
        steps = DashboardState.load_dashboard.fn(state)
        next(steps)
        self.assertTrue(state.is_loading_kpis)
        client.list_ordens_servico.assert_not_called()
        with self.assertRaises(StopIteration):
            next(steps)
        self.assertFalse(state.is_loading_kpis)
        self.assertEqual(state.kpis["faturamento"], "R$ 236.789,70")

    def test_errors_are_visible_and_anonymous_visitors_load_nothing(self):
        client = self.patched_client()
        client.list_ordens_servico.side_effect = XanoRateLimitError("429")
        state = self.make_state("MECANICO")
        run_event(DashboardState.load_dashboard, state)
        self.assertIn("Muitas requisições", state.kpi_error)
        self.assertEqual(state.kpis, {})
        anonimo = self.make_state("GERENTE")
        anonimo.is_authenticated = False
        client.reset_mock()
        run_event(DashboardState.load_dashboard, anonimo)
        client.list_ordens_servico.assert_not_called()


if __name__ == "__main__":
    unittest.main()
