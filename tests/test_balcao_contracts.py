"""Change 11: XanoScript contracts of the counter sale (venda de balcão de peças)."""

import re
import unittest
from pathlib import Path


XANO = Path(__file__).parents[1] / "xano"
ENDPOINT = "api/harley/balcao/vendas_POST.xs"


def read(relative_path: str) -> str:
    return (XANO / relative_path).read_text(encoding="utf-8")


def catch_start(content: str) -> int:
    """Start of the standalone ``catch {`` block (``try_catch {`` also contains the text)."""
    return re.search(r"^\s*catch \{", content, re.MULTILINE).start()


class ItensTransacaoSchemaTests(unittest.TestCase):
    def setUp(self):
        self.content = read("table/itens_transacao.xs")

    def test_items_belong_to_a_transaction_and_a_product(self):
        self.assertIn("table itens_transacao {", self.content)
        self.assertRegex(self.content, r'int id_transacao \{\s*table = "transacoes"\s*\}')
        self.assertRegex(self.content, r'int id_produto \{\s*table = "produtos"\s*\}')
        for field in (
            "int quantidade filters=min:1",
            "decimal valor_unitario filters=min:0.01",
            "decimal valor_total_item filters=min:0.01",
            "text chave_venda filters=trim",
        ):
            with self.subTest(field=field):
                self.assertIn(field, self.content)

    def test_one_product_per_sale_and_one_sale_per_key(self):
        self.assertRegex(
            self.content,
            r'type : "btree\|unique"\s*field: \[\{name: "chave_venda"\}, \{name: "id_produto"\}\]',
        )
        self.assertIn('{type: "btree", field: [{name: "id_transacao"}]}', self.content)

    def test_items_have_no_generic_routes(self):
        users = sorted(
            path.relative_to(XANO).as_posix()
            for path in (XANO / "api").rglob("*.xs")
            if "itens_transacao" in path.read_text(encoding="utf-8")
        )
        self.assertEqual(users, [ENDPOINT])
        self.assertFalse((XANO / "api" / "harley" / "itens_transacao").exists())


class LivroEstoqueTests(unittest.TestCase):
    def test_ledger_records_the_counter_sale_exit(self):
        table = read("table/movimentacoes_estoque.xs")
        self.assertIn('values = ["ENTRADA", "SAIDA_OS", "ESTORNO_OS", "SAIDA_VENDA"]', table)
        self.assertRegex(table, r'int\? id_transacao\? \{\s*table = "transacoes"\s*\}')
        self.assertIn('{type: "btree", field: [{name: "id_transacao"}]}', table)

    def test_stock_function_subtracts_both_exits_and_records_the_sale(self):
        function = read("function/estoque/movimentar_estoque.xs")
        self.assertIn('values = ["ENTRADA", "SAIDA_OS", "ESTORNO_OS", "SAIDA_VENDA"]', function)
        self.assertIn("int? id_transacao?", function)
        self.assertIn('if ($input.tipo == "SAIDA_OS" || $input.tipo == "SAIDA_VENDA")', function)
        self.assertIn("id_transacao   : $input.id_transacao", function)
        # Returning parts to a product deactivated after the inclusion stays allowed.
        self.assertIn(
            '($input.tipo != "SAIDA_OS" && $input.tipo != "SAIDA_VENDA") || $produto.ativo != false',
            function,
        )


class VendaBalcaoEndpointTests(unittest.TestCase):
    def setUp(self):
        self.content = read(ENDPOINT)
        self.input = self.content[self.content.index("input {") : self.content.index("stack {")]
        self.prechecks = self.content[: self.content.index("try_catch {")]
        self.transaction = self.content[self.content.index("db.transaction {") : catch_start(self.content)]
        self.catch = self.content[catch_start(self.content) :]

    def test_route_and_roles(self):
        self.assertIn('query "balcao/vendas" verb=POST', self.content)
        self.assertIn('api_group = "HARLEY"', self.content)
        self.assertIn('auth = "user"', self.content)
        # VENDEDOR in enforce_role admits GERENTE and VENDEDOR, never MECANICO.
        self.assertIn('required_role: "VENDEDOR"', self.content)

    def test_payload_has_no_price_author_or_item_total(self):
        for fragment in (
            "text chave_venda filters=trim|max:64",
            "int? id_cliente? filters=min:1",
            "decimal total_esperado filters=min:0.01",
            "int id_produto filters=min:1",
            "int quantidade filters=min:1",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.input)
        for forbidden in ("valor_unitario", "preco", "valor_total_item", "id_funcionario", "tipo_transacao"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.input)
        self.assertNotIn("$input.id_funcionario", self.content)
        self.assertIn("id_funcionario: $auth_user.id_funcionario", self.transaction)

    def test_repeated_key_returns_the_registered_sale_without_writing(self):
        replay = self.prechecks.index("where = $db.itens_transacao.chave_venda == $input.chave_venda")
        self.assertLess(replay, self.prechecks.index('if ($id_transacao == null)'))
        # Every write sits inside the branch taken only for a new key.
        self.assertLess(self.content.index('if ($id_transacao == null)'), self.content.index("db.transaction {"))
        self.assertIn('function.run "Balcao/detalhe_venda"', self.catch)
        self.assertIn("response = $recibo", self.content)

    def test_specific_validations_run_before_the_transaction(self):
        for message in (
            "Informe ao menos um item.",
            "A venda pode ter no máximo 30 itens.",
            "Um mesmo produto não pode aparecer mais de uma vez na venda.",
            "Cliente inativo ou inexistente.",
            "Produto inativo ou inexistente: ",
            '"Saldo insuficiente para "',
            "Os preços mudaram desde que o carrinho foi montado: o total agora é R$ ",
        ):
            with self.subTest(message=message):
                self.assertIn(message, self.prechecks)
        self.assertIn("(($input.itens|count) <= 30)", self.prechecks)
        self.assertIn("($produto_previo.estoque_qtd ?? 0) >= $item_pedido.quantidade", self.prechecks)
        self.assertIn("($total_previo|round:2) == ($input.total_esperado|round:2)", self.prechecks)

    def test_transaction_writes_header_items_and_stock_exits_in_product_order(self):
        ordered = self.transaction.index("where = $db.produtos.id in $ids_produto")
        self.assertIn('sort = {id: "asc"}', self.transaction[ordered : ordered + 120])
        # Prices are read again inside the transaction and the total is checked again.
        self.assertIn("valor_unitario  : $produto_atual.preco_venda", self.transaction)
        recheck = self.transaction.index("($total_atual|round:2) == ($input.total_esperado|round:2)")
        header = self.transaction.index("db.add transacoes")
        item = self.transaction.index("db.add itens_transacao")
        exit_ = self.transaction.index('function.run "Estoque/movimentar_estoque"')
        self.assertLess(ordered, recheck)
        self.assertLess(recheck, header)
        self.assertLess(header, item)
        self.assertLess(item, exit_)
        for fragment in (
            'tipo_transacao: "BALCAO"',
            "id_cliente    : $input.id_cliente",
            "valor_total   : $total_atual|round:2",
            "chave_venda     : $input.chave_venda",
            'tipo          : "SAIDA_VENDA"',
            "id_transacao  : $transacao.id",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.transaction)

    def test_races_roll_back_with_the_conflict_message(self):
        self.assertIn("precondition (false)", self.catch)
        self.assertIn(
            "A venda não foi registrada: o estoque ou os preços mudaram durante o fechamento.",
            self.catch,
        )
        self.assertIsNone(re.search(r"\bdb\.(add|edit|patch|del)\b", self.catch))


class DetalheVendaTests(unittest.TestCase):
    def setUp(self):
        self.content = read("function/balcao/detalhe_venda.xs")

    def test_receipt_is_read_only_and_only_for_counter_sales(self):
        self.assertIn('function "Balcao/detalhe_venda"', self.content)
        self.assertIn('$transacao.tipo_transacao == "BALCAO"', self.content)
        self.assertIsNone(re.search(r"\bdb\.(add|edit|patch|del|transaction)\b", self.content))

    def test_receipt_brings_names_and_items(self):
        for joined in ('table: "clientes"', 'table: "funcionarios"', 'table: "produtos"'):
            with self.subTest(join=joined):
                self.assertIn(joined, self.content)
        self.assertIn("where = $db.itens_transacao.id_transacao == $input.id_transacao", self.content)
        for field in ("id_transacao", "data_transacao", "valor_total", "nome_cliente", "nome_funcionario", "itens"):
            with self.subTest(field=field):
                self.assertRegex(self.content, rf"\n        {field}\s*:")


if __name__ == "__main__":
    unittest.main()
