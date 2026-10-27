"""Design-system building blocks shared by every page, and the reentrancy guard of page events."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from urllib.parse import quote

import reflex as rx

from Projeto_HarleyStore.services.leitura import url_de_midia
from Projeto_HarleyStore.styles.theme import (
    CARD,
    COLORS,
    DANGER_BUTTON,
    METAL_BUTTON,
    PRIMARY_BUTTON,
    RADII,
    STATUS_COLORS,
    STATUS_FALLBACK,
)


# ----- motorcycle media (Changes 12, 13 and 17) -----

# Remote images that only stand in for a real photo (the catalog seed uses placehold.co).
PLACEHOLDER_HOSTS = ("placehold.co", "placeholder.com", "dummyimage.com")
# Every photo comes from Xano (Change 17). Without one, a neutral image embedded in the page:
# no local file per model, no request that could answer 404.
FOTO_INDISPONIVEL = "data:image/svg+xml," + quote(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000">'
    f'<rect width="1600" height="1000" fill="{COLORS['surface']}"/>'
    f'<text x="800" y="520" fill="{COLORS['muted']}" font-family="sans-serif" font-size="56" '
    'text-anchor="middle">Foto indisponível</text></svg>'
)


def _campo(moto: object, nome: str) -> str:
    valor = moto.get(nome) if isinstance(moto, Mapping) else getattr(moto, nome, None)
    return str(valor or "").strip()


def _foto_real(url: object) -> str:
    """The photo as a safe https URL (``url_de_midia``), or "" for a remote placeholder or a non-web value."""
    url = url_de_midia(url)
    return "" if any(host in url for host in PLACEHOLDER_HOSTS) else url


def get_foto_moto(moto: object, imagem_url: str | None = None) -> str:
    """URL of a motorcycle photo: the color photo, else the model photo from Xano, else the neutral image.

    ``moto`` is a catalog model, a stock unit or a dict with ``imagem_principal``; ``imagem_url``
    is the photo of the chosen color. Placeholders and non-web values are skipped.
    """
    candidatas = (_foto_real(imagem_url), _foto_real(_campo(moto, "imagem_principal")))
    return next((url for url in candidatas if url), FOTO_INDISPONIVEL)


def get_lista_fotos_moto(moto: object, imagem_url: str | None = None) -> list[str]:
    """Photos of the detail carousel: the Xano gallery, else the single photo of ``get_foto_moto``.

    A real ``imagem_url`` (the chosen color) leads the list when the gallery does not have it.
    """
    galeria = moto.get("galeria") if isinstance(moto, Mapping) else getattr(moto, "galeria", None)
    fotos = [url for url in map(_foto_real, galeria or []) if url]
    if not fotos:
        return [get_foto_moto(moto, imagem_url)]
    cor = _foto_real(imagem_url)
    if cor and cor not in fotos:
        fotos.insert(0, cor)
    return fotos


def indice_carrossel(atual: int, passo: int, total: int) -> int:
    """Next carousel position, wrapping at both ends; 0 without photos."""
    return (atual + passo) % total if total else 0


# ----- form and feedback -----


def labeled(label: str, control: rx.Component, **props) -> rx.Component:
    """Stack a muted caption above a form control or value.

    The wrapper is a ``<label>``, so screen readers announce the caption with the control
    and a click on the caption focuses it.
    """
    return rx.el.label(
        rx.vstack(
            rx.text(label, size="2", color=COLORS["muted"]),
            control,
            align="stretch",
            spacing="1",
            width="100%",
        ),
        **{"display": "block", **props},
    )


def error_callout(message: rx.Var) -> rx.Component:
    """Red callout rendered only while the message is not empty; announced by screen readers."""
    return rx.cond(
        message != "",
        rx.callout(message, icon="triangle_alert", color_scheme="red", width="100%", role="alert"),
    )


def operation_is_blocked(
    is_loading_list: bool,
    is_saving: bool,
    is_deactivating: bool,
) -> bool:
    """Return whether a page operation must be rejected as reentrant."""
    return is_loading_list or is_saving or is_deactivating


# ----- buttons -----


def _button(style: dict, *children, **props) -> rx.Component:
    return rx.button(*children, **{**style, **props})


def primary_button(*children, **props) -> rx.Component:
    """Main action: Harley orange with black text."""
    return _button(PRIMARY_BUTTON, *children, **props)


def metal_button(*children, **props) -> rx.Component:
    """Secondary action: brushed metal with an orange glow on hover."""
    return _button(METAL_BUTTON, *children, **props)


def danger_button(*children, **props) -> rx.Component:
    """Destructive action outlined in red."""
    return _button(DANGER_BUTTON, *children, **props)


# ----- layout -----


def page_header(title: str, subtitle: str = "", *actions: rx.Component) -> rx.Component:
    """Module title in uppercase with an optional subtitle and right-aligned actions."""
    return rx.hstack(
        rx.vstack(
            rx.hstack(
                rx.box(width="4px", height="1.75rem", background=COLORS["orange"]),
                rx.heading(title, size="7"),
                align="center",
                spacing="3",
            ),
            rx.text(subtitle, color=COLORS["muted"]) if subtitle else rx.fragment(),
            align="start",
            spacing="1",
        ),
        rx.spacer(),
        *actions,
        width="100%",
        align="center",
        wrap="wrap",
        spacing="3",
    )


def section_title(title: str) -> rx.Component:
    return rx.hstack(
        rx.box(width="3px", height="1rem", background=COLORS["orange"]),
        rx.heading(title, size="3", color=COLORS["text"]),
        align="center",
        spacing="2",
    )


def card(*children: rx.Component, **props) -> rx.Component:
    """High-contrast industrial card."""
    return rx.box(*children, **{**CARD, "padding": "1.25rem", **props})


def modal_header(*title: rx.Component | str, on_close) -> rx.Component:
    """Title row of ``modal_panel``: the title names the dialog, "Fechar" runs ``on_close``."""
    return rx.hstack(
        rx.dialog.title(*title, margin_bottom="0"),
        rx.spacer(),
        metal_button("Fechar", on_click=on_close, size="2"),
        width="100%",
        align="center",
    )


def empty_state(message: str, icon: str = "inbox") -> rx.Component:
    return rx.vstack(
        rx.icon(icon, size=28, color=COLORS["muted"], aria_hidden="true"),
        rx.text(message, color=COLORS["muted"]),
        align="center",
        spacing="2",
        padding="2.5rem 1rem",
        width="100%",
    )


def stat_tile(
    label: str, value: rx.Var | str, accent: bool = False, color: rx.Var | str | None = None
) -> rx.Component:
    """Label over a value; ``accent`` enlarges it in orange, ``color`` overrides the value color."""
    return rx.vstack(
        rx.text(label, size="1", color=COLORS["muted"], text_transform="uppercase", letter_spacing="0.08em"),
        rx.text(
            value,
            font_weight="700",
            size="5" if accent else "4",
            color=color if color is not None else (COLORS["orange"] if accent else COLORS["text"]),
        ),
        spacing="0",
        align="start",
    )


# ----- lists -----


def toolbar(
    search_value: rx.Var,
    on_search,
    placeholder: str,
    *,
    disabled: rx.Var | bool = False,
    current_page: rx.Var | None = None,
    total_pages: rx.Var | None = None,
) -> rx.Component:
    """Search box with the page indicator of paginated lists."""
    page_label = rx.fragment()
    if current_page is not None and total_pages is not None:
        page_label = rx.text(
            rx.cond(total_pages > 1, f"Página {current_page} de {total_pages}", ""),
            size="2",
            color=COLORS["muted"],
        )
    return rx.hstack(
        rx.input(
            rx.input.slot(rx.icon("search", size=16, aria_hidden="true")),
            placeholder=placeholder,
            value=search_value,
            on_change=on_search,
            disabled=disabled,
            type="search",
            aria_label=placeholder.rstrip("…"),
            custom_attrs={"autoComplete": "off"},
            width="min(100%, 30rem)",
        ),
        rx.spacer(),
        page_label,
        width="100%",
        align="center",
    )


def pager(on_previous, on_next, disabled: rx.Var | bool = False) -> rx.Component:
    return rx.hstack(
        metal_button(rx.icon("chevron-left", size=16), "Anterior", on_click=on_previous, disabled=disabled, size="2"),
        metal_button("Próxima", rx.icon("chevron-right", size=16), on_click=on_next, disabled=disabled, size="2"),
        spacing="2",
    )


def _header_cell(header: str | tuple[str, str]) -> rx.Component:
    label, align = header if isinstance(header, tuple) else (header, "left")
    return rx.table.column_header_cell(
        label,
        text_align=align,
        color=COLORS["muted"],
        font_size="0.75rem",
        text_transform="uppercase",
        letter_spacing="0.08em",
    )


def data_table(
    headers: list[str | tuple[str, str]],
    rows: rx.Var,
    render_row: Callable[[rx.Var], rx.Component],
    *,
    empty_text: str,
    loading: rx.Var | None = None,
    loading_text: str = "Carregando…",
) -> rx.Component:
    """Table inside a card, with loading and empty states."""
    table = rx.table.root(
        rx.table.header(rx.table.row(*[_header_cell(header) for header in headers])),
        rx.table.body(rx.foreach(rows, render_row)),
        width="100%",
    )
    content = rx.cond(rows.length() > 0, table, empty_state(empty_text))
    if loading is not None:
        content = rx.cond(
            loading,
            rx.text(loading_text, color=COLORS["muted"], padding="2rem", role="status"),
            content,
        )
    return rx.box(content, width="100%", overflow_x="auto", padding="0 1rem", **CARD)


# ----- status -----


def _badge(label: rx.Var | str, background: str, color: str) -> rx.Component:
    """Matte badge: dark background with text and thin border in the status color."""
    return rx.badge(
        label,
        background=background,
        color=color,
        border=f"1px solid {color}",
        variant="solid",
        radius="small",
        font_weight="700",
        text_transform="uppercase",
        letter_spacing="0.04em",
    )


def status_badge(status: rx.Var, label: rx.Var | str) -> rx.Component:
    """Single badge for every status (service orders and stock motorcycles)."""
    return rx.match(
        status,
        *[(name, _badge(label, background, color)) for name, (background, color) in STATUS_COLORS.items()],
        _badge(label, *STATUS_FALLBACK),
    )


def swatch(hex_color: rx.Var | str, name: rx.Var | str, *, selected: rx.Var | bool = False, on_click=None, size: str = "1.5rem") -> rx.Component:
    """Round color sample; a button when clickable, with the color name for screen readers."""
    hex_var = rx.Var.create(hex_color)
    style = {
        "width": size,
        "height": size,
        "min_width": size,
        "border_radius": RADII["pill"],
        # An unreadable color is read as "" (Change 15): an empty ring, never the button's accent color.
        "background": rx.cond(hex_var == "", "transparent", hex_var),
        # Without a fill the ring alone marks the control: muted reaches 3:1 on the surface, metal_edge does not.
        "border": rx.cond(
            selected,
            f"2px solid {COLORS['orange']}",
            rx.cond(hex_var == "", f"2px dashed {COLORS['muted']}", f"2px solid {COLORS['metal_edge']}"),
        ),
        "box_shadow": rx.cond(selected, f"0 0 0 2px {COLORS['black']} inset", "none"),
        "padding": "0",
        "aria_label": name,
        "custom_attrs": {"title": name},
    }
    if on_click is None:
        return rx.box(**style)
    return rx.button(on_click=on_click, cursor="pointer", **style)


# ----- photo carousel (Change 13) -----


def _seta(icon: str, label: str, on_click, lado: str) -> rx.Component:
    return rx.icon_button(
        rx.icon(icon, size=20, aria_hidden="true"),
        on_click=on_click,
        aria_label=label,
        radius="full",
        size="2",
        position="absolute",
        top="50%",
        transform="translateY(-50%)",
        background=COLORS["overlay"],
        color=COLORS["text"],
        cursor="pointer",
        _hover={"background": COLORS["orange"], "color": COLORS["on_orange"]},
        **{lado: "0.5rem"},
    )


def carrossel_fotos(
    fotos: rx.Var, foto_atual: rx.Var, indice: rx.Var, alt: rx.Var | str, on_anterior, on_proxima, on_selecionar
) -> rx.Component:
    """Hero photo with side arrows and clickable thumbnails (the active one framed in orange)."""
    varias = fotos.length() > 1
    return rx.vstack(
        rx.box(
            rx.image(
                src=foto_atual,
                alt=alt,
                width="100%",
                aspect_ratio="16 / 9",
                object_fit="cover",
                display="block",
                border_radius=RADII["sm"],
            ),
            rx.cond(varias, _seta("chevron-left", "Foto anterior", on_anterior, "left")),
            rx.cond(varias, _seta("chevron-right", "Próxima foto", on_proxima, "right")),
            position="relative",
            width="100%",
        ),
        rx.cond(
            varias,
            rx.hstack(
                rx.foreach(
                    fotos,
                    lambda foto, i: rx.el.button(
                        rx.image(src=foto, alt="", width="4.5rem", aspect_ratio="16 / 9", object_fit="cover", display="block"),
                        on_click=on_selecionar(i),
                        aria_label=f"Ver foto {i + 1}",
                        custom_attrs={"aria-current": rx.cond(i == indice, "true", "false")},
                        border=rx.cond(i == indice, f"2px solid {COLORS['orange']}", "2px solid transparent"),
                        opacity=rx.cond(i == indice, "1", "0.55"),
                        _hover={"opacity": "1"},
                        padding="0",
                        background="none",
                        border_radius=RADII["sm"],
                        overflow="hidden",
                        cursor="pointer",
                        flex_shrink="0",
                    ),
                ),
                spacing="2",
                width="100%",
                overflow_x="auto",
                padding_bottom="0.25rem",
            ),
        ),
        spacing="2",
        width="100%",
    )
