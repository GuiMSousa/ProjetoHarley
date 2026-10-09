"""Pages and reusable UI for basic registrations."""

from __future__ import annotations

import reflex as rx

from Projeto_HarleyStore.cadastros_state import SECTION_ROUTES, CadastrosState
from Projeto_HarleyStore.components import guarded_page, modal_panel, page_body
from Projeto_HarleyStore.styles.theme import COLORS
from Projeto_HarleyStore.ui_helpers import (
    danger_button,
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


# section: (title, description, (primary, secondary, tertiary) column headers)
SECTIONS = {
    "clientes": ("Clientes", "Pessoas e compradores cadastrados.", ("Nome", "CPF/CNPJ", "Telefone")),
    "motos_clientes": (
        "Motos de clientes",
        "Veículos vinculados ao histórico da oficina.",
        ("Modelo", "Placa", "Chassi"),
    ),
    "produtos": (
        "Produtos e peças",
        "Catálogo, preço de venda e saldo atual.",
        ("Código", "Produto", "Preço e saldo"),
    ),
    "fornecedores": (
        "Fornecedores",
        "Parceiros de abastecimento da operação.",
        ("Razão social", "CNPJ", "Contato"),
    ),
    "funcionarios": (
        "Funcionários",
        "Equipe e tipos de acesso operacional.",
        ("Nome", "Tipo", "Cargo"),
    ),
}


def field(label: str, name: str, placeholder: str = "") -> rx.Component:
    return labeled(
        label,
        rx.input(
            value=CadastrosState.form_data[name],
            placeholder=placeholder,
            on_change=lambda value: CadastrosState.set_form_field(name, value),
            width="100%",
        ),
        width="100%",
    )


def cadastro_form() -> rx.Component:
    return rx.cond(
        CadastrosState.active_section == "clientes",
        rx.vstack(
            field("Nome", "nome_cliente"),
            field("CPF/CNPJ", "cpf_cnpj"),
            field("Telefone", "telefone"),
            field("Email", "email"),
            field("Endereço", "endereco"),
            align="stretch",
            spacing="3",
        ),
        rx.cond(
            CadastrosState.active_section == "motos_clientes",
            rx.vstack(
                labeled(
                    "Cliente existente",
                    rx.select(
                        CadastrosState.client_options,
                        value=CadastrosState.form_data["id_cliente"],
                        on_change=lambda value: CadastrosState.set_form_field("id_cliente", value),
                        placeholder="Selecione um cliente",
                        width="100%",
                    ),
                    width="100%",
                ),
                field("Modelo", "modelo"),
                field("Placa (opcional)", "placa", "Vazia em moto 0 km ainda sem emplacamento"),
                field("Chassi", "chassi"),
                align="stretch",
                spacing="3",
            ),
            rx.cond(
                CadastrosState.active_section == "produtos",
                rx.vstack(
                    field("Código", "codigo", "SKU ou part number alfanumérico"),
                    field("Nome", "nome_produto"),
                    field("Descrição", "descricao"),
                    field("Categoria", "categoria"),
                    field("Preço de venda", "preco_venda"),
                    rx.cond(
                        CadastrosState.editing_id == "",
                        field("Saldo inicial de estoque", "estoque_qtd"),
                        rx.text(
                            "O saldo de estoque é alterado somente por entradas de mercadoria.",
                            size="2",
                            color=COLORS["muted"],
                        ),
                    ),
                    align="stretch",
                    spacing="3",
                ),
                rx.cond(
                    CadastrosState.active_section == "fornecedores",
                    rx.vstack(
                        field("Razão social", "nome_fornecedor"),
                        field("CNPJ", "cnpj"),
                        field("Contato", "contato"),
                        align="stretch",
                        spacing="3",
                    ),
                    rx.vstack(
                        field("Nome", "nome_funcionario"),
                        field("Cargo", "cargo"),
                        field("Tipo", "tipo", "GERENTE, VENDEDOR ou MECANICO"),
                        field("Contato", "contato"),
                        align="stretch",
                        spacing="3",
                    ),
                ),
            ),
        ),
    )


def cadastro_modal() -> rx.Component:
    return modal_panel(
        modal_header("Cadastro", on_close=CadastrosState.close_form),
        error_callout(CadastrosState.form_error),
        cadastro_form(),
        rx.hstack(
            rx.spacer(),
            metal_button("Cancelar", on_click=CadastrosState.close_form),
            primary_button(
                rx.cond(CadastrosState.is_saving, "Salvando...", "Salvar"),
                on_click=CadastrosState.save_form,
                disabled=CadastrosState.is_busy,
            ),
            width="100%",
        ),
    )


def cadastro_row(row: rx.Var, section: str) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(row["primary"], font_weight="700")),
        rx.table.cell(row["secondary"], color=COLORS["muted"]),
        rx.table.cell(row["tertiary"]),
        rx.table.cell(status_badge(row["status"], row["ativo"])),
        rx.table.cell(
            rx.cond(
                CadastrosState.can_write_active,
                rx.hstack(
                    metal_button(
                        "Editar",
                        on_click=CadastrosState.open_edit(section, row["id"]),
                        size="1",
                        disabled=CadastrosState.is_busy,
                    ),
                    danger_button(
                        "Desativar",
                        on_click=CadastrosState.deactivate(section, row["id"]),
                        size="1",
                        disabled=CadastrosState.is_busy,
                    ),
                    spacing="2",
                    justify="end",
                ),
            ),
            text_align="right",
        ),
        align="center",
    )


def cadastro_page(section: str) -> rx.Component:
    title, description, (primary, secondary, tertiary) = SECTIONS[section]
    return guarded_page(
        page_body(
            page_header(
                title,
                description,
                rx.cond(
                    CadastrosState.can_write_active,
                    primary_button(
                        rx.icon("plus", size=16),
                        "Novo cadastro",
                        on_click=CadastrosState.open_create(section),
                        disabled=CadastrosState.is_busy,
                    ),
                ),
            ),
            toolbar(
                CadastrosState.search_text,
                CadastrosState.set_search_text,
                "Buscar neste cadastro...",
                disabled=CadastrosState.is_loading_list,
                current_page=CadastrosState.current_page,
                total_pages=CadastrosState.total_pages,
            ),
            error_callout(CadastrosState.list_error),
            data_table(
                [primary, secondary, tertiary, "Situação", ("", "right")],
                CadastrosState.visible_rows,
                lambda row: cadastro_row(row, section),
                empty_text="Nenhum registro encontrado.",
                loading=CadastrosState.is_loading_list,
                loading_text="Carregando registros...",
            ),
            pager(CadastrosState.previous_page, CadastrosState.next_page, CadastrosState.is_busy),
            rx.cond(CadastrosState.form_open, cadastro_modal()),
        ),
        SECTION_ROUTES[section],
    )
