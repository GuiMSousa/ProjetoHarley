"""Public showroom page (/catalogo): hero, family tabs, search and model cards."""

from __future__ import annotations

import reflex as rx

from Projeto_HarleyStore.auth import AuthState
from Projeto_HarleyStore.catalogo_state import FAMILIA_TABS, CatalogoState, ModeloCard
from Projeto_HarleyStore.components import modal_panel, page_body, public_shell
from Projeto_HarleyStore.styles.theme import CARD, COLORS, GRADIENTS, RADII
from Projeto_HarleyStore.ui_helpers import (
    empty_state,
    error_callout,
    metal_button,
    modal_header,
    primary_button,
    swatch,
)
from Projeto_HarleyStore.vendas_state import VENDAS_ROUTE


def _imagem(modelo: ModeloCard) -> rx.Var:
    """Photo of the color chosen on this card, or the model's main photo."""
    return rx.cond(
        CatalogoState.imagem_por_modelo.contains(modelo.id),
        CatalogoState.imagem_por_modelo[modelo.id],
        modelo.imagem,
    )


def _disponibilidade_badge(modelo: ModeloCard) -> rx.Component:
    return rx.badge(
        modelo.disponibilidade,
        variant="solid",
        radius="small",
        color_scheme=rx.cond(modelo.disponivel, "green", "gray"),
        font_weight="700",
        text_transform="uppercase",
    )


def _swatches(modelo: ModeloCard) -> rx.Component:
    return rx.hstack(
        rx.foreach(
            modelo.cores,
            lambda cor: swatch(
                cor.hex,
                cor.nome,
                selected=CatalogoState.cor_por_modelo[modelo.id] == cor.nome,
                on_click=CatalogoState.select_cor(modelo.id, cor.nome, cor.imagem_url),
            ),
        ),
        spacing="2",
        wrap="wrap",
        min_height="1.5rem",
    )


def _can_sell() -> rx.Var:
    """Sellers (routes allowed to reach /vendas) see the reservation shortcut."""
    return AuthState.allowed_routes.contains(VENDAS_ROUTE)


def _cta(modelo: ModeloCard) -> rx.Component:
    """Sellers go to the stock units; visitors are invited to talk to a seller."""
    return rx.cond(
        _can_sell(),
        rx.link(
            primary_button("Reservar", size="2"),
            href=f"{VENDAS_ROUTE}?modelo={modelo.id}",
        ),
        primary_button("Fale com um vendedor", on_click=CatalogoState.open_detail(modelo.id), size="2"),
    )


# ----- hero -----


def hero() -> rx.Component:
    destaque = CatalogoState.hero
    return rx.cond(
        CatalogoState.tem_hero,
        rx.box(
            rx.image(
                src=destaque.imagem,
                alt=destaque.nome,
                position="absolute",
                inset="0",
                width="100%",
                height="100%",
                object_fit="cover",
            ),
            rx.box(position="absolute", inset="0", background=GRADIENTS["hero"]),
            rx.vstack(
                rx.badge("Lançamento", variant="solid", radius="small", font_weight="700", text_transform="uppercase"),
                rx.heading(destaque.nome, size=rx.breakpoints(initial="7", md="9")),
                rx.text(destaque.familia_label, color=COLORS["muted"], text_transform="uppercase", letter_spacing="0.12em"),
                rx.text(destaque.preco_label, color=COLORS["orange"], font_weight="700", size="5"),
                rx.hstack(
                    primary_button("Ver detalhes", on_click=CatalogoState.open_detail(destaque.id), size="3"),
                    spacing="3",
                ),
                position="relative",
                align="start",
                spacing="3",
                max_width="36rem",
                padding=rx.breakpoints(initial="1.5rem", md="3rem"),
            ),
            position="relative",
            overflow="hidden",
            width="100%",
            min_height=rx.breakpoints(initial="22rem", md="30rem"),
            display="flex",
            align_items="flex-end",
            background=COLORS["graphite"],
            border_bottom=f"3px solid {COLORS['orange']}",
        ),
    )


# ----- cards -----


def modelo_card(modelo: ModeloCard) -> rx.Component:
    return rx.box(
        rx.box(
            rx.image(
                src=_imagem(modelo),
                alt=modelo.nome,
                width="100%",
                aspect_ratio="16 / 10",
                object_fit="cover",
                display="block",
            ),
            rx.box(position="absolute", inset="0", background=GRADIENTS["card_image"]),
            rx.box(_disponibilidade_badge(modelo), position="absolute", top="0.75rem", left="0.75rem"),
            position="relative",
            background=COLORS["graphite"],
        ),
        rx.vstack(
            rx.text(
                modelo.familia_label,
                size="1",
                color=COLORS["muted"],
                text_transform="uppercase",
                letter_spacing="0.14em",
            ),
            rx.heading(modelo.nome, size="5"),
            rx.text(modelo.preco_label, color=COLORS["orange"], font_weight="700"),
            _swatches(modelo),
            rx.hstack(
                metal_button("Detalhes", on_click=CatalogoState.open_detail(modelo.id), size="2"),
                _cta(modelo),
                spacing="2",
                wrap="wrap",
            ),
            align="start",
            spacing="3",
            padding="1.25rem",
        ),
        overflow="hidden",
        transition="border-color 0.15s ease",
        _hover={"border_color": COLORS["orange"]},
        **CARD,
    )


def family_tabs() -> rx.Component:
    # On narrow screens the family tabs scroll horizontally instead of overflowing the page.
    return rx.tabs.root(
        rx.tabs.list(
            *[rx.tabs.trigger(label, value=value) for value, label in FAMILIA_TABS],
            overflow_x="auto",
            flex_wrap="nowrap",
        ),
        value=CatalogoState.familia,
        on_change=CatalogoState.set_familia,
        width=rx.breakpoints(initial="100%", md="auto"),
        max_width="100%",
        min_width="0",
    )


def detail_modal() -> rx.Component:
    modelo = CatalogoState.detalhe
    return modal_panel(
        modal_header(modelo.nome, on_close=CatalogoState.close_detail),
        rx.image(
            src=_imagem(modelo),
            alt=modelo.nome,
            width="100%",
            aspect_ratio="16 / 9",
            object_fit="cover",
            border_radius=RADII["md"],
        ),
        rx.hstack(
            rx.vstack(
                rx.text(modelo.familia_label, color=COLORS["muted"], text_transform="uppercase", letter_spacing="0.12em", size="1"),
                rx.text(modelo.preco_label, color=COLORS["orange"], font_weight="700", size="5"),
                spacing="1",
                align="start",
            ),
            rx.spacer(),
            _disponibilidade_badge(modelo),
            width="100%",
            align="center",
        ),
        _swatches(modelo),
        rx.cond(modelo.descricao != "", rx.text(modelo.descricao, color=COLORS["text"])),
        rx.cond(
            _can_sell(),
            rx.hstack(rx.spacer(), _cta(modelo), width="100%"),
            rx.callout(
                "Para reservar esta moto, procure um de nossos vendedores na loja.",
                icon="info",
                width="100%",
            ),
        ),
        width="min(100%, 48rem)",
    )


def catalogo_page() -> rx.Component:
    return public_shell(
        rx.vstack(
            hero(),
            page_body(
                rx.hstack(
                    family_tabs(),
                    rx.spacer(),
                    rx.input(
                        rx.input.slot(rx.icon("search", size=16)),
                        placeholder="Buscar modelo…",
                        value=CatalogoState.busca,
                        on_change=CatalogoState.set_busca,
                        width=rx.breakpoints(initial="100%", md="18rem"),
                    ),
                    width="100%",
                    align="center",
                    wrap="wrap",
                    spacing="3",
                ),
                error_callout(CatalogoState.erro),
                rx.cond(
                    CatalogoState.is_loading_catalogo | ~CatalogoState.carregado,
                    rx.text("Carregando catálogo…", color=COLORS["muted"]),
                    rx.cond(
                        CatalogoState.cards_visiveis.length() > 0,
                        rx.grid(
                            rx.foreach(CatalogoState.cards_visiveis, modelo_card),
                            columns=rx.breakpoints(initial="1", sm="2", lg="3"),
                            spacing="5",
                            width="100%",
                        ),
                        rx.cond(
                            CatalogoState.erro == "",
                            empty_state("Nenhum modelo encontrado para este filtro.", icon="search-x"),
                        ),
                    ),
                ),
                rx.cond(CatalogoState.detalhe_id != "", detail_modal()),
            ),
            spacing="0",
            width="100%",
        ),
    )
