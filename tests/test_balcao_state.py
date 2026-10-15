"""Change 11: cart rules and events of the counter sale page (/balcao)."""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from reflex.state import State

from Projeto_HarleyStore.balcao_state import (
    CONSUMIDOR_FINAL,
    TODAS_CATEGORIAS,
    BalcaoFormError,
    BalcaoState,
    adicionar_item,
    alterar_quantidade,
    build_venda_payload,
    cliente_nome,
    produtos_visiveis,
    recibo_view,
    remover_item,
    sincronizar_carrinho,
    total_carrinho,
)
from Projeto_HarleyStore.listing import produto_row
from Projeto_HarleyStore.services.balcao import MAX_ITENS_VENDA, VendaBalcaoDetalhe
from Projeto_HarleyStore.services.cadastros import Cliente, Produto
from Projeto_HarleyStore.services.xano_client import XanoError, XanoValidationError

from tests.event_runner import run_event


def produto(produto_id=7, codigo="FLT0001", nome="Filtro de óleo", saldo=5, preco="89.90", categoria="Filtros", ativo=True):
    return Produto(
        id=produto_id,
        codigo=codigo,
        nome_produto=nome,
        categoria=categoria,
        estoque_qtd=saldo,
        preco_venda=Decimal(preco),
        ativo=ativo,
    )


FILTRO = produto_row(produto())
PASTILHA = produto_row(produto(12, "PST0102", "Pastilha de freio", saldo=1, preco="209.90", categoria="Freios"))
SEM_SALDO = produto_row(produto(15, "CAB0001", "Cabo de embreagem", saldo=0, preco="59.90", categoria="Cabos"))


def recibo(**overrides):
    data = {
        "id_transacao": 128,
        "data_transacao": 1791990000000,
        "valor_total": "389.70",
        "id_cliente": 14,
        "nome_cliente": "Ana Souza",
        "id_funcionario": 3,
        "nome_funcionario": "Carlos Vendedor",
        "itens": [
            {"id_produto": 7, "codigo": "FLT0001", "nome_produto": "Filtro de óleo", "quantidade": 2, "valor_unitario": "89.90", "valor_total_item": "179.80"},
            {"id_produto": 12, "codigo": "PST0102", "nome_produto": "Pastilha de freio", "quantidade": 1, "valor_unitario": "209.90", "valor_total_item": "209.90"},
        ],
    }
    data.update(overrides)
    return VendaBalcaoDetalhe(**data)


class CarrinhoRulesTests(unittest.TestCase):
    def test_adding_the_same_product_again_sums_the_quantity(self):
        carrinho = adicionar_item([], FILTRO)
        carrinho = adicionar_item(carrinho, FILTRO)
        self.assertEqual(len(carrinho), 1)
        self.assertEqual((carrinho[0]["quantidade"], carrinho[0]["subtotal"]), ("2", "R$ 179,80"))

    def test_cart_never_exceeds_the_loaded_balance(self):
        carrinho = adicionar_item([], PASTILHA)
        with self.assertRaises(BalcaoFormError) as context:
            adicionar_item(carrinho, PASTILHA)
        self.assertEqual(str(context.exception), "Saldo insuficiente para PST0102: disponível 1.")
        with self.assertRaises(BalcaoFormError):
            adicionar_item([], SEM_SALDO)

    def test_cart_is_limited_to_thirty_products(self):
        carrinho = []
        for numero in range(1, MAX_ITENS_VENDA + 1):
            carrinho = adicionar_item(carrinho, produto_row(produto(numero, f"P{numero}")))
        with self.assertRaises(BalcaoFormError) as context:
            adicionar_item(carrinho, produto_row(produto(99, "P99")))
        self.assertEqual(str(context.exception), "A venda pode ter no máximo 30 itens.")
        # A product already in the cart can still grow.
        self.assertEqual(adicionar_item(carrinho, produto_row(produto(1, "P1")))[0]["quantidade"], "2")

    def test_typed_quantity_keeps_digits_and_only_valid_lines_count(self):
        carrinho = adicionar_item(adicionar_item([], FILTRO), PASTILHA)
        carrinho = alterar_quantidade(carrinho, "7", " 3x")
        self.assertEqual((carrinho[0]["quantidade"], carrinho[0]["subtotal"]), ("3", "R$ 269,70"))
        self.assertEqual(total_carrinho(carrinho), Decimal("479.60"))
        carrinho = alterar_quantidade(carrinho, "7", "")
        self.assertEqual(carrinho[0]["subtotal"], "—")
        self.assertEqual(total_carrinho(carrinho), Decimal("209.90"))
        self.assertEqual(remover_item(carrinho, "7"), carrinho[1:])

    def test_reload_refreshes_prices_and_drops_products_no_longer_sold(self):
        carrinho = adicionar_item(adicionar_item([], FILTRO), PASTILHA)
        novo_preco = produto_row(produto(preco="99.90", saldo=8))
        sincronizado = sincronizar_carrinho(carrinho, [novo_preco])
        self.assertEqual([linha["id"] for linha in sincronizado], ["7"])
        self.assertEqual(
            (sincronizado[0]["preco"], sincronizado[0]["saldo"], sincronizado[0]["subtotal"]),
            ("R$ 99,90", "8", "R$ 99,90"),
        )

    def test_payload_for_the_final_consumer_and_for_a_customer(self):
        carrinho = adicionar_item(adicionar_item(adicionar_item([], FILTRO), FILTRO), PASTILHA)
        anonima = build_venda_payload(carrinho, CONSUMIDOR_FINAL, "chave-1")
        self.assertIsNone(anonima.id_cliente)
        self.assertEqual(anonima.total_esperado, Decimal("389.70"))
        self.assertEqual(
            [(item.id_produto, item.quantidade) for item in anonima.itens], [(7, 2), (12, 1)]
        )
        self.assertEqual(anonima.chave_venda, "chave-1")
        self.assertEqual(build_venda_payload(carrinho, "14 - Ana Souza", "chave-1").id_cliente, 14)

    def test_payload_explains_what_is_wrong(self):
        carrinho = adicionar_item([], FILTRO)
        cases = (
            ([], "Adicione ao menos uma peça ao carrinho."),
            (alterar_quantidade(carrinho, "7", "0"), "Informe a quantidade de FLT0001: um número inteiro maior que zero."),
            (alterar_quantidade(carrinho, "7", "6"), "Saldo insuficiente para FLT0001: disponível 5."),
        )
        for cart, message in cases:
            with self.subTest(message=message), self.assertRaises(BalcaoFormError) as context:
                build_venda_payload(cart, CONSUMIDOR_FINAL, "chave-1")
            self.assertEqual(str(context.exception), message)

    def test_receipt_view_names_the_final_consumer(self):
        resumo, linhas = recibo_view(recibo(id_cliente=None, nome_cliente=None))
        self.assertEqual((resumo["numero"], resumo["cliente"], resumo["total"]), ("128", CONSUMIDOR_FINAL, "R$ 389,70"))
        self.assertEqual(resumo["vendedor"], "Carlos Vendedor")
        self.assertEqual(
            [(linha["produto"], linha["quantidade"], linha["subtotal"]) for linha in linhas],
            [("FLT0001 · Filtro de óleo", "2", "R$ 179,80"), ("PST0102 · Pastilha de freio", "1", "R$ 209,90")],
        )
        self.assertEqual(recibo_view(recibo())[0]["cliente"], "Ana Souza")

    def test_category_filter_and_search_are_local(self):
        catalogo = [FILTRO, PASTILHA, SEM_SALDO]
        self.assertEqual(len(produtos_visiveis(catalogo, TODAS_CATEGORIAS, "")), 3)
        self.assertEqual([row["id"] for row in produtos_visiveis(catalogo, "Freios", "")], ["12"])
        self.assertEqual([row["id"] for row in produtos_visiveis(catalogo, TODAS_CATEGORIAS, "oleo")], ["7"])
        self.assertEqual(produtos_visiveis(catalogo, "Freios", "oleo"), [])

    def test_customer_name_drops_the_option_id(self):
        self.assertEqual(cliente_nome("14 - Ana Souza"), "Ana Souza")
        self.assertEqual(cliente_nome(CONSUMIDOR_FINAL), CONSUMIDOR_FINAL)


class BalcaoStateTests(unittest.TestCase):
    def make_state(self, role="VENDEDOR"):
        root = State(_reflex_internal_init=True)
        state = root.get_substate(BalcaoState.get_full_name().split("."))
        state.auth_token = "token"
        state.is_authenticated = True
        state.employee_role = role
        state.employee_id = 3
        return state

    def patched_client(self):
        patcher = patch("Projeto_HarleyStore.balcao_state.XanoClient")
        client_class = patcher.start()
        self.addCleanup(patcher.stop)
        client = MagicMock()
        client_class.return_value.__enter__.return_value = client
        client.list_produtos.return_value = [
            produto(),
            produto(12, "PST0102", "Pastilha de freio", saldo=1, preco="209.90", categoria="Freios"),
            produto(20, "OLD0001", "Inativo", ativo=False),
        ]
        client.list_clientes.return_value = [
            Cliente(id=14, nome_cliente="Ana Souza", cpf_cnpj="1"),
            Cliente(id=15, nome_cliente="Inativo", cpf_cnpj="2", ativo=False),
        ]
        client.vender_balcao.return_value = recibo()
        return client_class, client

    def loaded_cart(self, client):
        state = self.make_state()
        run_event(BalcaoState.load_balcao, state)
        run_event(BalcaoState.adicionar, state, "7")
        run_event(BalcaoState.adicionar, state, "7")
        run_event(BalcaoState.adicionar, state, "12")
        run_event(BalcaoState.set_cliente, state, "14 - Ana Souza")
        return state

    def test_seller_loads_active_products_and_customers(self):
        self.patched_client()
        state = self.make_state()
        run_event(BalcaoState.load_balcao, state)
        self.assertEqual([row["id"] for row in state.catalogo], ["7", "12"])
        self.assertEqual(state.cliente_options, [CONSUMIDOR_FINAL, "14 - Ana Souza"])
        self.assertEqual(state.categorias, [TODAS_CATEGORIAS, "Filtros", "Freios"])
        self.assertTrue(state.chave_venda)

    def test_mechanic_never_loads_the_counter(self):
        _, client = self.patched_client()
        state = self.make_state(role="MECANICO")
        run_event(BalcaoState.load_balcao, state)
        client.list_produtos.assert_not_called()
        self.assertEqual(state.catalogo, [])

    def test_confirmation_requires_a_valid_cart(self):
        self.patched_client()
        state = self.make_state()
        run_event(BalcaoState.load_balcao, state)
        self.assertIsNotNone(run_event(BalcaoState.abrir_confirmacao, state))
        self.assertEqual(state.form_error, "Adicione ao menos uma peça ao carrinho.")
        self.assertFalse(state.confirm_open)

    def test_sale_renders_the_busy_state_before_calling_xano(self):
        _, client = self.patched_client()
        state = self.loaded_cart(client)
        run_event(BalcaoState.abrir_confirmacao, state)
        steps = BalcaoState.confirmar_venda.fn(state)
        next(steps)  # first state update sent to the browser
        self.assertTrue(state.is_selling and state.is_busy)
        client.vender_balcao.assert_not_called()
        with self.assertRaises(StopIteration):
            next(steps)
        client.vender_balcao.assert_called_once()
        self.assertFalse(state.is_selling)

    def test_successful_sale_shows_the_receipt_and_starts_a_new_cart(self):
        _, client = self.patched_client()
        state = self.loaded_cart(client)
        chave = state.chave_venda
        run_event(BalcaoState.abrir_confirmacao, state)
        run_event(BalcaoState.confirmar_venda, state)
        (payload,), _ = client.vender_balcao.call_args
        self.assertEqual((payload.chave_venda, payload.id_cliente, payload.total_esperado), (chave, 14, Decimal("389.70")))
        self.assertEqual(state.recibo["numero"], "128")
        self.assertTrue(state.recibo_open)
        self.assertEqual((state.carrinho, state.cliente, state.confirm_open), ([], CONSUMIDOR_FINAL, False))
        self.assertNotEqual(state.chave_venda, chave)
        self.assertEqual(client.list_produtos.call_count, 2)  # balances reloaded after the sale
        run_event(BalcaoState.fechar_recibo, state)
        self.assertFalse(state.recibo_open)

    def test_second_click_never_sells_twice(self):
        _, client = self.patched_client()
        state = self.loaded_cart(client)
        run_event(BalcaoState.abrir_confirmacao, state)
        run_event(BalcaoState.confirmar_venda, state)
        run_event(BalcaoState.confirmar_venda, state)
        client.vender_balcao.assert_called_once()

    def test_rejection_keeps_the_cart_and_key_and_reloads_balances(self):
        _, client = self.patched_client()
        state = self.loaded_cart(client)
        chave = state.chave_venda
        client.vender_balcao.side_effect = XanoValidationError("Saldo insuficiente para PST0102: disponível 0, solicitado 1.")
        run_event(BalcaoState.abrir_confirmacao, state)
        run_event(BalcaoState.confirmar_venda, state)
        self.assertEqual(state.form_error, "Saldo insuficiente para PST0102: disponível 0, solicitado 1.")
        self.assertEqual(state.chave_venda, chave)
        self.assertEqual([linha["id"] for linha in state.carrinho], ["7", "12"])
        self.assertFalse(state.confirm_open)
        self.assertEqual(client.list_produtos.call_count, 2)

    def test_lost_response_keeps_the_key_so_a_retry_is_idempotent(self):
        _, client = self.patched_client()
        state = self.loaded_cart(client)
        chave = state.chave_venda
        client.vender_balcao.side_effect = XanoError("timeout")
        run_event(BalcaoState.abrir_confirmacao, state)
        run_event(BalcaoState.confirmar_venda, state)
        self.assertEqual(state.chave_venda, chave)
        self.assertEqual(len(state.carrinho), 2)
        client.vender_balcao.side_effect = None
        run_event(BalcaoState.abrir_confirmacao, state)
        run_event(BalcaoState.confirmar_venda, state)
        self.assertEqual(client.vender_balcao.call_args_list[1].args[0].chave_venda, chave)

    def test_sale_is_blocked_while_the_page_loads(self):
        _, client = self.patched_client()
        state = self.loaded_cart(client)
        run_event(BalcaoState.abrir_confirmacao, state)
        state.is_loading_list = True
        run_event(BalcaoState.confirmar_venda, state)
        client.vender_balcao.assert_not_called()

    def test_clearing_the_cart_renews_the_key(self):
        _, client = self.patched_client()
        state = self.loaded_cart(client)
        chave = state.chave_venda
        run_event(BalcaoState.limpar_carrinho, state)
        self.assertEqual((state.carrinho, state.cliente), ([], CONSUMIDOR_FINAL))
        self.assertNotEqual(state.chave_venda, chave)


if __name__ == "__main__":
    unittest.main()
