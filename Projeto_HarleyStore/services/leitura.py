"""Tolerant reading of Xano records (Change 15): display fields never take a whole list down."""

from __future__ import annotations

from typing import Annotated

from pydantic import BeforeValidator


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
