"""Change 10: XanoScript contracts of the financial closing and the consolidated view."""

import re
import unittest
from pathlib import Path


XANO = Path(__file__).parents[1] / "xano"
API = "api/harley"


def read(relative_path: str) -> str:
    return (XANO / relative_path).read_text(encoding="utf-8")


class TransacoesSchemaTests(unittest.TestCase):
    def test_transaction_links_the_billed_order_with_a_plain_index(self):
        content = read("table/transacoes.xs")
        self.assertRegex(content, r'int\? id_os\? \{\s*table = "ordens_servico"\s*\}')
        self.assertRegex(content, r'\{type: "btree", field: \[\{name: "id_os"\}\]\}')
        # D8: not unique; the order state machine already allows one posting per order.
        self.assertNotRegex(content, r'"btree\|unique", field: \[\{name: "id_os"\}\]')
        self.assertIn("decimal valor_total? filters=min:0.01", content)


class ConclusaoOSTests(unittest.TestCase):
    def setUp(self):
        self.content = read(f"{API}/ordens_servico/ordens_servico_id_status_POST.xs")
        self.transaction = self.content[self.content.index("db.transaction {") :]

    def test_conclusion_posts_the_revenue_inside_the_same_transaction(self):
        posting = self.transaction[self.transaction.index('if ($input.status_novo == "CONCLUIDA")') :]
        self.assertLess(self.transaction.index("db.patch ordens_servico"), self.transaction.index('function.run "Oficina/totais_os"'))
        self.assertLess(posting.index('function.run "Oficina/totais_os"'), posting.index("db.add transacoes"))
        self.assertIn("if ($totais.valor_total > 0)", posting)
        for fragment in (
            'tipo_transacao : "ORDEM_SERVICO"',
            "id_funcionario : $auth_user.id_funcionario",
            "id_os          : $input.ordens_servico_id",
            "id_moto_cliente: $os.id_moto_cliente",
            "id_cliente     : $id_cliente",
            "data_transacao : $agora",
            "valor_total    : $totais.valor_total",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, posting)
        # Rollback on any failure: the posting lives in the try branch, before the catch.
        self.assertLess(self.transaction.index("db.add transacoes"), self.transaction.index("catch {"))

    def test_customer_falls_back_to_the_bike_owner_for_old_orders(self):
        self.assertIn('output = ["id", "status", "id_cliente", "id_moto_cliente"]', self.content)
        self.assertIn("value = $os.id_cliente", self.content)
        self.assertIn("value = $moto_da_os.id_cliente", self.content)

    def test_amount_and_author_never_come_from_the_payload(self):
        for untrusted in ("$input.valor_total", "$input.id_funcionario", "$input.id_cliente"):
            with self.subTest(field=untrusted):
                self.assertNotIn(untrusted, self.content)

    def test_order_detail_returns_the_posting(self):
        detail = read("function/oficina/detalhe_os.xs")
        self.assertIn("where = $db.transacoes.id_os == $input.os_id", detail)
        self.assertIn('|set:"id_transacao":$transacao.id', detail)
        self.assertIn('|set:"data_lancamento":$transacao.data_transacao', detail)


class ImutabilidadeTests(unittest.TestCase):
    def test_manual_writes_are_blocked_for_every_role(self):
        for relative_path, message in (
            (f"{API}/transacoes_POST.xs", "Transações são registradas somente pelas operações de venda e de oficina."),
            (f"{API}/transacoes/transacoes_id_PUT.xs", "Transações são imutáveis."),
            (f"{API}/transacoes/transacoes_id_PATCH.xs", "Transações são imutáveis."),
        ):
            with self.subTest(path=relative_path):
                content = read(relative_path)
                self.assertLess(content.index('function.run "Quick Start/enforce_role"'), content.index("precondition (false)"))
                self.assertIn('error_type = "accessdenied"', content)
                self.assertIn(message, content)
                self.assertRegex(content, r'guid = "[^"]+"')
                self.assertIsNone(re.search(r"\bdb\.(add|edit|patch|del)\s", content))

    def test_only_business_operations_create_transactions(self):
        writers = sorted(
            path.relative_to(XANO).as_posix()
            for path in XANO.rglob("*.xs")
            if re.search(r"\bdb\.add transacoes\b", path.read_text(encoding="utf-8"))
        )
        self.assertEqual(
            writers,
            [
                f"{API}/ordens_servico/ordens_servico_id_status_POST.xs",
                "function/financeiro/lancar_os_concluidas_legadas.xs",
                "function/vendas/vender_moto.xs",
            ],
        )
        for path in XANO.rglob("*.xs"):
            with self.subTest(path=path.relative_to(XANO).as_posix()):
                self.assertIsNone(re.search(r"\bdb\.(edit|patch|del) transacoes\b", path.read_text(encoding="utf-8")))


class ResumoTests(unittest.TestCase):
    def setUp(self):
        self.endpoint = read(f"{API}/financeiro/resumo_GET.xs")
        self.function = read("function/financeiro/resumo_operacoes.xs")

    def test_endpoint_is_manager_only_and_delegates_to_the_view(self):
        self.assertIn('query "financeiro/resumo" verb=GET', self.endpoint)
        self.assertIn('api_group = "HARLEY"', self.endpoint)
        self.assertIn('auth = "user"', self.endpoint)
        self.assertIn('required_role: "GERENTE"', self.endpoint)
        self.assertIn("timestamp inicio", self.endpoint)
        self.assertIn("timestamp fim", self.endpoint)
        self.assertIn('function.run "Financeiro/resumo_operacoes"', self.endpoint)

    def test_period_is_validated_up_to_366_days(self):
        self.assertIn("precondition ($input.fim >= $input.inicio)", self.function)
        self.assertIn("O fim do período deve ser igual ou posterior ao início.", self.function)
        self.assertIn(f"<= {366 * 24 * 60 * 60 * 1000}", self.function)
        self.assertIn("O período pode ter no máximo 366 dias.", self.function)

    def test_view_joins_transactions_and_goods_receipts_of_the_period(self):
        self.assertIn("$db.transacoes.data_transacao >= $input.inicio && $db.transacoes.data_transacao <= $input.fim", self.function)
        self.assertIn(
            "$db.entrada_mercadoria.data_entrada >= $input.inicio && $db.entrada_mercadoria.data_entrada <= $input.fim",
            self.function,
        )
        for joined in ('table: "clientes"', 'table: "funcionarios"', 'table: "motos_clientes"', 'table: "fornecedores"'):
            with self.subTest(join=joined):
                self.assertIn(joined, self.function)
        # D4: goods receipts are expenses read directly; COMPRA transactions are expenses too.
        self.assertIn('origem          : "ENTRADA"', self.function)
        self.assertIn('natureza        : "DESPESA"', self.function)
        self.assertIn('if ($transacao.tipo_transacao == "COMPRA")', self.function)

    def test_totals_cover_the_period_and_the_list_is_capped(self):
        self.assertIn('($operacoes|sort:"data":"number":false)|slice:0:500', self.function)
        self.assertLess(self.function.index("var $total_operacoes"), self.function.index("|slice:0:500"))
        for field in ("receitas", "despesas", "saldo", "por_tipo", "operacoes", "total_operacoes", "truncado"):
            with self.subTest(field=field):
                self.assertRegex(self.function, rf"\n    {field}\s*:")
        self.assertIn("truncado       : $total_operacoes > 500", self.function)

    def test_view_never_writes(self):
        for content in (self.endpoint, self.function):
            self.assertIsNone(re.search(r"\bdb\.(add|edit|patch|del|transaction)\b", content))


class LegadoTests(unittest.TestCase):
    def setUp(self):
        self.content = read("function/financeiro/lancar_os_concluidas_legadas.xs")

    def test_backfill_is_idempotent_and_posts_only_positive_totals(self):
        self.assertIn('function "Financeiro/lancar_os_concluidas_legadas"', self.content)
        self.assertIn('where = $db.ordens_servico.status == "CONCLUIDA"', self.content)
        self.assertIn("where = $db.transacoes.id_os == $os.id", self.content)
        self.assertIn("if (!$ja_lancada)", self.content)
        self.assertIn("if ($totais.valor_total > 0)", self.content)
        self.assertIn("data_transacao : $os.data_encerramento ?? $os.data_abertura", self.content)

    def test_backfill_author_must_be_an_active_manager(self):
        self.assertIn('$gerente.tipo == "GERENTE"', self.content)
        self.assertIn("$gerente.ativo != false", self.content)

    def test_backfill_is_never_called_by_an_endpoint(self):
        for path in (XANO / "api").rglob("*.xs"):
            with self.subTest(path=path.relative_to(XANO).as_posix()):
                self.assertNotIn("Financeiro/lancar_os_concluidas_legadas", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
