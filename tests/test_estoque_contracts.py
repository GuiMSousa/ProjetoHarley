from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]
API = "xano/api/harley"


class EstoqueContractTests(unittest.TestCase):
    def read(self, relative_path):
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_receipt_post_is_atomic_and_manager_only(self):
        content = self.read(f"{API}/entrada_mercadoria_POST.xs")
        self.assertIn('required_role: "GERENTE"', content)
        self.assertIn("db.transaction {", content)
        self.assertNotIn("dblink", content)
        transaction = content[content.index("db.transaction {") :]
        for operation in (
            "db.add entrada_mercadoria",
            "db.add itens_compra_estoque",
            'function.run "Estoque/movimentar_estoque"',
        ):
            with self.subTest(operation=operation):
                self.assertIn(operation, transaction)

    def test_receipt_post_moves_stock_through_the_ledger(self):
        content = self.read(f"{API}/entrada_mercadoria_POST.xs")
        self.assertNotIn("db.edit produtos", content)
        for fragment in (
            'tipo          : "ENTRADA"',
            "quantidade    : $item.quantidade",
            "id_funcionario: $auth_user.id_funcionario",
            "id_entrada    : $entrada.id",
            # Same lock order as the cancellation, to avoid deadlocks.
            'foreach ($input.itens|sort:"id_produto":"int":false)',
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, content)

    def test_stock_function_writes_ledger_before_product(self):
        content = self.read("xano/function/estoque/movimentar_estoque.xs")
        self.assertIn('function "Estoque/movimentar_estoque"', content)
        self.assertIn('output = ["id", "codigo", "estoque_qtd", "versao_estoque", "ativo"]', content)
        self.assertLess(
            content.index("db.add movimentacoes_estoque"), content.index("db.edit produtos")
        )
        self.assertIn("precondition ($saldo_posterior >= 0)", content)
        self.assertIn('"Saldo insuficiente para "', content)
        self.assertIn("versao_anterior: $versao", content)
        self.assertIn("versao_estoque: $versao + 1", content)
        self.assertIn('$input.tipo != "SAIDA_OS" || $produto.ativo != false', content)

    def test_ledger_serializes_movements_per_product(self):
        content = self.read("xano/table/movimentacoes_estoque.xs")
        self.assertIn('values = ["ENTRADA", "SAIDA_OS", "ESTORNO_OS"]', content)
        self.assertIn("int saldo_posterior filters=min:0", content)
        self.assertRegex(
            content,
            r'type : "btree\|unique"\s*field: \[\{name: "id_produto"\}, \{name: "versao_anterior"\}\]',
        )
        self.assertIn("int? versao_estoque? filters=min:0", self.read("xano/table/produtos.xs"))

    def test_only_the_stock_function_writes_the_balance(self):
        allowed = {
            Path("xano/function/estoque/movimentar_estoque.xs"),
            # Initial balance, set only when the product is created.
            Path("xano/api/harley/produtos_POST.xs"),
        }
        for path in (ROOT / "xano").rglob("*.xs"):
            relative = path.relative_to(ROOT)
            content = path.read_text(encoding="utf-8")
            if re.search(r"estoque_qtd\s*:", content):
                with self.subTest(path=str(relative)):
                    self.assertIn(relative, allowed)

    def test_receipt_post_validates_supplier_products_and_items(self):
        content = self.read(f"{API}/entrada_mercadoria_POST.xs")
        transaction = content[content.index("db.transaction {") :]
        self.assertIn("$fornecedor.ativo != false", transaction)
        self.assertIn("$produto.ativo != false", transaction)
        self.assertIn("$documento_existente", transaction)
        self.assertIn("($input.itens|count) > 0", content)
        self.assertIn("($ids_produto|unique|count)", content)
        self.assertIn("int quantidade filters=min:1", content)
        self.assertIn("decimal valor_unitario filters=min:0.01", content)

    def test_receipt_authorship_and_total_come_from_server(self):
        content = self.read(f"{API}/entrada_mercadoria_POST.xs")
        self.assertIn("field_value = $auth.id", content)
        self.assertIn("id_funcionario  : $auth_user.id_funcionario", content)
        self.assertIn("valor_total     : $valor_total", content)
        self.assertIn("data_entrada    : now", content)
        for untrusted in ("$input.id_funcionario", "$input.valor_total", "$input.data_entrada"):
            with self.subTest(field=untrusted):
                self.assertNotIn(untrusted, content)

    def test_receipt_schema_has_document_author_and_unique_document(self):
        content = self.read("xano/table/entrada_mercadoria.xs")
        # Nullable so legacy rows (null) never collide in the unique index.
        self.assertIn("text? numero_documento? filters=trim", content)
        self.assertRegex(content, r"int\? id_funcionario\? \{\s*table = \"funcionarios\"")
        self.assertRegex(
            content,
            r'type : "btree\|unique"\s*field: \[\{name: "id_fornecedor"\}, \{name: "numero_documento"\}\]',
        )

    def test_receipt_reads_are_open_to_all_roles(self):
        for relative_path in (
            f"{API}/entrada_mercadoria_GET.xs",
            f"{API}/entrada_mercadoria/entrada_mercadoria_id_GET.xs",
            f"{API}/itens_compra_estoque_GET.xs",
            f"{API}/itens_compra_estoque/itens_compra_estoque_id_GET.xs",
        ):
            with self.subTest(path=relative_path):
                self.assertIn('required_role: "ALL"', self.read(relative_path))

    def test_receipt_reads_are_enriched(self):
        listing = self.read(f"{API}/entrada_mercadoria_GET.xs")
        for field in ("nome_fornecedor", "nome_funcionario", "quantidade_itens"):
            self.assertIn(field, listing)
        detail = self.read(f"{API}/entrada_mercadoria/entrada_mercadoria_id_GET.xs")
        self.assertIn('function.run "Estoque/detalhe_entrada"', detail)
        function = self.read("xano/function/estoque/detalhe_entrada.xs")
        for field in ("nome_fornecedor", "nome_funcionario", "codigo", "nome_produto", "valor_total_item"):
            self.assertIn(field, function)

    def test_direct_receipt_and_item_mutations_are_blocked(self):
        blocked = [
            "entrada_mercadoria/entrada_mercadoria_id_PUT.xs",
            "entrada_mercadoria/entrada_mercadoria_id_PATCH.xs",
            "entrada_mercadoria/entrada_mercadoria_id_DELETE.xs",
            "itens_compra_estoque_POST.xs",
            "itens_compra_estoque/itens_compra_estoque_id_PUT.xs",
            "itens_compra_estoque/itens_compra_estoque_id_PATCH.xs",
            "itens_compra_estoque/itens_compra_estoque_id_DELETE.xs",
        ]
        for relative_path in blocked:
            with self.subTest(path=relative_path):
                content = self.read(f"{API}/{relative_path}")
                self.assertIn("precondition (false)", content)
                self.assertIn('error_type = "accessdenied"', content)
                self.assertNotRegex(content, r"db\.(add|edit|patch|del) ")

    def test_product_edits_cannot_change_stock_balance(self):
        self.assertNotIn(
            "estoque_qtd",
            self.read(f"{API}/produtos/produtos_id_PUT.xs"),
        )
        patch = self.read(f"{API}/produtos/produtos_id_PATCH.xs")
        self.assertIn('|unset:"estoque_qtd"', patch)
        self.assertIn('|unset:"versao_estoque"', patch)
        self.assertNotIn("versao_estoque", self.read(f"{API}/produtos/produtos_id_PUT.xs"))
        self.assertIn("estoque_qtd", self.read(f"{API}/produtos_POST.xs"))
        self.assertNotIn("versao_estoque", self.read(f"{API}/produtos_POST.xs"))

    def test_supplier_reads_are_manager_only(self):
        for relative_path in (
            f"{API}/fornecedores_GET.xs",
            f"{API}/fornecedores/fornecedores_id_GET.xs",
        ):
            with self.subTest(path=relative_path):
                content = self.read(relative_path)
                self.assertIn('required_role: "GERENTE"', content)
                self.assertIsNone(re.search(r'required_role: "ALL"', content))


if __name__ == "__main__":
    unittest.main()
