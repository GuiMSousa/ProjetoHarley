"""DTOs for stock motorcycle units, their reservations and their sale."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from Projeto_HarleyStore.services.catalogo import FamiliaMoto, VariacaoCor


StatusMoto = Literal["DISPONIVEL", "RESERVADA", "VENDIDA"]
STATUS_MOTO_LABELS = {"DISPONIVEL": "Disponível", "RESERVADA": "Reservada", "VENDIDA": "Vendida"}
VIN_PATTERN = r"^[A-HJ-NPR-Z0-9]{17}$"
# Brazilian plate: old format ABC1234 or Mercosul ABC1D23.
PLACA_PATTERN = r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$"
ANO_MINIMO = 1990
DIAS_RESERVA_PADRAO = 7


def _upper(value: object) -> object:
    return value.strip().upper() if isinstance(value, str) else value


def _normalize_placa(value: object) -> object:
    """Upper case without hyphen or spaces; a blank plate means no plate (0 km bike)."""
    if not isinstance(value, str):
        return value
    placa = "".join(value.split()).replace("-", "").upper()
    return placa or None


def _check_ano(value: int | None) -> int | None:
    if value is not None and value > date.today().year + 1:
        raise ValueError("Ano do modelo inválido.")
    return value


class MotoEstoqueCreate(BaseModel):
    """New stock unit; status, customer and seller are always set by Xano."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id_modelo: int = Field(gt=0)
    chassi: str = Field(pattern=VIN_PATTERN)
    cor: str = Field(min_length=1, max_length=60)
    ano_modelo: int = Field(ge=ANO_MINIMO)
    preco_venda: Decimal = Field(gt=0, decimal_places=2)

    @field_validator("chassi", mode="before")
    @classmethod
    def _normalize_chassi(cls, value: object) -> object:
        return _upper(value)

    @field_validator("ano_modelo")
    @classmethod
    def _ano(cls, value: int) -> int:
        return _check_ano(value)


class MotoEstoqueUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    chassi: str | None = Field(default=None, pattern=VIN_PATTERN)
    cor: str | None = Field(default=None, min_length=1, max_length=60)
    ano_modelo: int | None = Field(default=None, ge=ANO_MINIMO)
    preco_venda: Decimal | None = Field(default=None, gt=0, decimal_places=2)

    @field_validator("chassi", mode="before")
    @classmethod
    def _normalize_chassi(cls, value: object) -> object:
        return _upper(value)

    @field_validator("ano_modelo")
    @classmethod
    def _ano(cls, value: int | None) -> int | None:
        return _check_ano(value)


class ReservaMotoCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id_cliente: int = Field(gt=0)
    dias_validade: int = Field(default=DIAS_RESERVA_PADRAO, ge=1, le=30)
    observacao: str | None = Field(default=None, max_length=500)


class CancelamentoReservaMoto(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    motivo: str = Field(min_length=1, max_length=500)


class VendaMotoCreate(BaseModel):
    """Body of POST vender_moto; the seller always comes from the JWT, never from here."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id_moto: int = Field(gt=0)
    id_cliente: int = Field(gt=0)
    valor_venda: Decimal = Field(gt=0, decimal_places=2)
    placa: str | None = Field(default=None, pattern=PLACA_PATTERN)
    observacao: str | None = Field(default=None, max_length=500)

    @field_validator("placa", mode="before")
    @classmethod
    def _placa(cls, value: object) -> object:
        return _normalize_placa(value)

    @field_validator("observacao", mode="before")
    @classmethod
    def _blank_observacao(cls, value: object) -> object:
        return (value.strip() or None) if isinstance(value, str) else value


class VendaMotoResultado(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id_transacao: int
    id_moto_cliente: int
    status: Literal["SUCESSO"]


class HistoricoStatusMoto(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    status_anterior: StatusMoto | None = None
    status_novo: StatusMoto
    id_funcionario: int | None = None
    nome_funcionario: str | None = None
    id_cliente: int | None = None
    observacao: str | None = None
    created_at: datetime | None = None


class MotoEstoque(BaseModel):
    """Stock unit as listed for sellers; units created before Change 8 have no model."""

    model_config = ConfigDict(extra="ignore")

    id: int
    status: StatusMoto = "DISPONIVEL"
    id_modelo: int | None = None
    nome_modelo: str | None = None
    familia: FamiliaMoto | None = None
    variacoes_cor: list[VariacaoCor] = []
    marca: str | None = None
    modelo: str | None = None
    chassi: str | None = None
    cor: str | None = None
    ano_modelo: int | None = None
    preco_venda: Decimal | None = None
    clientes_id: int | None = None
    nome_cliente: str | None = None
    id_vendedor_reserva: int | None = None
    nome_vendedor: str | None = None
    reservada_ate: datetime | None = None
    atualizado_em: datetime | None = None

    @field_validator("status", mode="before")
    @classmethod
    def _legacy_status(cls, value: object) -> object:
        return "DISPONIVEL" if value is None else value

    @field_validator("variacoes_cor", mode="before")
    @classmethod
    def _null_cores(cls, value: object) -> object:
        return [] if value is None else value


class MotoEstoqueDetalhe(MotoEstoque):
    historico: list[HistoricoStatusMoto] = []
