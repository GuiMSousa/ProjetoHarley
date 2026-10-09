"""Reflex state of /financeiro (Change 10): revenue, expenses and balance of a period (GERENTE)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import reflex as rx
from pydantic import ValidationError

from Projeto_HarleyStore.auth import AuthState, role_allows_route
from Projeto_HarleyStore.feedback import error_feedback, validation_feedback
from Projeto_HarleyStore.formatting import EMPTY_VALUE, format_currency, format_datetime
from Projeto_HarleyStore.listing import normalize_text
from Projeto_HarleyStore.services.financeiro import (
    FUSO_LOJA,
    NATUREZA_LABELS,
    TIPO_LABELS,
    OperacaoFinanceira,
    PeriodoFinanceiro,
    ResumoFinanceiro,
    TotalPorTipo,
)
from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoClient,
    XanoError,
)


FINANCEIRO_ROUTE = "/financeiro"
FILTRO_TODOS = "TODOS"
ATALHOS = {
    "MES_ATUAL": "Este mês",
    "MES_ANTERIOR": "Mês anterior",
    "ULTIMOS_30_DIAS": "Últimos 30 dias",
}
FIELD_MESSAGES = {
    "inicio": "Informe a data inicial do período.",
    "fim": "Informe a data final do período.",
}
MINUS = "−"


class FinanceiroFormError(ValueError):
    """Readable validation error of the period form."""


# ----- rules -----


def hoje_loja() -> date:
    return datetime.now(FUSO_LOJA).date()


def periodo_padrao(hoje: date) -> tuple[date, date]:
    """Current month up to today."""
    return hoje.replace(day=1), hoje


def atalho_periodo(nome: str, hoje: date) -> tuple[date, date]:
    if nome == "MES_ANTERIOR":
        fim = hoje.replace(day=1) - timedelta(days=1)
        return fim.replace(day=1), fim
    if nome == "ULTIMOS_30_DIAS":
        return hoje - timedelta(days=29), hoje
    return periodo_padrao(hoje)


def build_periodo(inicio: str, fim: str) -> PeriodoFinanceiro:
    try:
        return PeriodoFinanceiro(inicio=inicio, fim=fim)
    except ValidationError as error:
        raise FinanceiroFormError(validation_feedback(error, FIELD_MESSAGES)) from error


def valor_com_sinal(valor: Decimal, negativo: bool) -> str:
    """Currency with an explicit sign: expenses and a negative balance get a minus."""
    return f"{MINUS} {format_currency(abs(valor))}" if negativo else format_currency(abs(valor))


def descricao_operacao(operacao: OperacaoFinanceira) -> str:
    if operacao.origem == "ENTRADA":
        return f"Entrada {operacao.numero_documento}" if operacao.numero_documento else f"Entrada #{operacao.id}"
    if operacao.tipo == "ORDEM_SERVICO" and operacao.id_os is not None:
        return " · ".join(parte for parte in (f"OS #{operacao.id_os}", operacao.modelo) if parte)
    if operacao.tipo == "MOTO":
        return " · ".join(parte for parte in ("Venda de moto", operacao.modelo, operacao.placa) if parte)
    # Transactions created by the generic CRUD before Change 10.
    return f"Transação #{operacao.id}"


def operacao_row(operacao: OperacaoFinanceira) -> dict[str, str]:
    return {
        "chave": f"{operacao.origem}-{operacao.id}",
        "data": format_datetime(operacao.data),
        "tipo": operacao.tipo,
        "tipo_label": TIPO_LABELS[operacao.tipo],
        "natureza": operacao.natureza,
        "natureza_label": NATUREZA_LABELS[operacao.natureza],
        "descricao": descricao_operacao(operacao),
        "contraparte": operacao.contraparte or EMPTY_VALUE,
        "funcionario": operacao.funcionario or EMPTY_VALUE,
        "valor": valor_com_sinal(operacao.valor, operacao.natureza == "DESPESA"),
    }


def tipo_row(total: TotalPorTipo) -> dict[str, str]:
    return {
        "tipo": total.tipo,
        "tipo_label": TIPO_LABELS[total.tipo],
        "natureza": total.natureza,
        "natureza_label": NATUREZA_LABELS[total.natureza],
        "quantidade": str(total.quantidade),
        "valor": valor_com_sinal(total.valor, total.natureza == "DESPESA"),
    }


def ordenar_por_tipo(totais: list[TotalPorTipo]) -> list[TotalPorTipo]:
    """Revenue first, then expenses; the largest amounts first inside each group."""
    return sorted(totais, key=lambda total: (total.natureza != "RECEITA", -total.valor))


def resumo_row(resumo: ResumoFinanceiro) -> dict[str, str]:
    truncado = resumo.truncado
    return {
        "receitas": format_currency(resumo.receitas),
        "despesas": valor_com_sinal(resumo.despesas, resumo.despesas > 0),
        "saldo": valor_com_sinal(resumo.saldo, resumo.saldo < 0),
        "saldo_negativo": "true" if resumo.saldo < 0 else "false",
        "total_operacoes": str(resumo.total_operacoes),
        "aviso_truncado": (
            f"Mostrando as {len(resumo.operacoes)} operações mais recentes de {resumo.total_operacoes}; "
            "os totais cobrem o período inteiro."
            if truncado
            else ""
        ),
    }


def filtrar_operacoes(rows: list[dict[str, str]], tipo: str, busca: str) -> list[dict[str, str]]:
    """Local filter: changing the type or the search never calls Xano again."""
    termo = normalize_text(busca.strip())
    return [
        row
        for row in rows
        if (tipo == FILTRO_TODOS or row["tipo"] == tipo)
        and (
            not termo
            or termo in normalize_text(f"{row['descricao']} {row['contraparte']} {row['funcionario']}")
        )
    ]


# ----- state -----


class FinanceiroState(AuthState):
    """Consolidated view of revenue (transactions) and expenses (goods receipts) by period."""

    inicio: str = ""
    fim: str = ""
    resumo: dict[str, str] = {}
    por_tipo: list[dict[str, str]] = []
    operacoes: list[dict[str, str]] = []
    filtro_tipo: str = FILTRO_TODOS
    busca: str = ""
    periodo_error: str = ""
    list_error: str = ""
    is_loading_resumo: bool = False

    @rx.var
    def visible_rows(self) -> list[dict[str, str]]:
        return filtrar_operacoes(self.operacoes, self.filtro_tipo, self.busca)

    @rx.var
    def tipo_options(self) -> list[dict[str, str]]:
        """Filter tabs: "Todos" plus the types that have operations in the period."""
        return [{"value": FILTRO_TODOS, "label": "Todos"}] + [
            {"value": row["tipo"], "label": row["tipo_label"]} for row in self.por_tipo
        ]

    def _apply(self, resumo: ResumoFinanceiro) -> None:
        self.resumo = resumo_row(resumo)
        self.por_tipo = [tipo_row(total) for total in ordenar_por_tipo(resumo.por_tipo)]
        self.operacoes = [operacao_row(operacao) for operacao in resumo.operacoes]
        if self.filtro_tipo not in {row["tipo"] for row in self.por_tipo}:
            self.filtro_tipo = FILTRO_TODOS

    def _consultar(self):
        try:
            periodo = build_periodo(self.inicio, self.fim)
        except FinanceiroFormError as error:
            self.periodo_error = str(error)
            return None
        self.periodo_error = ""
        self.list_error = ""
        self.is_loading_resumo = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                self._apply(client.resumo_financeiro(periodo))
        except XanoError as error:
            self.list_error = error_feedback(error)
            if isinstance(error, XanoAuthenticationError):
                return self._xano_error_response(error)
        finally:
            self.is_loading_resumo = False
        return None

    @rx.event
    def load_financeiro(self):
        if self.is_loading_resumo:
            return None
        if not self.is_authenticated or not role_allows_route(self.employee_role, FINANCEIRO_ROUTE):
            return None
        if not self.inicio or not self.fim:
            inicio, fim = periodo_padrao(hoje_loja())
            self.inicio, self.fim = inicio.isoformat(), fim.isoformat()
        return (yield from self._consultar())

    @rx.event
    def set_inicio(self, value: str) -> None:
        self.inicio = value
        self.periodo_error = ""

    @rx.event
    def set_fim(self, value: str) -> None:
        self.fim = value
        self.periodo_error = ""

    @rx.event
    def aplicar_periodo(self):
        if self.is_loading_resumo:
            return None
        return (yield from self._consultar())

    @rx.event
    def usar_atalho(self, nome: str):
        if self.is_loading_resumo or nome not in ATALHOS:
            return None
        inicio, fim = atalho_periodo(nome, hoje_loja())
        self.inicio, self.fim = inicio.isoformat(), fim.isoformat()
        return (yield from self._consultar())

    @rx.event
    def set_filtro_tipo(self, value: str) -> None:
        self.filtro_tipo = value

    @rx.event
    def set_busca(self, value: str) -> None:
        self.busca = value
