"""DTOs for goods receipts (entradas de mercadoria) and their items."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ItemEntradaCreate(BaseModel):
    """Item sent when registering a goods receipt."""

    id_produto: int = Field(gt=0)
    quantidade: int = Field(gt=0)
    valor_unitario: Decimal = Field(gt=0)


class EntradaMercadoriaCreate(BaseModel):
    """Payload for the atomic goods receipt endpoint.

    Authorship, total and date are derived by Xano and never sent.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    id_fornecedor: int = Field(gt=0)
    numero_documento: str = Field(min_length=1)
    itens: list[ItemEntradaCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_repeated_products(self) -> EntradaMercadoriaCreate:
        product_ids = [item.id_produto for item in self.itens]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError(
                "Um mesmo produto não pode aparecer mais de uma vez na entrada."
            )
        return self


class EntradaMercadoriaResumo(BaseModel):
    """Goods receipt row returned by the history endpoint."""

    model_config = ConfigDict(extra="ignore")

    id: int
    id_fornecedor: int
    numero_documento: str | None = None
    data_entrada: datetime | None = None
    valor_total: Decimal | None = None
    nome_fornecedor: str | None = None
    id_funcionario: int | None = None
    nome_funcionario: str | None = None
    quantidade_itens: int = 0


class ItemEntrada(BaseModel):
    """Item of a registered goods receipt."""

    model_config = ConfigDict(extra="ignore")

    id: int
    id_produto: int
    codigo: str | None = None
    nome_produto: str | None = None
    quantidade: int
    valor_unitario: Decimal
    valor_total_item: Decimal | None = None

    @model_validator(mode="after")
    def fill_item_total(self) -> ItemEntrada:
        if self.valor_total_item is None:
            self.valor_total_item = self.quantidade * self.valor_unitario
        return self


class EntradaMercadoriaDetalhe(EntradaMercadoriaResumo):
    """Goods receipt with its items."""

    itens: list[ItemEntrada] = []
