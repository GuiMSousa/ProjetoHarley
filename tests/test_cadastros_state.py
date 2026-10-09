import unittest
from unittest.mock import patch

from reflex.state import State

from decimal import Decimal

from Projeto_HarleyStore.cadastros_state import CadastrosState, produto_resumo
from Projeto_HarleyStore.services.cadastros import (
    MotoCliente,
    MotoClienteCreate,
    MotoClienteUpdate,
    Produto,
    ProdutoCreate,
    ProdutoUpdate,
)
from Projeto_HarleyStore.services.xano_client import XanoAuthenticationError, XanoError

from tests.event_runner import run_event


class CadastrosStateTests(unittest.TestCase):
    def make_state(self, role):
        return type("StateFixture", (), {"employee_role": role})()

    def test_manager_can_write_every_registration(self):
        state = self.make_state("GERENTE")
        for section in {
            "clientes",
            "motos_clientes",
            "produtos",
            "fornecedores",
            "funcionarios",
        }:
            with self.subTest(section=section):
                self.assertTrue(CadastrosState._can_write(state, section))

    def test_vendor_can_write_only_clients_and_customer_bikes(self):
        state = self.make_state("VENDEDOR")
        self.assertTrue(CadastrosState._can_write(state, "clientes"))
        self.assertTrue(CadastrosState._can_write(state, "motos_clientes"))
        self.assertFalse(CadastrosState._can_write(state, "produtos"))
        self.assertFalse(CadastrosState._can_write(state, "fornecedores"))
        self.assertFalse(CadastrosState._can_write(state, "funcionarios"))

    def test_mechanic_is_read_only_for_basic_registrations(self):
        state = self.make_state("MECANICO")
        for section in {
            "clientes",
            "motos_clientes",
            "produtos",
            "fornecedores",
            "funcionarios",
        }:
            with self.subTest(section=section):
                self.assertFalse(CadastrosState._can_write(state, section))

    def make_real_state(self, role="GERENTE", authenticated=True):
        root = State(_reflex_internal_init=True)
        state = root.get_substate(CadastrosState.get_full_name().split("."))
        state.auth_token = "token"
        state.is_authenticated = authenticated
        state.employee_role = role
        return state

    def test_list_load_waits_for_session_and_allowed_role(self):
        cases = [
            ("GERENTE", False, "load_clientes"),
            ("VENDEDOR", True, "load_fornecedores"),
            ("MECANICO", True, "load_funcionarios"),
        ]
        for role, authenticated, handler in cases:
            with self.subTest(role=role, handler=handler):
                state = self.make_real_state(role, authenticated)
                with patch("Projeto_HarleyStore.cadastros_state.XanoClient") as client_class:
                    run_event(getattr(CadastrosState, handler), state)
                client_class.assert_not_called()
                self.assertFalse(state.is_loading_list)

    def test_list_load_error_is_visible_and_clears_flag(self):
        state = self.make_real_state("VENDEDOR")
        with patch("Projeto_HarleyStore.cadastros_state.XanoClient") as client_class:
            client_class.return_value.__enter__.return_value.list_produtos.side_effect = (
                XanoError("Unable to reach the Xano API.")
            )
            run_event(CadastrosState.load_produtos, state)
        self.assertEqual(
            state.list_error, "Não foi possível comunicar com o Xano. Tente novamente."
        )
        self.assertEqual(state.produtos, [])
        self.assertFalse(state.is_loading_list)

    def test_successful_save_is_not_reported_as_failure_when_reload_fails(self):
        state = self.make_real_state("GERENTE")
        state.active_section = "clientes"
        state.editing_id = ""
        state.form_open = True
        state.form_data = {"nome_cliente": "Ana", "cpf_cnpj": "12345678900"}
        with patch("Projeto_HarleyStore.cadastros_state.XanoClient") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.list_clientes.side_effect = XanoError("Unable to reach the Xano API.")
            run_event(CadastrosState.save_form, state)
        client.create_cliente.assert_called_once()
        self.assertEqual(state.form_error, "")
        self.assertFalse(state.form_open)
        self.assertIn("Xano", state.list_error)

    def test_expired_session_on_save_clears_session(self):
        state = self.make_real_state("GERENTE")
        state.active_section = "clientes"
        state.editing_id = ""
        state.form_data = {"nome_cliente": "Ana", "cpf_cnpj": "12345678900"}
        with patch("Projeto_HarleyStore.cadastros_state.XanoClient") as client_class:
            client_class.return_value.__enter__.return_value.create_cliente.side_effect = (
                XanoAuthenticationError("expired")
            )
            run_event(CadastrosState.save_form, state)
        self.assertEqual(state.auth_token, "")
        self.assertFalse(state.is_authenticated)
        self.assertFalse(state.is_saving)

    def test_edit_of_bike_with_unloaded_client_does_not_crash(self):
        state = self.make_real_state("VENDEDOR")
        state.clientes = []
        state.motos_clientes = [
            {"id": "5", "id_cliente": "9", "modelo": "Street", "ativo_value": "true"}
        ]
        run_event(CadastrosState.open_edit, state, "motos_clientes", "5")
        self.assertTrue(state.form_open)
        self.assertEqual(state.form_data["id_cliente"], "9 - ")

    def test_blank_plate_is_absent_on_create_and_unchanged_on_edit(self):
        state = self.make_real_state("VENDEDOR")
        state.active_section = "motos_clientes"
        form = {"id_cliente": "5 - Ana", "modelo": "Street Glide", "placa": "  ", "chassi": "CH1"}
        state.editing_id = ""
        state.form_data = form
        payload, model = state._payload()
        self.assertIs(model, MotoClienteCreate)
        self.assertIsNone(payload.placa)
        state.editing_id = "87"
        payload, model = state._payload()
        self.assertIs(model, MotoClienteUpdate)
        self.assertNotIn("placa", payload.model_dump(exclude_unset=True))
        state.form_data = {**form, "placa": "ABC1D23"}
        self.assertEqual(state._payload()[0].placa, "ABC1D23")

    def test_bike_without_plate_lists_with_an_empty_plate_column(self):
        state = self.make_real_state("VENDEDOR")
        rows = state._rows(
            [MotoCliente(id=87, id_cliente=5, modelo="Street Glide", placa=None, chassi="CH1")],
            "modelo",
            "placa",
            "chassi",
        )
        self.assertEqual((rows[0]["secondary"], rows[0]["placa"]), ("", ""))

    def test_product_edit_payload_never_carries_stock_balance(self):
        state = self.make_real_state("GERENTE")
        state.active_section = "produtos"
        state.editing_id = "4"
        state.form_data = {
            "codigo": "SKU4",
            "nome_produto": "Filtro",
            "categoria": "Motor",
            "preco_venda": "45.50",
            "estoque_qtd": "999",
        }
        payload, model = state._payload()
        self.assertIs(model, ProdutoUpdate)
        self.assertNotIn("estoque_qtd", payload.model_dump(exclude_unset=True))

    def test_product_create_payload_keeps_initial_stock(self):
        state = self.make_real_state("GERENTE")
        state.active_section = "produtos"
        state.editing_id = ""
        state.form_data = {
            "codigo": "SKU4",
            "nome_produto": "Filtro",
            "categoria": "Motor",
            "preco_venda": "45.50",
            "estoque_qtd": "3",
        }
        payload, model = state._payload()
        self.assertIs(model, ProdutoCreate)
        self.assertEqual(payload.estoque_qtd, 3)


    def test_product_rows_show_formatted_price_and_balance(self):
        produto = Produto(
            id=4, codigo="SKU4", nome_produto="Filtro", categoria="Motor",
            estoque_qtd=3, preco_venda=Decimal("45.5"), ativo=False,
        )
        self.assertEqual(produto_resumo(produto), "R$ 45,50 · 3 em estoque")
        state = State(_reflex_internal_init=True).get_substate(CadastrosState.get_full_name().split("."))
        (row,) = state._rows([produto], "codigo", "nome_produto", produto_resumo)
        self.assertEqual(row["tertiary"], "R$ 45,50 · 3 em estoque")
        self.assertEqual(row["preco_venda"], "45.5")  # raw value still feeds the edit form
        self.assertEqual((row["status"], row["ativo"]), ("INATIVO", "Inativo"))


if __name__ == "__main__":
    unittest.main()
