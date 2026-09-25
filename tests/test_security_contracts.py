from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]
XANO = ROOT / "xano"


class SecurityContractTests(unittest.TestCase):
    def read(self, relative_path):
        return (XANO / relative_path).read_text(encoding="utf-8")

    def test_patch_endpoints_never_accept_authorship(self):
        self.assertIn(
            '|unset:"id_funcionario"',
            self.read("api/harley/transacoes/transacoes_id_PATCH.xs"),
        )
        # Since Change 6 the generic OS PATCH is blocked: status changes go through
        # POST ordens_servico/{id}/status and nothing is written from the payload.
        content = self.read("api/harley/ordens_servico/ordens_servico_id_PATCH.xs")
        self.assertIn("precondition (false)", content)
        self.assertNotIn("db.patch", content)

    def test_every_write_that_sets_authorship_uses_the_authenticated_user(self):
        for path in (XANO / "api").rglob("*.xs"):
            content = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(XANO).as_posix()):
                self.assertNotIn("id_funcionario : $input.id_funcionario", content)
                self.assertNotIn("id_funcionario  : $input.id_funcionario", content)

    def test_welcome_email_requires_manager(self):
        content = self.read("api/authentication/message/send_welcome_email_POST.xs")
        self.assertIn('auth = "user"', content)
        self.assertIn('required_role: "GERENTE"', content)
        self.assertIn('output = ["id", "name", "email"]', content)

    def test_physical_deletes_are_blocked(self):
        for resource in (
            "clientes",
            "motos_clientes",
            "produtos",
            "fornecedores",
            "funcionarios",
            "motos",
            "transacoes",
        ):
            with self.subTest(resource=resource):
                content = self.read(f"api/harley/{resource}/{resource}_id_DELETE.xs")
                self.assertIn(f'query "{resource}/{{{resource}_id}}" verb=DELETE', content)
                self.assertIn('required_role: "GERENTE"', content)
                self.assertIn("precondition (false)", content)
                self.assertIn('error_type = "accessdenied"', content)
                self.assertNotIn("db.del", content)

    def test_only_open_order_items_are_physically_deleted(self):
        deleting = [
            path.relative_to(XANO).as_posix()
            for path in (XANO / "api").rglob("*.xs")
            if re.search(r"db\.(del|bulk\.delete) ", path.read_text(encoding="utf-8"))
        ]
        self.assertEqual(
            deleting, ["api/harley/ordens_servico/ordens_servico_id_itens_item_id_DELETE.xs"]
        )

    def test_password_change_requires_current_password_and_active_employee(self):
        content = self.read("api/authentication/reset/update_password_POST.xs")
        for declaration in (
            "text current_password\n",
            "text password filters=min:8\n",
            "text confirm_password\n",
        ):
            with self.subTest(declaration=declaration):
                self.assertIn(declaration, content)
        # Passwords are compared raw, as in auth/login and auth/signup.
        self.assertNotIn("trim", content[content.index("input {"):content.index("stack {")])
        self.assertIn('required_role: "ALL"', content)
        self.assertIn("text_password = $input.current_password", content)
        self.assertLess(content.index("security.check_password"), content.index("db.edit user"))
        self.assertIn("$input.password != $input.current_password", content)
        self.assertIn("metadata: {id: $auth.id}", content)

    def test_unapproved_recovery_endpoints_are_blocked(self):
        for relative_path in (
            "api/authentication/reset/request_reset_link_GET.xs",
            "api/authentication/reset/magic_link_login_POST.xs",
        ):
            with self.subTest(path=relative_path):
                content = self.read(relative_path)
                self.assertIn("precondition (false)", content)
                self.assertNotIn("security.create_auth_token", content)
                self.assertNotIn("util.send_email", content)

    def test_only_login_endpoint_is_public(self):
        public = []
        for path in (XANO / "api").rglob("*.xs"):
            content = path.read_text(encoding="utf-8")
            if not content.lstrip().startswith(("query", "//")) or "query " not in content:
                continue
            blocked = "precondition (false)" in content
            if not re.search(r'^\s*auth = "user"', content, re.M) and not blocked:
                public.append(path.relative_to(XANO).as_posix())
        self.assertEqual(public, ["api/authentication/auth/login_POST.xs"])

    def test_event_logs_never_store_whole_records(self):
        for path in (XANO / "api").rglob("*.xs"):
            content = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(XANO).as_posix()):
                self.assertIsNone(re.search(r"metadata:\s*\$user\d*\s*$", content, re.M))

    def test_signup_does_not_issue_tokens_for_other_users(self):
        content = self.read("api/authentication/auth/signup_POST.xs")
        self.assertNotIn("security.create_auth_token", content)
        self.assertNotIn("authToken", content)
        self.assertIn("email email filters=trim|lower", content)
        self.assertIn("text password filters=min:8", content)
        self.assertIn("$employee.ativo != false", content)
        self.assertIn("$employee_has_user", content)

    def test_inactive_employee_loses_business_access(self):
        self.assertIn(
            "precondition ($employee.ativo != false)",
            self.read("function/quick_start/enforce_role.xs"),
        )
        me = self.read("api/authentication/auth/me_GET.xs")
        self.assertIn('"ativo"', me)
        self.assertNotIn("log_event", me)

    def test_legacy_receipts_can_be_normalized(self):
        content = self.read("function/estoque/normalizar_entradas_legadas.xs")
        self.assertIn('"LEGADO-" ~ $entrada.id', content)
        self.assertIn("numero_documento == null", content)


if __name__ == "__main__":
    unittest.main()
