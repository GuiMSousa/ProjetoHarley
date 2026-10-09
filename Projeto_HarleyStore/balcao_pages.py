"""Counter sale page (/balcao): parts search, cart, optional customer and receipt (Change 11)."""

from __future__ import annotations

import reflex as rx

from Projeto_HarleyStore.balcao_state import BALCAO_ROUTE, BalcaoState
from Projeto_HarleyStore.components import guarded_page, modal_panel, page_body
from Projeto_HarleyStore.styles.theme import COLORS, PANEL
from Projeto_HarleyStore.ui_helpers import (
    card,
    data_table,
    empty_state,
    error_callout,
    labeled,
    metal_button,
    modal_header,
    page_header,
    primary_button,
    section_title,
    stat_tile,
    toolbar,
)


def produto_item(produto: rx.Var) -> rx.Component:
    disponivel = produto["disponivel"] == "true"
    return rx.hstack(
        rx.vstack(
            rx.text(produto["codigo"], font_weight="700", font_family="monospace"),
            rx.text(produto["nome"], size="2", trim="end"),
            spacing="0",
            align="start",
            flex="1",
            min_width="0",
        ),
        rx.vstack(
            rx.text(produto["preco"], font_weight="700", color=COLORS["orange"]),
            rx.text(
                rx.cond(disponivel, f"saldo {produto['saldo']}", "sem saldo"),
                size="1",
                color=COLORS["muted"],
            ),
            spacing="0",
            align="end",
        ),
        metal_button(
            rx.cond(disponivel, "Adicionar", "Sem saldo"),
            on_click=BalcaoState.adicionar(produto["id"]),
            disabled=(produto["disponivel"] != "true") | BalcaoState.is_busy,
            size="2",
            aria_label=f"Adicionar {produto['codigo']} ao carrinho",
        ),
        width="100%",
        align="center",
        spacing="3",
        padding="0.6rem 0.75rem",
        **PANEL,
    )


def produtos_panel() -> rx.Component:
    return card(
        rx.vstack(
            section_title("Peças"),
            rx.select(
                BalcaoState.categorias,
                value=BalcaoState.categoria,
                on_change=BalcaoState.set_categoria,
                disabled=BalcaoState.is_loading_list,
                aria_label="Filtrar por categoria",
                width="100%",
            ),
            toolbar(
                BalcaoState.busca,
                BalcaoState.set_busca,
                "Buscar peça por código ou nome…",
                disabled=BalcaoState.is_loading_list,
            ),
            error_callout(BalcaoState.list_error),
            rx.cond(
                BalcaoState.is_loading_list,
                rx.text("Carregando produtos…", color=COLORS["muted"], role="status"),
                rx.cond(
                    BalcaoState.resultados.length() > 0,
                    rx.vstack(
                        rx.foreach(BalcaoState.resultados, produto_item),
                        rx.cond(
                            BalcaoState.resultados_truncados,
                            rx.text(
                                "Mostrando os 20 primeiros resultados; refine a busca para ver outros.",
                                size="1",
                                color=COLORS["muted"],
                            ),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    empty_state("Nenhum produto ativo encontrado.", "package-search"),
                ),
            ),
            spacing="3",
            width="100%",
        ),
    )


def carrinho_row(linha: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.vstack(
                rx.text(linha["codigo"], font_weight="700", font_family="monospace"),
                rx.text(linha["nome"], size="1", color=COLORS["muted"]),
                spacing="0",
            ),
        ),
        rx.table.cell(linha["preco"], text_align="right", white_space="nowrap"),
        rx.table.cell(
            rx.input(
                value=linha["quantidade"],
                on_change=lambda value: BalcaoState.set_quantidade(linha["id"], value),
                type="number",
                min=1,
                max=linha["saldo"],
                input_mode="numeric",
                aria_label=f"Quantidade de {linha['codigo']}",
                disabled=BalcaoState.is_busy,
                width="5rem",
            ),
        ),
        rx.table.cell(linha["subtotal"], text_align="right", white_space="nowrap"),
        rx.table.cell(
            rx.icon_button(
                rx.icon("trash-2"),
                on_click=BalcaoState.remover(linha["id"]),
                disabled=BalcaoState.is_busy,
                variant="ghost",
                color_scheme="red",
                aria_label=f"Remover {linha['codigo']} do carrinho",
            ),
        ),
    )


def carrinho_panel() -> rx.Component:
    return rx.vstack(
        section_title("Carrinho"),
        data_table(
            ["Produto", ("Preço", "right"), "Qtd.", ("Subtotal", "right"), ""],
            BalcaoState.carrinho,
            carrinho_row,
            empty_text="Adicione peças para iniciar a venda.",
        ),
        labeled(
            "Cliente",
            rx.select(
                BalcaoState.cliente_options,
                value=BalcaoState.cliente,
                on_change=BalcaoState.set_cliente,
                disabled=BalcaoState.is_busy,
                width="100%",
            ),
        ),
        error_callout(BalcaoState.form_error),
        rx.hstack(
            stat_tile("Total", BalcaoState.total, accent=True),
            rx.spacer(),
            metal_button(
                "Limpar",
                on_click=BalcaoState.limpar_carrinho,
                disabled=(BalcaoState.itens_no_carrinho == 0) | BalcaoState.is_busy,
            ),
            primary_button(
                rx.icon("shopping-cart", size=16),
                "Fechar venda",
                on_click=BalcaoState.abrir_confirmacao,
                disabled=(BalcaoState.itens_no_carrinho == 0) | BalcaoState.is_busy,
            ),
            width="100%",
            align="center",
            wrap="wrap",
            spacing="3",
        ),
        spacing="3",
        width="100%",
    )


def resumo_linha(linha: rx.Var) -> rx.Component:
    return rx.hstack(
        rx.text(linha["quantidade"], " × ", linha["codigo"], " · ", linha["nome"], size="2", flex="1"),
        rx.text(linha["subtotal"], size="2", white_space="nowrap"),
        width="100%",
        spacing="3",
    )


def confirmacao_modal() -> rx.Component:
    return modal_panel(
        modal_header("Confirmar venda", on_close=BalcaoState.fechar_confirmacao),
        rx.vstack(
            rx.foreach(BalcaoState.carrinho, resumo_linha),
            spacing="1",
            width="100%",
            padding="0.75rem",
            **PANEL,
        ),
        rx.hstack(
            stat_tile("Cliente", BalcaoState.cliente_selecionado),
            rx.spacer(),
            stat_tile("Total", BalcaoState.total, accent=True),
            width="100%",
            align="end",
        ),
        rx.text(
            "Os preços são conferidos pelo Xano no fechamento. O vendedor vem do seu login; "
            "as peças saem do estoque e a receita entra no financeiro.",
            size="1",
            color=COLORS["muted"],
        ),
        rx.hstack(
            rx.spacer(),
            metal_button("Voltar", on_click=BalcaoState.fechar_confirmacao, disabled=BalcaoState.is_selling),
            primary_button(
                rx.cond(BalcaoState.is_selling, "Registrando venda…", "Confirmar venda"),
                on_click=BalcaoState.confirmar_venda,
                disabled=BalcaoState.is_busy,
                loading=BalcaoState.is_selling,
            ),
            width="100%",
        ),
        width="min(100%, 32rem)",
    )


def recibo_linha(linha: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(linha["produto"]),
        rx.table.cell(linha["quantidade"], text_align="right"),
        rx.table.cell(linha["preco"], text_align="right", white_space="nowrap"),
        rx.table.cell(linha["subtotal"], text_align="right", white_space="nowrap"),
    )


def recibo_modal() -> rx.Component:
    recibo = BalcaoState.recibo
    return modal_panel(
        modal_header("Venda #", recibo["numero"], " registrada", on_close=BalcaoState.fechar_recibo),
        rx.hstack(
            stat_tile("Data", recibo["data"]),
            stat_tile("Cliente", recibo["cliente"]),
            stat_tile("Vendedor", recibo["vendedor"]),
            width="100%",
            wrap="wrap",
            spacing="5",
        ),
        data_table(
            ["Produto", ("Qtd.", "right"), ("Preço", "right"), ("Subtotal", "right")],
            BalcaoState.recibo_itens,
            recibo_linha,
            empty_text="Venda sem itens.",
        ),
        rx.hstack(
            stat_tile("Total", recibo["total"], accent=True),
            rx.spacer(),
            primary_button("Nova venda", on_click=BalcaoState.fechar_recibo),
            width="100%",
            align="center",
        ),
        width="min(100%, 40rem)",
    )


def balcao_page() -> rx.Component:
    return guarded_page(
        page_body(
            page_header("Venda no balcão", "Peças do estoque para clientes ou consumidor final."),
            rx.grid(
                produtos_panel(),
                carrinho_panel(),
                columns=rx.breakpoints(initial="1", lg="2"),
                spacing="5",
                width="100%",
                align_items="start",
            ),
            rx.cond(BalcaoState.confirm_open, confirmacao_modal()),
            rx.cond(BalcaoState.recibo_open, recibo_modal()),
        ),
        BALCAO_ROUTE,
    )
