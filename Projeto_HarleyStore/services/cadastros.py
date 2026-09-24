"""DTOs for the basic registration resources."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CadastroModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    ativo: bool = True


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


class Cliente(CadastroModel, ClienteCreate):
    pass


class MotoClienteCreate(BaseModel):
    id_cliente: int = Field(gt=0)
    modelo: str = Field(min_length=1)
    placa: str = Field(min_length=1)
    chassi: str = Field(min_length=1)


class MotoClienteUpdate(BaseModel):
    id_cliente: int | None = Field(default=None, gt=0)
    modelo: str | None = Field(default=None, min_length=1)
    placa: str | None = Field(default=None, min_length=1)
    chassi: str | None = Field(default=None, min_length=1)
    ativo: bool | None = None


class MotoCliente(CadastroModel, MotoClienteCreate):
    pass


class ProdutoCreate(BaseModel):
    codigo: str = Field(min_length=1, pattern=r"^[A-Za-z0-9]+$")
    nome_produto: str = Field(min_length=1)
    descricao: str | None = None
    categoria: str = Field(min_length=1)
    estoque_qtd: int = Field(default=0, ge=0)
    preco_venda: Decimal = Field(gt=0)


class ProdutoUpdate(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, pattern=r"^[A-Za-z0-9]+$")
    nome_produto: str | None = Field(default=None, min_length=1)
    descricao: str | None = None
    categoria: str | None = Field(default=None, min_length=1)
    estoque_qtd: int | None = Field(default=None, ge=0)
    preco_venda: Decimal | None = Field(default=None, gt=0)
    ativo: bool | None = None


class Produto(CadastroModel, ProdutoCreate):
    pass


class FornecedorCreate(BaseModel):
    nome_fornecedor: str = Field(min_length=1)
    cnpj: str = Field(min_length=1)
    contato: str | None = None


class FornecedorUpdate(BaseModel):
    nome_fornecedor: str | None = Field(default=None, min_length=1)
    cnpj: str | None = Field(default=None, min_length=1)
    contato: str | None = None
    ativo: bool | None = None


class Fornecedor(CadastroModel, FornecedorCreate):
    pass


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


class Funcionario(CadastroModel, FuncionarioCreate):
    pass
