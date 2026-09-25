import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from reflex.state import State

from Projeto_HarleyStore.services.cadastros import Cliente, MotoCliente, Produto
from Projeto_HarleyStore.services.ordens_servico import (
    HistoricoStatusOS,
    ItemOrdemServico,
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
    build_item_payload,
    build_transicao_payload,
    can_edit_items,
    can_operate_os,
    detalhe_row,
    filter_by_status,
    filtrar_produtos,
    historico_row,
    item_row,
    motos_do_cliente,
    os_row,
    preview_item_total,
    produto_row,
    status_counts,
    totais_row,
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
    return OrdemServicoDetalhe(**{**resumo(os_id, status).model_dump(), **extra})


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


class WorkshopStateTestCase(unittest.TestCase):
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


class WorkshopStateEventTests(WorkshopStateTestCase):
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


def produto(produto_id=3, codigo="OLEO20W50", nome="Óleo 20W50", saldo=5, preco="45.90", ativo=True):
    return Produto(
        id=produto_id,
        codigo=codigo,
        nome_produto=nome,
        categoria="Lubrificantes",
        estoque_qtd=saldo,
        preco_venda=Decimal(preco),
        ativo=ativo,
    )


def item(item_id=7, **extra):
    data = {
        "id": item_id,
        "tipo_item": "PECA",
        "id_produto": 3,
        "codigo": "OLEO20W50",
        "nome_produto": "Óleo 20W50",
        "quantidade": 2,
        "valor_unitario": Decimal("45.90"),
        "valor_total_item": Decimal("91.80"),
        "estoque_baixado": True,
    }
    data.update(extra)
    return ItemOrdemServico(**data)


CATALOGO = [
    produto_row(produto()),
    produto_row(produto(4, "PASTILHA01", "Pastilha de freio", saldo=0, preco="120.00")),
    produto_row(produto(5, "FILTROAR", "Filtro de ar", saldo=2, preco="80.00")),
]


class WorkshopItemRulesTests(unittest.TestCase):
    def test_items_are_editable_only_in_open_orders_by_operators(self):
        for status in ("ABERTA", "EM_ANDAMENTO"):
            self.assertTrue(can_edit_items(status, "MECANICO"))
            self.assertTrue(can_edit_items(status, "GERENTE"))
            self.assertFalse(can_edit_items(status, "VENDEDOR"))
        for status in ("CONCLUIDA", "CANCELADA"):
            self.assertFalse(can_edit_items(status, "GERENTE"))

    def test_product_rows_expose_balance_price_and_availability(self):
        row = CATALOGO[0]
        self.assertEqual(
            (row["saldo"], row["preco"], row["preco_valor"], row["disponivel"]),
            ("5", "R$ 45,90", "45.90", "true"),
        )
        self.assertEqual((CATALOGO[1]["saldo"], CATALOGO[1]["disponivel"]), ("0", "false"))

    def test_product_search_ignores_case_accents_and_limits_results(self):
        self.assertEqual([row["id"] for row in filtrar_produtos(CATALOGO, "oleo")], ["3"])
        self.assertEqual([row["id"] for row in filtrar_produtos(CATALOGO, "FILTRO")], ["5"])
        self.assertEqual(len(filtrar_produtos(CATALOGO, "")), 3)
        self.assertEqual(len(filtrar_produtos(CATALOGO, "", limite=2)), 2)

    def test_part_payload_checks_selection_quantity_and_balance(self):
        payload = build_item_payload("PECA", "3", CATALOGO, "2", "", "")
        self.assertEqual(
            payload.model_dump(exclude_none=True),
            {"tipo_item": "PECA", "id_produto": 3, "quantidade": 2},
        )
        cases = {
            "Selecione o produto.": ("", "1"),
            "A quantidade deve ser um número inteiro maior que zero.": ("3", "0"),
            "Saldo insuficiente para OLEO20W50: disponível 5.": ("3", "6"),
        }
        for message, (produto_id, quantidade) in cases.items():
            with self.subTest(message=message), self.assertRaises(WorkshopFormError) as context:
                build_item_payload("PECA", produto_id, CATALOGO, quantidade, "", "")
            self.assertEqual(str(context.exception), message)

    def test_service_payload_parses_comma_decimal(self):
        payload = build_item_payload("SERVICO", "", CATALOGO, "1", " Revisão ", "380,50")
        self.assertEqual(payload.valor_unitario, Decimal("380.50"))
        self.assertEqual(payload.descricao, "Revisão")
        cases = {
            "Informe a descrição do serviço.": ("", "10"),
            "Informe o valor do serviço.": ("Revisão", ""),
            "Informe um valor numérico válido para o serviço.": ("Revisão", "abc"),
            "O valor do serviço deve ser positivo, com até duas casas decimais.": ("Revisão", "-1"),
        }
        for message, (descricao, valor) in cases.items():
            with self.subTest(message=message), self.assertRaises(WorkshopFormError) as context:
                build_item_payload("SERVICO", "", CATALOGO, "1", descricao, valor)
            self.assertEqual(str(context.exception), message)

    def test_preview_only_for_complete_forms(self):
        self.assertEqual(preview_item_total("PECA", CATALOGO[0], "2", ""), Decimal("91.80"))
        self.assertEqual(preview_item_total("SERVICO", None, "2", "10,5"), Decimal("21.0"))
        for args in (("PECA", None, "2", ""), ("PECA", CATALOGO[0], "x", ""), ("SERVICO", None, "1", "")):
            with self.subTest(args=args):
                self.assertIsNone(preview_item_total(*args))

    def test_item_rows_and_totals(self):
        peca = item_row(item())
        self.assertEqual(
            (peca["tipo_label"], peca["descricao"], peca["unitario"], peca["total"], peca["baixado"]),
            ("Peça", "OLEO20W50 · Óleo 20W50", "R$ 45,90", "R$ 91,80", "true"),
        )
        servico = item_row(
            item(8, tipo_item="SERVICO", id_produto=None, codigo=None, nome_produto=None,
                 descricao="Troca do kit", estoque_baixado=False)
        )
        self.assertEqual((servico["tipo_label"], servico["descricao"]), ("Serviço", "Troca do kit"))
        legado = item_row(
            ItemOrdemServico(id=1, tipo_item=None, id_produto=2, quantidade=1, valor_total_item=10)
        )
        self.assertEqual((legado["tipo"], legado["unitario"], legado["baixado"]), ("PECA", "—", "false"))
        totais = totais_row(
            detalhe(valor_pecas=Decimal("91.8"), valor_servicos=Decimal("380"), valor_total=Decimal("471.8"))
        )
        self.assertEqual(
            (totais["pecas"], totais["servicos"], totais["total"]),
            ("R$ 91,80", "R$ 380,00", "R$ 471,80"),
        )
        self.assertEqual(totais_row(detalhe())["total"], "R$ 0,00")
        self.assertEqual(os_row(resumo(valor_total=Decimal("471.8")))["total"], "R$ 471,80")


class WorkshopItemEventTests(WorkshopStateTestCase):
    def open_state(self, role="MECANICO", status="EM_ANDAMENTO"):
        state = self.make_state(role)
        client_class, client = self.patched_client()
        client.get_ordem_servico.return_value = detalhe(31, status, itens=[item()])
        client.list_ordens_servico.return_value = [resumo(31, status)]
        client.list_produtos.return_value = [produto(), produto(9, "INATIVO", "x", ativo=False)]
        WorkshopState.open_detail.fn(state, "31")
        return state, client_class, client

    def test_open_order_loads_active_catalog_for_operators(self):
        state, _, client = self.open_state()
        self.assertTrue(state.can_edit_items)
        self.assertEqual([row["id"] for row in state.catalogo_produtos], ["3"])
        state, _, client = self.open_state(role="VENDEDOR")
        self.assertFalse(state.can_edit_items)
        client.list_produtos.assert_not_called()

    def test_closed_order_hides_editing_and_rejects_forged_events(self):
        state, client_class, client = self.open_state(status="CONCLUIDA")
        self.assertFalse(state.can_edit_items)
        client.list_produtos.assert_not_called()
        WorkshopState.ask_remove_item.fn(state, "7")
        self.assertEqual(state.item_to_remove, "")
        client_class.reset_mock()
        WorkshopState.save_item.fn(state)
        client_class.assert_not_called()
        self.assertIn("aberta ou em andamento", state.item_error)

    def test_selecting_product_without_balance_is_ignored(self):
        state, _, _ = self.open_state()
        state.catalogo_produtos = CATALOGO
        WorkshopState.select_produto.fn(state, "4")
        self.assertEqual(state.item_produto_id, "")
        WorkshopState.select_produto.fn(state, "3")
        self.assertEqual(state.produto_selecionado["codigo"], "OLEO20W50")

    def test_segmented_control_value_is_normalized(self):
        state = self.make_state()
        WorkshopState.set_item_tipo.fn(state, ["SERVICO"])
        self.assertEqual(state.item_tipo, "SERVICO")
        WorkshopState.set_item_tipo.fn(state, "OUTRO")
        self.assertEqual(state.item_tipo, "SERVICO")

    def test_local_balance_check_does_not_call_xano(self):
        state, client_class, client = self.open_state()
        state.item_produto_id = "3"
        state.item_quantidade = "9"
        WorkshopState.save_item.fn(state)
        client.adicionar_item_ordem_servico.assert_not_called()
        self.assertEqual(state.item_error, "Saldo insuficiente para OLEO20W50: disponível 5.")

    def test_successful_add_applies_detail_totals_and_resets_form(self):
        state, _, client = self.open_state()
        state.item_produto_id = "3"
        state.item_quantidade = "2"
        self.assertEqual(state.item_preview, "R$ 91,80")
        client.adicionar_item_ordem_servico.return_value = detalhe(
            31,
            "EM_ANDAMENTO",
            itens=[item(), item(8, id_produto=5, codigo="FILTROAR")],
            valor_pecas=Decimal("183.6"),
            valor_total=Decimal("183.6"),
        )
        client.list_produtos.return_value = [produto(saldo=3)]
        WorkshopState.save_item.fn(state)
        os_id, payload = client.adicionar_item_ordem_servico.call_args.args
        self.assertEqual((os_id, payload.id_produto, payload.quantidade), (31, 3, 2))
        self.assertEqual(len(state.detalhe_itens), 2)
        self.assertEqual(state.detalhe_totais["total"], "R$ 183,60")
        self.assertEqual(state.catalogo_produtos[0]["saldo"], "3")
        self.assertEqual((state.item_produto_id, state.item_quantidade, state.item_error), ("", "1", ""))
        self.assertFalse(state.is_saving_item)

    def test_rejected_add_keeps_form_and_reloads_real_balance(self):
        state, _, client = self.open_state()
        state.item_produto_id = "3"
        state.item_quantidade = "2"
        message = "Saldo insuficiente para OLEO20W50: disponível 1, solicitado 2."
        client.adicionar_item_ordem_servico.side_effect = XanoValidationError(message, status_code=400)
        client.list_produtos.return_value = [produto(saldo=1)]
        WorkshopState.save_item.fn(state)
        self.assertEqual(state.item_error, message)
        self.assertEqual(state.item_produto_id, "3")
        self.assertEqual(state.catalogo_produtos[0]["saldo"], "1")
        self.assertEqual(client.get_ordem_servico.call_count, 2)

    def test_remove_requires_confirmation_and_reports_stock_return(self):
        state, _, client = self.open_state()
        WorkshopState.ask_remove_item.fn(state, "7")
        self.assertIn("A peça volta ao estoque.", state.remove_message)
        WorkshopState.cancel_remove_item.fn(state)
        client.remover_item_ordem_servico.assert_not_called()
        WorkshopState.ask_remove_item.fn(state, "7")
        client.remover_item_ordem_servico.return_value = detalhe(31, "EM_ANDAMENTO")
        response = WorkshopState.confirm_remove_item.fn(state)
        client.remover_item_ordem_servico.assert_called_once_with(31, 7)
        self.assertEqual(state.detalhe_itens, [])
        self.assertEqual(state.item_to_remove, "")
        self.assertIn("voltou ao estoque", str(response))

    def test_item_events_are_blocked_while_another_operation_runs(self):
        state, _, client = self.open_state()
        state.item_produto_id = "3"
        state.is_transitioning = True
        WorkshopState.save_item.fn(state)
        state.item_to_remove = "7"
        WorkshopState.confirm_remove_item.fn(state)
        client.adicionar_item_ordem_servico.assert_not_called()
        client.remover_item_ordem_servico.assert_not_called()


if __name__ == "__main__":
    unittest.main()
