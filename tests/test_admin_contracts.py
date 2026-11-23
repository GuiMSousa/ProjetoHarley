"""Change 18: static contracts of the /admin endpoints, of the rules /admin shows and of the partial PATCH."""

import re
import unittest
from pathlib import Path

from Projeto_HarleyStore.services.admin import PARAMETROS_SISTEMA

XANO = Path(__file__).parents[1] / "xano"
ADMIN = "api/harley/admin"


def read(relative_path: str) -> str:
    return (XANO / relative_path).read_text(encoding="utf-8")


def code_of(content: str) -> str:
    """The file without comment lines, so a comment never satisfies or breaks a contract."""
    return "\n".join(line for line in content.splitlines() if not line.strip().startswith("//"))


def stack_of(content: str) -> str:
    return content[content.index("stack {") :]


class AdminEndpointContractTests(unittest.TestCase):
    ENDPOINTS = ("usuarios_GET.xs", "usuarios_id_senha_POST.xs", "eventos_GET.xs")

    def test_manager_role_is_the_first_step_of_every_endpoint(self):
        for name in self.ENDPOINTS:
            with self.subTest(endpoint=name):
                stack = stack_of(code_of(read(f"{ADMIN}/{name}")))
                first = re.search(r"(function\.run \"[^\"]+\"|\bdb\.\w+|\bprecondition\b|\bconditional\b|\bvar\b)", stack)
                self.assertEqual(first.group(1), 'function.run "Quick Start/enforce_role"')
                self.assertIn('required_role: "GERENTE"', stack[: stack.index("} as $role_check")])
                self.assertIn('auth = "user"', read(f"{ADMIN}/{name}"))

    def test_users_list_never_carries_secrets(self):
        content = code_of(read(f"{ADMIN}/usuarios_GET.xs"))
        self.assertNotIn("password", content)
        # Rows are built from an explicit whitelist, not returned as the raw user records.
        self.assertIn("response = $lista", content)
        whitelist = re.search(r"var\.update \$linha \{\s*value = \{(.*?)\}\s*\}", content, re.DOTALL).group(1)
        fields = re.findall(r"^\s*(\w+)\s*:", whitelist, re.MULTILINE)
        self.assertEqual(
            fields,
            ["id", "name", "email", "role", "created_at", "id_funcionario", "nome_funcionario", "tipo", "cargo", "ativo"],
        )
        self.assertIn('type : "left"', content)
        self.assertEqual(content.count("db.query"), 1)  # one query, no N+1

    def test_password_reset_checks_everything_before_writing_and_never_returns_the_password(self):
        content = code_of(read(f"{ADMIN}/usuarios_id_senha_POST.xs"))
        write = content.index("db.edit user")
        for check in (
            "precondition ($alvo != null)",
            "precondition ($input.usuarios_id != $auth.id)",
            'precondition ($alvo.role != "admin")',
            'precondition ($tipo_alvo != "GERENTE")',
            "precondition ($input.password == $input.confirm_password)",
        ):
            with self.subTest(check=check):
                self.assertLess(content.index(check), write)
        # Another manager's account is refused (review M1); the lookup runs only with an id, and the
        # type is read only from a record that exists.
        steps = " ".join(content.split())
        self.assertIn(
            "conditional { if ($alvo.id_funcionario != null) { db.get funcionarios { field_name = \"id\" "
            "field_value = $alvo.id_funcionario output = [\"id\", \"tipo\"] } as $funcionario_alvo "
            "conditional { if ($funcionario_alvo != null) { var.update $tipo_alvo { value = $funcionario_alvo.tipo } } } } }",
            steps,
        )
        self.assertEqual(content.count("$funcionario_alvo."), 1)
        # Null guard first (lesson of Oficina/detalhe_os): no field of $alvo before the check.
        self.assertLess(content.index("precondition ($alvo != null)"), content.index("$alvo."))
        self.assertIn("text password filters=min:8", content)
        self.assertNotIn("password filters=trim", content)
        self.assertIn("data = {password: $input.password}", content)
        response = content[content.index("response =") :]
        self.assertEqual(response.splitlines()[0], "response = {id: $alvo.id, name: $alvo.name, email: $alvo.email}")
        log = content[content.index('function.run "Quick Start/log_event"') :]
        self.assertIn('action  : "admin_reset_password"', log)
        metadata = re.search(r"metadata: \{(.*?)\}", log).group(1)
        self.assertEqual(re.findall(r"(\w+):", metadata), ["id_usuario", "id_funcionario", "id_gerente"])
        self.assertNotIn("password", metadata)

    def test_audit_is_paged_newest_first_with_optional_filters(self):
        content = code_of(read(f"{ADMIN}/eventos_GET.xs"))
        self.assertIn("paging: {page: $pagina, per_page: 25, totals: true}", content)
        self.assertIn('sort = {created_at: "desc"}', content)
        self.assertIn(
            "where = $db.event_log.action ==? $acao && $db.event_log.created_at >=? $input.data_inicio"
            " && $db.event_log.created_at <=? $input.data_fim",
            content,
        )
        self.assertIn("precondition (($input.data_fim - $input.data_inicio) <= 31622400000)", content)
        self.assertIn("nome_usuario    : $db.usuario.name", content)
        self.assertNotIn("password", content)

    def test_no_filter_takes_a_parenthesized_argument(self):
        # Lesson of GET entrada_mercadoria (2026-11-18): get:("e" ~ $x) passed the validator and
        # failed live with HTTP 500 "Invalid expression".
        for name in self.ENDPOINTS:
            with self.subTest(endpoint=name):
                self.assertNotIn(":(", code_of(read(f"{ADMIN}/{name}")))


class SystemRulesSyncTests(unittest.TestCase):
    """The /admin panel shows these rules; each must equal what Xano applies."""

    def applied(self) -> dict[str, int]:
        reserva = code_of(read("api/harley/motos/motos_id_reserva_POST.xs"))
        balcao = code_of(read("api/harley/balcao/vendas_POST.xs"))
        entrada = code_of(read("api/harley/entrada_mercadoria_POST.xs"))
        resumo = code_of(read("function/financeiro/resumo_operacoes.xs"))
        periodo_ms = int(re.search(r"precondition \(\(\$input\.fim - \$input\.inicio\) <= (\d+)\)", resumo).group(1))
        return {
            "reserva_padrao": int(re.search(r"\$input\.dias_validade \?\? (\d+)\) \* 86400", reserva).group(1)),
            "reserva_maximo": int(re.search(r"int\? dias_validade\? filters=min:1\|max:(\d+)", reserva).group(1)),
            "itens_balcao": int(re.search(r"precondition \(\(\$input\.itens\|count\) <= (\d+)\)", balcao).group(1)),
            "itens_entrada": int(re.search(r"precondition \(\(\$input\.itens\|count\) <= (\d+)\)", entrada).group(1)),
            "periodo_resumo": periodo_ms // 86_400_000,
            "operacoes_resumo": int(re.search(r"\|slice:0:(\d+)", resumo).group(1)),
        }

    def test_every_rule_shown_equals_the_rule_xano_applies(self):
        applied = self.applied()
        shown = {regra["chave"]: regra["valor"] for regra in PARAMETROS_SISTEMA}
        self.assertEqual(set(shown), set(applied))
        for chave, valor in applied.items():
            with self.subTest(regra=chave):
                self.assertEqual(shown[chave], valor)

    def test_summary_flags_truncation_at_the_same_limit(self):
        resumo = code_of(read("function/financeiro/resumo_operacoes.xs"))
        limite = re.search(r"truncado\s*: \$total_operacoes > (\d+)", resumo).group(1)
        self.assertEqual(int(limite), self.applied()["operacoes_resumo"])


PARTIAL_PATCHES = {
    "clientes/clientes_id_PATCH.xs": ("nome_cliente", "cpf_cnpj", "telefone", "email", "endereco", "ativo"),
    "fornecedores/fornecedores_id_PATCH.xs": ("nome_fornecedor", "cnpj", "contato", "ativo"),
    "funcionarios/funcionarios_id_PATCH.xs": ("nome_funcionario", "cargo", "tipo", "contato", "ativo"),
    "motos_clientes/motos_clientes_id_PATCH.xs": ("id_cliente", "modelo", "placa", "chassi", "ativo"),
    "produtos/produtos_id_PATCH.xs": ("codigo", "nome_produto", "descricao", "categoria", "preco_venda", "ativo"),
}


class PartialPatchContractTests(unittest.TestCase):
    """2026-11-23, live: with `dblink`, PATCH funcionarios/{id} {"contato": ...} answered 400
    "Missing param: nome_funcionario", so "Desativar" ({"ativo": false}) failed in every register."""

    def test_register_patches_take_any_subset_of_their_fields(self):
        for path, fields in PARTIAL_PATCHES.items():
            with self.subTest(endpoint=path):
                content = code_of(read(f"api/harley/{path}"))
                self.assertNotIn("dblink", content)
                inputs = content[content.index("input {") : content.index("stack {")]
                declared = re.findall(r"^\s{4}(?:\w+)(\??) (\w+)(\??)", inputs, re.MULTILINE)
                body = [(nullable, name, optional) for nullable, name, optional in declared if not name.endswith("_id")]
                self.assertEqual([name for _, name, _ in body], list(fields))
                for nullable, name, optional in body:
                    self.assertEqual((nullable, optional), ("?", "?"), f"{name} must be optional")
                self.assertIn("data = `$input|pick:($raw_input|keys)`", content)

    def test_product_patch_still_cannot_touch_the_stock_balance(self):
        content = code_of(read("api/harley/produtos/produtos_id_PATCH.xs"))
        inputs = content[content.index("input {") : content.index("stack {")]
        self.assertNotIn("estoque_qtd", inputs)
        self.assertNotIn("versao_estoque", inputs)
        self.assertIn('|unset:"estoque_qtd"|unset:"versao_estoque"', content)


if __name__ == "__main__":
    unittest.main()
