import unittest

from Projeto_HarleyStore.cadastros_state import CadastrosState


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


if __name__ == "__main__":
    unittest.main()
