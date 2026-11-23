"""Change 18: DTOs of the /admin panel (access accounts, access audit and read-only system rules)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from Projeto_HarleyStore.services.balcao import MAX_ITENS_VENDA
from Projeto_HarleyStore.services.entradas import MAX_ITENS_ENTRADA
from Projeto_HarleyStore.services.financeiro import OPERACOES_LIMITE, PERIODO_MAXIMO_DIAS
from Projeto_HarleyStore.services.motos import DIAS_RESERVA_MAXIMO, DIAS_RESERVA_PADRAO

# Password policy of the `user` table (min:8|minAlpha:1|minDigit:1); passwords are never trimmed.
SENHA_MINIMA = 8
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

# event_log actions written today (login, signup, reset/update_password, welcome email, Change 18 reset).
ACOES_EVENTO = {
    "login": "Login",
    "signup": "Acesso criado",
    "reset_password": "Troca da própria senha",
    "admin_reset_password": "Senha redefinida pelo gerente",
    "welcome_email_sent": "Email de boas-vindas",
}

# Rules shown read-only in /admin. Each value is the constant the app applies, and
# tests/test_admin_contracts.py checks it against the .xs where Xano applies the same rule.
PARAMETROS_SISTEMA: tuple[dict[str, Any], ...] = (
    {"chave": "reserva_padrao", "grupo": "Reserva de moto", "regra": "Prazo padrão", "valor": DIAS_RESERVA_PADRAO, "unidade": "dias"},
    {"chave": "reserva_maximo", "grupo": "Reserva de moto", "regra": "Prazo máximo", "valor": DIAS_RESERVA_MAXIMO, "unidade": "dias"},
    {"chave": "itens_balcao", "grupo": "Venda de balcão", "regra": "Itens por venda", "valor": MAX_ITENS_VENDA, "unidade": "itens"},
    {"chave": "itens_entrada", "grupo": "Entrada de mercadoria", "regra": "Itens por entrada", "valor": MAX_ITENS_ENTRADA, "unidade": "itens"},
    {"chave": "periodo_resumo", "grupo": "Resumo financeiro", "regra": "Período máximo", "valor": PERIODO_MAXIMO_DIAS, "unidade": "dias"},
    {"chave": "operacoes_resumo", "grupo": "Resumo financeiro", "regra": "Operações listadas", "valor": OPERACOES_LIMITE, "unidade": "operações"},
)


def senha_problema(senha: str, confirmacao: str) -> str:
    """Readable reason the password breaks the `user` policy, or "" when it is valid."""
    if len(senha) < SENHA_MINIMA:
        return f"A senha deve ter ao menos {SENHA_MINIMA} caracteres."
    if not re.search(r"[^\W\d_]", senha) or not re.search(r"\d", senha):
        return "A senha deve ter ao menos uma letra e um número."
    if senha != confirmacao:
        return "A confirmação não confere com a senha."
    return ""


class UsuarioAdmin(BaseModel):
    """Row of GET admin/usuarios. The endpoint never sends the password; extra fields are ignored."""

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str | None = None
    email: str | None = None
    role: str | None = None
    created_at: datetime | None = None
    id_funcionario: int | None = None
    nome_funcionario: str | None = None
    tipo: str | None = None
    cargo: str | None = None
    ativo: bool | None = None


class AcessoCreate(BaseModel):
    """Payload of POST auth/signup (Authentication group): the login of an active employee."""

    name: str = Field(min_length=1)
    email: str = Field(pattern=EMAIL_PATTERN)
    password: str = Field(min_length=SENHA_MINIMA)
    id_funcionario: int = Field(gt=0)


class AcessoCriado(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: int
    id_funcionario: int


class SenhaReset(BaseModel):
    """Payload of POST admin/usuarios/{id}/senha."""

    password: str = Field(min_length=SENHA_MINIMA)
    confirm_password: str


class UsuarioResumo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str | None = None
    email: str | None = None


class EventoAcesso(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    created_at: datetime | None = None
    action: str | None = None
    user_id: int | None = None
    nome_usuario: str | None = None
    nome_funcionario: str | None = None
    metadata: Any = None


class EventosPagina(BaseModel):
    """GET admin/eventos: one page of event_log with Xano's paging fields."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    items: list[EventoAcesso] = []
    pagina: int = Field(default=1, alias="curPage")
    proxima: int | None = Field(default=None, alias="nextPage")
    anterior: int | None = Field(default=None, alias="prevPage")
    total: int | None = Field(default=None, alias="itemsTotal")
