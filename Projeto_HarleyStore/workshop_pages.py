"""Workshop page: service orders, opening form, items and status machine actions."""

from __future__ import annotations

import reflex as rx

from Projeto_HarleyStore.components import guarded_page, modal_panel
from Projeto_HarleyStore.styles.theme import COLORS, PANEL, PRIMARY_BUTTON
from Projeto_HarleyStore.ui_helpers import error_callout, labeled
from Projeto_HarleyStore.workshop_state import (
    STATUS_FILTER_ALL,
    TIPO_OPTIONS,
    WORKSHOP_ROUTE,
    WorkshopState,
)


STATUS_FILTERS = (
    (STATUS_FILTER_ALL, "Todas"),
    ("ABERTA", "Abertas"),
    ("EM_ANDAMENTO", "Em andamento"),
    ("CONCLUIDA", "Concluídas"),
    ("CANCELADA", "Canceladas"),
)


def status_badge(status: rx.Var, label: rx.Var) -> rx.Component:
    return rx.match(
        status,
        ("ABERTA", rx.badge(label, color_scheme="orange", variant="soft")),
        ("EM_ANDAMENTO", rx.badge(label, color_scheme="blue", variant="soft")),
        ("CONCLUIDA", rx.badge(label, color_scheme="green", variant="soft")),
        rx.badge(label, color_scheme="gray", variant="soft"),
    )


def info(label: str, value: rx.Var) -> rx.Component:
    return labeled(label, rx.text(value, color=COLORS["text"]))


# ----- list -----


def status_filter_button(value: str, label: str) -> rx.Component:
    return rx.button(
        label,
        rx.badge(WorkshopState.status_counts[value], variant="surface", color_scheme="gray"),
        on_click=WorkshopState.set_status_filter(value),
        variant=rx.cond(WorkshopState.status_filter == value, "solid", "outline"),
        color_scheme="orange",
        size="2",
    )


def ordem_row(row: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(row["numero"], font_weight="700")),
        rx.table.cell(row["abertura"]),
        rx.table.cell(row["cliente"]),
        rx.table.cell(row["moto"]),
        rx.table.cell(row["tipo"]),
        rx.table.cell(row["mecanico"], color=COLORS["muted"]),
        rx.table.cell(row["total"], text_align="right"),
        rx.table.cell(status_badge(row["status"], row["status_label"])),
        rx.table.cell(
            rx.button(
                "Detalhes",
                on_click=WorkshopState.open_detail(row["id"]),
                variant="outline",
                size="1",
                disabled=WorkshopState.is_busy,
            ),
            text_align="right",
        ),
        align="center",
    )


def ordens_table() -> rx.Component:
    return rx.box(
        rx.cond(
            WorkshopState.is_loading_list,
            rx.text("Carregando ordens de serviço...", color=COLORS["muted"], padding="2rem"),
            rx.cond(
                WorkshopState.visible_rows.length() > 0,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Nº"),
                            rx.table.column_header_cell("Abertura"),
                            rx.table.column_header_cell("Cliente"),
                            rx.table.column_header_cell("Moto"),
                            rx.table.column_header_cell("Tipo"),
                            rx.table.column_header_cell("Mecânico"),
                            rx.table.column_header_cell("Total", text_align="right"),
                            rx.table.column_header_cell("Status"),
                            rx.table.column_header_cell(""),
                        ),
                    ),
                    rx.table.body(rx.foreach(WorkshopState.visible_rows, ordem_row)),
                    width="100%",
                ),
                rx.text("Nenhuma ordem de serviço encontrada.", color=COLORS["muted"], padding="2rem"),
            ),
        ),
        width="100%",
        padding="0 1rem",
        overflow_x="auto",
        **PANEL,
    )


# ----- detail -----


def transition_button(action: rx.Var) -> rx.Component:
    return rx.match(
        action["value"],
        (
            "CANCELADA",
            rx.button(
                action["label"],
                on_click=WorkshopState.start_transition(action["value"]),
                color_scheme="red",
                variant="soft",
                disabled=WorkshopState.is_busy,
            ),
        ),
        rx.button(
            action["label"],
            on_click=WorkshopState.start_transition(action["value"]),
            disabled=WorkshopState.is_busy,
            **PRIMARY_BUTTON,
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
            rx.button(
                rx.cond(WorkshopState.is_transitioning, "Registrando...", "Confirmar"),
                on_click=WorkshopState.confirm_transition,
                disabled=WorkshopState.is_busy,
                **PRIMARY_BUTTON,
            ),
            rx.button("Voltar", on_click=WorkshopState.cancel_transition, variant="outline"),
            spacing="2",
        ),
        align="stretch",
        spacing="3",
        width="100%",
        padding="1rem",
        border=f"1px solid {COLORS['border']}",
        border_radius="8px",
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


# ----- items -----


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
        rx.cond(
            WorkshopState.can_edit_items,
            rx.table.cell(
                rx.button(
                    "Remover",
                    on_click=WorkshopState.ask_remove_item(item["id"]),
                    color_scheme="red",
                    variant="ghost",
                    size="1",
                    disabled=WorkshopState.is_busy,
                ),
                text_align="right",
            ),
        ),
        align="center",
    )


def itens_table() -> rx.Component:
    return rx.cond(
        WorkshopState.detalhe_itens.length() > 0,
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Tipo"),
                    rx.table.column_header_cell("Item"),
                    rx.table.column_header_cell("Qtd.", text_align="right"),
                    rx.table.column_header_cell("Unitário", text_align="right"),
                    rx.table.column_header_cell("Total", text_align="right"),
                    rx.cond(WorkshopState.can_edit_items, rx.table.column_header_cell("")),
                ),
            ),
            rx.table.body(rx.foreach(WorkshopState.detalhe_itens, item_row)),
            width="100%",
        ),
        rx.text("Nenhum item registrado.", size="2", color=COLORS["muted"]),
    )


def remove_confirm() -> rx.Component:
    return rx.cond(
        WorkshopState.item_to_remove != "",
        rx.hstack(
            rx.text(WorkshopState.remove_message, size="2", flex="1"),
            rx.button(
                rx.cond(WorkshopState.is_removing_item, "Removendo...", "Remover"),
                on_click=WorkshopState.confirm_remove_item,
                color_scheme="red",
                size="1",
                disabled=WorkshopState.is_busy,
            ),
            rx.button(
                "Voltar",
                on_click=WorkshopState.cancel_remove_item,
                variant="outline",
                size="1",
            ),
            width="100%",
            align="center",
            padding="0.75rem",
            border=f"1px solid {COLORS['border']}",
            border_radius="8px",
        ),
    )


def custo(label: str, value: rx.Var, **props) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="1", color=COLORS["muted"]),
        rx.text(value, font_weight="700", **props),
        spacing="0",
        align="start",
    )


def custos_resumo() -> rx.Component:
    totais = WorkshopState.detalhe_totais
    return rx.vstack(
        rx.hstack(
            custo("Peças", totais["pecas"]),
            rx.text("+", color=COLORS["muted"]),
            custo("Mão de obra", totais["servicos"]),
            rx.text("=", color=COLORS["muted"]),
            custo("Total OS", totais["total"], color=COLORS["orange"], size="5"),
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
        border=f"1px solid {COLORS['border']}",
        border_radius="8px",
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
            rx.button("Trocar", on_click=WorkshopState.clear_produto, variant="ghost", size="1"),
            width="100%",
            align="end",
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
    )


def item_form() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text("Adicionar item", font_weight="700"),
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
            rx.button(
                rx.cond(WorkshopState.is_saving_item, "Adicionando...", "Adicionar"),
                on_click=WorkshopState.save_item,
                disabled=WorkshopState.is_busy,
                **PRIMARY_BUTTON,
            ),
            width="100%",
        ),
        spacing="3",
        width="100%",
        padding="1rem",
        border=f"1px solid {COLORS['border']}",
        border_radius="8px",
    )


def historico_moto_row(row: rx.Var) -> rx.Component:
    return rx.hstack(
        rx.text(row["numero"], font_weight="700", min_width="3rem"),
        rx.text(row["abertura"], size="2", color=COLORS["muted"], min_width="8rem"),
        rx.text(row["tipo"], size="2", min_width="6rem"),
        status_badge(row["status"], row["status_label"]),
        rx.text(row["descricao"], size="2", color=COLORS["muted"], flex="1", trim="end"),
        rx.button(
            "Ver",
            on_click=WorkshopState.open_detail(row["id"]),
            variant="ghost",
            size="1",
            disabled=WorkshopState.is_busy,
        ),
        width="100%",
        align="center",
        padding="0.4rem 0",
        border_bottom=f"1px solid {COLORS['border']}",
    )


def section(title: str, *children: rx.Component) -> rx.Component:
    return rx.vstack(
        rx.text(title, font_weight="700", color=COLORS["orange"]),
        *children,
        align="stretch",
        spacing="2",
        width="100%",
    )


def detail_modal() -> rx.Component:
    detalhe = WorkshopState.detalhe
    return modal_panel(
        rx.hstack(
            rx.heading("OS ", detalhe["numero"], size="5"),
            status_badge(detalhe["status"], detalhe["status_label"]),
            rx.spacer(),
            rx.button("Fechar", on_click=WorkshopState.close_detail, variant="ghost"),
            width="100%",
            align="center",
        ),
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
            columns="3",
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
        section(
            "Linha do tempo",
            rx.foreach(WorkshopState.detalhe_historico, timeline_row),
        ),
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


# ----- opening -----


def create_modal() -> rx.Component:
    return modal_panel(
        rx.hstack(
            rx.heading("Nova ordem de serviço", size="5"),
            rx.spacer(),
            rx.button("Fechar", on_click=WorkshopState.close_form, variant="ghost"),
            width="100%",
        ),
        error_callout(WorkshopState.form_error),
        labeled(
            "Cliente",
            rx.select(
                WorkshopState.cliente_options,
                value=WorkshopState.cliente,
                on_change=WorkshopState.set_cliente,
                placeholder="Selecione o cliente",
                width="100%",
            ),
        ),
        labeled(
            "Moto do cliente",
            rx.select(
                WorkshopState.moto_options,
                value=WorkshopState.moto,
                on_change=WorkshopState.set_moto,
                placeholder=rx.cond(
                    WorkshopState.cliente == "",
                    "Selecione primeiro o cliente",
                    "Selecione a moto",
                ),
                disabled=WorkshopState.cliente == "",
                width="100%",
            ),
        ),
        rx.hstack(
            labeled(
                "Mecânico responsável",
                rx.select(
                    WorkshopState.mecanico_options,
                    value=WorkshopState.mecanico,
                    on_change=WorkshopState.set_mecanico,
                    placeholder="Selecione o mecânico",
                    width="100%",
                ),
                flex="2",
            ),
            labeled(
                "Tipo de serviço",
                rx.select(
                    TIPO_OPTIONS,
                    value=WorkshopState.tipo_servico,
                    on_change=WorkshopState.set_tipo_servico,
                    placeholder="Preventiva ou corretiva",
                    width="100%",
                ),
                flex="1",
            ),
            width="100%",
        ),
        labeled(
            "Descrição do problema ou serviço",
            rx.text_area(
                value=WorkshopState.descricao_problema,
                on_change=WorkshopState.set_descricao_problema,
                placeholder="Ex.: ruído na embreagem ao trocar de marcha",
                width="100%",
                rows="4",
            ),
        ),
        labeled(
            "Quilometragem (opcional)",
            rx.input(
                value=WorkshopState.quilometragem,
                on_change=WorkshopState.set_quilometragem,
                placeholder="Ex.: 18350",
                type="number",
                min=0,
                width="12rem",
            ),
        ),
        rx.hstack(
            rx.spacer(),
            rx.button("Cancelar", on_click=WorkshopState.close_form, variant="outline"),
            rx.button(
                rx.cond(WorkshopState.is_saving, "Abrindo...", "Abrir OS"),
                on_click=WorkshopState.save_os,
                disabled=WorkshopState.is_busy,
                **PRIMARY_BUTTON,
            ),
            width="100%",
        ),
        width="min(100%, 40rem)",
    )


# ----- page -----


def workshop_page() -> rx.Component:
    return guarded_page(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.heading("Oficina", size="7"),
                    rx.text(
                        "Ordens de serviço das motos de clientes.",
                        color=COLORS["muted"],
                    ),
                    align="start",
                    spacing="1",
                ),
                rx.spacer(),
                rx.cond(
                    WorkshopState.can_operate,
                    rx.button(
                        "Nova OS",
                        on_click=WorkshopState.open_create,
                        disabled=WorkshopState.is_busy,
                        **PRIMARY_BUTTON,
                    ),
                ),
                width="100%",
                align="center",
            ),
            rx.hstack(
                *[status_filter_button(value, label) for value, label in STATUS_FILTERS],
                spacing="2",
                wrap="wrap",
            ),
            rx.hstack(
                rx.input(
                    placeholder="Buscar por nº, cliente, placa, mecânico ou descrição...",
                    value=WorkshopState.search_text,
                    on_change=WorkshopState.set_search_text,
                    disabled=WorkshopState.is_loading_list,
                    width="min(100%, 30rem)",
                ),
                rx.spacer(),
                rx.text(
                    rx.cond(
                        WorkshopState.total_pages > 1,
                        f"Página {WorkshopState.current_page} de {WorkshopState.total_pages}",
                        "",
                    ),
                    size="2",
                    color=COLORS["muted"],
                ),
                width="100%",
            ),
            error_callout(WorkshopState.list_error),
            ordens_table(),
            rx.hstack(
                rx.button("Anterior", on_click=WorkshopState.previous_page, variant="outline", disabled=WorkshopState.is_busy),
                rx.button("Próxima", on_click=WorkshopState.next_page, variant="outline", disabled=WorkshopState.is_busy),
                spacing="2",
            ),
            rx.cond(WorkshopState.detail_open, detail_modal()),
            rx.cond(WorkshopState.form_open, create_modal()),
            align="stretch",
            spacing="5",
            padding="2rem",
            width="100%",
        ),
        WORKSHOP_ROUTE,
    )
