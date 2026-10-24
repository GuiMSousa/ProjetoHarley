"""DTOs for the basic registration resources.

Read DTOs (Cliente, MotoCliente, Produto, Fornecedor, Funcionario) are tolerant on display
fields since Change 15: a record created outside the app must not break a whole list. The
*Create/*Update DTOs keep every rule for what the app writes.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from Projeto_HarleyStore.services.leitura import TextoLido


class CadastroModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    ativo: bool = True

    @field_validator("ativo", mode="before")
    @classmethod
    def _ativo_nulo(cls, value: object) -> object:
        # A row created outside the app may leave the flag empty; Xano's default is active.
        return True if value is None else value


class ClienteCreate(BaseModel):
    nome_cliente: str = Field(min_length=1)
    cpf_cnpj: str = Field(min_length=1)
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None


class ClienteUpdate(BaseModel):
    nome_cliente: str | None = Field(default=None, min_length=1)
    cpf_cnpj: str | None = Field(default=None, min_length=1)
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    ativo: bool | None = None


class Cliente(CadastroModel):
    nome_cliente: TextoLido = ""
    cpf_cnpj: TextoLido = ""
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None


class MotoClienteCreate(BaseModel):
    id_cliente: int = Field(gt=0)
    modelo: str = Field(min_length=1)
    # Optional since Change 9: a 0 km bike leaves the store before it gets a plate.
    placa: str | None = Field(default=None, min_length=1)
    chassi: str = Field(min_length=1)


class MotoClienteUpdate(BaseModel):
    id_cliente: int | None = Field(default=None, gt=0)
    modelo: str | None = Field(default=None, min_length=1)
    placa: str | None = Field(default=None, min_length=1)
    chassi: str | None = Field(default=None, min_length=1)
    ativo: bool | None = None


class MotoCliente(CadastroModel):
    id_cliente: int = Field(gt=0)
    modelo: TextoLido = ""
    placa: str | None = None
    chassi: TextoLido = ""


class ProdutoCreate(BaseModel):
    codigo: str = Field(min_length=1, pattern=r"^[A-Za-z0-9]+$")
    nome_produto: str = Field(min_length=1)
    descricao: str | None = None
    categoria: str = Field(min_length=1)
    estoque_qtd: int = Field(default=0, ge=0)
    preco_venda: Decimal = Field(gt=0)


class ProdutoUpdate(BaseModel):
    """Stock balance is changed only by stock movements, never by edition."""

    codigo: str | None = Field(default=None, min_length=1, pattern=r"^[A-Za-z0-9]+$")
    nome_produto: str | None = Field(default=None, min_length=1)
    descricao: str | None = None
    categoria: str | None = Field(default=None, min_length=1)
    preco_venda: Decimal | None = Field(default=None, gt=0)
    ativo: bool | None = None


class Produto(CadastroModel):
    """Part as read from Xano: free texts are tolerant; stock and price stay business rules."""

    codigo: TextoLido = ""
    nome_produto: TextoLido = ""
    descricao: str | None = None
    categoria: TextoLido = ""
    estoque_qtd: int = Field(default=0, ge=0)
    preco_venda: Decimal = Field(gt=0)

    @field_validator("estoque_qtd", mode="before")
    @classmethod
    def null_stock_is_zero(cls, value: object) -> object:
        # Xano allows a null balance (legacy rows); Estoque/movimentar_estoque reads it as 0.
        return 0 if value is None else value


class FornecedorCreate(BaseModel):
    nome_fornecedor: str = Field(min_length=1)
    cnpj: str = Field(min_length=1)
    contato: str | None = None


class FornecedorUpdate(BaseModel):
    nome_fornecedor: str | None = Field(default=None, min_length=1)
    cnpj: str | None = Field(default=None, min_length=1)
    contato: str | None = None
    ativo: bool | None = None


class Fornecedor(CadastroModel):
    nome_fornecedor: TextoLido = ""
    cnpj: TextoLido = ""
    contato: str | None = None


FuncionarioTipo = Literal["GERENTE", "VENDEDOR", "MECANICO"]


class FuncionarioCreate(BaseModel):
    nome_funcionario: str = Field(min_length=1)
    cargo: str = Field(min_length=1)
    tipo: FuncionarioTipo
    contato: str | None = None


class FuncionarioUpdate(BaseModel):
    nome_funcionario: str | None = Field(default=None, min_length=1)
    cargo: str | None = Field(default=None, min_length=1)
    tipo: FuncionarioTipo | None = None
    contato: str | None = None
    ativo: bool | None = None


class Funcionario(CadastroModel):
    nome_funcionario: TextoLido = ""
    cargo: TextoLido = ""
    tipo: FuncionarioTipo
    contato: str | None = None
