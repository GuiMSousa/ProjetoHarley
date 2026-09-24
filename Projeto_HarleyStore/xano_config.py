"""Configuration for the Xano integration."""

from __future__ import annotations

import os


class XanoConfigurationError(RuntimeError):
    """Raised when the Xano integration is not configured."""


def xano_api_base_url() -> str:
    """Return the configured Xano API base URL without a trailing slash."""
    value = os.getenv("XANO_API_BASE_URL", "").strip().rstrip("/")
    if not value:
        raise XanoConfigurationError(
            "XANO_API_BASE_URL must be configured before calling Xano."
        )
    return value


def xano_auth_cookie_secure() -> bool:
    """Return whether the JWT cookie must only be sent over HTTPS."""
    value = os.getenv("XANO_AUTH_COOKIE_SECURE", "false").strip().lower()
    if value in {"", "0", "false", "no", "off"}:
        return False
    if value in {"1", "true", "yes", "on"}:
        return True
    raise XanoConfigurationError(
        "XANO_AUTH_COOKIE_SECURE must be a boolean value."
    )
