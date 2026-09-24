"""Pages and reusable UI for basic registrations."""

from __future__ import annotations

import reflex as rx

from Projeto_HarleyStore.cadastros_state import CadastrosState
from Projeto_HarleyStore.components import app_shell
from Projeto_HarleyStore.styles.theme import COLORS, PANEL, PRIMARY_BUTTON


SECTIONS = {
    "clientes": ("Clientes", "Pessoas e compradores cadastrados."),
    "motos_clientes": ("Motos de clientes", "Veículos vinculados ao histórico da oficina."),
    "produtos": ("Produtos e peças", "Catálogo, preço de venda e saldo atual."),
    "fornecedores": ("Fornecedores", "Parceiros de abastecimento da operação."),
    "funcionarios": ("Funcionários", "Equipe e tipos de acesso operacional."),
}


def field(label: str, name: str, placeholder: str = "") -> rx.Component:
    return rx.vstack(
        rx.text(label, size="2", color=COLORS["muted"]),
        rx.input(
            value=CadastrosState.form_data[name],
            placeholder=placeholder,
            on_change=lambda value: CadastrosState.set_form_field(name, value),
            width="100%",
        ),
        align="stretch",
        spacing="1",
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
                rx.vstack(
                    rx.text("Cliente existente", size="2", color=COLORS["muted"]),
                    rx.select(
                        CadastrosState.client_options,
                        value=CadastrosState.form_data["id_cliente"],
                        on_change=lambda value: CadastrosState.set_form_field("id_cliente", value),
                        placeholder="Selecione um cliente",
                        width="100%",
                    ),
                    align="stretch",
                    spacing="1",
                    width="100%",
                ),
                field("Modelo", "modelo"),
                field("Placa", "placa"),
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
                    field("Saldo de estoque", "estoque_qtd"),
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
    return rx.box(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.heading("Cadastro", size="5"),
                    rx.spacer(),
                    rx.button("Fechar", on_click=CadastrosState.close_form, variant="ghost"),
                    width="100%",
                ),
                rx.cond(
                    CadastrosState.form_error != "",
                    rx.callout(
                        CadastrosState.form_error,
                        icon="triangle_alert",
                        color_scheme="red",
                        width="100%",
                    ),
                ),
                cadastro_form(),
                rx.hstack(
                    rx.spacer(),
                    rx.button("Cancelar", on_click=CadastrosState.close_form, variant="outline"),
                    rx.button("Salvar", on_click=CadastrosState.save_form, **PRIMARY_BUTTON),
                    width="100%",
                ),
                align="stretch",
                spacing="4",
                width="min(100%, 34rem)",
                max_height="90vh",
                overflow_y="auto",
                padding="1.5rem",
                **PANEL,
            ),
            position="relative",
        ),
        position="fixed",
        inset="0",
        z_index="20",
        display="flex",
        align_items="center",
        justify_content="center",
        padding="1rem",
        background="rgba(0, 0, 0, 0.78)",
    )


def cadastro_row(row: rx.Var, section: str) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(row["primary"], font_weight="700", color=COLORS["text"]),
            rx.text(row["secondary"], size="2", color=COLORS["muted"]),
            align="start",
            spacing="1",
            min_width="12rem",
        ),
        rx.text(row["tertiary"], size="2", color=COLORS["muted"], flex="1"),
        rx.text(row["ativo"], size="2", color=COLORS["orange"]),
        rx.cond(
            CadastrosState.can_write_active,
            rx.hstack(
                rx.button(
                    "Editar",
                    on_click=CadastrosState.open_edit(section, row["id"]),
                    variant="outline",
                    size="2",
                ),
                rx.button(
                    "Desativar",
                    on_click=CadastrosState.deactivate(section, row["id"]),
                    variant="ghost",
                    color=COLORS["danger"],
                    size="2",
                ),
                spacing="2",
            ),
        ),
        width="100%",
        padding="0.8rem 0",
        border_bottom=f"1px solid {COLORS['border']}",
        align="center",
    )


def cadastro_page(section: str) -> rx.Component:
    title, description = SECTIONS[section]
    return app_shell(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.heading(title, size="7"),
                    rx.text(description, color=COLORS["muted"]),
                    align="start",
                    spacing="1",
                ),
                rx.spacer(),
                rx.cond(
                    CadastrosState.can_write_active,
                    rx.button(
                        "Novo cadastro",
                        on_click=CadastrosState.open_create(section),
                        **PRIMARY_BUTTON,
                    ),
                ),
                width="100%",
                align="center",
            ),
            rx.hstack(
                rx.input(
                    placeholder="Buscar neste cadastro...",
                    value=CadastrosState.search_text,
                    on_change=CadastrosState.set_search_text,
                    width="min(100%, 28rem)",
                ),
                rx.spacer(),
                rx.text(
                    rx.cond(
                        CadastrosState.total_pages > 1,
                        f"Página {CadastrosState.current_page} de {CadastrosState.total_pages}",
                        "",
                    ),
                    size="2",
                    color=COLORS["muted"],
                ),
                width="100%",
            ),
            rx.box(
                rx.cond(
                    CadastrosState.visible_rows.length() > 0,
                    rx.vstack(
                        rx.foreach(
                            CadastrosState.visible_rows,
                            lambda row: cadastro_row(row, section),
                        ),
                        align="stretch",
                        width="100%",
                    ),
                    rx.text("Nenhum registro encontrado.", color=COLORS["muted"], padding="2rem"),
                ),
                width="100%",
                padding="0 1rem",
                **PANEL,
            ),
            rx.hstack(
                rx.button("Anterior", on_click=CadastrosState.previous_page, variant="outline"),
                rx.button("Próxima", on_click=CadastrosState.next_page, variant="outline"),
                spacing="2",
            ),
            rx.cond(CadastrosState.form_open, cadastro_modal()),
            align="stretch",
            spacing="5",
            padding="2rem",
            width="100%",
        )
    )
