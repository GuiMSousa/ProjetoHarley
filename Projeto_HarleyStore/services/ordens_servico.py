"""DTOs for service orders (ordens de serviço) and their status machine."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


StatusOS = Literal["ABERTA", "EM_ANDAMENTO", "CONCLUIDA", "CANCELADA"]
TipoServico = Literal["PREVENTIVA", "CORRETIVA"]
TipoItemOS = Literal["PECA", "SERVICO"]

# Items can only change while the order is in one of these statuses.
STATUS_EDITAVEIS_OS: tuple[str, ...] = ("ABERTA", "EM_ANDAMENTO")

# Mirror of the Xano function "Oficina/validar_transicao_os"; Xano is the authority.
TRANSICOES_OS: dict[str, tuple[str, ...]] = {
    "ABERTA": ("EM_ANDAMENTO", "CANCELADA"),
    "EM_ANDAMENTO": ("CONCLUIDA", "CANCELADA"),
    "CONCLUIDA": (),
    "CANCELADA": (),
}


class OrdemServicoCreate(BaseModel):
    """Payload to open a service order.

    Status, opening date, author and customer are always defined by Xano.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    id_moto_cliente: int = Field(gt=0)
    id_mecanico: int | None = Field(default=None, gt=0)
    tipo_servico: TipoServico
    descricao_problema: str = Field(min_length=1, max_length=2000)
    quilometragem: int | None = Field(default=None, ge=0)


class TransicaoStatusOS(BaseModel):
    """Status transition sent with the status the client is currently seeing."""

    model_config = ConfigDict(str_strip_whitespace=True)

    status_atual: StatusOS
    status_novo: StatusOS
    observacao: str | None = None

    @model_validator(mode="after")
    def check_transition(self) -> TransicaoStatusOS:
        if not TRANSICOES_OS[self.status_atual]:
            raise ValueError("OS encerrada não pode ser reaberta ou alterada.")
        if self.status_novo not in TRANSICOES_OS[self.status_atual]:
            raise ValueError("Transição de status inválida.")
        if self.status_novo == "CANCELADA" and not self.observacao:
            raise ValueError("Informe o motivo do cancelamento.")
        return self


class ItemOSCreate(BaseModel):
    """Item added to a service order.

    Parts (PECA) are priced by Xano from the product and leave the stock on
    insertion; services (SERVICO) carry a description and a typed unit value.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    tipo_item: TipoItemOS
    id_produto: int | None = Field(default=None, gt=0)
    descricao: str | None = Field(default=None, max_length=200)
    quantidade: int = Field(gt=0)
    valor_unitario: Decimal | None = Field(default=None, gt=0, decimal_places=2)

    @model_validator(mode="after")
    def check_tipo(self) -> ItemOSCreate:
        if self.tipo_item == "PECA":
            if self.id_produto is None:
                raise ValueError("Selecione o produto.")
            # Xano prices parts from produtos.preco_venda.
            self.descricao = None
            self.valor_unitario = None
            return self
        if not self.descricao:
            raise ValueError("Informe a descrição do serviço.")
        if self.valor_unitario is None:
            raise ValueError("Informe o valor do serviço.")
        self.id_produto = None
        return self


class OrdemServicoResumo(BaseModel):
    """Service order row; Change 6 fields are optional for legacy orders."""

    model_config = ConfigDict(extra="ignore")

    id: int
    status: StatusOS
    id_moto_cliente: int
    data_abertura: datetime | None = None
    tipo_servico: TipoServico | None = None
    descricao_problema: str | None = None
    data_inicio: datetime | None = None
    data_encerramento: datetime | None = None
    id_cliente: int | None = None
    nome_cliente: str | None = None
    placa: str | None = None
    modelo: str | None = None
    id_funcionario: int | None = None
    nome_funcionario: str | None = None
    id_mecanico: int | None = None
    nome_mecanico: str | None = None
    valor_total: Decimal | None = None


class HistoricoStatusOS(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    status_anterior: StatusOS | None = None
    status_novo: StatusOS
    id_funcionario: int | None = None
    nome_funcionario: str | None = None
    created_at: datetime | None = None
    observacao: str | None = None


class ItemOrdemServico(BaseModel):
    """Order item; items recorded before Change 7 have no type and no stock flag."""

    model_config = ConfigDict(extra="ignore")

    id: int
    tipo_item: TipoItemOS = "PECA"
    id_produto: int | None = None
    codigo: str | None = None
    nome_produto: str | None = None
    descricao: str | None = None
    quantidade: int
    valor_unitario: Decimal | None = None
    valor_total_item: Decimal | None = None
    estoque_baixado: bool | None = None
    created_at: datetime | None = None

    @field_validator("tipo_item", mode="before")
    @classmethod
    def legacy_tipo(cls, value: object) -> object:
        return "PECA" if value is None else value


class OrdemServicoDetalhe(OrdemServicoResumo):
    quilometragem: int | None = None
    motivo_cancelamento: str | None = None
    valor_pecas: Decimal | None = None
    valor_servicos: Decimal | None = None
    historico: list[HistoricoStatusOS] = []
    itens: list[ItemOrdemServico] = []


class Mecanico(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    nome_funcionario: str
