import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from reflex.state import State

from Projeto_HarleyStore.feedback import error_feedback
from Projeto_HarleyStore.entradas_state import (
    EntradaFormError,
    EntradasState,
    add_item_row,
    build_entrada_payload,
    can_register_entrada,
    entrada_row,
    estimate_total,
    format_currency,
    remove_item_row,
    update_item_row,
)
from Projeto_HarleyStore.listing import (
    filter_rows,
    option_id,
    option_label,
    page_count,
    paginate,
)
from Projeto_HarleyStore.services.entradas import EntradaMercadoriaResumo
from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoError,
    XanoNotFoundError,
    XanoPermissionError,
    XanoValidationError,
)


def item(produto="10 - PX100 · Pastilha", quantidade="5", valor="10,00"):
    return {"produto": produto, "quantidade": quantidade, "valor_unitario": valor}


class EntradaFormRulesTests(unittest.TestCase):
    def test_only_manager_registers_receipts(self):
        self.assertTrue(can_register_entrada("GERENTE"))
        self.assertFalse(can_register_entrada("VENDEDOR"))
        self.assertFalse(can_register_entrada("MECANICO"))
        self.assertFalse(can_register_entrada(""))

    def test_items_can_be_added_updated_and_removed_keeping_one(self):
        items = add_item_row([])
        self.assertEqual(len(items), 1)
        items = add_item_row(items)
        items = update_item_row(items, 1, "quantidade", "3")
        self.assertEqual(items[1]["quantidade"], "3")
        self.assertEqual(items[0]["quantidade"], "")
        items = remove_item_row(items, 0)
        self.assertEqual(items, [{"produto": "", "quantidade": "3", "valor_unitario": ""}])
        self.assertEqual(remove_item_row(items, 0), items)
        self.assertEqual(remove_item_row(items, 5), items)

    def test_total_preview_accepts_comma_and_ignores_incomplete_rows(self):
        items = [item(valor="10,00"), item(quantidade="2", valor="25.50"), item(quantidade="", valor="")]
        self.assertEqual(estimate_total(items), Decimal("101.00"))
        self.assertEqual(format_currency(estimate_total(items)), "R$ 101,00")
        self.assertEqual(format_currency(Decimal("1234567.5")), "R$ 1.234.567,50")
        self.assertEqual(format_currency(None), "—")

    def test_build_payload_from_form_values(self):
        payload = build_entrada_payload(
            "3 - Moto Parts",
            " NF-1 ",
            [item(), item("11 - FL200 · Filtro", "2", "25,50")],
        )
        self.assertEqual(payload.id_fornecedor, 3)
        self.assertEqual(payload.numero_documento, "NF-1")
        self.assertEqual([i.id_produto for i in payload.itens], [10, 11])
        self.assertEqual(payload.itens[1].valor_unitario, Decimal("25.50"))

    def test_build_payload_reports_readable_errors(self):
        cases = {
            "Selecione um fornecedor.": ("", "NF", [item()]),
            "Informe o número do documento.": ("3 - A", "  ", [item()]),
            "Adicione ao menos um item.": ("3 - A", "NF", []),
            "Item 1: selecione um produto.": ("3 - A", "NF", [item(produto="")]),
            "Item 1: a quantidade deve ser maior que zero.": ("3 - A", "NF", [item(quantidade="0")]),
            "Item 1: o preço de custo deve ser maior que zero.": ("3 - A", "NF", [item(valor="0")]),
            "Item 1: informe quantidade inteira e preço de custo numérico.": ("3 - A", "NF", [item(valor="abc")]),
            "Um mesmo produto não pode aparecer mais de uma vez na entrada.": ("3 - A", "NF", [item(), item()]),
        }
        for message, args in cases.items():
            with self.subTest(message=message):
                with self.assertRaises(EntradaFormError) as context:
                    build_entrada_payload(*args)
                self.assertEqual(str(context.exception), message)

    def test_error_feedback_is_readable_per_error_type(self):
        self.assertIn("sessão", error_feedback(XanoAuthenticationError("x")))
        self.assertIn("permissão", error_feedback(XanoPermissionError("x")))
        self.assertEqual(error_feedback(XanoValidationError("Fornecedor inativo.")), "Fornecedor inativo.")
        self.assertIn("Xano", error_feedback(XanoError("boom")))
        self.assertIn("não foi encontrado", error_feedback(XanoNotFoundError("x")))

    def test_history_row_is_human_readable(self):
        row = entrada_row(
            EntradaMercadoriaResumo(
                id=7,
                id_fornecedor=3,
                numero_documento=None,
                data_entrada=datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc),
                valor_total=Decimal("834.5"),
                nome_fornecedor="Moto Parts",
                quantidade_itens=2,
            )
        )
        self.assertEqual(row["documento"], "—")
        self.assertEqual(row["responsavel"], "—")
        self.assertEqual(row["total"], "R$ 834,50")
        self.assertEqual(row["itens"], "2")
        self.assertRegex(row["data"], r"^\d{2}/\d{2}/2026 \d{2}:\d{2}$")


class ListingHelpersTests(unittest.TestCase):
    def test_filter_paginate_and_count(self):
        rows = [{"nome": f"Item {n}"} for n in range(10)]
        self.assertEqual(len(filter_rows(rows, "  item 1 ")), 1)
        self.assertEqual(filter_rows(rows, ""), rows)
        self.assertEqual(paginate(rows, 2, 4), rows[4:8])
        self.assertEqual(page_count(10, 4), 3)
        self.assertEqual(page_count(0, 4), 1)

    def test_option_round_trip(self):
        label = option_label(12, "Cliente - com hífen")
        self.assertEqual(label, "12 - Cliente - com hífen")
        self.assertEqual(option_id(label), 12)


class EntradasStateEventTests(unittest.TestCase):
    def make_state(self, role="GERENTE", authenticated=True):
        root = State(_reflex_internal_init=True)
        state = root.get_substate(EntradasState.get_full_name().split("."))
        state.auth_token = "token"
        state.is_authenticated = authenticated
        state.employee_role = role
        state.is_loading_list = False
        state.is_saving = False
        state.is_loading_detail = False
        state.list_error = ""
        state.form_error = ""
        state.form_open = True
        state.entradas = []
        state.current_page = 1
        state.fornecedor = "3 - Moto Parts"
        state.numero_documento = "NF-1"
        state.itens_form = [item()]
        return state

    def test_load_skips_xano_without_session(self):
        state = self.make_state(authenticated=False)
        with patch("Projeto_HarleyStore.entradas_state.XanoClient") as client_class:
            EntradasState.load_entradas.fn(state)
        client_class.assert_not_called()

    def test_save_blocks_non_manager_before_calling_xano(self):
        for role in ("VENDEDOR", "MECANICO"):
            with self.subTest(role=role):
                state = self.make_state(role=role)
                with patch("Projeto_HarleyStore.entradas_state.XanoClient") as client_class:
                    EntradasState.save_entrada.fn(state)
                client_class.assert_not_called()
                self.assertIn("gerente", state.form_error)

    def test_save_validates_locally_without_calling_xano(self):
        state = self.make_state()
        state.itens_form = [item(quantidade="0")]
        with patch("Projeto_HarleyStore.entradas_state.XanoClient") as client_class:
            EntradasState.save_entrada.fn(state)
        client_class.assert_not_called()
        self.assertIn("quantidade", state.form_error)
        self.assertTrue(state.form_open)

    def test_save_is_blocked_while_another_operation_runs(self):
        state = self.make_state()
        state.is_saving = True
        with patch("Projeto_HarleyStore.entradas_state.XanoClient") as client_class:
            EntradasState.save_entrada.fn(state)
        client_class.assert_not_called()

    def test_successful_save_closes_form_reloads_history_and_clears_flag(self):
        state = self.make_state()
        client = MagicMock()
        client.list_entradas.return_value = [
            EntradaMercadoriaResumo(id=1, id_fornecedor=3, numero_documento="NF-1")
        ]
        with patch("Projeto_HarleyStore.entradas_state.XanoClient") as client_class:
            client_class.return_value.__enter__.return_value = client
            EntradasState.save_entrada.fn(state)
        payload = client.registrar_entrada.call_args.args[0]
        self.assertEqual(payload.numero_documento, "NF-1")
        self.assertFalse(state.form_open)
        self.assertFalse(state.is_saving)
        self.assertEqual(state.entradas[0]["documento"], "NF-1")

    def test_business_rejection_keeps_form_open_with_message(self):
        state = self.make_state()
        client = MagicMock()
        client.registrar_entrada.side_effect = XanoValidationError(
            "Este documento já foi registrado para o fornecedor.", status_code=400
        )
        with patch("Projeto_HarleyStore.entradas_state.XanoClient") as client_class:
            client_class.return_value.__enter__.return_value = client
            EntradasState.save_entrada.fn(state)
        self.assertTrue(state.form_open)
        self.assertFalse(state.is_saving)
        self.assertEqual(state.form_error, "Este documento já foi registrado para o fornecedor.")


if __name__ == "__main__":
    unittest.main()
