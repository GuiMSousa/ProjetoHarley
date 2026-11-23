"""Page /admin (Change 18, GERENTE): access accounts, access audit and read-only system rules."""

from __future__ import annotations

import reflex as rx

from Projeto_HarleyStore.admin_state import ADMIN_ROUTE, AdminState
from Projeto_HarleyStore.components import guarded_page, modal_panel, page_body
from Projeto_HarleyStore.services.admin import PARAMETROS_SISTEMA
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
)

PASSWORD_ATTRS = {"autoComplete": "new-password"}
# Below `lg` each user is one stacked cell (name, email, type, status, actions): measured on 2026-11-23,
# hiding only Email and Tipo still left the actions 107px off a 320px screen. From `lg`, the full table.
COLUNA_LARGA = {"display": rx.breakpoints(initial="none", lg="table-cell")}
SO_COMPACTO = {"display": rx.breakpoints(initial="flex", lg="none")}


def nota(texto: str) -> rx.Component:
    return rx.text(texto, size="1", color=COLORS["muted"])


# ----- users and access -----


def acoes_usuario(row: rx.Var, justify: str) -> rx.Component:
    """Row actions; rendered once per layout, the hidden one leaves the accessibility tree (display none)."""
    return rx.hstack(
        rx.cond(
            row["pode_redefinir"] == "true",
            metal_button(
                "Redefinir senha",
                on_click=AdminState.open_senha(row["id"], row["nome"]),
                size="1",
                disabled=AdminState.is_busy,
                aria_label=f"Redefinir senha de {row['nome']}",
            ),
        ),
        rx.cond(
            row["pode_alternar"] == "true",
            rx.cond(
                row["ativo"] == "true",
                danger_button(
                    "Desativar acesso",
                    on_click=AdminState.open_status(row["id_funcionario"], row["nome"]),
                    size="1",
                    disabled=AdminState.is_busy,
                    aria_label=f"Desativar acesso de {row['nome']}",
                ),
                metal_button(
                    "Reativar acesso",
                    on_click=AdminState.open_status(row["id_funcionario"], row["nome"]),
                    size="1",
                    disabled=AdminState.is_busy,
                    aria_label=f"Reativar acesso de {row['nome']}",
                ),
            ),
        ),
        rx.cond(row["proprio"] == "true", nota("Seu acesso")),
        spacing="2",
        justify=justify,
        wrap="wrap",
    )


def usuario_row(row: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.vstack(
                rx.text(row["nome"], font_weight="700"),
                rx.vstack(
                    rx.text(row["email"], size="1", color=COLORS["muted"], word_break="break-all"),
                    rx.text(row["tipo"], size="1", color=COLORS["muted"]),
                    status_badge(row["status"], row["status_label"]),
                    acoes_usuario(row, "start"),
                    spacing="2",
                    align="start",
                    **SO_COMPACTO,
                ),
                spacing="1",
                align="start",
            ),
        ),
        rx.table.cell(row["email"], word_break="break-all", **COLUNA_LARGA),
        rx.table.cell(row["tipo"], color=COLORS["muted"], **COLUNA_LARGA),
        rx.table.cell(status_badge(row["status"], row["status_label"]), **COLUNA_LARGA),
        rx.table.cell(acoes_usuario(row, "end"), text_align="right", **COLUNA_LARGA),
        align="center",
    )


def usuarios_tab() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            nota("Desativar o acesso corta na hora todas as operações do funcionário e o próximo login."),
            rx.spacer(),
            primary_button(
                rx.icon("user-plus", size=16),
                "Criar acesso",
                on_click=AdminState.open_acesso,
                disabled=AdminState.is_busy,
            ),
            width="100%",
            align="center",
            wrap="wrap",
        ),
        error_callout(AdminState.usuarios_error),
        data_table(
            [
                "Funcionário",
                ("Email", "left", COLUNA_LARGA),
                ("Tipo", "left", COLUNA_LARGA),
                ("Status", "left", COLUNA_LARGA),
                ("", "right", COLUNA_LARGA),
            ],
            AdminState.usuarios,
            usuario_row,
            empty_text="Nenhum usuário encontrado.",
            loading=AdminState.is_loading_usuarios,
            loading_text="Carregando usuários…",
        ),
        spacing="4",
        width="100%",
        align="stretch",
    )


def acesso_modal() -> rx.Component:
    return modal_panel(
        modal_header("Criar acesso", on_close=AdminState.close_acesso),
        error_callout(AdminState.acesso_error),
        labeled(
            "Funcionário ativo sem acesso",
            rx.select(
                AdminState.acesso_options,
                value=AdminState.acesso_funcionario,
                on_change=AdminState.set_acesso_funcionario,
                placeholder="Selecione o funcionário",
                width="100%",
            ),
        ),
        labeled(
            "Email de acesso",
            rx.input(
                value=AdminState.acesso_email,
                on_change=AdminState.set_acesso_email,
                type="email",
                placeholder="nome@loja.com.br",
                custom_attrs={"autoComplete": "off"},
                width="100%",
            ),
        ),
        labeled(
            "Senha temporária",
            rx.input(
                value=AdminState.acesso_senha,
                on_change=AdminState.set_acesso_senha,
                type="password",
                custom_attrs=PASSWORD_ATTRS,
                width="100%",
            ),
        ),
        labeled(
            "Confirme a senha",
            rx.input(
                value=AdminState.acesso_confirmacao,
                on_change=AdminState.set_acesso_confirmacao,
                type="password",
                custom_attrs=PASSWORD_ATTRS,
                width="100%",
            ),
        ),
        nota("Mínimo de 8 caracteres, com ao menos uma letra e um número."),
        nota("Informe a senha ao funcionário pessoalmente: o sistema não a envia por email."),
        rx.hstack(
            rx.spacer(),
            metal_button("Cancelar", on_click=AdminState.close_acesso),
            primary_button(
                rx.cond(AdminState.is_saving, "Criando acesso…", "Criar acesso"),
                on_click=AdminState.save_acesso,
                disabled=AdminState.is_busy,
            ),
            width="100%",
            wrap="wrap",
        ),
        on_close=AdminState.close_acesso,
    )


def senha_modal() -> rx.Component:
    return modal_panel(
        modal_header("Redefinir senha de ", AdminState.senha_usuario_nome, on_close=AdminState.close_senha),
        error_callout(AdminState.senha_error),
        labeled(
            "Nova senha temporária",
            rx.input(
                value=AdminState.senha_nova,
                on_change=AdminState.set_senha_nova,
                type="password",
                custom_attrs=PASSWORD_ATTRS,
                width="100%",
            ),
        ),
        labeled(
            "Confirme a senha",
            rx.input(
                value=AdminState.senha_confirmacao,
                on_change=AdminState.set_senha_confirmacao,
                type="password",
                custom_attrs=PASSWORD_ATTRS,
                width="100%",
            ),
        ),
        nota("Mínimo de 8 caracteres, com ao menos uma letra e um número."),
        # S3 and S4 (design.md of Change 18).
        rx.callout(
            "A sessão já aberta do usuário continua válida até expirar. Para cortar o acesso na hora, desative o acesso.",
            icon="info",
            color_scheme="gray",
            width="100%",
        ),
        nota("Informe a senha temporária ao funcionário pessoalmente: o sistema não a envia por email."),
        rx.hstack(
            rx.spacer(),
            metal_button("Cancelar", on_click=AdminState.close_senha),
            primary_button(
                rx.cond(AdminState.is_saving, "Redefinindo…", "Redefinir senha"),
                on_click=AdminState.save_senha,
                disabled=AdminState.is_busy,
            ),
            width="100%",
            wrap="wrap",
        ),
        on_close=AdminState.close_senha,
    )


def status_modal() -> rx.Component:
    return modal_panel(
        modal_header(
            rx.cond(AdminState.status_ativar, "Reativar acesso de ", "Desativar acesso de "),
            AdminState.status_nome,
            on_close=AdminState.close_status,
        ),
        rx.cond(
            AdminState.status_ativar,
            rx.text("O funcionário volta a entrar e a operar conforme o tipo dele."),
            rx.vstack(
                rx.text("O funcionário perde na hora todas as operações e não consegue mais entrar."),
                # Review L5: deactivating the access deactivates the employee record itself.
                nota(
                    "Ele também sai das listas operacionais: deixa de aparecer na escolha de mecânico das novas OS "
                    "e não registra vendas, OS nem entradas até ser reativado."
                ),
                spacing="2",
                align="stretch",
            ),
        ),
        # S2 (design.md of Change 18).
        rx.cond(
            AdminState.status_ultimo_gerente,
            rx.callout(
                "Este é o último gerente ativo com acesso. Sem ele, só o painel do Xano recupera a administração.",
                icon="triangle_alert",
                color_scheme="red",
                width="100%",
                role="alert",
            ),
        ),
        rx.hstack(
            rx.spacer(),
            metal_button("Cancelar", on_click=AdminState.close_status),
            rx.cond(
                AdminState.status_ativar,
                primary_button(
                    rx.cond(AdminState.is_saving, "Reativando…", "Reativar acesso"),
                    on_click=AdminState.confirm_status,
                    disabled=AdminState.is_busy,
                ),
                danger_button(
                    rx.cond(AdminState.is_saving, "Desativando…", "Desativar acesso"),
                    on_click=AdminState.confirm_status,
                    disabled=AdminState.is_busy,
                ),
            ),
            width="100%",
            wrap="wrap",
        ),
        on_close=AdminState.close_status,
    )


# ----- access audit -----


def evento_row(row: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(row["data"], white_space="nowrap"),
        rx.table.cell(rx.text(row["acao"], font_weight="700")),
        rx.table.cell(row["usuario"]),
        rx.table.cell(row["detalhe"], color=COLORS["muted"]),
        align="center",
    )


def auditoria_tab() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            labeled(
                "Ação",
                rx.select(
                    AdminState.acao_options,
                    value=AdminState.filtro_acao,
                    on_change=AdminState.set_filtro_acao,
                    width="100%",
                ),
                flex="2 1 12rem",
                min_width="0",
            ),
            labeled(
                "Início",
                rx.input(type="date", value=AdminState.filtro_inicio, on_change=AdminState.set_filtro_inicio, width="100%"),
                flex="1 1 9rem",
                min_width="0",
            ),
            labeled(
                "Fim",
                rx.input(type="date", value=AdminState.filtro_fim, on_change=AdminState.set_filtro_fim, width="100%"),
                flex="1 1 9rem",
                min_width="0",
            ),
            primary_button(
                rx.cond(AdminState.is_loading_eventos, "Filtrando…", "Filtrar"),
                on_click=AdminState.aplicar_filtros,
                disabled=AdminState.is_busy,
            ),
            width="100%",
            align="end",
            wrap="wrap",
        ),
        nota("O registro cobre logins, criação de acessos e trocas de senha. Vendas, OS e estoque têm histórico próprio."),
        error_callout(AdminState.eventos_error),
        data_table(
            ["Data", "Ação", "Usuário", "Detalhe"],
            AdminState.eventos,
            evento_row,
            empty_text="Nenhum evento no filtro.",
            loading=AdminState.is_loading_eventos,
            loading_text="Carregando eventos…",
        ),
        rx.hstack(
            pager(AdminState.eventos_anterior, AdminState.eventos_proxima, AdminState.is_busy),
            rx.spacer(),
            rx.text("Página ", AdminState.eventos_pagina, " · ", AdminState.eventos_total, size="2", color=COLORS["muted"]),
            width="100%",
            align="center",
            wrap="wrap",
        ),
        spacing="4",
        width="100%",
        align="stretch",
    )


# ----- system rules (read-only) -----

PARAMETROS_ROWS = [
    {"grupo": p["grupo"], "regra": p["regra"], "valor": f"{p['valor']} {p['unidade']}"} for p in PARAMETROS_SISTEMA
]


def parametro_row(row: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(row["grupo"], color=COLORS["muted"]),
        rx.table.cell(rx.text(row["regra"], font_weight="700")),
        rx.table.cell(row["valor"], text_align="right"),
    )


def parametros_tab() -> rx.Component:
    return rx.vstack(
        nota("Regras vigentes, aplicadas pelo servidor. Esta tela só mostra os valores; mudá-los exige uma alteração no sistema."),
        data_table(
            ["Área", "Regra", ("Valor", "right")],
            rx.Var.create(PARAMETROS_ROWS),
            parametro_row,
            empty_text="Nenhuma regra cadastrada.",
        ),
        spacing="4",
        width="100%",
        align="stretch",
    )


def admin_page() -> rx.Component:
    return guarded_page(
        page_body(
            page_header("Administração", "Acessos dos funcionários, auditoria de acessos e regras do sistema."),
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("Usuários e acessos", value="usuarios"),
                    rx.tabs.trigger("Auditoria de acessos", value="auditoria"),
                    rx.tabs.trigger("Parâmetros do sistema", value="parametros"),
                    overflow_x="auto",
                ),
                rx.tabs.content(usuarios_tab(), value="usuarios", padding_top="1rem"),
                rx.tabs.content(auditoria_tab(), value="auditoria", padding_top="1rem"),
                rx.tabs.content(parametros_tab(), value="parametros", padding_top="1rem"),
                value=AdminState.aba,
                on_change=AdminState.set_aba,
                width="100%",
            ),
            rx.cond(AdminState.acesso_open, acesso_modal()),
            rx.cond(AdminState.senha_open, senha_modal()),
            rx.cond(AdminState.status_open, status_modal()),
        ),
        ADMIN_ROUTE,
    )
