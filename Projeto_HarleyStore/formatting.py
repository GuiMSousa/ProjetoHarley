"""Display formatting and numeric input parsing shared by page states."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

EMPTY_VALUE = "—"


def format_currency(value: Decimal | None) -> str:
    if value is None:
        return EMPTY_VALUE
    formatted = f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {formatted}"


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return EMPTY_VALUE
    return value.astimezone().strftime("%d/%m/%Y %H:%M")


def parse_decimal(value: str) -> Decimal:
    """Parse a decimal typed with comma or dot as the decimal separator."""
    return Decimal(value.strip().replace(",", "."))
