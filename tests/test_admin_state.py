"""Change 18: /admin state, row rules (S1, S2) and the client methods of the panel."""

import json
import os
import unittest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import httpx
from reflex.state import State

from Projeto_HarleyStore.admin_state import (
    TODAS_ACOES,
    AdminState,
    detalhe_evento,
    evento_row,
    gerentes_ativos,
    usuario_row,
)
from Projeto_HarleyStore.services.admin import (
    AcessoCreate,
    EventoAcesso,
    EventosPagina,
    SenhaReset,
    UsuarioAdmin,
    senha_problema,
)
from Projeto_HarleyStore.services.cadastros import Funcionario
from Projeto_HarleyStore.services.financeiro import PeriodoFinanceiro
from Projeto_HarleyStore.services.xano_client import XanoClient, XanoValidationError

from tests.event_runner import run_event

CLIENT = "Projeto_HarleyStore.admin_state.XanoClient"


def usuario(id=2, id_funcionario=12, tipo="VENDEDOR", ativo=True, role="member", nome="Ana"):
    return UsuarioAdmin(
        id=id, name=nome, email=f"{nome.lower()}@loja.test", role=role,
        id_funcionario=id_funcionario, nome_funcionario=nome, tipo=tipo, ativo=ativo,
    )


def pagina(itens=(), cur=1, nxt=None, prv=None, total=0):
    return EventosPagina.model_validate(
        {"items": list(itens), "curPage": cur, "nextPage": nxt, "prevPage": prv, "itemsTotal": total}
    )


class RowRuleTests(unittest.TestCase):
    def test_own_row_can_neither_reset_its_password_nor_lose_access(self):
        row = usuario_row(usuario(id=1, id_funcionario=10, tipo="GERENTE"), meu_funcionario=10)
        self.assertEqual((row["proprio"], row["pode_redefinir"], row["pode_alternar"]), ("true", "false", "false"))

    def test_technical_admin_password_is_reset_only_in_the_xano_panel(self):
        row = usuario_row(usuario(role="admin"), meu_funcionario=10)
        self.assertEqual((row["pode_redefinir"], row["pode_alternar"]), ("false", "true"))

    def test_another_managers_password_cannot_be_reset_but_access_can_be_toggled(self):
        # Review M1: the server refuses it with 403; the panel does not offer it.
        row = usuario_row(usuario(id=3, id_funcionario=11, tipo="GERENTE", nome="Outro"), meu_funcionario=10)
        self.assertEqual((row["pode_redefinir"], row["pode_alternar"]), ("false", "true"))

    def test_status_follows_the_linked_employee(self):
        self.assertEqual(usuario_row(usuario(ativo=False), 10)["status"], "INATIVO")
        sem = usuario_row(UsuarioAdmin(id=3, name="Painel", email="p@x.test"), 10)
        self.assertEqual((sem["status"], sem["pode_alternar"], sem["nome"]), ("SEM_VINCULO", "false", "Painel"))

    def test_counts_only_active_managers(self):
        rows = [usuario_row(usuario(id=i, id_funcionario=i, tipo=t, ativo=a), 99) for i, t, a in
                ((1, "GERENTE", True), (2, "GERENTE", False), (3, "VENDEDOR", True))]
        self.assertEqual(gerentes_ativos(rows), 1)

    def test_event_rows_are_labelled_and_secret_free(self):
        reset = EventoAcesso(id=9, action="admin_reset_password", user_id=1, nome_funcionario="Gerente",
                             metadata={"id_usuario": 2, "id_funcionario": 12, "id_gerente": 10},
                             created_at=datetime(2026, 11, 23, 15, 0, tzinfo=UTC))
        row = evento_row(reset)
        self.assertEqual((row["acao"], row["usuario"], row["detalhe"]), ("Senha redefinida pelo gerente", "Gerente", "Usuário #2"))
        signup = EventoAcesso(id=8, action="signup", user_id=1, metadata={"id": 5, "email": "novo@loja.test", "role": "member"})
        self.assertEqual(detalhe_evento(signup), "Usuário #5 · novo@loja.test")
        self.assertEqual(evento_row(EventoAcesso(id=7, action="outra", user_id=4))["usuario"], "Usuário #4")


class PasswordPolicyTests(unittest.TestCase):
    def test_policy_of_the_user_table(self):
        self.assertIn("8 caracteres", senha_problema("Ab1", "Ab1"))
        self.assertIn("letra e um número", senha_problema("somenteletras", "somenteletras"))
        self.assertIn("letra e um número", senha_problema("12345678", "12345678"))
        self.assertIn("confirmação", senha_problema("Senha1234", "Senha12345"))
        self.assertEqual(senha_problema(" Senha1234 ", " Senha1234 "), "")  # never trimmed


class AdminStateTests(unittest.TestCase):
    def make_state(self, role="GERENTE", authenticated=True):
        root = State(_reflex_internal_init=True)
        state = root.get_substate(AdminState.get_full_name().split("."))
        state.auth_token = "token"
        state.is_authenticated = authenticated
        state.employee_role = role
        state.employee_id = 10
        state.is_loading_usuarios = state.is_loading_eventos = state.is_saving = False
        state.usuarios = [
            usuario_row(usuario(id=1, id_funcionario=10, tipo="GERENTE", nome="Gerente"), 10),
            usuario_row(usuario(id=2, id_funcionario=12), 10),
        ]
        state.eventos_pagina = 1
        state.acao_aplicada = state.inicio_aplicado = state.fim_aplicado = ""
        return state

    def test_load_skips_xano_for_other_roles_and_without_session(self):
        for role, authenticated in (("VENDEDOR", True), ("MECANICO", True), ("GERENTE", False)):
            with self.subTest(role=role, authenticated=authenticated), patch(CLIENT) as client_class:
                run_event(AdminState.load_admin, self.make_state(role, authenticated))
                client_class.assert_not_called()

    def test_load_reads_users_and_the_first_audit_page(self):
        state = self.make_state()
        client = MagicMock()
        client.list_usuarios_admin.return_value = [usuario(id=1, id_funcionario=10, tipo="GERENTE")]
        client.list_eventos.return_value = pagina([{"id": 1, "action": "login", "user_id": 1}], nxt=2, total=30)
        with patch(CLIENT) as client_class:
            client_class.return_value.__enter__.return_value = client
            run_event(AdminState.load_admin, state)
        client.list_eventos.assert_called_once_with(page=1, action=None, periodo=None)
        self.assertEqual(state.usuarios[0]["proprio"], "true")
        self.assertEqual((state.eventos[0]["acao"], state.eventos_tem_proxima, state.eventos_total), ("Login", True, "30 eventos"))
        self.assertFalse(state.is_loading_usuarios or state.is_loading_eventos)

    def test_create_access_lists_only_active_employees_without_a_login(self):
        state = self.make_state()
        client = MagicMock()
        client.list_funcionarios.return_value = [
            Funcionario(id=10, nome_funcionario="Gerente", cargo="g", tipo="GERENTE", ativo=True),
            Funcionario(id=5, nome_funcionario="Funcionário Teste", cargo="v", tipo="VENDEDOR", ativo=True),
            Funcionario(id=6, nome_funcionario="Inativo", cargo="v", tipo="VENDEDOR", ativo=False),
        ]
        client.list_usuarios_admin.return_value = [usuario(id=1, id_funcionario=10, tipo="GERENTE")]
        with patch(CLIENT) as client_class:
            client_class.return_value.__enter__.return_value = client
            run_event(AdminState.open_acesso, state)
        self.assertEqual(state.acesso_options, ["5 - Funcionário Teste"])
        self.assertTrue(state.acesso_open)

    def test_weak_password_or_bad_email_never_reaches_xano(self):
        for senha, confirmacao, email in (("curta1", "curta1", "a@loja.test"), ("Senha1234", "Outra1234", "a@loja.test"), ("Senha1234", "Senha1234", "sem-arroba")):
            state = self.make_state()
            state.acesso_funcionario, state.acesso_email = "5 - Funcionário Teste", email
            state.acesso_senha, state.acesso_confirmacao = senha, confirmacao
            with self.subTest(senha=senha, email=email), patch(CLIENT) as client_class:
                self.assertIsNotNone(run_event(AdminState.save_acesso, state))
                client_class.assert_not_called()
                self.assertTrue(state.acesso_error)

    def test_created_access_sends_the_untrimmed_password_and_clears_it(self):
        state = self.make_state()
        state.acesso_open = True
        state.acesso_funcionario, state.acesso_email = "5 - Funcionário Teste", " Novo@Loja.test "
        state.acesso_senha = state.acesso_confirmacao = " Senha1234"
        client = MagicMock()
        client.list_usuarios_admin.return_value = []
        with patch(CLIENT) as client_class:
            client_class.return_value.__enter__.return_value = client
            run_event(AdminState.save_acesso, state)
        payload = client.criar_acesso.call_args.args[0]
        self.assertEqual(payload, AcessoCreate(name="Funcionário Teste", email="novo@loja.test", password=" Senha1234", id_funcionario=5))
        self.assertFalse(state.acesso_open)
        self.assertEqual((state.acesso_senha, state.acesso_confirmacao), ("", ""))

    def test_password_reset_refuses_the_own_row_and_clears_on_success(self):
        state = self.make_state()
        self.assertIsNotNone(run_event(AdminState.open_senha, state, "1", "Gerente"))  # S1: own account
        self.assertEqual(state.senha_usuario_id, "")
        run_event(AdminState.open_senha, state, "2", "Ana")
        state.senha_nova = state.senha_confirmacao = "Temp12345"
        client = MagicMock()
        with patch(CLIENT) as client_class:
            client_class.return_value.__enter__.return_value = client
            run_event(AdminState.save_senha, state)
        client.redefinir_senha.assert_called_once_with(2, SenhaReset(password="Temp12345", confirm_password="Temp12345"))
        self.assertEqual((state.senha_usuario_id, state.senha_nova), ("", ""))

    def test_rejected_reset_keeps_the_modal_with_the_server_message(self):
        state = self.make_state()
        run_event(AdminState.open_senha, state, "2", "Ana")
        state.senha_nova = state.senha_confirmacao = "Temp12345"
        client = MagicMock()
        client.redefinir_senha.side_effect = XanoValidationError("A confirmação não confere.", status_code=400)
        with patch(CLIENT) as client_class:
            client_class.return_value.__enter__.return_value = client
            run_event(AdminState.save_senha, state)
        self.assertEqual(state.senha_usuario_id, "2")
        self.assertTrue(state.senha_error)
        self.assertFalse(state.is_saving)

    def test_manager_cannot_deactivate_own_access(self):
        state = self.make_state()
        self.assertIsNotNone(run_event(AdminState.open_status, state, "10", "Gerente"))  # S1
        self.assertEqual(state.status_funcionario_id, "")
        state.status_funcionario_id, state.status_ativar = "10", False  # forged: confirm also refuses
        with patch(CLIENT) as client_class:
            run_event(AdminState.confirm_status, state)
            client_class.assert_not_called()

    def test_warns_before_taking_away_the_last_active_manager(self):
        state = self.make_state()
        state.employee_id = 99  # e.g. a technical admin without a manager row
        state.usuarios = [usuario_row(usuario(id=1, id_funcionario=10, tipo="GERENTE"), 99)]
        run_event(AdminState.open_status, state, "10", "Gerente")
        self.assertTrue(state.status_ultimo_gerente)  # S2
        state.usuarios = [usuario_row(usuario(id=i, id_funcionario=i, tipo="GERENTE"), 99) for i in (10, 11)]
        run_event(AdminState.open_status, state, "10", "Gerente")
        self.assertFalse(state.status_ultimo_gerente)

    def test_deactivate_and_reactivate_use_the_employee_patch(self):
        for ativo, metodo in ((True, "deactivate_funcionario"), (False, "reactivate_funcionario")):
            state = self.make_state()
            state.usuarios = [usuario_row(usuario(id=2, id_funcionario=12, ativo=ativo), 10)]
            run_event(AdminState.open_status, state, "12", "Ana")
            client = MagicMock()
            client.list_usuarios_admin.return_value = []
            with self.subTest(metodo=metodo), patch(CLIENT) as client_class:
                client_class.return_value.__enter__.return_value = client
                run_event(AdminState.confirm_status, state)
                getattr(client, metodo).assert_called_once_with(12)
                self.assertEqual(state.status_funcionario_id, "")

    def test_audit_paging_checks_the_role_before_calling_xano(self):
        # Review L1: paging carries the same guard as every other action that reads Xano.
        for role in ("VENDEDOR", "MECANICO"):
            state = self.make_state(role)
            state.eventos_tem_proxima = state.eventos_tem_anterior = True
            state.eventos_pagina = 2
            with self.subTest(role=role), patch(CLIENT) as client_class:
                run_event(AdminState.eventos_proxima, state)
                run_event(AdminState.eventos_anterior, state)
                client_class.assert_not_called()
                self.assertEqual(state.eventos_pagina, 2)

    def test_audit_filters_validate_the_period_before_calling_xano(self):
        state = self.make_state()
        state.filtro_inicio, state.filtro_fim = "2026-11-01", ""
        with patch(CLIENT) as client_class:
            self.assertIsNotNone(run_event(AdminState.aplicar_filtros, state))
            client_class.assert_not_called()
        state.filtro_inicio, state.filtro_fim = "2025-01-01", "2026-11-23"
        with patch(CLIENT) as client_class:
            self.assertIsNotNone(run_event(AdminState.aplicar_filtros, state))  # more than 366 days
            client_class.assert_not_called()

    def test_audit_filters_and_paging_reach_the_client(self):
        state = self.make_state()
        state.filtro_acao, state.filtro_inicio, state.filtro_fim = "Senha redefinida pelo gerente", "2026-11-01", "2026-11-23"
        client = MagicMock()
        client.list_eventos.side_effect = [pagina(nxt=2, total=40), pagina(cur=2, prv=1, total=40)]
        with patch(CLIENT) as client_class:
            client_class.return_value.__enter__.return_value = client
            run_event(AdminState.aplicar_filtros, state)
            state.filtro_acao = TODAS_ACOES  # typing after filtering does not change the next page
            run_event(AdminState.eventos_proxima, state)
        first, second = client.list_eventos.call_args_list
        periodo = PeriodoFinanceiro(inicio="2026-11-01", fim="2026-11-23")
        self.assertEqual(first.kwargs, {"page": 1, "action": "admin_reset_password", "periodo": periodo})
        self.assertEqual(second.kwargs, {"page": 2, "action": "admin_reset_password", "periodo": periodo})
        self.assertEqual((state.eventos_pagina, state.eventos_tem_anterior), (2, True))


class AdminClientTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {"XANO_API_BASE_URL": "https://xano.test/api:test", "XANO_AUTH_API_BASE_URL": "https://xano.test/api:auth"},
        )
        self.environment.start()
        self.requests = []

    def tearDown(self):
        self.environment.stop()

    def client(self, payload):
        def handler(request):
            self.requests.append(request)
            return httpx.Response(200, json=payload)

        return XanoClient(token="token", transport=httpx.MockTransport(handler))

    def test_create_access_goes_to_the_authentication_group(self):
        with self.client({"user_id": 7, "id_funcionario": 5}) as client:
            criado = client.criar_acesso(AcessoCreate(name="Teste", email="t@loja.test", password="Senha1234", id_funcionario=5))
        request = self.requests[0]
        self.assertEqual((request.method, str(request.url)), ("POST", "https://xano.test/api:auth/auth/signup"))
        self.assertEqual(json.loads(request.content)["id_funcionario"], 5)
        self.assertEqual(criado.user_id, 7)

    def test_audit_sends_page_action_and_period_in_milliseconds(self):
        with self.client({"items": [], "curPage": 1, "nextPage": None, "prevPage": None, "itemsTotal": 0}) as client:
            client.list_eventos(page=2, action="login", periodo=PeriodoFinanceiro(inicio="2026-11-01", fim="2026-11-01"))
        params = dict(self.requests[0].url.params)
        self.assertEqual(self.requests[0].url.path, "/api:test/admin/eventos")
        self.assertEqual((params["page"], params["action"]), ("2", "login"))
        self.assertEqual(int(params["data_fim"]) - int(params["data_inicio"]), 86_400_000 - 1)

    def test_users_list_ignores_any_secret_the_server_might_send(self):
        with self.client([{"id": 1, "email": "a@loja.test", "password": "hash", "password_reset": {"token": "x"}}]) as client:
            usuarios = client.list_usuarios_admin()
        self.assertNotIn("password", usuarios[0].model_dump())
        self.assertNotIn("password_reset", usuarios[0].model_dump())

    def test_password_reset_posts_to_the_user_and_returns_no_password(self):
        with self.client({"id": 2, "name": "Ana", "email": "ana@loja.test"}) as client:
            resumo = client.redefinir_senha(2, SenhaReset(password="Temp12345", confirm_password="Temp12345"))
        self.assertEqual(self.requests[0].url.path, "/api:test/admin/usuarios/2/senha")
        self.assertNotIn("password", resumo.model_dump())


if __name__ == "__main__":
    unittest.main()
