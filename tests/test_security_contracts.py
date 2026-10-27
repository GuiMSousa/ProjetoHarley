from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]
XANO = ROOT / "xano"


class SecurityContractTests(unittest.TestCase):
    def read(self, relative_path):
        return (XANO / relative_path).read_text(encoding="utf-8")

    def test_patch_endpoints_never_accept_authorship(self):
        # Since Change 10 transactions are immutable: the generic PATCH writes nothing.
        transacoes = self.read("api/harley/transacoes/transacoes_id_PATCH.xs")
        self.assertIn("precondition (false)", transacoes)
        self.assertNotIn("db.patch", transacoes)
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

    def test_public_surface_is_explicit(self):
        """Login plus the read-only showroom (Change 8, D3) are the only public endpoints."""
        public = []
        for path in (XANO / "api").rglob("*.xs"):
            content = path.read_text(encoding="utf-8")
            if not content.lstrip().startswith(("query", "//")) or "query " not in content:
                continue
            blocked = "precondition (false)" in content
            if not re.search(r'^\s*auth = "user"', content, re.MULTILINE) and not blocked:
                public.append(path.relative_to(XANO).as_posix())
        self.assertEqual(
            sorted(public),
            [
                "api/authentication/auth/login_POST.xs",
                "api/harley/catalogo/catalogo_id_GET.xs",
                "api/harley/catalogo_GET.xs",
            ],
        )
        for relative_path in ("api/harley/catalogo_GET.xs", "api/harley/catalogo/catalogo_id_GET.xs"):
            with self.subTest(path=relative_path):
                self.assertIn("verb=GET", self.read(relative_path))

    def test_every_authenticated_endpoint_enforces_an_employee_role(self):
        """A valid token is not enough: the linked employee must exist, be active and have the role.

        ``auth/me`` is the only exception: it returns just the caller's own identity, so the
        Reflex can explain an inactive employee instead of showing a generic 403.
        """
        identity_only = {"api/authentication/auth/me_GET.xs"}
        checked = 0
        for path in (XANO / "api").rglob("*.xs"):
            content = path.read_text(encoding="utf-8")
            relative = path.relative_to(XANO).as_posix()
            if relative in identity_only or not re.search(r'^\s*auth = "user"', content, re.MULTILINE):
                continue
            checked += 1
            with self.subTest(path=relative):
                self.assertIn('function.run "Quick Start/enforce_role"', content)
        self.assertGreater(checked, 70)

    def test_event_logs_never_store_whole_records(self):
        for path in (XANO / "api").rglob("*.xs"):
            content = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(XANO).as_posix()):
                self.assertIsNone(re.search(r"metadata:\s*\$user\d*\s*$", content, re.MULTILINE))

    def test_signup_does_not_issue_tokens_for_other_users(self):
        content = self.read("api/authentication/auth/signup_POST.xs")
        self.assertNotIn("security.create_auth_token", content)
        self.assertNotIn("authToken", content)
        self.assertIn("email email filters=trim|lower", content)
        self.assertIn("text password filters=min:8", content)
        self.assertIn("$employee.ativo != false", content)
        self.assertIn("$employee_has_user", content)

    def test_role_denial_answers_403_not_a_200_with_the_error(self):
        # Audit 2026-10-27: Xano answers a throw with HTTP 200; only a precondition gives 403.
        content = self.read("function/quick_start/enforce_role.xs")
        self.assertNotRegex(content, r"(?m)^\s*throw\s*\{")
        # The role precondition alone (from its condition to its error type), so a branch elsewhere
        # in the file cannot satisfy the check. Each branch keeps a profile out of a 403 lockout.
        bloco = re.search(r'precondition \(\s*\$user\.role == "admin"(.*?)\)\s*\{\s*error_type = "(\w+)"', content, re.DOTALL)
        self.assertIsNotNone(bloco)
        self.assertEqual(bloco.group(2), "accessdenied")
        for ramo in (
            '$input.required_role == "ALL"',
            '($input.required_role == "GERENTE" && $employee.tipo == "GERENTE")',
            '($input.required_role == "VENDEDOR" && ($employee.tipo == "GERENTE" || $employee.tipo == "VENDEDOR"))',
            '($input.required_role == "MECANICO" && ($employee.tipo == "GERENTE" || $employee.tipo == "MECANICO"))',
        ):
            with self.subTest(ramo=ramo):
                self.assertIn(ramo, bloco.group(1))

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
