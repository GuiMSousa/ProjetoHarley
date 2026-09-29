"""Service order detail: status transitions, timeline, parts and labor, and bike history."""

from __future__ import annotations

import reflex as rx

from Projeto_HarleyStore.components import modal_panel
from Projeto_HarleyStore.styles.theme import COLORS, PANEL
from Projeto_HarleyStore.ui_helpers import (
    danger_button,
    data_table,
    error_callout,
    labeled,
    metal_button,
    modal_header,
    primary_button,
    section_title,
    stat_tile,
    status_badge,
)
from Projeto_HarleyStore.workshop_state import WorkshopState


def info(label: str, value: rx.Var) -> rx.Component:
    return labeled(label, rx.text(value, color=COLORS["text"]))


def section(title: str, *children: rx.Component) -> rx.Component:
    return rx.vstack(section_title(title), *children, align="stretch", spacing="3", width="100%")


# ----- status transitions -----


def transition_button(action: rx.Var) -> rx.Component:
    return rx.match(
        action["value"],
        (
            "CANCELADA",
            danger_button(
                action["label"],
                on_click=WorkshopState.start_transition(action["value"]),
                disabled=WorkshopState.is_busy,
            ),
        ),
        primary_button(
            action["label"],
            on_click=WorkshopState.start_transition(action["value"]),
            disabled=WorkshopState.is_busy,
        ),
    )


def transition_panel() -> rx.Component:
    confirm = rx.vstack(
        rx.text("Confirmar: ", rx.text.strong(WorkshopState.transition_label), "?"),
        rx.cond(
            WorkshopState.transition_target == "CANCELADA",
            labeled(
                "Motivo do cancelamento",
                rx.text_area(
                    value=WorkshopState.transition_note,
                    on_change=WorkshopState.set_transition_note,
                    placeholder="Explique por que a OS está sendo cancelada",
                    width="100%",
                ),
                width="100%",
            ),
        ),
        rx.hstack(
            primary_button(
                rx.cond(WorkshopState.is_transitioning, "Registrando...", "Confirmar"),
                on_click=WorkshopState.confirm_transition,
                disabled=WorkshopState.is_busy,
            ),
            metal_button("Voltar", on_click=WorkshopState.cancel_transition),
            spacing="2",
        ),
        align="stretch",
        spacing="3",
        width="100%",
        padding="1rem",
        **PANEL,
    )
    return rx.cond(
        WorkshopState.can_operate & (WorkshopState.available_transitions.length() > 0),
        rx.vstack(
            error_callout(WorkshopState.transition_error),
            rx.cond(
                WorkshopState.transition_target == "",
                rx.hstack(
                    rx.foreach(WorkshopState.available_transitions, transition_button),
                    spacing="2",
                    wrap="wrap",
                ),
                confirm,
            ),
            align="stretch",
            spacing="3",
            width="100%",
        ),
        error_callout(WorkshopState.transition_error),
    )


def timeline_row(evento: rx.Var) -> rx.Component:
    return rx.hstack(
        status_badge(evento["status"], evento["para"]),
        rx.vstack(
            rx.text(evento["de"], " → ", evento["para"], size="2"),
            rx.text(evento["quando"], " · ", evento["funcionario"], size="1", color=COLORS["muted"]),
            rx.cond(
                evento["observacao"] != "",
                rx.text(evento["observacao"], size="1", color=COLORS["muted"]),
            ),
            align="start",
            spacing="0",
        ),
        align="start",
        spacing="3",
        width="100%",
    )


# ----- parts and labor -----


def item_row(item: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.badge(
                item["tipo_label"],
                color_scheme=rx.cond(item["tipo"] == "SERVICO", "blue", "orange"),
                variant="soft",
            )
        ),
        rx.table.cell(item["descricao"]),
        rx.table.cell(item["quantidade"], text_align="right"),
        rx.table.cell(item["unitario"], text_align="right"),
        rx.table.cell(item["total"], text_align="right"),
        rx.table.cell(
            rx.cond(
                WorkshopState.can_edit_items,
                danger_button(
                    "Remover",
                    on_click=WorkshopState.ask_remove_item(item["id"]),
                    size="1",
                    disabled=WorkshopState.is_busy,
                ),
            ),
            text_align="right",
        ),
        align="center",
    )


def itens_table() -> rx.Component:
    return data_table(
        ["Tipo", "Item", ("Qtd.", "right"), ("Unitário", "right"), ("Total", "right"), ("", "right")],
        WorkshopState.detalhe_itens,
        item_row,
        empty_text="Nenhum item registrado.",
    )


def remove_confirm() -> rx.Component:
    return rx.cond(
        WorkshopState.item_to_remove != "",
        rx.hstack(
            rx.text(WorkshopState.remove_message, size="2", flex="1"),
            danger_button(
                rx.cond(WorkshopState.is_removing_item, "Removendo...", "Remover"),
                on_click=WorkshopState.confirm_remove_item,
                size="1",
                disabled=WorkshopState.is_busy,
            ),
            metal_button("Voltar", on_click=WorkshopState.cancel_remove_item, size="1"),
            width="100%",
            align="center",
            padding="0.75rem",
            **PANEL,
        ),
    )


def custos_resumo() -> rx.Component:
    totais = WorkshopState.detalhe_totais
    return rx.vstack(
        rx.hstack(
            stat_tile("Peças", totais["pecas"]),
            rx.text("+", color=COLORS["muted"]),
            stat_tile("Mão de obra", totais["servicos"]),
            rx.text("=", color=COLORS["muted"]),
            stat_tile("Total OS", totais["total"], accent=True),
            spacing="4",
            align="center",
            wrap="wrap",
        ),
        rx.cond(
            WorkshopState.total_previsto != "",
            rx.text(
                f"Item em edição: {WorkshopState.item_preview} · "
                f"total após inclusão: {WorkshopState.total_previsto}",
                size="1",
                color=COLORS["muted"],
            ),
        ),
        spacing="1",
        width="100%",
        padding="0.75rem 1rem",
        **PANEL,
    )


def produto_option(produto: rx.Var) -> rx.Component:
    return rx.button(
        rx.hstack(
            rx.text(produto["codigo"], font_weight="700", min_width="6rem"),
            rx.text(produto["nome"], flex="1", trim="end", text_align="left"),
            rx.text(
                rx.cond(
                    produto["disponivel"] == "true",
                    f"saldo {produto['saldo']}",
                    "sem saldo",
                ),
                size="1",
                color=COLORS["muted"],
            ),
            rx.text(produto["preco"], size="2"),
            width="100%",
            align="center",
            spacing="3",
        ),
        on_click=WorkshopState.select_produto(produto["id"]),
        disabled=produto["disponivel"] != "true",
        variant="ghost",
        width="100%",
        justify="start",
    )


def peca_fields() -> rx.Component:
    selecionado = WorkshopState.produto_selecionado
    return rx.cond(
        WorkshopState.item_produto_id == "",
        rx.vstack(
            rx.input(
                rx.input.slot(rx.icon("search", size=16)),
                placeholder="Buscar peça por código ou nome...",
                value=WorkshopState.produto_busca,
                on_change=WorkshopState.set_produto_busca,
                width="100%",
            ),
            rx.cond(
                WorkshopState.produtos_filtrados.length() > 0,
                rx.vstack(
                    rx.foreach(WorkshopState.produtos_filtrados, produto_option),
                    spacing="1",
                    width="100%",
                ),
                rx.text("Nenhum produto ativo encontrado.", size="2", color=COLORS["muted"]),
            ),
            spacing="2",
            width="100%",
        ),
        rx.hstack(
            rx.vstack(
                rx.text(selecionado["codigo"], " · ", selecionado["nome"], font_weight="700"),
                rx.text(
                    "Saldo disponível: ", selecionado["saldo"], " · preço ", selecionado["preco"],
                    size="1",
                    color=COLORS["muted"],
                ),
                spacing="0",
                align="start",
                flex="1",
            ),
            labeled(
                "Quantidade",
                rx.input(
                    value=WorkshopState.item_quantidade,
                    on_change=WorkshopState.set_item_quantidade,
                    type="number",
                    min=1,
                    max=selecionado["saldo"],
                    width="7rem",
                ),
            ),
            metal_button("Trocar", on_click=WorkshopState.clear_produto, size="1"),
            width="100%",
            align="end",
            wrap="wrap",
        ),
    )


def servico_fields() -> rx.Component:
    return rx.hstack(
        labeled(
            "Descrição do serviço",
            rx.input(
                value=WorkshopState.item_descricao,
                on_change=WorkshopState.set_item_descricao,
                placeholder="Ex.: troca do kit de embreagem",
                max_length=200,
                width="100%",
            ),
            flex="1",
            min_width="14rem",
        ),
        labeled(
            "Quantidade",
            rx.input(
                value=WorkshopState.item_quantidade,
                on_change=WorkshopState.set_item_quantidade,
                type="number",
                min=1,
                width="6rem",
            ),
        ),
        labeled(
            "Valor unitário (R$)",
            rx.input(
                value=WorkshopState.item_valor_unitario,
                on_change=WorkshopState.set_item_valor_unitario,
                placeholder="0,00",
                width="9rem",
            ),
        ),
        width="100%",
        align="end",
        wrap="wrap",
    )


def item_form() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text("Adicionar item", font_weight="700", text_transform="uppercase", letter_spacing="0.06em"),
            rx.spacer(),
            rx.segmented_control.root(
                rx.segmented_control.item("Peça", value="PECA"),
                rx.segmented_control.item("Serviço", value="SERVICO"),
                value=WorkshopState.item_tipo,
                on_change=WorkshopState.set_item_tipo,
                size="1",
            ),
            width="100%",
            align="center",
        ),
        error_callout(WorkshopState.catalogo_error),
        rx.cond(WorkshopState.item_tipo == "PECA", peca_fields(), servico_fields()),
        error_callout(WorkshopState.item_error),
        rx.hstack(
            rx.spacer(),
            primary_button(
                rx.cond(WorkshopState.is_saving_item, "Adicionando...", "Adicionar"),
                on_click=WorkshopState.save_item,
                disabled=WorkshopState.is_busy,
            ),
            width="100%",
        ),
        spacing="3",
        width="100%",
        padding="1rem",
        **PANEL,
    )


# ----- bike history -----


def historico_moto_row(row: rx.Var) -> rx.Component:
    return rx.hstack(
        rx.text(row["numero"], font_weight="700", min_width="3rem"),
        rx.text(row["abertura"], size="2", color=COLORS["muted"], min_width="8rem"),
        rx.text(row["tipo"], size="2", min_width="6rem"),
        status_badge(row["status"], row["status_label"]),
        rx.text(row["descricao"], size="2", color=COLORS["muted"], flex="1", trim="end"),
        metal_button(
            "Ver",
            on_click=WorkshopState.open_detail(row["id"]),
            size="1",
            disabled=WorkshopState.is_busy,
        ),
        width="100%",
        align="center",
        padding="0.4rem 0",
        border_bottom=f"1px solid {COLORS['border']}",
    )


def detail_modal() -> rx.Component:
    detalhe = WorkshopState.detalhe
    return modal_panel(
        modal_header("OS ", detalhe["numero"], on_close=WorkshopState.close_detail),
        status_badge(detalhe["status"], detalhe["status_label"]),
        rx.grid(
            info("Cliente", detalhe["cliente"]),
            info("Moto", detalhe["moto"]),
            info("Mecânico responsável", detalhe["mecanico"]),
            info("Aberta por", detalhe["autor"]),
            info("Tipo de serviço", detalhe["tipo"]),
            info("Quilometragem", detalhe["quilometragem"]),
            info("Abertura", detalhe["abertura"]),
            info("Início", detalhe["inicio"]),
            info("Encerramento", detalhe["encerramento"]),
            columns=rx.breakpoints(initial="1", sm="2", md="3"),
            spacing="4",
            width="100%",
        ),
        labeled("Descrição do problema", rx.text(detalhe["descricao"])),
        rx.cond(
            detalhe["motivo"] != "",
            rx.callout(
                f"Motivo do cancelamento: {detalhe['motivo']}",
                icon="info",
                color_scheme="gray",
                width="100%",
            ),
        ),
        transition_panel(),
        section("Linha do tempo", rx.foreach(WorkshopState.detalhe_historico, timeline_row)),
        section(
            "Peças e serviços",
            custos_resumo(),
            itens_table(),
            remove_confirm(),
            rx.cond(
                WorkshopState.can_edit_items,
                item_form(),
                error_callout(WorkshopState.item_error),
            ),
        ),
        section(
            "Histórico desta moto",
            rx.cond(
                WorkshopState.historico_moto.length() > 0,
                rx.vstack(
                    rx.foreach(WorkshopState.historico_moto, historico_moto_row),
                    spacing="0",
                    width="100%",
                ),
                rx.text("Esta é a primeira OS desta moto.", size="2", color=COLORS["muted"]),
            ),
        ),
        width="min(100%, 56rem)",
    )
