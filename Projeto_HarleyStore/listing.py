"""Pure helpers for client-side search, pagination and select options."""

from __future__ import annotations


def filter_rows(rows: list[dict[str, str]], query: str) -> list[dict[str, str]]:
    """Keep rows whose values contain the case-insensitive search text."""
    query = query.strip().lower()
    if not query:
        return rows
    return [row for row in rows if query in " ".join(row.values()).lower()]


def page_count(total_rows: int, page_size: int) -> int:
    return max(1, (total_rows + page_size - 1) // page_size)


def paginate(
    rows: list[dict[str, str]], page: int, page_size: int
) -> list[dict[str, str]]:
    start = (page - 1) * page_size
    return rows[start : start + page_size]


def option_label(record_id: int | str, name: str) -> str:
    """Build a select option that carries the record id before the name."""
    return f"{record_id} - {name}"


def option_id(option: str) -> int:
    """Return the record id encoded by ``option_label``."""
    return int(option.split(" - ", 1)[0])
