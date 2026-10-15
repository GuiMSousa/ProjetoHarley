"""Workshop page: service order list, status filters and the opening form.

The order detail (transitions, timeline, parts and labor) lives in workshop_detail.py.
"""

from __future__ import annotations

import reflex as rx

from Projeto_HarleyStore.components import guarded_page, modal_panel, page_body
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
    status_badge,
    toolbar,
)
from Projeto_HarleyStore.workshop_detail import detail_modal
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


def status_filter_button(value: str, label: str) -> rx.Component:
    content = (
        label,
        rx.badge(WorkshopState.status_counts[value], variant="surface", color_scheme="gray"),
    )
    return rx.cond(
        WorkshopState.status_filter == value,
        primary_button(*content, on_click=WorkshopState.set_status_filter(value), size="2"),
        metal_button(*content, on_click=WorkshopState.set_status_filter(value), size="2"),
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
            metal_button(
                "Detalhes",
                on_click=WorkshopState.open_detail(row["id"]),
                size="1",
                disabled=WorkshopState.is_busy,
            ),
            text_align="right",
        ),
        align="center",
    )


def create_modal() -> rx.Component:
    return modal_panel(
        modal_header("Nova ordem de serviço", on_close=WorkshopState.close_form),
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
                min_width="12rem",
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
                min_width="10rem",
            ),
            width="100%",
            wrap="wrap",
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
            metal_button("Cancelar", on_click=WorkshopState.close_form),
            primary_button(
                rx.cond(WorkshopState.is_saving, "Abrindo…", "Abrir OS"),
                on_click=WorkshopState.save_os,
                disabled=WorkshopState.is_busy,
            ),
            width="100%",
        ),
        width="min(100%, 40rem)",
        on_close=WorkshopState.close_form,
    )


def workshop_page() -> rx.Component:
    return guarded_page(
        page_body(
            page_header(
                "Oficina",
                "Ordens de serviço das motos de clientes.",
                rx.cond(
                    WorkshopState.can_operate,
                    primary_button(
                        rx.icon("plus", size=16),
                        "Nova OS",
                        on_click=WorkshopState.open_create,
                        disabled=WorkshopState.is_busy,
                    ),
                ),
            ),
            rx.hstack(
                *[status_filter_button(value, label) for value, label in STATUS_FILTERS],
                spacing="2",
                wrap="wrap",
            ),
            toolbar(
                WorkshopState.search_text,
                WorkshopState.set_search_text,
                "Buscar por nº, cliente, placa, mecânico ou descrição…",
                disabled=WorkshopState.is_loading_list,
                current_page=WorkshopState.current_page,
                total_pages=WorkshopState.total_pages,
            ),
            error_callout(WorkshopState.list_error),
            data_table(
                [
                    "Nº",
                    "Abertura",
                    "Cliente",
                    "Moto",
                    "Tipo",
                    "Mecânico",
                    ("Total", "right"),
                    "Status",
                    ("", "right"),
                ],
                WorkshopState.visible_rows,
                ordem_row,
                empty_text="Nenhuma ordem de serviço encontrada.",
                loading=WorkshopState.is_loading_list,
                loading_text="Carregando ordens de serviço…",
            ),
            pager(WorkshopState.previous_page, WorkshopState.next_page, WorkshopState.is_busy),
            rx.cond(WorkshopState.detail_open, detail_modal()),
            rx.cond(WorkshopState.form_open, create_modal()),
        ),
        WORKSHOP_ROUTE,
    )
