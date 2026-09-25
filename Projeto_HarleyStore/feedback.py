"""User-facing messages for Xano errors, shared by every page state."""

from __future__ import annotations

from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoError,
    XanoNotFoundError,
    XanoPermissionError,
    XanoValidationError,
)


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
    return "Não foi possível comunicar com o Xano. Tente novamente."
