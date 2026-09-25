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


if __name__ == "__main__":
    unittest.main()
