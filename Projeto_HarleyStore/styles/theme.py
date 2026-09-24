"""Central visual constants for the dark Harley-Davidson theme."""

import reflex as rx


COLORS = {
    "black": "#070707",
    "graphite": "#121212",
    "surface": "#1c1c1c",
    "surface_alt": "#252525",
    "orange": "#f36f21",
    "orange_hover": "#ff8738",
    "text": "#f4f4f4",
    "muted": "#a7a7a7",
    "danger": "#ef6b73",
    "border": "#363636",
}

SPACING = {"xs": "0.5rem", "sm": "0.75rem", "md": "1rem", "lg": "1.5rem", "xl": "2.5rem"}
FONT_FAMILY = "Arial, sans-serif"

APP_BACKGROUND = {
    "background": COLORS["black"],
    "color": COLORS["text"],
    "font_family": FONT_FAMILY,
}

PANEL = {
    "background": COLORS["graphite"],
    "border": f"1px solid {COLORS['border']}",
    "border_radius": "8px",
}

PRIMARY_BUTTON = {
    "background": COLORS["orange"],
    "color": COLORS["black"],
    "font_weight": "700",
    "cursor": "pointer",
    "_hover": {"background": COLORS["orange_hover"]},
}


def global_theme() -> rx.Component:
    return rx.theme(appearance="dark", accent_color="orange", has_background=True)


theme_config = rx.theme(appearance="dark", accent_color="orange", has_background=True)