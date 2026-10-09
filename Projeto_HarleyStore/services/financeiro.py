"""DTOs of the consolidated financial view (Change 10): period, totals by type and operations."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


TipoOperacao = Literal["MOTO", "PECAS", "BALCAO", "ORDEM_SERVICO", "COMPRA", "ENTRADA_MERCADORIA"]
Natureza = Literal["RECEITA", "DESPESA"]
OrigemOperacao = Literal["TRANSACAO", "ENTRADA"]

TIPO_LABELS: dict[str, str] = {
    "MOTO": "Venda de moto",
    "ORDEM_SERVICO": "Serviço de oficina",
    "PECAS": "Peças",
    "BALCAO": "Balcão",
    "COMPRA": "Compra",
    "ENTRADA_MERCADORIA": "Entrada de mercadoria",
}
# Mirror of Financeiro/resumo_operacoes in Xano: entries are expenses, every sale is revenue.
NATUREZA_POR_TIPO: dict[str, Natureza] = {
    "MOTO": "RECEITA",
    "ORDEM_SERVICO": "RECEITA",
    "PECAS": "RECEITA",
    "BALCAO": "RECEITA",
    "COMPRA": "DESPESA",
    "ENTRADA_MERCADORIA": "DESPESA",
}
NATUREZA_LABELS: dict[str, str] = {"RECEITA": "Receita", "DESPESA": "Despesa"}
PERIODO_MAXIMO_DIAS = 366
# The response lists at most this many operations; totals always cover the whole period (D7).
OPERACOES_LIMITE = 500
# Store time zone (D9). Brazil has no daylight saving time since 2019, so a fixed offset is exact
# and the tzdata package is not needed.
FUSO_LOJA = timezone(timedelta(hours=-3), "BRT")


def _epoch_ms(moment: datetime) -> int:
    return int(moment.timestamp()) * 1000


class PeriodoFinanceiro(BaseModel):
    """Whole days, both inclusive, in the store time zone; at most 366 days."""

    inicio: date
    fim: date

    @model_validator(mode="after")
    def _check_range(self) -> PeriodoFinanceiro:
        if self.fim < self.inicio:
            raise ValueError("O fim do período deve ser igual ou posterior ao início.")
        if (self.fim - self.inicio).days >= PERIODO_MAXIMO_DIAS:
            raise ValueError(f"O período pode ter no máximo {PERIODO_MAXIMO_DIAS} dias.")
        return self

    def params(self) -> dict[str, int]:
        """Query string of GET financeiro/resumo: 00:00:00.000 to 23:59:59.999, in milliseconds."""
        start = datetime.combine(self.inicio, time.min, FUSO_LOJA)
        next_day = datetime.combine(self.fim + timedelta(days=1), time.min, FUSO_LOJA)
        return {"inicio": _epoch_ms(start), "fim": _epoch_ms(next_day) - 1}


class TotalPorTipo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tipo: TipoOperacao
    natureza: Natureza
    quantidade: int = 0
    valor: Decimal = Decimal("0")


class OperacaoFinanceira(BaseModel):
    """One line of the consolidated view: a transaction (revenue) or a goods receipt (expense)."""

    model_config = ConfigDict(extra="ignore")

    origem: OrigemOperacao
    id: int
    tipo: TipoOperacao
    natureza: Natureza
    data: datetime
    valor: Decimal = Decimal("0")
    contraparte: str | None = None
    funcionario: str | None = None
    id_os: int | None = None
    id_moto_cliente: int | None = None
    modelo: str | None = None
    placa: str | None = None
    id_entrada: int | None = None
    numero_documento: str | None = None


class ResumoFinanceiro(BaseModel):
    model_config = ConfigDict(extra="ignore")

    inicio: datetime
    fim: datetime
    receitas: Decimal = Decimal("0")
    despesas: Decimal = Decimal("0")
    saldo: Decimal = Decimal("0")
    por_tipo: list[TotalPorTipo] = []
    operacoes: list[OperacaoFinanceira] = []
    total_operacoes: int = 0
    truncado: bool = False
