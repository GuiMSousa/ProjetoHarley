"""Reflex state of the overview (/): executive KPI cards filtered by role (Change 12)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import reflex as rx

from Projeto_HarleyStore.auth import AuthState
from Projeto_HarleyStore.feedback import error_feedback
from Projeto_HarleyStore.formatting import format_currency
from Projeto_HarleyStore.services.financeiro import FUSO_LOJA, PeriodoFinanceiro, ResumoFinanceiro
from Projeto_HarleyStore.services.motos import MotoEstoque
from Projeto_HarleyStore.services.ordens_servico import OrdemServicoResumo
from Projeto_HarleyStore.services.xano_client import XanoAuthenticationError, XanoClient, XanoError


# Who sees each KPI. It mirrors the Xano permissions: financial data (revenue and counter sales)
# is the manager's only, stock motorcycles are the sellers' and every role reads service orders.
KPI_ROLES: dict[str, frozenset[str]] = {
    "faturamento": frozenset({"GERENTE"}),
    "motos": frozenset({"GERENTE", "VENDEDOR"}),
    "os": frozenset({"GERENTE", "VENDEDOR", "MECANICO"}),
    "balcao": frozenset({"GERENTE"}),
}


def kpis_visiveis(role: str) -> list[str]:
    return [chave for chave, roles in KPI_ROLES.items() if role in roles]


def montar_kpis(
    ordens: list[OrdemServicoResumo] | None,
    motos: list[MotoEstoque] | None,
    resumo: ResumoFinanceiro | None,
) -> dict[str, str]:
    """Value and detail line of each KPI card; a source the role cannot read is ``None``."""
    kpis: dict[str, str] = {}
    if ordens is not None:
        abertas = sum(1 for ordem in ordens if ordem.status == "ABERTA")
        andamento = sum(1 for ordem in ordens if ordem.status == "EM_ANDAMENTO")
        kpis["os"] = str(abertas + andamento)
        kpis["os_detalhe"] = f"{abertas} abertas · {andamento} em andamento"
    if motos is not None:
        disponiveis = sum(1 for moto in motos if moto.status == "DISPONIVEL")
        reservadas = sum(1 for moto in motos if moto.status == "RESERVADA")
        kpis["motos"] = str(disponiveis + reservadas)
        kpis["motos_detalhe"] = f"{disponiveis} disponíveis · {reservadas} reservadas"
    if resumo is not None:
        kpis["faturamento"] = format_currency(resumo.receitas)
        kpis["faturamento_detalhe"] = "Receitas do mês até hoje"
        balcao = next((total for total in resumo.por_tipo if total.tipo == "BALCAO"), None)
        kpis["balcao"] = str(balcao.quantidade if balcao else 0)
        kpis["balcao_detalhe"] = f"{format_currency(balcao.valor if balcao else Decimal(0))} no mês"
    return kpis


class DashboardState(AuthState):
    """KPI cards of the overview; each role loads only what Xano lets it read."""

    kpis: dict[str, str] = {}
    is_loading_kpis: bool = False
    kpi_error: str = ""

    @rx.var
    def kpis_do_perfil(self) -> list[str]:
        return kpis_visiveis(self.employee_role)

    @rx.event
    def load_dashboard(self):
        if self.is_loading_kpis or not self.is_authenticated:
            return None
        visiveis = kpis_visiveis(self.employee_role)
        if not visiveis:
            return None
        self.is_loading_kpis = True
        self.kpi_error = ""
        yield  # render the busy state before the Xano call
        erros: list[XanoError] = []

        def buscar(carregar):
            # Each source fails alone (Change 15): its card shows "—" and the others keep their values.
            try:
                return carregar()
            except XanoAuthenticationError:
                raise
            except XanoError as error:
                erros.append(error)
                return None

        try:
            with XanoClient(token=self.auth_token) as client:
                ordens = buscar(client.list_ordens_servico) if "os" in visiveis else None
                motos = buscar(client.list_motos_estoque) if "motos" in visiveis else None
                resumo = None
                if "faturamento" in visiveis:
                    hoje = datetime.now(FUSO_LOJA).date()
                    periodo = PeriodoFinanceiro(inicio=hoje.replace(day=1), fim=hoje)
                    resumo = buscar(lambda: client.resumo_financeiro(periodo))
            self.kpis = montar_kpis(ordens, motos, resumo)
            self.kpi_error = error_feedback(erros[0]) if erros else ""
        except XanoAuthenticationError as error:
            self.kpis = {}
            self.kpi_error = error_feedback(error)
            return self._xano_error_response(error)
        finally:
            self.is_loading_kpis = False
        return None
