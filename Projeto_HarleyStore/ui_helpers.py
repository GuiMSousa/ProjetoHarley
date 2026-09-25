"""UI building blocks shared by every page, and the reentrancy guard of page events."""

from __future__ import annotations

import reflex as rx

from Projeto_HarleyStore.styles.theme import COLORS


def labeled(label: str, control: rx.Component, **props) -> rx.Component:
    """Stack a muted caption above a form control or value."""
    return rx.vstack(
        rx.text(label, size="2", color=COLORS["muted"]),
        control,
        align="stretch",
        spacing="1",
        **props,
    )


def error_callout(message: rx.Var) -> rx.Component:
    """Red callout rendered only while the message is not empty."""
    return rx.cond(
        message != "",
        rx.callout(message, icon="triangle_alert", color_scheme="red", width="100%"),
    )


def operation_is_blocked(
    is_loading_list: bool,
    is_saving: bool,
    is_deactivating: bool,
) -> bool:
    """Return whether a page operation must be rejected as reentrant."""
    return is_loading_list or is_saving or is_deactivating
