"""Financial page (/financeiro, GERENTE): revenue, expenses and balance of a period (Change 10)."""

from __future__ import annotations

import reflex as rx

from Projeto_HarleyStore.components import guarded_page, page_body
from Projeto_HarleyStore.financeiro_state import ATALHOS, FINANCEIRO_ROUTE, FinanceiroState
from Projeto_HarleyStore.styles.theme import COLORS
from Projeto_HarleyStore.ui_helpers import (
    card,
    data_table,
    error_callout,
    labeled,
    metal_button,
    page_header,
    primary_button,
    section_title,
    stat_tile,
    status_badge,
    toolbar,
)


def periodo_bar() -> rx.Component:
    busy = FinanceiroState.is_loading_resumo
    return card(
        rx.hstack(
            labeled(
                "De",
                rx.input(type="date", value=FinanceiroState.inicio, on_change=FinanceiroState.set_inicio),
                min_width="9.5rem",
            ),
            labeled(
                "Até",
                rx.input(type="date", value=FinanceiroState.fim, on_change=FinanceiroState.set_fim),
                min_width="9.5rem",
            ),
            primary_button(
                rx.cond(busy, "Carregando…", "Aplicar período"),
                on_click=FinanceiroState.aplicar_periodo,
                disabled=busy,
                size="2",
            ),
            rx.spacer(),
            rx.hstack(
                *[
                    metal_button(label, on_click=FinanceiroState.usar_atalho(nome), disabled=busy, size="2")
                    for nome, label in ATALHOS.items()
                ],
                spacing="2",
                wrap="wrap",
            ),
            align="end",
            spacing="3",
            wrap="wrap",
            width="100%",
        ),
    )


def resumo_tiles() -> rx.Component:
    resumo = FinanceiroState.resumo
    return card(
        rx.hstack(
            stat_tile("Receitas", resumo["receitas"]),
            stat_tile("Despesas", resumo["despesas"]),
            stat_tile(
                "Saldo",
                resumo["saldo"],
                accent=True,
                color=rx.cond(resumo["saldo_negativo"] == "true", COLORS["danger"], COLORS["orange"]),
            ),
            rx.spacer(),
            rx.text(resumo["total_operacoes"], " operações no período", size="2", color=COLORS["muted"]),
            align="end",
            spacing="6",
            wrap="wrap",
            width="100%",
        ),
    )


def _valor_cell(row: rx.Var) -> rx.Component:
    return rx.table.cell(
        rx.text(
            row["valor"],
            font_weight="700",
            white_space="nowrap",
            color=rx.cond(row["natureza"] == "DESPESA", COLORS["danger"], COLORS["text"]),
        ),
        text_align="right",
    )


def tipo_row(row: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(row["tipo_label"], font_weight="600")),
        rx.table.cell(status_badge(row["natureza"], row["natureza_label"])),
        rx.table.cell(row["quantidade"], text_align="right"),
        _valor_cell(row),
        align="center",
    )


def operacao_row(row: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(row["data"], white_space="nowrap")),
        rx.table.cell(
            rx.vstack(
                rx.text(row["tipo_label"], size="2"),
                status_badge(row["natureza"], row["natureza_label"]),
                spacing="1",
                align="start",
            )
        ),
        rx.table.cell(rx.text(row["descricao"], font_weight="600")),
        rx.table.cell(row["contraparte"]),
        rx.table.cell(row["funcionario"], color=COLORS["muted"]),
        _valor_cell(row),
        align="center",
    )


def filtro_tipo() -> rx.Component:
    return rx.tabs.root(
        rx.tabs.list(
            rx.foreach(
                FinanceiroState.tipo_options,
                lambda opcao: rx.tabs.trigger(opcao["label"], value=opcao["value"]),
            ),
            overflow_x="auto",
            flex_wrap="nowrap",
        ),
        value=FinanceiroState.filtro_tipo,
        on_change=FinanceiroState.set_filtro_tipo,
        max_width="100%",
        min_width="0",
    )


def financeiro_page() -> rx.Component:
    busy = FinanceiroState.is_loading_resumo
    return guarded_page(
        page_body(
            page_header("Financeiro", "Receitas, despesas e saldo do período."),
            periodo_bar(),
            error_callout(FinanceiroState.periodo_error),
            error_callout(FinanceiroState.list_error),
            resumo_tiles(),
            section_title("Por tipo"),
            data_table(
                ["Tipo", "Natureza", ("Operações", "right"), ("Valor", "right")],
                FinanceiroState.por_tipo,
                tipo_row,
                empty_text="Nenhuma operação no período.",
                loading=busy,
                loading_text="Carregando resumo…",
            ),
            section_title("Operações"),
            filtro_tipo(),
            toolbar(
                FinanceiroState.busca,
                FinanceiroState.set_busca,
                "Buscar por descrição, cliente, fornecedor ou funcionário…",
                disabled=busy,
            ),
            rx.cond(
                FinanceiroState.resumo["aviso_truncado"] != "",
                rx.callout(
                    FinanceiroState.resumo["aviso_truncado"],
                    icon="info",
                    color_scheme="gray",
                    width="100%",
                ),
            ),
            data_table(
                ["Data", "Tipo", "Descrição", "Cliente ou fornecedor", "Funcionário", ("Valor", "right")],
                FinanceiroState.visible_rows,
                operacao_row,
                empty_text="Nenhuma operação encontrada com estes filtros.",
                loading=busy,
                loading_text="Carregando operações…",
            ),
        ),
        FINANCEIRO_ROUTE,
    )
