"""User-facing messages and notifications for Xano and form errors, shared by every page state."""

from __future__ import annotations

import reflex as rx
from pydantic import ValidationError
from reflex.event import EventSpec

from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoError,
    XanoNotFoundError,
    XanoPermissionError,
    XanoRateLimitError,
    XanoValidationError,
)


TOAST_POSITION = "top-right"


def error_feedback(error: XanoError) -> str:
    """Translate a typed Xano error into a readable message for the UI."""
    if isinstance(error, XanoAuthenticationError):
        return "Sua sessão expirou. Entre novamente."
    if isinstance(error, XanoPermissionError):
        return "Seu perfil não possui permissão para esta operação."
    if isinstance(error, XanoNotFoundError):
        return "O registro solicitado não foi encontrado."
    if isinstance(error, XanoValidationError):
        return str(error)
    if isinstance(error, XanoRateLimitError):
        return "Muitas requisições ao Xano. Aguarde alguns segundos e tente novamente."
    return "Não foi possível comunicar com o Xano. Tente novamente."


def validation_feedback(error: ValidationError, field_messages: dict[str, str]) -> str:
    """First readable message of a DTO validation error: a field message or the validator text."""
    detail = error.errors()[0]
    location = detail.get("loc") or ("",)
    if location[0] in field_messages:
        return field_messages[location[0]]
    return str(detail.get("msg", "")).removeprefix("Value error, ")


def toast_error(message: str) -> EventSpec:
    """Error notification used by every page state."""
    return rx.toast(message, level="error", position=TOAST_POSITION)


def toast_success(message: str) -> EventSpec:
    """Success notification used by every page state."""
    return rx.toast(message, level="success", position=TOAST_POSITION)
