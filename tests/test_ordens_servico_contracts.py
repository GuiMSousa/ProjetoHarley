from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]
XANO = ROOT / "xano"
API = "api/harley"


class OrdemServicoContractTests(unittest.TestCase):
    def read(self, relative_path):
        return (XANO / relative_path).read_text(encoding="utf-8")

    def test_schema_adds_nullable_fields_for_legacy_orders(self):
        content = self.read("table/ordens_servico.xs")
        for declaration in (
            "int? id_cliente?",
            "int? id_mecanico?",
            "enum? tipo_servico?",
            "text? descricao_problema?",
            "int? quilometragem? filters=min:0",
            "timestamp? data_inicio?",
            "timestamp? data_encerramento?",
            "text? motivo_cancelamento?",
        ):
            with self.subTest(declaration=declaration):
                self.assertIn(declaration, content)

    def test_history_table_serializes_transitions_per_status(self):
        content = self.read("table/historico_status_os.xs")
        self.assertIn("enum? status_anterior?", content)
        self.assertIn("enum status_novo", content)
        self.assertRegex(
            content,
            r'type : "btree\|unique"\s*field: \[\{name: "id_os"\}, \{name: "status_anterior"\}\]',
        )

    def test_opening_always_starts_open_with_server_side_authorship(self):
        content = self.read(f"{API}/ordens_servico_POST.xs")
        self.assertIn('required_role: "MECANICO"', content)
        self.assertIn("db.transaction {", content)
        self.assertNotIn("dblink", content)
        self.assertIn('status            : "ABERTA"', content)
        self.assertIn("data_abertura     : now", content)
        self.assertIn("id_funcionario    : $auth_user.id_funcionario", content)
        self.assertIn("id_cliente        : $moto.id_cliente", content)
        for untrusted in ("$input.status", "$input.id_funcionario", "$input.id_cliente", "$input.data_abertura"):
            with self.subTest(field=untrusted):
                self.assertNotIn(untrusted, content)

    def test_opening_validates_bike_customer_mechanic_and_open_order(self):
        content = self.read(f"{API}/ordens_servico_POST.xs")
        transaction = content[content.index("db.transaction {"):]
        self.assertIn("$moto.ativo != false", transaction)
        self.assertIn("$cliente.ativo != false", transaction)
        self.assertIn('$mecanico.tipo == "MECANICO"', transaction)
        self.assertIn("$os_em_aberto == null", transaction)
        self.assertIn('"Informe o mecânico responsável."', content)
        self.assertIn("db.add historico_status_os", transaction)

    def test_transition_endpoint_uses_state_machine_and_history(self):
        content = self.read(f"{API}/ordens_servico/ordens_servico_id_status_POST.xs")
        self.assertIn('query "ordens_servico/{ordens_servico_id}/status" verb=POST', content)
        self.assertIn('required_role: "MECANICO"', content)
        self.assertIn('function.run "Oficina/validar_transicao_os"', content)
        self.assertIn("$os.status == $input.status_atual", content)
        transaction = content[content.index("db.transaction {"):]
        self.assertLess(
            transaction.index("db.add historico_status_os"),
            transaction.index("db.patch ordens_servico"),
        )
        self.assertIn("id_funcionario : $auth_user.id_funcionario", transaction)
        self.assertNotIn("$input.id_funcionario", content)

    def test_transition_function_encodes_the_table(self):
        content = self.read("function/oficina/validar_transicao_os.xs")
        self.assertIn('$input.status_atual != "CONCLUIDA" && $input.status_atual != "CANCELADA"', content)
        self.assertIn(
            '($input.status_atual == "ABERTA" && ($input.status_novo == "EM_ANDAMENTO" || $input.status_novo == "CANCELADA"))',
            content,
        )
        self.assertIn(
            '($input.status_atual == "EM_ANDAMENTO" && ($input.status_novo == "CONCLUIDA" || $input.status_novo == "CANCELADA"))',
            content,
        )
        self.assertIn('"Informe o motivo do cancelamento."', content)

    def test_reads_are_open_to_all_roles(self):
        for relative_path in (
            f"{API}/ordens_servico_GET.xs",
            f"{API}/ordens_servico/ordens_servico_id_GET.xs",
            f"{API}/itens_ordem_servico_GET.xs",
            f"{API}/itens_ordem_servico/itens_ordem_servico_id_GET.xs",
        ):
            with self.subTest(path=relative_path):
                self.assertIn('required_role: "ALL"', self.read(relative_path))

    def test_list_supports_status_and_bike_filters(self):
        content = self.read(f"{API}/ordens_servico_GET.xs")
        self.assertIn("$db.ordens_servico.status ==? $input.status", content)
        self.assertIn("$db.ordens_servico.id_moto_cliente ==? $input.id_moto_cliente", content)
        for field in ("nome_cliente", "placa", "modelo", "nome_funcionario", "nome_mecanico"):
            self.assertIn(field, content)

    def test_mechanics_endpoint_exposes_only_id_and_name(self):
        content = self.read(f"{API}/oficina/mecanicos_GET.xs")
        self.assertIn('required_role: "MECANICO"', content)
        self.assertIn('$db.funcionarios.tipo == "MECANICO"', content)
        self.assertIn("{id: $$.id, nome_funcionario: $$.nome_funcionario}", content)
        self.assertNotIn("contato", content)

    def test_generic_order_and_item_mutations_are_blocked(self):
        blocked = [
            "ordens_servico/ordens_servico_id_PUT.xs",
            "ordens_servico/ordens_servico_id_PATCH.xs",
            "ordens_servico/ordens_servico_id_DELETE.xs",
            "itens_ordem_servico_POST.xs",
            "itens_ordem_servico/itens_ordem_servico_id_PUT.xs",
            "itens_ordem_servico/itens_ordem_servico_id_PATCH.xs",
            "itens_ordem_servico/itens_ordem_servico_id_DELETE.xs",
        ]
        for relative_path in blocked:
            with self.subTest(path=relative_path):
                content = self.read(f"{API}/{relative_path}")
                self.assertIn("precondition (false)", content)
                self.assertIn('error_type = "accessdenied"', content)
                self.assertIsNone(re.search(r"db\.(add|edit|patch|del) ", content))


ITENS_POST = f"{API}/ordens_servico/ordens_servico_id_itens_POST.xs"
ITENS_DELETE = f"{API}/ordens_servico/ordens_servico_id_itens_item_id_DELETE.xs"
STATUS_POST = f"{API}/ordens_servico/ordens_servico_id_status_POST.xs"


class ItemOrdemServicoContractTests(unittest.TestCase):
    def read(self, relative_path):
        return (XANO / relative_path).read_text(encoding="utf-8")

    def transaction(self, content):
        return content[content.index("db.transaction {"):]

    def test_item_schema_supports_services_and_legacy_rows(self):
        content = self.read("table/itens_ordem_servico.xs")
        for declaration in (
            "int? id_produto?",
            "enum? tipo_item?",
            'values = ["PECA", "SERVICO"]',
            "text? descricao? filters=trim",
            "decimal? valor_unitario? filters=min:0.01",
            "bool? estoque_baixado?",
            "int? id_funcionario?",
            "decimal valor_total_item filters=min:0.01",
        ):
            with self.subTest(declaration=declaration):
                self.assertIn(declaration, content)
        order = self.read("table/ordens_servico.xs")
        for declaration in (
            "decimal? valor_pecas?",
            "decimal? valor_servicos?",
            "decimal? valor_total?",
            "timestamp? atualizado_em?",
        ):
            with self.subTest(declaration=declaration):
                self.assertIn(declaration, order)

    def test_item_routes_are_operator_only_and_declare_explicit_inputs(self):
        routes = {
            ITENS_POST: 'query "ordens_servico/{ordens_servico_id}/itens" verb=POST',
            ITENS_DELETE: 'query "ordens_servico/{ordens_servico_id}/itens/{item_id}" verb=DELETE',
        }
        for relative_path, route in routes.items():
            with self.subTest(path=relative_path):
                content = self.read(relative_path)
                self.assertIn(route, content)
                self.assertIn('required_role: "MECANICO"', content)
                self.assertNotIn("dblink", content)
                self.assertIn("try_catch {", content)
                self.assertIn('function.run "Oficina/detalhe_os"', content)
                self.assertIn("OS encerrada não permite alterar itens.", content)

    def test_mutations_lock_the_order_before_rereading_status(self):
        for relative_path in (ITENS_POST, ITENS_DELETE):
            with self.subTest(path=relative_path):
                transaction = self.transaction(self.read(relative_path))
                lock = transaction.index("data = {atualizado_em: now}")
                self.assertLess(lock, transaction.index("db.get ordens_servico"))
                self.assertLess(lock, transaction.index('"Estoque/movimentar_estoque"'))
                self.assertIn('function.run "Oficina/totais_os"', transaction)
                self.assertIn("valor_total   : $totais.valor_total", transaction)

    def test_part_is_priced_by_server_and_leaves_stock_in_the_same_transaction(self):
        content = self.read(ITENS_POST)
        transaction = self.transaction(content)
        self.assertIn("valor_unitario  : $produto.preco_venda", transaction)
        self.assertIn(
            "valor_total_item: ($input.quantidade * $produto.preco_venda)|round:2", transaction
        )
        self.assertIn("estoque_baixado : true", transaction)
        self.assertIn('tipo          : "SAIDA_OS"', transaction)
        self.assertIn("id_item_os    : $item_peca.id", transaction)
        self.assertIn("id_funcionario  : $auth_user.id_funcionario", transaction)
        for untrusted in ("$input.valor_total_item", "$input.estoque_baixado", "$input.id_funcionario"):
            with self.subTest(field=untrusted):
                self.assertNotIn(untrusted, content)
        for message in (
            "Selecione o produto.",
            "Este produto já está na OS.",
            '"Saldo insuficiente para "',
            "Informe a descrição do serviço.",
            "Informe o valor do serviço.",
        ):
            with self.subTest(message=message):
                self.assertIn(message, content)

    def test_service_does_not_move_stock(self):
        transaction = self.transaction(self.read(ITENS_POST))
        servico = transaction[transaction.index('tipo_item       : "SERVICO"'):]
        servico = servico[: servico.index("function.run")]
        self.assertIn("estoque_baixado : false", servico)
        self.assertIn("valor_unitario  : $input.valor_unitario", servico)

    def test_removal_returns_only_parts_taken_from_stock(self):
        transaction = self.transaction(self.read(ITENS_DELETE))
        self.assertIn("if ($item.estoque_baixado == true)", transaction)
        self.assertIn('tipo          : "ESTORNO_OS"', transaction)
        self.assertLess(
            transaction.index('"ESTORNO_OS"'), transaction.index("db.del itens_ordem_servico")
        )
        self.assertIn("$item.id_os == $input.ordens_servico_id", transaction)

    def test_cancellation_returns_parts_after_locking_the_order(self):
        transaction = self.transaction(self.read(STATUS_POST))
        self.assertLess(
            transaction.index("db.add historico_status_os"),
            transaction.index("db.patch ordens_servico"),
        )
        self.assertLess(
            transaction.index("db.patch ordens_servico"),
            transaction.index("db.query itens_ordem_servico"),
        )
        self.assertIn('if ($input.status_novo == "CANCELADA")', transaction)
        self.assertIn("$db.itens_ordem_servico.estoque_baixado == true", transaction)
        self.assertIn('sort = {id_produto: "asc"}', transaction)
        self.assertIn('tipo          : "ESTORNO_OS"', transaction)
        self.assertIn("atualizado_em: $agora", self.read(STATUS_POST))

    def test_totals_are_recalculated_from_items(self):
        function = self.read("function/oficina/totais_os.xs")
        self.assertIn('if ($item.tipo_item == "SERVICO")', function)
        self.assertIn("valor_total   : ($valor_pecas + $valor_servicos)|round:2", function)
        detail = self.read("function/oficina/detalhe_os.xs")
        self.assertIn('function.run "Oficina/totais_os"', detail)
        self.assertIn('|set:"valor_total":$totais.valor_total', detail)

    def test_legacy_item_routes_point_to_the_new_routes(self):
        for relative_path in (
            "itens_ordem_servico_POST.xs",
            "itens_ordem_servico/itens_ordem_servico_id_PUT.xs",
            "itens_ordem_servico/itens_ordem_servico_id_PATCH.xs",
            "itens_ordem_servico/itens_ordem_servico_id_DELETE.xs",
        ):
            with self.subTest(path=relative_path):
                self.assertIn(
                    '"Use POST/DELETE ordens_servico/{id}/itens."',
                    self.read(f"{API}/{relative_path}"),
                )


if __name__ == "__main__":
    unittest.main()
