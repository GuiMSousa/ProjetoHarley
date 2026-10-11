"""Sales page (/vendas): stock units by status, reservations, sales and catalog management."""

from __future__ import annotations

import reflex as rx

from Projeto_HarleyStore.components import guarded_page, modal_panel, page_body
from Projeto_HarleyStore.styles.theme import COLORS, PANEL
from Projeto_HarleyStore.ui_helpers import (
    danger_button,
    data_table,
    error_callout,
    labeled,
    metal_button,
    modal_header,
    page_header,
    primary_button,
    section_title,
    status_badge,
    swatch,
    toolbar,
)
from Projeto_HarleyStore.vendas_state import (
    ABA_ESTOQUE,
    FAMILIA_OPTIONS,
    VENDAS_ROUTE,
    VendasState,
)


ABAS = (("DISPONIVEL", "Disponíveis"), ("RESERVADA", "Reservadas"), ("VENDIDA", "Vendidas"))


def _tab_trigger(value: str, label: str) -> rx.Component:
    return rx.tabs.trigger(
        rx.hstack(
            rx.text(label),
            rx.badge(VendasState.counts[value], variant="surface", color_scheme="gray"),
            spacing="2",
            align="center",
        ),
        value=value,
    )


def abas() -> rx.Component:
    return rx.tabs.root(
        rx.tabs.list(
            *[_tab_trigger(value, label) for value, label in ABAS],
            rx.cond(VendasState.can_manage, rx.tabs.trigger("Estoque", value=ABA_ESTOQUE)),
        ),
        value=VendasState.aba,
        on_change=VendasState.set_aba,
    )


def filtro_modelo() -> rx.Component:
    return rx.cond(
        VendasState.filtro_modelo != "",
        rx.hstack(
            rx.text("Modelo: ", rx.text.strong(VendasState.filtro_modelo_nome), size="2"),
            metal_button(rx.icon("x", size=14), "Limpar filtro", on_click=VendasState.clear_filtro_modelo, size="1"),
            align="center",
            spacing="3",
        ),
    )


# ----- units -----


def _modelo_cell(row: rx.Var) -> rx.Component:
    return rx.hstack(
        rx.cond(row["cor_hex"] != "", swatch(row["cor_hex"], row["cor"], size="1rem")),
        rx.vstack(
            rx.text(row["modelo"], font_weight="700"),
            rx.text(row["familia"], " · ", row["cor"], size="1", color=COLORS["muted"]),
            spacing="0",
            align="start",
        ),
        align="center",
        spacing="2",
    )


def moto_row(row: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(_modelo_cell(row)),
        rx.table.cell(rx.text(row["chassi_curto"], font_family="monospace", custom_attrs={"title": row["chassi"]})),
        rx.table.cell(row["ano"]),
        rx.table.cell(rx.text(row["preco"], color=COLORS["orange"], font_weight="700"), text_align="right"),
        rx.table.cell(status_badge(row["status"], row["status_label"])),
        rx.table.cell(row["cliente"]),
        rx.table.cell(
            rx.hstack(
                rx.text(row["validade"], size="2"),
                rx.cond(row["vencida"] == "true", rx.badge("Vencida", color_scheme="red", variant="solid")),
                spacing="2",
                align="center",
            )
        ),
        rx.table.cell(
            rx.hstack(
                metal_button("Detalhes", on_click=VendasState.open_detail(row["id"]), size="1", disabled=VendasState.is_busy),
                rx.cond(
                    row["pode_vender"] == "true",
                    primary_button("Vender", on_click=VendasState.open_venda(row["id"]), size="1", disabled=VendasState.is_busy),
                ),
                rx.cond(
                    row["pode_reservar"] == "true",
                    metal_button("Reservar", on_click=VendasState.open_reserva(row["id"]), size="1", disabled=VendasState.is_busy),
                ),
                rx.cond(
                    row["pode_cancelar"] == "true",
                    danger_button("Cancelar reserva", on_click=VendasState.open_cancelamento(row["id"]), size="1", disabled=VendasState.is_busy),
                ),
                rx.cond(
                    VendasState.can_manage & (VendasState.aba == ABA_ESTOQUE),
                    metal_button("Editar", on_click=VendasState.open_moto_edit(row["id"]), size="1", disabled=VendasState.is_busy),
                ),
                spacing="2",
                justify="end",
                wrap="wrap",
            ),
            text_align="right",
        ),
        align="center",
    )


def motos_table() -> rx.Component:
    return data_table(
        ["Modelo", "Chassi", "Ano", ("Preço", "right"), "Status", "Cliente", "Validade", ("", "right")],
        VendasState.visible_rows,
        moto_row,
        empty_text="Nenhuma moto nesta situação.",
        loading=VendasState.is_loading_list,
        loading_text="Carregando estoque de motos…",
    )


# ----- catalog management -----


def modelo_row(row: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.text(row["nome"], font_weight="700"),
                rx.cond(row["destaque"] != "", rx.badge(row["destaque"], variant="solid")),
                spacing="2",
                align="center",
            )
        ),
        rx.table.cell(row["familia"]),
        rx.table.cell(row["preco_base"], text_align="right"),
        rx.table.cell(row["cores"], color=COLORS["muted"]),
        rx.table.cell(status_badge(row["status"], row["ativo"])),
        rx.table.cell(
            rx.hstack(
                metal_button("Editar", on_click=VendasState.open_modelo_edit(row["id"]), size="1", disabled=VendasState.is_busy),
                rx.cond(
                    row["ativo_valor"] == "true",
                    danger_button("Retirar", on_click=VendasState.toggle_modelo_ativo(row["id"], row["ativo_valor"]), size="1", disabled=VendasState.is_busy),
                    metal_button("Reativar", on_click=VendasState.toggle_modelo_ativo(row["id"], row["ativo_valor"]), size="1", disabled=VendasState.is_busy),
                ),
                spacing="2",
                justify="end",
            ),
            text_align="right",
        ),
        align="center",
    )


def estoque_panel() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            section_title("Modelos do catálogo"),
            rx.spacer(),
            primary_button(rx.icon("plus", size=14), "Novo modelo", on_click=VendasState.open_modelo_create, size="2"),
            width="100%",
            align="center",
        ),
        data_table(
            ["Modelo", "Família", ("Preço base", "right"), "Cores", "Situação", ("", "right")],
            VendasState.modelos,
            modelo_row,
            empty_text="Nenhum modelo cadastrado.",
        ),
        rx.hstack(
            section_title("Unidades em estoque"),
            rx.spacer(),
            primary_button(rx.icon("plus", size=14), "Nova unidade", on_click=VendasState.open_moto_create, size="2"),
            width="100%",
            align="center",
        ),
        motos_table(),
        spacing="4",
        align="stretch",
        width="100%",
    )


# ----- modals -----


def reserva_modal() -> rx.Component:
    return modal_panel(
        modal_header("Reservar moto", on_close=VendasState.close_reserva),
        error_callout(VendasState.reserva_error),
        labeled(
            "Cliente",
            rx.select(
                VendasState.cliente_options,
                value=VendasState.reserva_cliente,
                on_change=VendasState.set_reserva_cliente,
                placeholder="Selecione o cliente",
                width="100%",
            ),
        ),
        labeled(
            "Validade da reserva (dias)",
            rx.input(
                value=VendasState.reserva_dias,
                on_change=VendasState.set_reserva_dias,
                type="number",
                min=1,
                max=30,
                width="8rem",
            ),
        ),
        labeled(
            "Observação (opcional)",
            rx.text_area(
                value=VendasState.reserva_observacao,
                on_change=VendasState.set_reserva_observacao,
                placeholder="Ex.: sinal combinado, retirada na sexta",
                max_length=500,
                width="100%",
            ),
        ),
        rx.text("O vendedor e o prazo são registrados pelo servidor.", size="1", color=COLORS["muted"]),
        rx.hstack(
            rx.spacer(),
            metal_button("Cancelar", on_click=VendasState.close_reserva),
            primary_button(
                rx.cond(VendasState.is_reserving, "Reservando…", "Confirmar reserva"),
                on_click=VendasState.confirm_reserva,
                disabled=VendasState.is_busy,
            ),
            width="100%",
        ),
    )


def cancelamento_modal() -> rx.Component:
    return modal_panel(
        modal_header("Cancelar reserva", on_close=VendasState.close_cancelamento),
        error_callout(VendasState.cancel_error),
        labeled(
            "Motivo do cancelamento",
            rx.text_area(
                value=VendasState.cancel_motivo,
                on_change=VendasState.set_cancel_motivo,
                placeholder="Explique por que a reserva está sendo cancelada",
                max_length=500,
                width="100%",
            ),
        ),
        rx.hstack(
            rx.spacer(),
            metal_button("Voltar", on_click=VendasState.close_cancelamento),
            danger_button(
                rx.cond(VendasState.is_cancelling, "Cancelando…", "Cancelar reserva"),
                on_click=VendasState.confirm_cancelamento,
                disabled=VendasState.is_busy,
            ),
            width="100%",
        ),
    )


def _venda_resumo() -> rx.Component:
    resumo = VendasState.venda_resumo
    return rx.hstack(
        rx.vstack(
            rx.text(resumo["modelo"], font_weight="700"),
            rx.text(resumo["familia"], " · ", resumo["cor"], " · ", resumo["ano"], size="1", color=COLORS["muted"]),
            rx.text(resumo["chassi"], size="1", font_family="monospace", color=COLORS["muted"]),
            spacing="0",
            align="start",
        ),
        rx.spacer(),
        rx.vstack(
            rx.text("Preço de tabela", size="1", color=COLORS["muted"]),
            rx.text(resumo["preco"], color=COLORS["orange"], font_weight="700"),
            spacing="0",
            align="end",
        ),
        width="100%",
        align="center",
        padding="0.75rem",
        **PANEL,
    )


def venda_modal() -> rx.Component:
    return modal_panel(
        modal_header("Fechar venda", on_close=VendasState.close_venda),
        error_callout(VendasState.venda_error),
        _venda_resumo(),
        labeled(
            "Cliente",
            rx.select(
                VendasState.cliente_options,
                value=VendasState.venda_cliente,
                on_change=VendasState.set_venda_cliente,
                placeholder="Selecione o cliente",
                disabled=VendasState.venda_cliente_fixo,
                width="100%",
            ),
        ),
        rx.cond(
            VendasState.venda_cliente_fixo,
            rx.text("Unidade reservada: só pode ser vendida ao cliente da reserva.", size="1", color=COLORS["muted"]),
        ),
        rx.hstack(
            labeled(
                "Valor da venda (R$)",
                rx.input(
                    value=VendasState.venda_valor,
                    on_change=VendasState.set_venda_valor,
                    placeholder="189900,00",
                    width="100%",
                ),
                flex="1",
                min_width="10rem",
            ),
            labeled(
                "Placa (opcional)",
                rx.input(
                    value=VendasState.venda_placa,
                    on_change=VendasState.set_venda_placa,
                    placeholder="ABC1D23",
                    max_length=8,
                    font_family="monospace",
                    width="100%",
                ),
                flex="1",
                min_width="9rem",
            ),
            width="100%",
            wrap="wrap",
        ),
        labeled(
            "Observação (opcional)",
            rx.text_area(
                value=VendasState.venda_observacao,
                on_change=VendasState.set_venda_observacao,
                placeholder="Ex.: pagamento à vista, entrega na sexta",
                max_length=500,
                width="100%",
            ),
        ),
        rx.text(
            "Moto 0 km pode sair sem placa. O vendedor vem do seu login; a moto passa a vendida, "
            "entra nas motos do cliente e gera a transação financeira.",
            size="1",
            color=COLORS["muted"],
        ),
        rx.hstack(
            rx.spacer(),
            metal_button("Cancelar", on_click=VendasState.close_venda),
            primary_button(
                rx.cond(VendasState.is_selling, "Registrando venda…", "Confirmar venda"),
                on_click=VendasState.confirm_venda,
                disabled=VendasState.is_busy,
            ),
            width="100%",
        ),
        width="min(100%, 36rem)",
    )


def timeline_row(evento: rx.Var) -> rx.Component:
    return rx.hstack(
        status_badge(evento["status"], evento["para"]),
        rx.vstack(
            rx.text(evento["de"], " → ", evento["para"], size="2"),
            rx.text(evento["quando"], " · ", evento["funcionario"], size="1", color=COLORS["muted"]),
            rx.cond(evento["observacao"] != "", rx.text(evento["observacao"], size="1", color=COLORS["muted"])),
            spacing="0",
            align="start",
        ),
        align="start",
        spacing="3",
        width="100%",
    )


def detail_modal() -> rx.Component:
    detalhe = VendasState.detalhe
    return modal_panel(
        modal_header(detalhe["modelo"], on_close=VendasState.close_detail),
        status_badge(detalhe["status"], detalhe["status_label"]),
        rx.grid(
            labeled("Chassi", rx.text(detalhe["chassi"], font_family="monospace")),
            labeled("Cor", rx.text(detalhe["cor"])),
            labeled("Ano", rx.text(detalhe["ano"])),
            labeled("Preço", rx.text(detalhe["preco"], color=COLORS["orange"], font_weight="700")),
            labeled("Cliente", rx.text(detalhe["cliente"])),
            labeled("Vendedor", rx.text(detalhe["vendedor"])),
            labeled("Validade da reserva", rx.text(detalhe["validade"])),
            columns=rx.breakpoints(initial="1", sm="2"),
            spacing="4",
            width="100%",
        ),
        section_title("Linha do tempo"),
        rx.foreach(VendasState.detalhe_historico, timeline_row),
        width="min(100%, 40rem)",
    )


def _cor_row(cor: rx.Var, index: rx.Var) -> rx.Component:
    return rx.hstack(
        swatch(cor["hex"], cor["nome"], size="1.75rem"),
        rx.input(
            value=cor["nome"],
            on_change=lambda value: VendasState.set_cor_field(index, "nome", value),
            placeholder="Nome da cor",
            aria_label="Nome da cor",
            width="10rem",
        ),
        rx.input(
            value=cor["hex"],
            on_change=lambda value: VendasState.set_cor_field(index, "hex", value),
            placeholder="#RRGGBB",
            aria_label="Cor em hexadecimal (#RRGGBB)",
            width="7rem",
            font_family="monospace",
        ),
        rx.input(
            value=cor["imagem_url"],
            on_change=lambda value: VendasState.set_cor_field(index, "imagem_url", value),
            placeholder="https://… foto nesta cor",
            aria_label="URL da foto nesta cor",
            flex="1",
            min_width="12rem",
        ),
        rx.icon_button(
            rx.icon("trash-2"),
            on_click=VendasState.remove_cor(index),
            variant="ghost",
            color_scheme="red",
            aria_label="Remover cor",
        ),
        width="100%",
        align="center",
        wrap="wrap",
    )


def modelo_form_modal() -> rx.Component:
    dados = VendasState.modelo_dados
    return modal_panel(
        modal_header(
            rx.cond(VendasState.modelo_editing_id == "", "Novo modelo", "Editar modelo"),
            on_close=VendasState.close_modelo_form,
        ),
        error_callout(VendasState.modelo_error),
        rx.hstack(
            labeled(
                "Nome do modelo",
                rx.input(
                    value=dados["nome_modelo"],
                    on_change=lambda value: VendasState.set_modelo_field("nome_modelo", value),
                    width="100%",
                ),
                flex="2",
                min_width="12rem",
            ),
            labeled(
                "Família",
                rx.select(
                    FAMILIA_OPTIONS,
                    value=dados["familia"],
                    on_change=lambda value: VendasState.set_modelo_field("familia", value),
                    placeholder="Selecione",
                    width="100%",
                ),
                flex="1",
                min_width="9rem",
            ),
            width="100%",
            wrap="wrap",
        ),
        rx.hstack(
            labeled(
                "Preço base (R$)",
                rx.input(
                    value=dados["preco_base"],
                    on_change=lambda value: VendasState.set_modelo_field("preco_base", value),
                    placeholder="189900,00",
                    width="100%",
                ),
                flex="1",
                min_width="9rem",
            ),
            rx.hstack(
                rx.switch(
                    checked=dados["destaque"] == "true",
                    on_change=VendasState.set_modelo_destaque,
                    aria_label="Destaque no hero da vitrine",
                ),
                rx.text("Destaque no hero da vitrine", size="2"),
                align="center",
                spacing="2",
            ),
            width="100%",
            align="end",
            wrap="wrap",
        ),
        labeled(
            "Imagem principal (URL https)",
            rx.input(
                value=dados["imagem_principal"],
                on_change=lambda value: VendasState.set_modelo_field("imagem_principal", value),
                placeholder="https://… imagem própria ou licenciada",
                width="100%",
            ),
        ),
        labeled(
            "Descrição",
            rx.text_area(
                value=dados["descricao"],
                on_change=lambda value: VendasState.set_modelo_field("descricao", value),
                max_length=2000,
                width="100%",
            ),
        ),
        rx.hstack(
            section_title("Variações de cor"),
            rx.spacer(),
            metal_button(rx.icon("plus", size=14), "Adicionar cor", on_click=VendasState.add_cor, size="1"),
            width="100%",
            align="center",
        ),
        rx.vstack(
            rx.foreach(VendasState.modelo_cores, _cor_row),
            spacing="2",
            width="100%",
            padding="0.75rem",
            **PANEL,
        ),
        rx.hstack(
            rx.spacer(),
            metal_button("Cancelar", on_click=VendasState.close_modelo_form),
            primary_button(
                rx.cond(VendasState.is_saving_modelo, "Salvando…", "Salvar modelo"),
                on_click=VendasState.save_modelo,
                disabled=VendasState.is_busy,
            ),
            width="100%",
        ),
        width="min(100%, 52rem)",
    )


def moto_form_modal() -> rx.Component:
    dados = VendasState.moto_dados
    return modal_panel(
        modal_header(
            rx.cond(VendasState.moto_editing_id == "", "Nova unidade", "Editar unidade"),
            on_close=VendasState.close_moto_form,
        ),
        error_callout(VendasState.moto_error),
        rx.cond(
            VendasState.moto_editing_id == "",
            labeled(
                "Modelo",
                rx.select(
                    VendasState.modelo_options,
                    value=dados["modelo"],
                    on_change=lambda value: VendasState.set_moto_field("modelo", value),
                    placeholder="Selecione um modelo ativo",
                    width="100%",
                ),
            ),
        ),
        labeled(
            "Chassi (VIN, 17 caracteres)",
            rx.input(
                value=dados["chassi"],
                on_change=lambda value: VendasState.set_moto_field("chassi", value),
                placeholder="1HD1KTP19RB600001",
                font_family="monospace",
                max_length=17,
                width="100%",
            ),
        ),
        labeled(
            "Cor",
            rx.cond(
                VendasState.cor_options.length() > 0,
                rx.select(
                    VendasState.cor_options,
                    value=dados["cor"],
                    on_change=lambda value: VendasState.set_moto_field("cor", value),
                    placeholder="Selecione a cor",
                    width="100%",
                ),
                rx.input(
                    value=dados["cor"],
                    on_change=lambda value: VendasState.set_moto_field("cor", value),
                    width="100%",
                ),
            ),
        ),
        rx.hstack(
            labeled(
                "Ano do modelo",
                rx.input(
                    value=dados["ano_modelo"],
                    on_change=lambda value: VendasState.set_moto_field("ano_modelo", value),
                    type="number",
                    width="100%",
                ),
                flex="1",
            ),
            labeled(
                "Preço de venda (R$)",
                rx.input(
                    value=dados["preco_venda"],
                    on_change=lambda value: VendasState.set_moto_field("preco_venda", value),
                    placeholder="189900,00",
                    width="100%",
                ),
                flex="1",
            ),
            width="100%",
        ),
        rx.text(
            "A unidade nasce disponível; o status muda somente por reserva, cancelamento e venda.",
            size="1",
            color=COLORS["muted"],
        ),
        rx.hstack(
            rx.spacer(),
            metal_button("Cancelar", on_click=VendasState.close_moto_form),
            primary_button(
                rx.cond(VendasState.is_saving_moto, "Salvando…", "Salvar unidade"),
                on_click=VendasState.save_moto,
                disabled=VendasState.is_busy,
            ),
            width="100%",
        ),
        width="min(100%, 36rem)",
    )


def vendas_page() -> rx.Component:
    return guarded_page(
        page_body(
            page_header(
                "Vendas de motos",
                "Unidades em estoque, reservas, fechamento de vendas e catálogo da vitrine.",
                rx.link(metal_button(rx.icon("store", size=14), "Ver vitrine"), href="/catalogo"),
            ),
            abas(),
            filtro_modelo(),
            toolbar(
                VendasState.busca,
                VendasState.set_busca,
                "Buscar por modelo, chassi ou cliente…",
                disabled=VendasState.is_loading_list,
            ),
            error_callout(VendasState.list_error),
            rx.cond(VendasState.aba == ABA_ESTOQUE, estoque_panel(), motos_table()),
            rx.cond(VendasState.reserva_moto_id != "", reserva_modal()),
            rx.cond(VendasState.cancel_moto_id != "", cancelamento_modal()),
            rx.cond(VendasState.venda_moto_id != "", venda_modal()),
            rx.cond(VendasState.detail_open, detail_modal()),
            rx.cond(VendasState.modelo_form_open, modelo_form_modal()),
            rx.cond(VendasState.moto_form_open, moto_form_modal()),
        ),
        VENDAS_ROUTE,
    )
