import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from reflex.istate.data import RouterData
from reflex.state import State

from Projeto_HarleyStore.services.catalogo import ModeloMoto, VariacaoCor
from Projeto_HarleyStore.services.cadastros import Cliente
from Projeto_HarleyStore.services.motos import MotoEstoque, MotoEstoqueDetalhe
from Projeto_HarleyStore.services.motos import VendaMotoResultado
from Projeto_HarleyStore.services.xano_client import (
    XanoNotFoundError,
    XanoPermissionError,
    XanoValidationError,
)
from Projeto_HarleyStore.vendas_state import (
    ABA_ESTOQUE,
    VendasFormError,
    VendasState,
    build_cancelamento_payload,
    build_modelo_payload,
    build_moto_payload,
    build_reserva_payload,
    build_venda_payload,
    can_cancel_reservation,
    can_manage_catalog,
    can_sell,
    can_sell_unit,
    empty_cor,
    filtrar_motos,
    moto_row,
    status_counts,
    valor_inicial_venda,
    venda_ainda_possivel,
)


AGORA = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
COR = VariacaoCor(nome="Vivid Black", hex="#0B0B0B", imagem_url="https://img.test/a.jpg")


def moto(moto_id=9, status="DISPONIVEL", **extra):
    data = {
        "id": moto_id,
        "status": status,
        "id_modelo": 3,
        "nome_modelo": "Street Glide",
        "familia": "TOURING",
        "variacoes_cor": [COR],
        "chassi": "1HD1KTP19RB600001",
        "cor": "Vivid Black",
        "ano_modelo": 2025,
        "preco_venda": Decimal("189900"),
    }
    data.update(extra)
    return MotoEstoque(**data)


def reservada(vendedor=2, ate=AGORA + timedelta(days=3), **extra):
    return moto(
        status="RESERVADA",
        id_vendedor_reserva=vendedor,
        reservada_ate=ate,
        clientes_id=5,
        nome_cliente="Ana Souza",
        **extra,
    )


def modelo(modelo_id=3, ativo=True):
    return ModeloMoto(
        id=modelo_id,
        nome_modelo="Street Glide",
        familia="TOURING",
        preco_base=Decimal("189900"),
        imagem_principal="https://img.test/sg.jpg",
        variacoes_cor=[COR],
        ativo=ativo,
    )


class VendasRulesTests(unittest.TestCase):
    def test_roles(self):
        self.assertTrue(can_sell("VENDEDOR") and can_sell("GERENTE"))
        self.assertFalse(can_sell("MECANICO"))
        self.assertTrue(can_manage_catalog("GERENTE"))
        self.assertFalse(can_manage_catalog("VENDEDOR"))

    def test_cancellation_rule_mirrors_xano(self):
        self.assertTrue(can_cancel_reservation(reservada(vendedor=2), "VENDEDOR", 2, AGORA))
        self.assertFalse(can_cancel_reservation(reservada(vendedor=2), "VENDEDOR", 7, AGORA))
        self.assertTrue(can_cancel_reservation(reservada(vendedor=2), "GERENTE", 7, AGORA))
        vencida = reservada(vendedor=2, ate=AGORA - timedelta(minutes=1))
        self.assertTrue(can_cancel_reservation(vencida, "VENDEDOR", 7, AGORA))
        self.assertFalse(can_cancel_reservation(vencida, "MECANICO", 7, AGORA))
        self.assertFalse(can_cancel_reservation(moto(), "GERENTE", 7, AGORA))

    def test_rows(self):
        row = moto_row(moto(), "VENDEDOR", 2, AGORA)
        self.assertEqual(
            (row["modelo"], row["familia"], row["cor_hex"], row["chassi_curto"], row["preco"]),
            ("Street Glide", "Touring", "#0B0B0B", "…600001", "R$ 189.900,00"),
        )
        self.assertEqual((row["pode_reservar"], row["pode_cancelar"], row["validade"]), ("true", "false", "—"))
        legado = moto_row(MotoEstoque(id=1, modelo="Iron"), "GERENTE", 1, AGORA)
        self.assertEqual((legado["modelo"], legado["pode_reservar"], legado["chassi_curto"]), ("Iron", "false", "—"))
        sem_nome = moto_row(MotoEstoque(id=2), "GERENTE", 1, AGORA)
        self.assertEqual(sem_nome["modelo"], "Sem modelo")
        vencida = moto_row(reservada(ate=AGORA - timedelta(days=1)), "VENDEDOR", 7, AGORA)
        self.assertEqual((vencida["vencida"], vencida["pode_cancelar"], vencida["cliente"]), ("true", "true", "Ana Souza"))

    def test_filters_and_counts(self):
        rows = [
            moto_row(moto(1), "GERENTE", 1, AGORA),
            moto_row(reservada(), "GERENTE", 1, AGORA),
            moto_row(moto(3, id_modelo=4, nome_modelo="Fat Boy"), "GERENTE", 1, AGORA),
        ]
        self.assertEqual([r["id"] for r in filtrar_motos(rows, "DISPONIVEL", "", "")], ["1", "3"])
        self.assertEqual([r["id"] for r in filtrar_motos(rows, "DISPONIVEL", "4", "")], ["3"])
        self.assertEqual([r["id"] for r in filtrar_motos(rows, "RESERVADA", "", "ana")], ["9"])
        self.assertEqual(len(filtrar_motos(rows, ABA_ESTOQUE, "", "")), 3)
        self.assertEqual(status_counts(rows), {"DISPONIVEL": 2, "RESERVADA": 1, "VENDIDA": 0})

    def test_payloads(self):
        reserva = build_reserva_payload("5 - Ana Souza", "10", "  sinal  ")
        self.assertEqual((reserva.id_cliente, reserva.dias_validade, reserva.observacao), (5, 10, "sinal"))
        for args, message in (
            (("", "7", ""), "Selecione o cliente."),
            (("5 - Ana", "x", ""), "A validade deve ser de 1 a 30 dias."),
            (("5 - Ana", "31", ""), "A validade deve ser de 1 a 30 dias."),
        ):
            with self.subTest(args=args), self.assertRaises(VendasFormError) as context:
                build_reserva_payload(*args)
            self.assertEqual(str(context.exception), message)
        with self.assertRaises(VendasFormError):
            build_cancelamento_payload("")

        form = {
            "nome_modelo": "Street Glide",
            "familia": "Touring",
            "descricao": "",
            "preco_base": "189.900,00".replace(".", "").replace(",", "."),
            "imagem_principal": "https://img.test/sg.jpg",
            "destaque": "true",
        }
        cores = [COR.model_dump(), empty_cor()]
        criado = build_modelo_payload(form, cores, editing=False)
        self.assertEqual((criado.familia, criado.destaque, len(criado.variacoes_cor)), ("TOURING", True, 1))
        with self.assertRaises(VendasFormError) as context:
            build_modelo_payload({**form, "imagem_principal": "http://x"}, cores, editing=False)
        self.assertIn("URL https", str(context.exception))
        with self.assertRaises(VendasFormError):
            build_modelo_payload({**form, "familia": ""}, cores, editing=False)

        moto_form = {"modelo": "3 - Street Glide", "chassi": "1hd1ktp19rb600009", "cor": "Vivid Black", "ano_modelo": "2025", "preco_venda": "189900"}
        nova = build_moto_payload(moto_form, editing=False)
        self.assertEqual((nova.id_modelo, nova.chassi), (3, "1HD1KTP19RB600009"))
        with self.assertRaises(VendasFormError) as context:
            build_moto_payload({**moto_form, "chassi": "123"}, editing=False)
        self.assertIn("17 caracteres", str(context.exception))
        with self.assertRaises(VendasFormError):
            build_moto_payload({**moto_form, "modelo": ""}, editing=False)
        self.assertNotIn("id_modelo", build_moto_payload(moto_form, editing=True).model_dump(exclude_unset=True))

    def test_sale_rule_mirrors_xano(self):
        self.assertTrue(can_sell_unit(moto(), "VENDEDOR"))
        self.assertTrue(can_sell_unit(reservada(), "GERENTE"))
        self.assertFalse(can_sell_unit(moto(), "MECANICO"))
        self.assertFalse(can_sell_unit(moto(status="VENDIDA"), "GERENTE"))
        self.assertFalse(can_sell_unit(moto(chassi=None), "GERENTE"))
        row = moto_row(reservada(), "VENDEDOR", 7, AGORA)
        self.assertEqual((row["pode_vender"], row["id_cliente"]), ("true", "5"))
        self.assertEqual(moto_row(moto(status="VENDIDA"), "VENDEDOR", 7, AGORA)["pode_vender"], "false")

    def test_sale_still_possible_after_a_refresh(self):
        disponivel = moto_row(moto(), "VENDEDOR", 2, AGORA)
        da_reserva = moto_row(reservada(), "VENDEDOR", 2, AGORA)
        vendida = moto_row(moto(status="VENDIDA", clientes_id=6), "VENDEDOR", 2, AGORA)
        self.assertTrue(venda_ainda_possivel(disponivel, "6 - Bruno"))
        self.assertTrue(venda_ainda_possivel(da_reserva, "5 - Ana Souza"))
        self.assertFalse(venda_ainda_possivel(da_reserva, "6 - Bruno"))
        self.assertFalse(venda_ainda_possivel(vendida, "6 - Bruno"))
        self.assertFalse(venda_ainda_possivel(None, "6 - Bruno"))

    def test_sale_payload(self):
        self.assertEqual(valor_inicial_venda("189900"), "189900,00")
        self.assertEqual(valor_inicial_venda(""), "")
        payload = build_venda_payload("9", "5 - Ana Souza", "185000,50", " abc-1d23 ", "  ")
        self.assertEqual(
            (payload.id_moto, payload.id_cliente, payload.valor_venda, payload.placa, payload.observacao),
            (9, 5, Decimal("185000.50"), "ABC1D23", None),
        )
        self.assertIsNone(build_venda_payload("9", "5 - Ana", "185000", "", "").placa)
        valor = "Informe o valor da venda: maior que zero, com até duas casas decimais."
        for args, message in (
            (("9", "", "185000", "", ""), "Selecione o cliente."),
            (("9", "5 - Ana", "", "", ""), valor),
            (("9", "5 - Ana", "abc", "", ""), valor),
            (("9", "5 - Ana", "0", "", ""), valor),
            (("9", "5 - Ana", "-10", "", ""), valor),
            (("9", "5 - Ana", "10,999", "", ""), valor),
            (("9", "5 - Ana", "185000", "XYZ", ""), "Placa inválida: use ABC1234 ou ABC1D23, ou deixe em branco para moto 0 km."),
            (("9", "5 - Ana", "185000", "", "x" * 501), "A observação deve ter até 500 caracteres."),
        ):
            with self.subTest(args=args), self.assertRaises(VendasFormError) as context:
                build_venda_payload(*args)
            self.assertEqual(str(context.exception), message)


class VendasStateTests(unittest.TestCase):
    def make_state(self, role="VENDEDOR", employee_id=2, modelo_param=""):
        root = State(_reflex_internal_init=True)
        state = root.get_substate(VendasState.get_full_name().split("."))
        query = {"modelo": modelo_param} if modelo_param else {}
        path = f"/vendas?modelo={modelo_param}" if modelo_param else "/vendas"
        root.router = RouterData.from_router_data({"pathname": "/vendas", "query": query, "asPath": path, "headers": {}})
        state.auth_token = "token"
        state.is_authenticated = True
        state.employee_role = role
        state.employee_id = employee_id
        return state

    def patched_client(self):
        patcher = patch("Projeto_HarleyStore.vendas_state.XanoClient")
        client_class = patcher.start()
        self.addCleanup(patcher.stop)
        client = MagicMock()
        client_class.return_value.__enter__.return_value = client
        client.list_motos_estoque.return_value = [moto(1), reservada()]
        client.list_modelos_moto.return_value = [modelo()]
        return client_class, client

    def test_seller_loads_units_filtered_by_the_model_query_parameter(self):
        _, client = self.patched_client()
        state = self.make_state(modelo_param="3")
        VendasState.load_vendas.fn(state)
        self.assertEqual(state.filtro_modelo, "3")
        self.assertEqual(state.filtro_modelo_nome, "Street Glide")
        self.assertEqual([row["id"] for row in state.visible_rows], ["1"])
        self.assertEqual(state.counts, {"DISPONIVEL": 1, "RESERVADA": 1, "VENDIDA": 0})
        client.list_modelos_moto.assert_not_called()
        VendasState.set_aba.fn(state, ABA_ESTOQUE)
        self.assertEqual(state.aba, "DISPONIVEL")

    def test_manager_also_loads_the_catalog_models(self):
        _, client = self.patched_client()
        state = self.make_state(role="GERENTE")
        VendasState.load_vendas.fn(state)
        self.assertEqual([row["nome"] for row in state.modelos], ["Street Glide"])
        self.assertEqual(state.modelo_options, ["3 - Street Glide"])
        VendasState.set_aba.fn(state, ABA_ESTOQUE)
        self.assertEqual(state.aba, ABA_ESTOQUE)

    def test_mechanic_does_not_load_sales(self):
        client_class, _ = self.patched_client()
        state = self.make_state(role="MECANICO")
        VendasState.load_vendas.fn(state)
        client_class.assert_not_called()

    @patch("Projeto_HarleyStore.vendas_state.catalogo_cache")
    def test_successful_reservation_refreshes_list_and_showroom_cache(self, cache):
        _, client = self.patched_client()
        client.list_clientes.return_value = [
            Cliente(id=5, nome_cliente="Ana Souza", cpf_cnpj="1"),
            Cliente(id=6, nome_cliente="Inativo", cpf_cnpj="2", ativo=False),
        ]
        client.reservar_moto.return_value = MotoEstoqueDetalhe(**reservada().model_dump())
        state = self.make_state()
        VendasState.open_reserva.fn(state, "1")
        self.assertEqual(state.cliente_options, ["5 - Ana Souza"])
        VendasState.set_reserva_cliente.fn(state, "5 - Ana Souza")
        VendasState.confirm_reserva.fn(state)
        moto_id, payload = client.reservar_moto.call_args.args
        self.assertEqual((moto_id, payload.id_cliente, payload.dias_validade), (1, 5, 7))
        cache.invalidate.assert_called_once()
        self.assertEqual(state.reserva_moto_id, "")
        self.assertFalse(state.is_reserving)

    def test_reservation_conflict_keeps_the_modal_with_the_message(self):
        _, client = self.patched_client()
        client.list_clientes.return_value = [Cliente(id=5, nome_cliente="Ana", cpf_cnpj="1")]
        client.reservar_moto.side_effect = XanoValidationError(
            "Esta moto não está disponível para reserva.", status_code=400
        )
        state = self.make_state()
        VendasState.open_reserva.fn(state, "1")
        VendasState.set_reserva_cliente.fn(state, "5 - Ana")
        VendasState.confirm_reserva.fn(state)
        self.assertEqual(state.reserva_moto_id, "1")
        self.assertEqual(state.reserva_error, "Esta moto não está disponível para reserva.")
        self.assertEqual(client.list_motos_estoque.call_count, 1)

    def test_forbidden_cancellation_shows_the_reason(self):
        _, client = self.patched_client()
        client.cancelar_reserva_moto.side_effect = XanoPermissionError("x", status_code=403)
        state = self.make_state()
        VendasState.open_cancelamento.fn(state, "9")
        VendasState.confirm_cancelamento.fn(state)
        self.assertEqual(state.cancel_error, "Informe o motivo do cancelamento (até 500 caracteres).")
        client.cancelar_reserva_moto.assert_not_called()
        VendasState.set_cancel_motivo.fn(state, "Cliente desistiu")
        VendasState.confirm_cancelamento.fn(state)
        self.assertIn("permissão", state.cancel_error)
        self.assertTrue(state.is_authenticated)

    @patch("Projeto_HarleyStore.vendas_state.catalogo_cache")
    def test_manager_creates_models_with_colors_and_units(self, cache):
        _, client = self.patched_client()
        state = self.make_state(role="GERENTE")
        VendasState.load_vendas.fn(state)
        VendasState.open_modelo_create.fn(state)
        for field, value in (
            ("nome_modelo", "Fat Boy"),
            ("familia", "Cruiser"),
            ("preco_base", "139900"),
            ("imagem_principal", "https://img.test/fb.jpg"),
        ):
            VendasState.set_modelo_field.fn(state, field, value)
        VendasState.set_cor_field.fn(state, 0, "nome", "Preto")
        VendasState.set_cor_field.fn(state, 0, "hex", "#1A1A1A")
        VendasState.set_cor_field.fn(state, 0, "imagem_url", "https://img.test/fb-preto.jpg")
        VendasState.add_cor.fn(state)
        VendasState.remove_cor.fn(state, 1)
        VendasState.save_modelo.fn(state)
        (payload,) = client.criar_modelo_moto.call_args.args
        self.assertEqual((payload.familia, [cor.nome for cor in payload.variacoes_cor]), ("CRUISER", ["Preto"]))
        self.assertFalse(state.modelo_form_open)

        VendasState.open_moto_create.fn(state)
        VendasState.set_moto_field.fn(state, "modelo", "3 - Street Glide")
        self.assertEqual(state.cor_options, ["Vivid Black"])
        for field, value in (("chassi", "1HD1KTP19RB600009"), ("cor", "Vivid Black"), ("ano_modelo", "2025"), ("preco_venda", "189900")):
            VendasState.set_moto_field.fn(state, field, value)
        VendasState.save_moto.fn(state)
        (nova,) = client.cadastrar_moto_estoque.call_args.args
        self.assertEqual((nova.id_modelo, nova.cor), (3, "Vivid Black"))
        self.assertEqual(cache.invalidate.call_count, 2)

    def test_seller_cannot_open_management_forms(self):
        self.patched_client()
        state = self.make_state()
        VendasState.open_modelo_create.fn(state)
        VendasState.open_moto_create.fn(state)
        self.assertFalse(state.modelo_form_open or state.moto_form_open)

    def test_operations_are_blocked_while_another_runs(self):
        _, client = self.patched_client()
        state = self.make_state()
        state.reserva_moto_id = "1"
        state.reserva_cliente = "5 - Ana"
        state.is_cancelling = True
        VendasState.confirm_reserva.fn(state)
        client.reservar_moto.assert_not_called()

    def open_sale(self, client, moto_id="1", role="VENDEDOR"):
        client.list_clientes.return_value = [
            Cliente(id=5, nome_cliente="Ana Souza", cpf_cnpj="1"),
            Cliente(id=6, nome_cliente="Bruno", cpf_cnpj="2"),
            Cliente(id=7, nome_cliente="Inativo", cpf_cnpj="3", ativo=False),
        ]
        client.vender_moto.return_value = VendaMotoResultado(id_transacao=41, id_moto_cliente=87, status="SUCESSO")
        state = self.make_state(role=role)
        VendasState.load_vendas.fn(state)
        VendasState.open_venda.fn(state, moto_id)
        return state

    @patch("Projeto_HarleyStore.vendas_state.catalogo_cache")
    def test_sale_of_an_available_unit_refreshes_list_and_showroom(self, cache):
        _, client = self.patched_client()
        state = self.open_sale(client)
        self.assertEqual(state.cliente_options, ["5 - Ana Souza", "6 - Bruno"])
        self.assertEqual((state.venda_valor, state.venda_cliente_fixo), ("189900,00", False))
        self.assertEqual(state.venda_resumo["modelo"], "Street Glide")
        VendasState.set_venda_cliente.fn(state, "6 - Bruno")
        VendasState.set_venda_valor.fn(state, "185000")
        VendasState.set_venda_placa.fn(state, "")
        VendasState.confirm_venda.fn(state)
        (payload,) = client.vender_moto.call_args.args
        self.assertEqual(
            (payload.id_moto, payload.id_cliente, payload.valor_venda, payload.placa),
            (1, 6, Decimal("185000"), None),
        )
        cache.invalidate.assert_called_once()
        self.assertEqual(client.list_motos_estoque.call_count, 2)
        self.assertEqual((state.venda_moto_id, state.venda_error, state.is_selling), ("", "", False))

    def test_reserved_unit_is_sold_only_to_the_reservation_customer(self):
        _, client = self.patched_client()
        state = self.open_sale(client, moto_id="9")
        client.list_clientes.assert_not_called()
        self.assertEqual((state.venda_cliente, state.venda_cliente_fixo), ("5 - Ana Souza", True))
        VendasState.set_venda_cliente.fn(state, "6 - Bruno")
        self.assertEqual(state.venda_cliente, "5 - Ana Souza")
        VendasState.confirm_venda.fn(state)
        self.assertEqual(client.vender_moto.call_args.args[0].id_cliente, 5)

    def test_invalid_form_never_reaches_xano(self):
        _, client = self.patched_client()
        state = self.open_sale(client)
        VendasState.confirm_venda.fn(state)
        self.assertEqual(state.venda_error, "Selecione o cliente.")
        VendasState.set_venda_cliente.fn(state, "6 - Bruno")
        VendasState.set_venda_valor.fn(state, "0")
        VendasState.confirm_venda.fn(state)
        self.assertIn("maior que zero", state.venda_error)
        client.vender_moto.assert_not_called()

    @patch("Projeto_HarleyStore.vendas_state.catalogo_cache")
    def test_unit_sold_by_another_employee_closes_the_modal_and_shows_the_new_status(self, cache):
        _, client = self.patched_client()
        vendida = moto(1, status="VENDIDA", clientes_id=5, nome_cliente="Ana Souza")
        client.list_motos_estoque.side_effect = [[moto(1), reservada()], [vendida, reservada()]]
        state = self.open_sale(client)
        VendasState.set_venda_cliente.fn(state, "6 - Bruno")
        client.vender_moto.side_effect = XanoValidationError("Esta moto já foi vendida.", status_code=400)
        VendasState.confirm_venda.fn(state)
        self.assertEqual(state.venda_moto_id, "")
        self.assertEqual(state.motos[0]["status"], "VENDIDA")
        self.assertEqual(state.counts["VENDIDA"], 1)
        cache.invalidate.assert_not_called()
        self.assertFalse(state.is_selling)

    def test_rejection_of_a_still_available_unit_keeps_the_modal(self):
        _, client = self.patched_client()
        state = self.open_sale(client)
        VendasState.set_venda_cliente.fn(state, "6 - Bruno")
        VendasState.set_venda_placa.fn(state, "ABC1D23")
        client.vender_moto.side_effect = XanoValidationError(
            "Placa já cadastrada em uma moto de cliente.", status_code=400
        )
        VendasState.confirm_venda.fn(state)
        self.assertEqual(state.venda_moto_id, "1")
        self.assertEqual(state.venda_error, "Placa já cadastrada em uma moto de cliente.")
        self.assertEqual(client.list_motos_estoque.call_count, 2)

    def test_removed_unit_closes_the_modal(self):
        _, client = self.patched_client()
        client.list_motos_estoque.side_effect = [[moto(1), reservada()], [reservada()]]
        state = self.open_sale(client)
        VendasState.set_venda_cliente.fn(state, "6 - Bruno")
        client.vender_moto.side_effect = XanoNotFoundError("x", status_code=404)
        VendasState.confirm_venda.fn(state)
        self.assertEqual(state.venda_moto_id, "")

    def test_forbidden_sale_shows_the_reason(self):
        _, client = self.patched_client()
        state = self.open_sale(client)
        VendasState.set_venda_cliente.fn(state, "6 - Bruno")
        client.vender_moto.side_effect = XanoPermissionError("x", status_code=403)
        VendasState.confirm_venda.fn(state)
        self.assertIn("permissão", state.venda_error)
        self.assertEqual(state.venda_moto_id, "1")
        self.assertTrue(state.is_authenticated)

    def test_mechanic_and_unsellable_units_cannot_open_the_sale(self):
        _, client = self.patched_client()
        client.list_motos_estoque.return_value = [moto(1, status="VENDIDA")]
        state = self.make_state()
        VendasState.load_vendas.fn(state)
        VendasState.open_venda.fn(state, "1")
        self.assertEqual(state.venda_moto_id, "")
        mecanico = self.make_state(role="MECANICO")
        VendasState.open_venda.fn(mecanico, "1")
        self.assertEqual(mecanico.venda_moto_id, "")
        client.list_clientes.assert_not_called()

    def test_sale_is_blocked_while_another_operation_runs(self):
        _, client = self.patched_client()
        state = self.open_sale(client)
        VendasState.set_venda_cliente.fn(state, "6 - Bruno")
        state.is_reserving = True
        VendasState.confirm_venda.fn(state)
        client.vender_moto.assert_not_called()


if __name__ == "__main__":
    unittest.main()
