"""Reflex state of the /admin panel (Change 18): access accounts, access audit and system rules."""

from __future__ import annotations

import reflex as rx
from pydantic import ValidationError

from Projeto_HarleyStore.auth import AuthState, role_allows_route
from Projeto_HarleyStore.feedback import error_feedback, toast_error, toast_success
from Projeto_HarleyStore.financeiro_state import FinanceiroFormError, build_periodo
from Projeto_HarleyStore.formatting import EMPTY_VALUE, format_datetime
from Projeto_HarleyStore.listing import option_id, option_label
from Projeto_HarleyStore.services.admin import (
    ACOES_EVENTO,
    AcessoCreate,
    EventoAcesso,
    SenhaReset,
    UsuarioAdmin,
    senha_problema,
)
from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoClient,
    XanoError,
    XanoValidationError,
)
from Projeto_HarleyStore.ui_helpers import operation_is_blocked

ADMIN_ROUTE = "/admin"
TODAS_ACOES = "Todas as ações"
ACAO_POR_ROTULO = {rotulo: acao for acao, rotulo in ACOES_EVENTO.items()}


def usuario_row(usuario: UsuarioAdmin, meu_funcionario: int) -> dict[str, str]:
    """Table row of an access account; `proprio` marks the manager's own row (S1)."""
    vinculado = usuario.id_funcionario is not None
    ativo = vinculado and usuario.ativo is not False
    proprio = vinculado and usuario.id_funcionario == meu_funcionario
    if not vinculado:
        status, rotulo = "SEM_VINCULO", "Sem vínculo"
    elif ativo:
        status, rotulo = "ATIVO", "Ativo"
    else:
        status, rotulo = "INATIVO", "Inativo"
    return {
        "id": str(usuario.id),
        "nome": usuario.nome_funcionario or usuario.name or EMPTY_VALUE,
        "email": usuario.email or EMPTY_VALUE,
        "tipo": usuario.tipo or EMPTY_VALUE,
        "id_funcionario": str(usuario.id_funcionario or ""),
        "ativo": "true" if ativo else "false",
        "status": status,
        "status_label": rotulo,
        "proprio": "true" if proprio else "false",
        # Server rules: not your own account (use the own-password change), not a technical admin and
        # not another manager's account (review M1).
        "pode_redefinir": "true" if not proprio and usuario.role != "admin" and usuario.tipo != "GERENTE" else "false",
        "pode_alternar": "true" if vinculado and not proprio else "false",
    }


def detalhe_evento(evento: EventoAcesso) -> str:
    """Short, secret-free summary of an event's metadata."""
    meta = evento.metadata if isinstance(evento.metadata, dict) else {}
    if evento.action == "admin_reset_password" and meta.get("id_usuario"):
        return f"Usuário #{meta['id_usuario']}"
    if evento.action == "signup" and meta.get("id"):
        return " · ".join(str(parte) for parte in (f"Usuário #{meta['id']}", meta.get("email")) if parte)
    return str(meta.get("email") or EMPTY_VALUE)


def evento_row(evento: EventoAcesso) -> dict[str, str]:
    acao = evento.action or ""
    autor = evento.nome_funcionario or evento.nome_usuario
    return {
        "id": str(evento.id),
        "data": format_datetime(evento.created_at),
        "acao": ACOES_EVENTO.get(acao, acao or EMPTY_VALUE),
        "usuario": autor or (f"Usuário #{evento.user_id}" if evento.user_id else EMPTY_VALUE),
        "detalhe": detalhe_evento(evento),
    }


def gerentes_ativos(rows: list[dict[str, str]]) -> int:
    return sum(1 for row in rows if row["tipo"] == "GERENTE" and row["ativo"] == "true")


class AdminState(AuthState):
    """Access accounts, access audit and the read-only system rules of /admin (GERENTE)."""

    aba: str = "usuarios"

    usuarios: list[dict[str, str]] = []
    usuarios_error: str = ""
    is_loading_usuarios: bool = False
    is_saving: bool = False

    acesso_open: bool = False
    acesso_options: list[str] = []
    acesso_funcionario: str = ""
    acesso_email: str = ""
    acesso_senha: str = ""
    acesso_confirmacao: str = ""
    acesso_error: str = ""

    senha_usuario_id: str = ""
    senha_usuario_nome: str = ""
    senha_nova: str = ""
    senha_confirmacao: str = ""
    senha_error: str = ""

    status_funcionario_id: str = ""
    status_nome: str = ""
    status_ativar: bool = False
    status_ultimo_gerente: bool = False

    eventos: list[dict[str, str]] = []
    eventos_error: str = ""
    is_loading_eventos: bool = False
    eventos_pagina: int = 1
    eventos_tem_proxima: bool = False
    eventos_tem_anterior: bool = False
    eventos_total: str = ""
    filtro_acao: str = TODAS_ACOES
    filtro_inicio: str = ""
    filtro_fim: str = ""
    # Filters of the page on screen: paging keeps them even if the inputs change.
    acao_aplicada: str = ""
    inicio_aplicado: str = ""
    fim_aplicado: str = ""

    @rx.var
    def acao_options(self) -> list[str]:
        return [TODAS_ACOES, *ACOES_EVENTO.values()]

    @rx.var
    def is_busy(self) -> bool:
        return operation_is_blocked(self.is_loading_usuarios, self.is_saving, self.is_loading_eventos)

    @rx.var
    def senha_open(self) -> bool:
        return self.senha_usuario_id != ""

    @rx.var
    def status_open(self) -> bool:
        return self.status_funcionario_id != ""

    def _pode_administrar(self) -> bool:
        return self.is_authenticated and role_allows_route(self.employee_role, ADMIN_ROUTE)

    def _ocupado(self) -> bool:
        return operation_is_blocked(self.is_loading_usuarios, self.is_saving, self.is_loading_eventos)

    def _limpar_acesso(self) -> None:
        self.acesso_open = False
        self.acesso_error = ""
        self.acesso_senha = ""
        self.acesso_confirmacao = ""

    def _limpar_senha(self) -> None:
        self.senha_usuario_id = ""
        self.senha_usuario_nome = ""
        self.senha_nova = ""
        self.senha_confirmacao = ""
        self.senha_error = ""

    def _limpar_status(self) -> None:
        self.status_funcionario_id = ""
        self.status_nome = ""
        self.status_ativar = False
        self.status_ultimo_gerente = False

    def _reload_usuarios(self, client: XanoClient) -> None:
        self.usuarios = [usuario_row(usuario, self.employee_id) for usuario in client.list_usuarios_admin()]

    def _reload_eventos(self, client: XanoClient) -> None:
        periodo = build_periodo(self.inicio_aplicado, self.fim_aplicado) if self.inicio_aplicado else None
        pagina = client.list_eventos(page=self.eventos_pagina, action=self.acao_aplicada or None, periodo=periodo)
        self.eventos = [evento_row(evento) for evento in pagina.items]
        self.eventos_pagina = pagina.pagina
        self.eventos_tem_proxima = pagina.proxima is not None
        self.eventos_tem_anterior = pagina.anterior is not None
        self.eventos_total = "" if pagina.total is None else f"{pagina.total} eventos"

    def _carregar_usuarios(self):
        self.usuarios_error = ""
        self.is_loading_usuarios = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                self._reload_usuarios(client)
        except XanoError as error:
            self.usuarios = []
            self.usuarios_error = error_feedback(error)
            if isinstance(error, XanoAuthenticationError):
                return self._xano_error_response(error)
        finally:
            self.is_loading_usuarios = False
        return None

    def _carregar_eventos(self):
        self.eventos_error = ""
        self.is_loading_eventos = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                self._reload_eventos(client)
        except XanoError as error:
            self.eventos = []
            self.eventos_error = error_feedback(error)
            if isinstance(error, XanoAuthenticationError):
                return self._xano_error_response(error)
        finally:
            self.is_loading_eventos = False
        return None

    @rx.event
    def load_admin(self):
        # Coming back to /admin never reopens a modal with the passwords typed before leaving the route.
        self._limpar_acesso()
        self._limpar_senha()
        self._limpar_status()
        if self.is_loading_usuarios or self.is_loading_eventos:
            return None
        self.usuarios_error = ""
        self.eventos_error = ""
        if not self._pode_administrar():
            return None
        resposta = yield from self._carregar_usuarios()
        if resposta is not None:
            return resposta
        self.eventos_pagina = 1
        return (yield from self._carregar_eventos())

    @rx.event
    def set_aba(self, value: str) -> None:
        self.aba = value

    # ----- create access (auth/signup) -----

    @rx.event
    def open_acesso(self):
        if not self._pode_administrar():
            return toast_error("Somente o gerente administra os acessos.")
        self.acesso_funcionario = ""
        self.acesso_email = ""
        self.acesso_senha = ""
        self.acesso_confirmacao = ""
        self.acesso_error = ""
        try:
            with XanoClient(token=self.auth_token) as client:
                funcionarios = client.list_funcionarios()
                usuarios = client.list_usuarios_admin()
        except XanoError as error:
            return self._xano_error_response(error)
        com_acesso = {usuario.id_funcionario for usuario in usuarios if usuario.id_funcionario is not None}
        self.acesso_options = [
            option_label(funcionario.id, funcionario.nome_funcionario)
            for funcionario in funcionarios
            if funcionario.ativo and funcionario.id not in com_acesso
        ]
        if not self.acesso_options:
            self.acesso_error = "Todos os funcionários ativos já têm acesso."
        self.acesso_open = True
        return None

    @rx.event
    def close_acesso(self) -> None:
        self._limpar_acesso()

    @rx.event
    def set_acesso_funcionario(self, value: str) -> None:
        self.acesso_funcionario = value
        self.acesso_error = ""

    @rx.event
    def set_acesso_email(self, value: str) -> None:
        self.acesso_email = value
        self.acesso_error = ""

    @rx.event
    def set_acesso_senha(self, value: str) -> None:
        self.acesso_senha = value
        self.acesso_error = ""

    @rx.event
    def set_acesso_confirmacao(self, value: str) -> None:
        self.acesso_confirmacao = value
        self.acesso_error = ""

    @rx.event
    def save_acesso(self):
        if self._ocupado() or not self._pode_administrar():
            return None
        if not self.acesso_funcionario:
            self.acesso_error = "Escolha o funcionário."
            return toast_error(self.acesso_error)
        problema = senha_problema(self.acesso_senha, self.acesso_confirmacao)
        if problema:
            self.acesso_error = problema
            return toast_error(problema)
        try:
            payload = AcessoCreate(
                name=self.acesso_funcionario.split(" - ", 1)[-1],
                email=self.acesso_email.strip().lower(),
                password=self.acesso_senha,
                id_funcionario=option_id(self.acesso_funcionario),
            )
        except (ValidationError, ValueError):
            self.acesso_error = "Informe um email válido."
            return toast_error(self.acesso_error)
        self.is_saving = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                client.criar_acesso(payload)
                self._limpar_acesso()
                try:
                    self._reload_usuarios(client)
                except XanoError as error:
                    self.usuarios_error = error_feedback(error)
            return toast_success("Acesso criado. Informe a senha ao funcionário pessoalmente.")
        except XanoValidationError as error:
            self.acesso_error = error_feedback(error)
            return toast_error(self.acesso_error)
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.is_saving = False

    # ----- reset another user's password -----

    @rx.event
    def open_senha(self, usuario_id: str, nome: str):
        row = next((row for row in self.usuarios if row["id"] == usuario_id), None)
        if row is None or row["pode_redefinir"] != "true":
            return toast_error("Use a troca de senha do próprio usuário para a sua conta.")
        self.senha_usuario_id = usuario_id
        self.senha_usuario_nome = nome
        self.senha_nova = ""
        self.senha_confirmacao = ""
        self.senha_error = ""
        return None

    @rx.event
    def close_senha(self) -> None:
        self._limpar_senha()

    @rx.event
    def set_senha_nova(self, value: str) -> None:
        self.senha_nova = value
        self.senha_error = ""

    @rx.event
    def set_senha_confirmacao(self, value: str) -> None:
        self.senha_confirmacao = value
        self.senha_error = ""

    @rx.event
    def save_senha(self):
        if self._ocupado() or not self._pode_administrar() or not self.senha_usuario_id:
            return None
        problema = senha_problema(self.senha_nova, self.senha_confirmacao)
        if problema:
            self.senha_error = problema
            return toast_error(problema)
        payload = SenhaReset(password=self.senha_nova, confirm_password=self.senha_confirmacao)
        self.is_saving = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                client.redefinir_senha(int(self.senha_usuario_id), payload)
            self._limpar_senha()
            return toast_success("Senha redefinida. Informe a senha temporária ao funcionário pessoalmente.")
        except XanoValidationError as error:
            self.senha_error = error_feedback(error)
            return toast_error(self.senha_error)
        except XanoError as error:
            if isinstance(error, XanoAuthenticationError):
                return self._xano_error_response(error)
            self.senha_error = error_feedback(error)
            return toast_error(self.senha_error)
        finally:
            self.is_saving = False

    # ----- deactivate / reactivate access (PATCH funcionarios) -----

    @rx.event
    def open_status(self, id_funcionario: str, nome: str):
        row = next((row for row in self.usuarios if row["id_funcionario"] == id_funcionario), None)
        if row is None or row["pode_alternar"] != "true":
            return toast_error("Você não pode desativar o próprio acesso.")
        self.status_ativar = row["ativo"] != "true"
        # S2: warn before taking away the last active manager.
        self.status_ultimo_gerente = (
            not self.status_ativar and row["tipo"] == "GERENTE" and gerentes_ativos(self.usuarios) <= 1
        )
        self.status_funcionario_id = id_funcionario
        self.status_nome = nome
        return None

    @rx.event
    def close_status(self) -> None:
        self._limpar_status()

    @rx.event
    def confirm_status(self):
        if self._ocupado() or not self._pode_administrar() or not self.status_funcionario_id:
            return None
        if self.status_funcionario_id == str(self.employee_id):
            self._limpar_status()
            return toast_error("Você não pode desativar o próprio acesso.")
        ativar = self.status_ativar
        self.is_saving = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                if ativar:
                    client.reactivate_funcionario(int(self.status_funcionario_id))
                else:
                    client.deactivate_funcionario(int(self.status_funcionario_id))
                self._limpar_status()
                try:
                    self._reload_usuarios(client)
                except XanoError as error:
                    self.usuarios_error = error_feedback(error)
            return toast_success("Acesso reativado." if ativar else "Acesso desativado.")
        except XanoError as error:
            if isinstance(error, XanoAuthenticationError):
                return self._xano_error_response(error)
            self._limpar_status()
            return toast_error(error_feedback(error))
        finally:
            self.is_saving = False

    # ----- access audit -----

    @rx.event
    def set_filtro_acao(self, value: str) -> None:
        self.filtro_acao = value

    @rx.event
    def set_filtro_inicio(self, value: str) -> None:
        self.filtro_inicio = value

    @rx.event
    def set_filtro_fim(self, value: str) -> None:
        self.filtro_fim = value

    @rx.event
    def aplicar_filtros(self):
        if self.is_loading_eventos or not self._pode_administrar():
            return None
        if bool(self.filtro_inicio) != bool(self.filtro_fim):
            self.eventos_error = "Informe o início e o fim do período, ou deixe os dois em branco."
            return toast_error(self.eventos_error)
        if self.filtro_inicio:
            try:
                build_periodo(self.filtro_inicio, self.filtro_fim)
            except FinanceiroFormError as error:
                self.eventos_error = str(error)
                return toast_error(self.eventos_error)
        self.acao_aplicada = ACAO_POR_ROTULO.get(self.filtro_acao, "")
        self.inicio_aplicado = self.filtro_inicio
        self.fim_aplicado = self.filtro_fim
        self.eventos_pagina = 1
        return (yield from self._carregar_eventos())

    @rx.event
    def eventos_proxima(self):
        if self.is_loading_eventos or not self.eventos_tem_proxima or not self._pode_administrar():
            return None
        self.eventos_pagina += 1
        return (yield from self._carregar_eventos())

    @rx.event
    def eventos_anterior(self):
        if self.is_loading_eventos or not self.eventos_tem_anterior or not self._pode_administrar():
            return None
        self.eventos_pagina = max(1, self.eventos_pagina - 1)
        return (yield from self._carregar_eventos())
