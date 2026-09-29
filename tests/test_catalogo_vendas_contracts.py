from pathlib import Path
import re
import unittest


XANO = Path(__file__).parents[1] / "xano"
API = "api/harley"


def read(relative_path):
    return (XANO / relative_path).read_text(encoding="utf-8")


class CatalogoContractTests(unittest.TestCase):
    def test_model_table(self):
        content = read("table/modelos_moto.xs")
        for declaration in (
            'values = ["TOURING", "CRUISER", "ADVENTURE", "SPORT"]',
            "decimal preco_base filters=min:0.01",
            "json? variacoes_cor?",
            "bool? destaque?=false",
            "bool? ativo?=true",
        ):
            with self.subTest(declaration=declaration):
                self.assertIn(declaration, content)
        self.assertRegex(content, r'type: "btree\|unique", field: \[\{name: "nome_modelo"\}\]')

    def test_public_endpoints_need_no_session_and_share_the_showroom_projection(self):
        for relative_path in (f"{API}/catalogo_GET.xs", f"{API}/catalogo/catalogo_id_GET.xs"):
            with self.subTest(path=relative_path):
                content = read(relative_path)
                self.assertIsNone(re.search(r'^\s*auth = "user"', content, re.M))
                self.assertNotIn("enforce_role", content)
                self.assertIn('function.run "Catalogo/vitrine"', content)
                self.assertNotRegex(content, r"db\.(add|edit|patch|del) ")
        self.assertIn('error_type = "notfound"', read(f"{API}/catalogo/catalogo_id_GET.xs"))

    def test_showroom_projection_exposes_only_public_fields(self):
        content = read("function/catalogo/vitrine.xs")
        self.assertIn("$db.modelos_moto.ativo != false", content)
        self.assertIn('$db.motos.status == "DISPONIVEL"', content)
        # One query for all units, aggregated per model (no N+1).
        self.assertEqual(content.count("db.query motos"), 1)
        card = content[content.index("var.update $card"):content.index("var.update $vitrine")]
        fields = set(re.findall(r"^\s+(\w+)\s*:", card, re.M))
        self.assertEqual(
            fields,
            {
                "id",
                "nome_modelo",
                "familia",
                "descricao",
                "imagem_principal",
                "variacoes_cor",
                "destaque",
                "preco_a_partir",
                "disponiveis",
            },
        )
        for internal in ("chassi", "clientes_id", "id_vendedor_reserva", "historico"):
            with self.subTest(field=internal):
                self.assertNotIn(internal, card)
        self.assertIn("preco_a_partir  : $menor_preco ?? $modelo.preco_base", card)

    def test_model_management_is_manager_only_with_explicit_validated_inputs(self):
        for relative_path in (
            f"{API}/modelos_moto_GET.xs",
            f"{API}/modelos_moto_POST.xs",
            f"{API}/modelos_moto/modelos_moto_id_PATCH.xs",
        ):
            with self.subTest(path=relative_path):
                content = read(relative_path)
                self.assertIn('required_role: "GERENTE"', content)
                self.assertNotIn("dblink", content)
        for relative_path in (f"{API}/modelos_moto_POST.xs", f"{API}/modelos_moto/modelos_moto_id_PATCH.xs"):
            with self.subTest(path=relative_path):
                content = read(relative_path)
                self.assertIn('startsWith:"https://"', content)
                self.assertIn('pattern:"^#[0-9A-Fa-f]{6}$"', content)
                self.assertIn("<= 12", content)
                self.assertIn("Já existe um modelo com esse nome.", content)


class VendasContractTests(unittest.TestCase):
    def transaction(self, content):
        return content[content.index("db.transaction {"):]

    def test_unit_schema_is_additive_and_chassi_unique(self):
        content = read("table/motos.xs")
        for declaration in (
            "int? id_modelo?",
            "text? chassi? filters=trim|upper",
            "decimal? preco_venda? filters=min:0.01",
            "enum? status?=DISPONIVEL",
            'values = ["DISPONIVEL", "RESERVADA", "VENDIDA"]',
            "int? id_vendedor_reserva?",
            "timestamp? reservada_ate?",
            "int? versao_status? filters=min:0",
        ):
            with self.subTest(declaration=declaration):
                self.assertIn(declaration, content)
        self.assertRegex(content, r'type: "btree\|unique", field: \[\{name: "chassi"\}\]')
        self.assertIn('guid = "7HTEhAwc3Lhjg19mElJ3FM0Rcdo"', content)

    def test_status_history_serializes_transitions_by_version(self):
        content = read("table/historico_status_moto.xs")
        self.assertRegex(
            content,
            r'type : "btree\|unique"\s*field: \[\{name: "id_moto"\}, \{name: "versao_anterior"\}\]',
        )
        function = read("function/vendas/transicionar_moto.xs")
        self.assertIn('($moto.status ?? "DISPONIVEL") == $input.status_esperado', function)
        self.assertLess(function.index("db.add historico_status_moto"), function.index("db.patch motos"))
        self.assertIn("versao_anterior: $versao", function)
        self.assertIn("versao_status      : $versao + 1", function)

    def test_reservation_takes_seller_and_expiry_from_the_server(self):
        content = read(f"{API}/motos/motos_id_reserva_POST.xs")
        self.assertIn('query "motos/{motos_id}/reserva" verb=POST', content)
        self.assertIn('required_role: "VENDEDOR"', content)
        self.assertIn("int? dias_validade? filters=min:1|max:30", content)
        self.assertIn("($input.dias_validade ?? 7) * 86400", content)
        self.assertIn("Esta moto não está disponível para reserva.", content)
        self.assertIn("$cliente.ativo != false", content)
        transaction = self.transaction(content)
        self.assertIn('function.run "Vendas/transicionar_moto"', transaction)
        self.assertIn("id_vendedor_reserva: $auth_user.id_funcionario", transaction)
        self.assertIn('status_esperado    : "DISPONIVEL"', transaction)
        self.assertIn("try_catch {", content)
        for untrusted in ("$input.id_vendedor_reserva", "$input.reservada_ate", "$input.status"):
            with self.subTest(field=untrusted):
                self.assertNotIn(untrusted, content)

    def test_cancellation_rule_and_mandatory_reason(self):
        content = read(f"{API}/motos/motos_id_reserva_cancelar_POST.xs")
        self.assertIn('query "motos/{motos_id}/reserva/cancelar" verb=POST', content)
        self.assertIn("text motivo filters=trim|min:1|max:500", content)
        self.assertIn(
            '$role_check.tipo == "GERENTE" || $moto.id_vendedor_reserva == $auth_user.id_funcionario || $vencida',
            content,
        )
        self.assertIn('error_type = "accessdenied"', content)
        self.assertIn('status_esperado: "RESERVADA"', self.transaction(content))

    def test_unit_writes_are_manager_only_explicit_and_never_touch_status(self):
        for relative_path in (f"{API}/motos_POST.xs", f"{API}/motos/motos_id_PATCH.xs"):
            with self.subTest(path=relative_path):
                content = read(relative_path)
                inputs = content[content.index("input {"):content.index("stack {")]
                self.assertIn('required_role: "GERENTE"', content)
                self.assertNotIn("dblink", content)
                self.assertIn('pattern:"^[A-HJ-NPR-Z0-9]{17}$"', inputs)
                for forbidden in ("status", "clientes_id", "id_vendedor_reserva", "reservada_ate"):
                    self.assertNotIn(forbidden, inputs)
                self.assertIn("db.query motos_clientes", content)
                self.assertIn("Este chassi já está cadastrado.", content)
        post = read(f"{API}/motos_POST.xs")
        self.assertIn('status       : "DISPONIVEL"', post)
        self.assertIn("db.add historico_status_moto", self.transaction(post))

    def test_generic_put_is_blocked_and_reads_are_for_sellers(self):
        put = read(f"{API}/motos/motos_id_PUT.xs")
        self.assertIn("precondition (false)", put)
        self.assertNotRegex(put, r"db\.(add|edit|patch|del) ")
        for relative_path in (f"{API}/motos_GET.xs", f"{API}/motos/motos_id_GET.xs"):
            with self.subTest(path=relative_path):
                self.assertIn('required_role: "VENDEDOR"', read(relative_path))
        self.assertIn("$db.motos.status ==? $input.status", read(f"{API}/motos_GET.xs"))

    def test_sample_data_is_idempotent_and_uses_neutral_https_placeholders(self):
        content = read("function/catalogo/seed_exemplo.xs")
        self.assertIn("if (!$ja_populado)", content)
        urls = re.findall(r'"(https?://[^"]+)"', content)
        self.assertTrue(urls)
        self.assertTrue(all(url.startswith("https://placehold.co/") for url in urls))
        self.assertEqual(
            set(re.findall(r'familia\s*: "(\w+)"', content)),
            {"TOURING", "CRUISER", "ADVENTURE", "SPORT"},
        )


if __name__ == "__main__":
    unittest.main()
