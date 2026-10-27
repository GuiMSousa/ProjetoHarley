"""Tolerant reading of Xano records (Change 15): display fields never take a whole list down."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import unquote, urlsplit

from pydantic import BeforeValidator

from Projeto_HarleyStore.xano_config import XanoConfigurationError, xano_api_base_url


def _vazio_se_nulo(value: object) -> object:
    return "" if value is None else value


# Text shown on screen. A record created outside the app (null or empty text) still renders;
# the strict rules stay in the *Create/*Update DTOs, which validate what the app writes.
TextoLido = Annotated[str, BeforeValidator(_vazio_se_nulo)]


def lista_lida(value: object, tipos: type | tuple[type, ...]) -> list:
    """A free JSON list (e.g. variacoes_cor typed in the Xano panel): only items of ``tipos``.

    Anything that is not a list (null, text, an object) reads as an empty list.
    """
    return [item for item in value if isinstance(item, tipos)] if isinstance(value, list) else []


def url_de_midia(item: object) -> str:
    """Absolute https URL of a photo read from Xano, or "" when it is not one (Change 17).

    A web URL is kept on https (the scheme in any case; ``http`` is promoted, so the page never
    mixes content). A Xano file, as its ``/vault/...`` path or as the stored object with
    ``path``, is public on the instance origin (that of ``XANO_API_BASE_URL``); a path that
    climbs out of the vault (``..``, also percent-encoded or after a backslash) is refused. Anything else
    (a local path, ``javascript:``, ``data:``) is dropped.
    """
    if isinstance(item, dict):
        item = item.get("path")
    if not isinstance(item, str):
        return ""
    item = item.strip()
    esquema, separador, resto = item.partition("://")
    if separador and esquema.lower() in ("https", "http"):
        return f"https://{resto}" if resto else ""
    # The browser resolves %2e%2e and backslashes as "..": check the path as it will read it.
    segmentos = unquote(item).replace("\\", "/").split("/")
    if not item.startswith("/vault/") or ".." in segmentos:
        return ""
    try:
        base = urlsplit(xano_api_base_url())
    except XanoConfigurationError:
        return ""
    if base.scheme in ("https", "http") and base.netloc:
        return f"{base.scheme}://{base.netloc}{item}"
    return ""


def galeria_lida(value: object) -> list[str]:
    """The carousel photos of a model as absolute URLs; unreadable items are dropped."""
    return [url for item in lista_lida(value, (str, dict)) if (url := url_de_midia(item))]
