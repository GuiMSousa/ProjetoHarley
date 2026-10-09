"""Design tokens of the Harley-Davidson industrial theme (single source of colors).

Every color used by the app lives here or in ``assets/harley.css``; a test rejects
color literals anywhere else. Text/background pairs are checked against WCAG AA.
"""

from __future__ import annotations

import reflex as rx


COLORS = {
    "black": "#000000",  # asphalt: app background
    "graphite": "#121212",  # matte black: sidebar, top bar, sections
    "surface": "#1A1A1A",  # industrial gray: cards, tables, modals
    "surface_alt": "#232323",  # alternate rows and hover
    "border": "#2E2E2E",
    "metal_edge": "#3A3A3A",
    "orange": "#FF6600",  # Harley orange: accent and primary action
    "orange_hover": "#FF7A1F",
    "orange_active": "#E65C00",
    "text": "#FFFFFF",
    "muted": "#A0A0A0",  # metallic gray: secondary text only
    "on_orange": "#000000",  # text on orange is always black (white fails AA)
    "danger": "#F87171",
    "overlay": "rgba(0, 0, 0, 0.72)",
    "shadow": "rgba(0, 0, 0, 0.45)",
    "glow": "rgba(255, 102, 0, 0.35)",
}

FONTS = {
    "heading": "'Oswald', 'Arial Narrow', Arial, sans-serif",
    "body": "'Inter', Arial, sans-serif",
}
# Loaded by rx.App(stylesheets=...); both families are licensed under the SIL OFL.
GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700"
    "&family=Oswald:wght@500;600;700&display=swap"
)
HEADING_LETTER_SPACING = "0.06em"

SPACING = {"xs": "0.5rem", "sm": "0.75rem", "md": "1rem", "lg": "1.5rem", "xl": "2.5rem"}
RADII = {"sm": "4px", "md": "8px", "pill": "999px"}
SHADOWS = {
    "card": f"0 8px 24px {COLORS['shadow']}",
    "glow": f"0 0 0 1px {COLORS['orange']}, 0 0 18px {COLORS['glow']}",
}

GRADIENTS = {
    "login": f"radial-gradient(circle at 15% 20%, {COLORS['glow']} 0%, transparent 40%), {COLORS['black']}",
    "hero": (
        f"linear-gradient(90deg, {COLORS['black']} 0%, rgba(0, 0, 0, 0.6) 55%, "
        "rgba(0, 0, 0, 0.1) 100%)"
    ),
    "card_image": f"linear-gradient(180deg, transparent 55%, {COLORS['shadow']} 100%)",
}

APP_BACKGROUND = {
    "background": COLORS["black"],
    "color": COLORS["text"],
    "font_family": FONTS["body"],
}

PANEL = {
    "background": COLORS["surface"],
    "border": f"1px solid {COLORS['border']}",
    "border_radius": RADII["md"],
}

CARD = {**PANEL, "box_shadow": SHADOWS["card"]}

_BUTTON_BASE = {
    "font_weight": "700",
    "text_transform": "uppercase",
    "letter_spacing": "0.05em",
    "cursor": "pointer",
    "border_radius": RADII["sm"],
    "_disabled": {"opacity": "0.5", "cursor": "not-allowed"},
}

PRIMARY_BUTTON = {
    **_BUTTON_BASE,
    "background": COLORS["orange"],
    "color": COLORS["on_orange"],
    "_hover": {"background": COLORS["orange_hover"]},
    "_active": {"background": COLORS["orange_active"]},
}

METAL_BUTTON = {
    **_BUTTON_BASE,
    "background": f"linear-gradient(180deg, {COLORS['surface_alt']} 0%, {COLORS['graphite']} 100%)",
    "color": COLORS["text"],
    "border": f"1px solid {COLORS['metal_edge']}",
    "_hover": {"border_color": COLORS["orange_hover"], "box_shadow": SHADOWS["glow"]},
}

DANGER_BUTTON = {
    **_BUTTON_BASE,
    "background": "transparent",
    "color": COLORS["danger"],
    "border": f"1px solid {COLORS['danger']}",
    "_hover": {"background": COLORS["surface_alt"]},
}

# Badge palette for every status in the system: (background, text).
STATUS_COLORS: dict[str, tuple[str, str]] = {
    # Service orders
    "ABERTA": ("#FF6600", "#000000"),
    "EM_ANDAMENTO": ("#1E3A5F", "#BFDBFE"),
    "CONCLUIDA": ("#14532D", "#BBF7D0"),
    "CANCELADA": ("#2E2E2E", "#D4D4D4"),
    # Stock motorcycles
    "DISPONIVEL": ("#14532D", "#BBF7D0"),
    "RESERVADA": ("#78350F", "#FDE68A"),
    "VENDIDA": ("#2E2E2E", "#D4D4D4"),
    # Registration records (soft delete)
    "ATIVO": ("#14532D", "#BBF7D0"),
    "INATIVO": ("#2E2E2E", "#D4D4D4"),
    # Financial operations (Change 10)
    "RECEITA": ("#14532D", "#BBF7D0"),
    "DESPESA": ("#7F1D1D", "#FECACA"),
}
STATUS_FALLBACK = ("#2E2E2E", "#D4D4D4")

# Text/background pairs used by the components; each must reach WCAG AA (4.5:1).
TEXT_PAIRS: dict[str, tuple[str, str]] = {
    "text_on_background": (COLORS["text"], COLORS["black"]),
    "text_on_surface": (COLORS["text"], COLORS["surface"]),
    "muted_on_background": (COLORS["muted"], COLORS["black"]),
    "muted_on_graphite": (COLORS["muted"], COLORS["graphite"]),
    # Brand pair of the shell: titles and the orange role/active text on the matte black bars.
    "text_on_graphite": (COLORS["text"], COLORS["graphite"]),
    "accent_on_graphite": (COLORS["orange"], COLORS["graphite"]),
    "muted_on_surface": (COLORS["muted"], COLORS["surface"]),
    "accent_on_surface": (COLORS["orange"], COLORS["surface"]),
    "accent_on_background": (COLORS["orange"], COLORS["black"]),
    "on_orange": (COLORS["on_orange"], COLORS["orange"]),
    "danger_on_surface": (COLORS["danger"], COLORS["surface"]),
    **{f"status_{name}": (text, background) for name, (background, text) in STATUS_COLORS.items()},
}


def _channel(value: int) -> float:
    srgb = value / 255
    return srgb / 12.92 if srgb <= 0.03928 else ((srgb + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    digits = hex_color.lstrip("#")
    red, green, blue = (int(digits[index : index + 2], 16) for index in (0, 2, 4))
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG 2.x contrast ratio between two ``#RRGGBB`` colors."""
    lighter, darker = sorted(
        (relative_luminance(foreground), relative_luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


# Radix theme of the whole app, applied by RadixThemesPlugin in rxconfig.py; the
# brand orange replaces Radix's orange through assets/harley.css.
theme_config = rx.theme(appearance="dark", accent_color="orange", has_background=True)
