from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]


class HardeningContractTests(unittest.TestCase):
    def read(self, relative_path):
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_customer_motorcycle_put_matches_vendor_matrix(self):
        content = self.read(
            "xano/api/harley/motos_clientes/motos_clientes_id_PUT.xs"
        )
        self.assertIn('required_role: "VENDEDOR"', content)

    def test_operational_authority_comes_from_authenticated_user(self):
        operation_files = [
            "xano/api/harley/ordens_servico_POST.xs",
            "xano/api/harley/ordens_servico/ordens_servico_id_status_POST.xs",
            "xano/api/harley/ordens_servico/ordens_servico_id_itens_POST.xs",
            "xano/api/harley/ordens_servico/ordens_servico_id_itens_item_id_DELETE.xs",
            "xano/api/harley/transacoes_POST.xs",
            "xano/api/harley/transacoes/transacoes_id_PUT.xs",
        ]
        for relative_path in operation_files:
            with self.subTest(path=relative_path):
                content = self.read(relative_path)
                self.assertIn('field_value = $auth.id', content)
                self.assertIn("as $auth_user", content)
                self.assertIn("$auth_user.id_funcionario", content)
                self.assertNotIn("id_funcionario : $input.id_funcionario", content)

    def test_financial_schemas_reject_zero(self):
        schemas = [
            "xano/table/entrada_mercadoria.xs",
            "xano/table/itens_ordem_servico.xs",
            "xano/table/transacoes.xs",
        ]
        for relative_path in schemas:
            with self.subTest(path=relative_path):
                self.assertIn("filters=min:0.01", self.read(relative_path))


if __name__ == "__main__":
    unittest.main()