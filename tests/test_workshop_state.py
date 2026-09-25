import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from reflex.state import State

from Projeto_HarleyStore.services.cadastros import Cliente, MotoCliente
from Projeto_HarleyStore.services.ordens_servico import (
    HistoricoStatusOS,
    Mecanico,
    OrdemServicoDetalhe,
    OrdemServicoResumo,
)
from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoValidationError,
)
from Projeto_HarleyStore.workshop_state import (
    STATUS_FILTER_ALL,
    WorkshopFormError,
    WorkshopState,
    allowed_transitions,
    build_abertura_payload,
    build_transicao_payload,
    can_operate_os,
    detalhe_row,
    filter_by_status,
    historico_row,
    motos_do_cliente,
    os_row,
    status_counts,
)


def resumo(os_id=31, status="ABERTA", **extra):
    data = {
        "id": os_id,
        "status": status,
        "id_moto_cliente": 12,
        "data_abertura": datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc),
        "tipo_servico": "CORRETIVA",
        "descricao_problema": "Ruído na embreagem",
        "nome_cliente": "Ana Souza",
        "placa": "ABC1D23",
        "modelo": "Street Glide",
        "nome_funcionario": "Carlos",
        "nome_mecanico": "Bruno",
    }
    data.update(extra)
    return OrdemServicoResumo(**data)


def detalhe(os_id=31, status="ABERTA", **extra):
    return OrdemServicoDetalhe(**resumo(os_id, status).model_dump(), **extra)


class WorkshopRulesTests(unittest.TestCase):
    def test_only_managers_and_mechanics_operate(self):
        self.assertTrue(can_operate_os("GERENTE"))
        self.assertTrue(can_operate_os("MECANICO"))
        self.assertFalse(can_operate_os("VENDEDOR"))
        self.assertFalse(can_operate_os(""))

    def test_allowed_transitions_follow_status_and_role(self):
        values = lambda status, role: [a["value"] for a in allowed_transitions(status, role)]
        self.assertEqual(values("ABERTA", "MECANICO"), ["EM_ANDAMENTO", "CANCELADA"])
        self.assertEqual(values("EM_ANDAMENTO", "GERENTE"), ["CONCLUIDA", "CANCELADA"])
        self.assertEqual(values("CONCLUIDA", "GERENTE"), [])
        self.assertEqual(values("CANCELADA", "MECANICO"), [])
        self.assertEqual(values("ABERTA", "VENDEDOR"), [])

    def test_status_filter_and_counts(self):
        rows = [os_row(resumo(1, "ABERTA")), os_row(resumo(2, "ABERTA")), os_row(resumo(3, "CONCLUIDA"))]
        self.assertEqual(len(filter_by_status(rows, STATUS_FILTER_ALL)), 3)
        self.assertEqual([r["id"] for r in filter_by_status(rows, "ABERTA")], ["1", "2"])
        self.assertEqual(
            status_counts(rows),
            {"TODAS": 3, "ABERTA": 2, "EM_ANDAMENTO": 0, "CONCLUIDA": 1, "CANCELADA": 0},
        )

    def test_bike_options_only_active_bikes_of_the_customer(self):
        motos = [
            {"id": "1", "id_cliente": "5", "label": "1 - ABC · Street", "ativo": "true"},
            {"id": "2", "id_cliente": "5", "label": "2 - DEF · Iron", "ativo": "false"},
            {"id": "3", "id_cliente": "6", "label": "3 - GHI · Fat Boy", "ativo": "true"},
        ]
        self.assertEqual(motos_do_cliente(motos, "5 - Ana"), ["1 - ABC · Street"])
        self.assertEqual(motos_do_cliente(motos, ""), [])

    def test_opening_payload_from_form(self):
        payload = build_abertura_payload(
            "5 - Ana", "12 - ABC · Street", "4 - Bruno", "Corretiva", " Ruído ", "18350", "GERENTE"
        )
        self.assertEqual(
            payload.model_dump(),
            {
                "id_moto_cliente": 12,
                "id_mecanico": 4,
                "tipo_servico": "CORRETIVA",
                "descricao_problema": "Ruído",
                "quilometragem": 18350,
            },
        )
        mechanic_self = build_abertura_payload(
            "5 - Ana", "12 - ABC · Street", "", "Preventiva", "Revisão", "", "MECANICO"
        )
        self.assertIsNone(mechanic_self.id_mecanico)
        self.assertIsNone(mechanic_self.quilometragem)

    def test_opening_payload_reports_readable_errors(self):
        base = ["5 - Ana", "12 - ABC", "4 - Bruno", "Corretiva", "Ruído", "", "GERENTE"]
        cases = {
            "Selecione o cliente.": {0: ""},
            "Selecione a moto do cliente.": {1: ""},
            "Informe o mecânico responsável.": {2: ""},
            "Selecione o tipo de serviço.": {3: "Revisão"},
            "Descreva o problema ou o serviço solicitado.": {4: "   "},
            "A quilometragem deve ser um número inteiro não negativo.": {5: "-3"},
        }
        cases_abc = {"A quilometragem deve ser um número inteiro não negativo.": {5: "abc"}}
        for message, changes in [*cases.items(), *cases_abc.items()]:
            args = list(base)
            for index, value in changes.items():
                args[index] = value
            with self.subTest(message=message, changes=changes):
                with self.assertRaises(WorkshopFormError) as context:
                    build_abertura_payload(*args)
                self.assertEqual(str(context.exception), message)

    def test_transition_payload_errors(self):
        with self.assertRaises(WorkshopFormError) as context:
            build_transicao_payload("ABERTA", "CANCELADA", "  ")
        self.assertEqual(str(context.exception), "Informe o motivo do cancelamento.")
        with self.assertRaises(WorkshopFormError):
            build_transicao_payload("ABERTA", "CONCLUIDA", "")
        payload = build_transicao_payload("EM_ANDAMENTO", "CANCELADA", " Peça indisponível ")
        self.assertEqual(payload.observacao, "Peça indisponível")

    def test_rows_are_human_readable(self):
        row = os_row(resumo(tipo_servico=None, placa=None))
        self.assertEqual(row["numero"], "#31")
        self.assertEqual(row["tipo"], "—")
        self.assertEqual(row["moto"], "Street Glide")
        self.assertEqual(row["status_label"], "Aberta")
        detail = detalhe_row(detalhe(quilometragem=18350))
        self.assertEqual(detail["quilometragem"], "18.350 km")
        self.assertEqual(detail["encerramento"], "—")
        opening = historico_row(HistoricoStatusOS(id=1, status_novo="ABERTA"))
        self.assertEqual((opening["de"], opening["para"]), ("Abertura", "Aberta"))


class WorkshopStateEventTests(unittest.TestCase):
    def make_state(self, role="MECANICO", authenticated=True):
        root = State(_reflex_internal_init=True)
        state = root.get_substate(WorkshopState.get_full_name().split("."))
        state.auth_token = "token"
        state.is_authenticated = authenticated
        state.employee_role = role
        state.employee_id = 4
        return state

    def patched_client(self):
        patcher = patch("Projeto_HarleyStore.workshop_state.XanoClient")
        client_class = patcher.start()
        self.addCleanup(patcher.stop)
        client = MagicMock()
        client_class.return_value.__enter__.return_value = client
        return client_class, client

    def test_load_without_session_does_not_call_xano(self):
        state = self.make_state(authenticated=False)
        client_class, _ = self.patched_client()
        WorkshopState.load_ordens.fn(state)
        client_class.assert_not_called()

    def test_salesperson_loads_orders_but_cannot_operate(self):
        state = self.make_state(role="VENDEDOR")
        client_class, client = self.patched_client()
        client.list_ordens_servico.return_value = [resumo()]
        WorkshopState.load_ordens.fn(state)
        self.assertEqual(state.ordens[0]["numero"], "#31")
        self.assertFalse(state.can_operate)

        client_class.reset_mock()
        WorkshopState.open_create.fn(state)
        WorkshopState.save_os.fn(state)
        client_class.assert_not_called()
        self.assertFalse(state.form_open)

    def test_open_create_preselects_the_mechanic_and_filters_bikes(self):
        state = self.make_state(role="MECANICO")
        _, client = self.patched_client()
        client.list_clientes.return_value = [
            Cliente(id=5, nome_cliente="Ana", cpf_cnpj="1"),
            Cliente(id=6, nome_cliente="Inativo", cpf_cnpj="2", ativo=False),
        ]
        client.list_motos_clientes.return_value = [
            MotoCliente(id=12, id_cliente=5, modelo="Street", placa="ABC", chassi="X1"),
            MotoCliente(id=13, id_cliente=6, modelo="Iron", placa="DEF", chassi="X2"),
        ]
        client.list_mecanicos.return_value = [
            Mecanico(id=3, nome_funcionario="Ana Mecânica"),
            Mecanico(id=4, nome_funcionario="Bruno"),
        ]
        WorkshopState.open_create.fn(state)
        self.assertTrue(state.form_open)
        self.assertEqual(state.cliente_options, ["5 - Ana"])
        self.assertEqual(state.mecanico, "4 - Bruno")
        WorkshopState.set_cliente.fn(state, "5 - Ana")
        self.assertEqual(state.moto_options, ["12 - ABC · Street"])

    def test_invalid_form_is_rejected_locally(self):
        state = self.make_state()
        client_class, _ = self.patched_client()
        state.cliente = "5 - Ana"
        WorkshopState.save_os.fn(state)
        client_class.assert_not_called()
        self.assertEqual(state.form_error, "Selecione a moto do cliente.")

    def test_successful_opening_closes_form_and_reloads(self):
        state = self.make_state()
        _, client = self.patched_client()
        client.abrir_ordem_servico.return_value = detalhe()
        client.list_ordens_servico.return_value = [resumo()]
        state.form_open = True
        state.cliente, state.moto, state.mecanico = "5 - Ana", "12 - ABC", "4 - Bruno"
        state.tipo_servico, state.descricao_problema = "Corretiva", "Ruído"
        WorkshopState.save_os.fn(state)
        self.assertEqual(client.abrir_ordem_servico.call_args.args[0].id_moto_cliente, 12)
        self.assertFalse(state.form_open)
        self.assertFalse(state.is_saving)
        self.assertEqual(len(state.ordens), 1)

    def test_business_rejection_keeps_form_open(self):
        state = self.make_state()
        _, client = self.patched_client()
        client.abrir_ordem_servico.side_effect = XanoValidationError(
            "Esta moto já possui uma OS em aberto (nº 30).", status_code=400
        )
        state.form_open = True
        state.cliente, state.moto = "5 - Ana", "12 - ABC"
        state.tipo_servico, state.descricao_problema = "Corretiva", "Ruído"
        WorkshopState.save_os.fn(state)
        self.assertTrue(state.form_open)
        self.assertIn("OS em aberto", state.form_error)

    def test_detail_excludes_current_order_from_bike_history(self):
        state = self.make_state()
        _, client = self.patched_client()
        client.get_ordem_servico.return_value = detalhe(31, "EM_ANDAMENTO")
        client.list_ordens_servico.return_value = [resumo(31), resumo(20, "CONCLUIDA")]
        WorkshopState.open_detail.fn(state, "31")
        self.assertTrue(state.detail_open)
        self.assertEqual([row["id"] for row in state.historico_moto], ["20"])
        self.assertEqual(
            [action["value"] for action in state.available_transitions],
            ["CONCLUIDA", "CANCELADA"],
        )
        client.list_ordens_servico.assert_called_with(id_moto_cliente=12)

    def test_transition_requires_allowed_target_and_reason(self):
        state = self.make_state()
        state.detalhe = {"id": "31", "status": "ABERTA"}
        WorkshopState.start_transition.fn(state, "CONCLUIDA")
        self.assertEqual(state.transition_target, "")
        WorkshopState.start_transition.fn(state, "CANCELADA")
        self.assertEqual(state.transition_target, "CANCELADA")
        client_class, _ = self.patched_client()
        WorkshopState.confirm_transition.fn(state)
        client_class.assert_not_called()
        self.assertEqual(state.transition_error, "Informe o motivo do cancelamento.")

    def test_successful_transition_updates_detail(self):
        state = self.make_state()
        state.detalhe = {"id": "31", "status": "ABERTA"}
        state.transition_target = "EM_ANDAMENTO"
        _, client = self.patched_client()
        client.transicionar_ordem_servico.return_value = detalhe(31, "EM_ANDAMENTO")
        client.list_ordens_servico.return_value = [resumo(31, "EM_ANDAMENTO")]
        WorkshopState.confirm_transition.fn(state)
        os_id, payload = client.transicionar_ordem_servico.call_args.args
        self.assertEqual((os_id, payload.status_atual, payload.status_novo), (31, "ABERTA", "EM_ANDAMENTO"))
        self.assertEqual(state.detalhe["status"], "EM_ANDAMENTO")
        self.assertEqual(state.transition_target, "")
        self.assertFalse(state.is_transitioning)

    def test_conflict_reloads_real_status_and_shows_message(self):
        state = self.make_state()
        state.detalhe = {"id": "31", "status": "ABERTA"}
        state.transition_target = "EM_ANDAMENTO"
        _, client = self.patched_client()
        client.transicionar_ordem_servico.side_effect = XanoValidationError(
            "A OS foi alterada por outro usuário. Atualize e tente novamente.", status_code=400
        )
        client.get_ordem_servico.return_value = detalhe(31, "CANCELADA")
        client.list_ordens_servico.return_value = []
        WorkshopState.confirm_transition.fn(state)
        self.assertEqual(state.detalhe["status"], "CANCELADA")
        self.assertEqual(state.transition_target, "")
        self.assertIn("alterada por outro usuário", state.transition_error)
        self.assertEqual(state.available_transitions, [])

    def test_blocked_while_another_operation_runs(self):
        state = self.make_state()
        state.detalhe = {"id": "31", "status": "ABERTA"}
        state.transition_target = "EM_ANDAMENTO"
        state.is_transitioning = True
        client_class, _ = self.patched_client()
        WorkshopState.confirm_transition.fn(state)
        client_class.assert_not_called()

    def test_expired_session_on_load_clears_session(self):
        state = self.make_state()
        _, client = self.patched_client()
        client.list_ordens_servico.side_effect = XanoAuthenticationError("expired")
        WorkshopState.load_ordens.fn(state)
        self.assertEqual(state.auth_token, "")
        self.assertFalse(state.is_authenticated)
        self.assertEqual(state.ordens, [])


if __name__ == "__main__":
    unittest.main()
