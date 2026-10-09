"""DTOs for counter sales of parts (venda no balcão, Change 11)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_ITENS_VENDA = 30


class ItemVendaBalcaoCreate(BaseModel):
    """Item sent when closing a counter sale; the price comes from Xano."""

    id_produto: int = Field(gt=0)
    quantidade: int = Field(gt=0)


class VendaBalcaoCreate(BaseModel):
    """Payload for the atomic counter sale endpoint.

    The seller comes from the JWT and the prices from the products. ``total_esperado`` is the
    total shown to the seller: Xano recalculates it and refuses the sale if it differs.
    ``chave_venda`` identifies the cart, so a retry returns the sale already registered.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    chave_venda: str = Field(min_length=1, max_length=64)
    id_cliente: int | None = Field(default=None, gt=0)
    total_esperado: Decimal = Field(gt=0, decimal_places=2)
    itens: list[ItemVendaBalcaoCreate] = Field(min_length=1, max_length=MAX_ITENS_VENDA)

    @model_validator(mode="after")
    def reject_repeated_products(self) -> VendaBalcaoCreate:
        product_ids = [item.id_produto for item in self.itens]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Um mesmo produto não pode aparecer mais de uma vez na venda.")
        return self


class ItemVendaBalcao(BaseModel):
    """Item of a registered counter sale, with the price photographed at closing."""

    model_config = ConfigDict(extra="ignore")

    id_produto: int
    codigo: str | None = None
    nome_produto: str | None = None
    quantidade: int
    valor_unitario: Decimal
    valor_total_item: Decimal


class VendaBalcaoDetalhe(BaseModel):
    """Receipt of a counter sale returned by ``POST balcao/vendas``."""

    model_config = ConfigDict(extra="ignore")

    id_transacao: int
    data_transacao: datetime
    valor_total: Decimal
    id_cliente: int | None = None
    nome_cliente: str | None = None
    id_funcionario: int
    nome_funcionario: str | None = None
    itens: list[ItemVendaBalcao] = []
