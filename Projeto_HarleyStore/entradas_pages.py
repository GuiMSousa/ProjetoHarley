"""Page for goods receipts: history, detail and master-detail form."""

from __future__ import annotations

import reflex as rx

from Projeto_HarleyStore.components import guarded_page, modal_panel
from Projeto_HarleyStore.entradas_state import ENTRADAS_ROUTE, EntradasState
from Projeto_HarleyStore.styles.theme import COLORS, PANEL, PRIMARY_BUTTON
from Projeto_HarleyStore.ui_helpers import error_callout, labeled


def history_row(row: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(row["data"]),
        rx.table.cell(rx.text(row["documento"], font_weight="700")),
        rx.table.cell(row["fornecedor"]),
        rx.table.cell(row["responsavel"], color=COLORS["muted"]),
        rx.table.cell(row["itens"], text_align="right"),
        rx.table.cell(rx.text(row["total"], color=COLORS["orange"]), text_align="right"),
        rx.table.cell(
            rx.button(
                "Detalhes",
                on_click=EntradasState.open_detail(row["id"]),
                variant="outline",
                size="1",
                disabled=EntradasState.is_busy,
            ),
            text_align="right",
        ),
        align="center",
    )


def history_table() -> rx.Component:
    return rx.box(
        rx.cond(
            EntradasState.is_loading_list,
            rx.text("Carregando entradas...", color=COLORS["muted"], padding="2rem"),
            rx.cond(
                EntradasState.visible_rows.length() > 0,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Data"),
                            rx.table.column_header_cell("Documento"),
                            rx.table.column_header_cell("Fornecedor"),
                            rx.table.column_header_cell("Responsável"),
                            rx.table.column_header_cell("Itens", text_align="right"),
                            rx.table.column_header_cell("Total", text_align="right"),
                            rx.table.column_header_cell(""),
                        ),
                    ),
                    rx.table.body(rx.foreach(EntradasState.visible_rows, history_row)),
                    width="100%",
                ),
                rx.text("Nenhuma entrada encontrada.", color=COLORS["muted"], padding="2rem"),
            ),
        ),
        width="100%",
        padding="0 1rem",
        overflow_x="auto",
        **PANEL,
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
        rx.hstack(
            rx.heading("Entrada ", detalhe["documento"], size="5"),
            rx.spacer(),
            rx.button("Fechar", on_click=EntradasState.close_detail, variant="ghost"),
            width="100%",
        ),
        rx.grid(
            labeled("Fornecedor", rx.text(detalhe["fornecedor"])),
            labeled("Data", rx.text(detalhe["data"])),
            labeled("Responsável", rx.text(detalhe["responsavel"])),
            labeled("Total", rx.text(detalhe["total"], color=COLORS["orange"], font_weight="700")),
            columns="2",
            spacing="4",
            width="100%",
        ),
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Código"),
                        rx.table.column_header_cell("Produto"),
                        rx.table.column_header_cell("Qtd.", text_align="right"),
                        rx.table.column_header_cell("Preço de custo", text_align="right"),
                        rx.table.column_header_cell("Subtotal", text_align="right"),
                    ),
                ),
                rx.table.body(rx.foreach(EntradasState.detalhe_itens, detail_item_row)),
                width="100%",
            ),
            width="100%",
            overflow_x="auto",
        ),
        width="min(100%, 48rem)",
    )


def item_form_row(item: rx.Var, index: rx.Var) -> rx.Component:
    return rx.hstack(
        rx.select(
            EntradasState.produto_options,
            value=item["produto"],
            on_change=lambda value: EntradasState.set_item_field(index, "produto", value),
            placeholder="Selecione um produto",
            width="100%",
        ),
        rx.input(
            value=item["quantidade"],
            on_change=lambda value: EntradasState.set_item_field(index, "quantidade", value),
            placeholder="Qtd.",
            type="number",
            min=1,
            width="6rem",
        ),
        rx.input(
            value=item["valor_unitario"],
            on_change=lambda value: EntradasState.set_item_field(index, "valor_unitario", value),
            placeholder="Preço de custo",
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
        rx.hstack(
            rx.heading("Nova entrada de mercadoria", size="5"),
            rx.spacer(),
            rx.button("Fechar", on_click=EntradasState.close_form, variant="ghost"),
            width="100%",
        ),
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
        ),
        rx.hstack(
            rx.text("Itens", font_weight="700"),
            rx.spacer(),
            rx.button("Adicionar item", on_click=EntradasState.add_item, variant="outline", size="2"),
            width="100%",
            align="center",
        ),
        rx.vstack(
            rx.foreach(EntradasState.itens_form, item_form_row),
            spacing="2",
            width="100%",
        ),
        rx.hstack(
            rx.vstack(
                rx.text("Total previsto", size="2", color=COLORS["muted"]),
                rx.text(EntradasState.total_previsto, color=COLORS["orange"], font_weight="800", size="5"),
                spacing="0",
                align="start",
            ),
            rx.spacer(),
            rx.button("Cancelar", on_click=EntradasState.close_form, variant="outline"),
            rx.button(
                rx.cond(EntradasState.is_saving, "Registrando...", "Registrar entrada"),
                on_click=EntradasState.save_entrada,
                disabled=EntradasState.is_busy,
                **PRIMARY_BUTTON,
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
    )


def entradas_page() -> rx.Component:
    return guarded_page(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.heading("Entradas de mercadoria", size="7"),
                    rx.text(
                        "Compras de fornecedores que abastecem o estoque.",
                        color=COLORS["muted"],
                    ),
                    align="start",
                    spacing="1",
                ),
                rx.spacer(),
                rx.cond(
                    EntradasState.can_register,
                    rx.button(
                        "Nova entrada",
                        on_click=EntradasState.open_create,
                        disabled=EntradasState.is_busy,
                        **PRIMARY_BUTTON,
                    ),
                ),
                width="100%",
                align="center",
            ),
            rx.hstack(
                rx.input(
                    placeholder="Buscar por documento, fornecedor ou responsável...",
                    value=EntradasState.search_text,
                    on_change=EntradasState.set_search_text,
                    disabled=EntradasState.is_loading_list,
                    width="min(100%, 28rem)",
                ),
                rx.spacer(),
                rx.text(
                    rx.cond(
                        EntradasState.total_pages > 1,
                        f"Página {EntradasState.current_page} de {EntradasState.total_pages}",
                        "",
                    ),
                    size="2",
                    color=COLORS["muted"],
                ),
                width="100%",
            ),
            error_callout(EntradasState.list_error),
            history_table(),
            rx.hstack(
                rx.button("Anterior", on_click=EntradasState.previous_page, variant="outline", disabled=EntradasState.is_busy),
                rx.button("Próxima", on_click=EntradasState.next_page, variant="outline", disabled=EntradasState.is_busy),
                spacing="2",
            ),
            rx.cond(EntradasState.detail_open, detail_modal()),
            rx.cond(EntradasState.form_open, entrada_form_modal()),
            align="stretch",
            spacing="5",
            padding="2rem",
            width="100%",
        ),
        ENTRADAS_ROUTE,
    )
