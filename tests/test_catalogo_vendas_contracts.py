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
            "image[1:10]? galeria?",
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
                self.assertIsNone(re.search(r'^\s*auth = "user"', content, re.MULTILINE))
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
        fields = set(re.findall(r"^\s+(\w+)\s*:", card, re.MULTILINE))
        self.assertEqual(
            fields,
            {
                "id",
                "nome_modelo",
                "familia",
                "descricao",
                "imagem_principal",
                "galeria",
                "variacoes_cor",
                "destaque",
                "preco_a_partir",
                "disponiveis",
            },
        )
        # Change 17: the public gallery is only the file paths, never the stored file objects.
        self.assertRegex(card, r"galeria\s*:\s*\(\$modelo\.galeria \?\? \[\]\)\|map:\$\$\.path")
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

    def test_stock_list_joins_names_in_one_query(self):
        # Change 16: no whole-table reads and no field access on a missing model, client or seller.
        content = read(f"{API}/motos_GET.xs")
        self.assertEqual(re.findall(r"db\.query (\w+)", content), ["motos"])
        self.assertNotIn("|find:", content)
        # Left joins keep units without a model, client or seller; an inner join would hide them.
        self.assertEqual(len(re.findall(r'type\s*:\s*"left"', content)), 3)
        for join in ("$db.motos.id_modelo == $db.modelos_moto.id", "$db.motos.clientes_id == $db.clientes.id",
                     "$db.motos.id_vendedor_reserva == $db.funcionarios.id"):
            with self.subTest(join=join):
                self.assertIn(join, content)
        eval_block = re.search(r"eval = \{(.*?)\}", content, re.DOTALL).group(1)
        self.assertEqual(
            set(re.findall(r"(\w+)\s*:", eval_block)),
            {"nome_modelo", "imagem_principal", "familia", "variacoes_cor", "nome_cliente", "nome_vendedor"},
        )

    def test_unit_detail_sends_the_model_gallery_as_paths(self):
        # Change 17: the /vendas carousel reads the gallery of the unit's model.
        content = read("function/vendas/detalhe_moto.xs")
        self.assertIn('"imagem_principal", "galeria"]', content)
        self.assertIn('|set:"galeria":(($modelo.galeria ?? [])|map:$$.path)', content)

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


class VendaContractTests(unittest.TestCase):
    def test_sale_endpoint_is_for_sellers_and_takes_the_employee_from_the_session(self):
        content = read(f"{API}/vender_moto_POST.xs")
        self.assertIn("query vender_moto verb=POST", content)
        self.assertIn('api_group = "HARLEY"', content)
        self.assertIn('auth = "user"', content)
        self.assertIn('required_role: "VENDEDOR"', content)
        self.assertIn("id_funcionario: $auth_user.id_funcionario", content)
        self.assertNotIn("id_funcionario: $auth.id", content)
        self.assertIn('function.run "Vendas/vender_moto"', content)
        for field in ("id_moto", "id_cliente", "placa", "valor_venda", "observacao"):
            with self.subTest(field=field):
                self.assertIn(f"$input.{field}", content)

    def test_sale_is_atomic_and_reuses_the_versioned_transition(self):
        content = read("function/vendas/vender_moto.xs")
        self.assertIn('function "Vendas/vender_moto"', content)
        transaction = content[content.index("db.transaction {"):]
        self.assertLess(transaction.index("db.add motos_clientes"), transaction.index("db.add transacoes"))
        self.assertIn('tipo_transacao : "MOTO"', transaction)
        self.assertIn('function.run "Vendas/transicionar_moto"', transaction)
        self.assertIn('status_novo   : "VENDIDA"', transaction)
        self.assertIn("try_catch {", content)
        for rule in (
            "Esta moto já foi vendida.",
            "Esta moto está reservada para outro cliente.",
            "Cliente inativo ou inexistente.",
            "Chassi já cadastrado em uma moto de cliente.",
            "Placa já cadastrada em uma moto de cliente.",
            "A moto foi alterada por outro usuário. Atualize e tente novamente.",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, content)

    def test_plate_is_optional_and_checked_only_when_informed(self):
        for relative_path in (f"{API}/vender_moto_POST.xs", "function/vendas/vender_moto.xs"):
            with self.subTest(path=relative_path):
                self.assertIn("text? placa? filters=trim|upper", read(relative_path))
        content = read("function/vendas/vender_moto.xs")
        # A combined "placa == x || chassi == y" query would match every bike without a plate.
        self.assertNotRegex(content, r"motos_clientes\.placa == \$input\.placa \|\|")
        conditional = content[content.index('if (($input.placa ?? "") != "")'):content.index("$nome_modelo {")]
        self.assertIn("$db.motos_clientes.placa == $placa", conditional)
        self.assertIn("placa     : $placa", content)
        table = read("table/motos_clientes.xs")
        self.assertIn("text? placa? filters=trim", table)
        self.assertRegex(table, r'type: "btree\|unique", field: \[\{name: "placa"\}\]')

    def test_customer_bike_gets_the_commercial_model_name(self):
        content = read("function/vendas/vender_moto.xs")
        self.assertIn('"id_modelo"', content)
        self.assertIn("db.get modelos_moto", content)
        self.assertIn("value = $modelo.nome_modelo", content)
        self.assertIn("modelo    : $nome_modelo", content)

    def test_functions_called_by_endpoints_exist(self):
        defined = {
            match
            for path in (XANO / "function").rglob("*.xs")
            for match in re.findall(r'^function "([^"]+)"', path.read_text(encoding="utf-8"), re.MULTILINE)
        }
        for path in (XANO / "api").rglob("*.xs"):
            for called in re.findall(r'function\.run "([^"]+)"', path.read_text(encoding="utf-8")):
                with self.subTest(path=path.relative_to(XANO).as_posix(), function=called):
                    self.assertIn(called, defined)


if __name__ == "__main__":
    unittest.main()
