"""Page for goods receipts: history, detail and master-detail form."""

from __future__ import annotations

import reflex as rx

from Projeto_HarleyStore.components import guarded_page, modal_panel, page_body
from Projeto_HarleyStore.entradas_state import ENTRADAS_ROUTE, EntradasState
from Projeto_HarleyStore.styles.theme import COLORS
from Projeto_HarleyStore.ui_helpers import (
    data_table,
    error_callout,
    labeled,
    metal_button,
    modal_header,
    page_header,
    pager,
    primary_button,
    section_title,
    stat_tile,
    toolbar,
)


def history_row(row: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(row["data"]),
        rx.table.cell(rx.text(row["documento"], font_weight="700")),
        rx.table.cell(row["fornecedor"]),
        rx.table.cell(row["responsavel"], color=COLORS["muted"]),
        rx.table.cell(row["itens"], text_align="right"),
        rx.table.cell(rx.text(row["total"], color=COLORS["orange"], font_weight="700"), text_align="right"),
        rx.table.cell(
            metal_button(
                "Detalhes",
                on_click=EntradasState.open_detail(row["id"]),
                size="1",
                disabled=EntradasState.is_busy,
            ),
            text_align="right",
        ),
        align="center",
    )


def detail_item_row(item: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(item["codigo"]),
        rx.table.cell(item["produto"]),
        rx.table.cell(item["quantidade"], text_align="right"),
        rx.table.cell(item["valor_unitario"], text_align="right"),
        rx.table.cell(item["subtotal"], text_align="right"),
    )


def detail_modal() -> rx.Component:
    detalhe = EntradasState.detalhe
    return modal_panel(
        modal_header("Entrada ", detalhe["documento"], on_close=EntradasState.close_detail),
        rx.grid(
            labeled("Fornecedor", rx.text(detalhe["fornecedor"])),
            labeled("Data", rx.text(detalhe["data"])),
            labeled("Responsável", rx.text(detalhe["responsavel"])),
            stat_tile("Total", detalhe["total"], accent=True),
            columns=rx.breakpoints(initial="1", sm="2"),
            spacing="4",
            width="100%",
        ),
        section_title("Itens"),
        data_table(
            ["Código", "Produto", ("Qtd.", "right"), ("Preço de custo", "right"), ("Subtotal", "right")],
            EntradasState.detalhe_itens,
            detail_item_row,
            empty_text="Entrada sem itens.",
        ),
        width="min(100%, 48rem)",
        on_close=EntradasState.close_detail,
    )


def item_form_row(item: rx.Var, index: rx.Var) -> rx.Component:
    return rx.hstack(
        rx.select(
            EntradasState.produto_options,
            value=item["produto"],
            on_change=lambda value: EntradasState.set_item_field(index, "produto", value),
            placeholder="Selecione um produto",
            aria_label="Produto do item",
            width="100%",
        ),
        rx.input(
            value=item["quantidade"],
            on_change=lambda value: EntradasState.set_item_field(index, "quantidade", value),
            placeholder="Qtd.",
            aria_label="Quantidade do item",
            type="number",
            min=1,
            width="6rem",
        ),
        rx.input(
            value=item["valor_unitario"],
            on_change=lambda value: EntradasState.set_item_field(index, "valor_unitario", value),
            placeholder="Preço de custo",
            aria_label="Preço de custo do item",
            input_mode="decimal",
            width="9rem",
        ),
        rx.icon_button(
            rx.icon("trash-2"),
            on_click=EntradasState.remove_item(index),
            disabled=EntradasState.itens_form.length() <= 1,
            variant="ghost",
            color_scheme="red",
            aria_label="Remover item",
        ),
        width="100%",
        align="center",
    )


def entrada_form_modal() -> rx.Component:
    return modal_panel(
        modal_header("Nova entrada de mercadoria", on_close=EntradasState.close_form),
        error_callout(EntradasState.form_error),
        rx.hstack(
            labeled(
                "Fornecedor",
                rx.select(
                    EntradasState.fornecedor_options,
                    value=EntradasState.fornecedor,
                    on_change=EntradasState.set_fornecedor,
                    placeholder="Selecione um fornecedor ativo",
                    width="100%",
                ),
                flex="2",
            ),
            labeled(
                "Número do documento",
                rx.input(
                    value=EntradasState.numero_documento,
                    on_change=EntradasState.set_numero_documento,
                    placeholder="NF-000123",
                    width="100%",
                ),
                flex="1",
            ),
            width="100%",
            align="end",
            wrap="wrap",
        ),
        rx.hstack(
            section_title("Itens"),
            rx.spacer(),
            metal_button(rx.icon("plus", size=14), "Adicionar item", on_click=EntradasState.add_item, size="2"),
            width="100%",
            align="center",
        ),
        rx.vstack(
            rx.foreach(EntradasState.itens_form, item_form_row),
            spacing="2",
            width="100%",
        ),
        rx.hstack(
            stat_tile("Total previsto", EntradasState.total_previsto, accent=True),
            rx.spacer(),
            metal_button("Cancelar", on_click=EntradasState.close_form),
            primary_button(
                rx.cond(EntradasState.is_saving, "Registrando…", "Registrar entrada"),
                on_click=EntradasState.save_entrada,
                disabled=EntradasState.is_busy,
            ),
            width="100%",
            align="center",
        ),
        rx.text(
            "O total é recalculado pelo servidor e o estoque é atualizado na mesma operação.",
            size="1",
            color=COLORS["muted"],
        ),
        width="min(100%, 52rem)",
        on_close=EntradasState.close_form,
    )


def entradas_page() -> rx.Component:
    return guarded_page(
        page_body(
            page_header(
                "Entradas de mercadoria",
                "Compras de fornecedores que abastecem o estoque.",
                rx.cond(
                    EntradasState.can_register,
                    primary_button(
                        rx.icon("plus", size=16),
                        "Nova entrada",
                        on_click=EntradasState.open_create,
                        disabled=EntradasState.is_busy,
                    ),
                ),
            ),
            toolbar(
                EntradasState.search_text,
                EntradasState.set_search_text,
                "Buscar por documento, fornecedor ou responsável…",
                disabled=EntradasState.is_loading_list,
                current_page=EntradasState.current_page,
                total_pages=EntradasState.total_pages,
            ),
            error_callout(EntradasState.list_error),
            data_table(
                [
                    "Data",
                    "Documento",
                    "Fornecedor",
                    "Responsável",
                    ("Itens", "right"),
                    ("Total", "right"),
                    ("", "right"),
                ],
                EntradasState.visible_rows,
                history_row,
                empty_text="Nenhuma entrada encontrada.",
                loading=EntradasState.is_loading_list,
                loading_text="Carregando entradas…",
            ),
            pager(EntradasState.previous_page, EntradasState.next_page, EntradasState.is_busy),
            rx.cond(EntradasState.detail_open, detail_modal()),
            rx.cond(EntradasState.form_open, entrada_form_modal()),
        ),
        ENTRADAS_ROUTE,
    )
