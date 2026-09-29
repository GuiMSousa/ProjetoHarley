import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from reflex.istate.data import RouterData
from reflex.state import State

from Projeto_HarleyStore.services.catalogo import ModeloMoto, VariacaoCor
from Projeto_HarleyStore.services.cadastros import Cliente
from Projeto_HarleyStore.services.motos import MotoEstoque, MotoEstoqueDetalhe
from Projeto_HarleyStore.services.xano_client import XanoPermissionError, XanoValidationError
from Projeto_HarleyStore.vendas_state import (
    ABA_ESTOQUE,
    VendasFormError,
    VendasState,
    build_cancelamento_payload,
    build_modelo_payload,
    build_moto_payload,
    build_reserva_payload,
    can_cancel_reservation,
    can_manage_catalog,
    can_sell,
    empty_cor,
    filtrar_motos,
    moto_row,
    status_counts,
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


if __name__ == "__main__":
    unittest.main()
