"""Pure helpers for client-side search, pagination and select options."""

from __future__ import annotations

import unicodedata

from Projeto_HarleyStore.formatting import format_currency
from Projeto_HarleyStore.services.cadastros import Produto

PRODUTO_SEARCH_LIMIT = 8


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


def normalize_text(text: str) -> str:
    """Lowercase text without accents, for tolerant searches."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def produto_row(produto: Produto) -> dict[str, str]:
    """Product picker row shared by the workshop and the counter (stock and price)."""
    saldo = produto.estoque_qtd
    return {
        "id": str(produto.id),
        "codigo": produto.codigo,
        "nome": produto.nome_produto,
        "saldo": str(saldo),
        "preco": format_currency(produto.preco_venda),
        "preco_valor": str(produto.preco_venda),
        "disponivel": "true" if saldo > 0 else "false",
        "categoria": produto.categoria,
    }


def filtrar_produtos(
    rows: list[dict[str, str]], busca: str, limite: int = PRODUTO_SEARCH_LIMIT
) -> list[dict[str, str]]:
    """Products whose code or name contain the search text, ignoring case and accents."""
    termo = normalize_text(busca.strip())
    matches = [
        row
        for row in rows
        if not termo or termo in normalize_text(f"{row['codigo']} {row['nome']}")
    ]
    return matches[:limite]
