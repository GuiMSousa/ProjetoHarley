"""Integration tests against a real Xano workspace.

The suite is skipped unless ``XANO_API_BASE_URL`` is configured in the
environment or in the project ``.env`` file, so the offline suite stays green.

Settings (environment variables take precedence over ``.env``):

- ``XANO_API_BASE_URL`` / ``XANO_AUTH_API_BASE_URL``: API group base URLs;
- ``XANO_TEST_<PERFIL>_EMAIL`` / ``XANO_TEST_<PERFIL>_PASSWORD`` for
  ``GERENTE``, ``VENDEDOR`` and ``MECANICO`` (each profile is optional);
- ``XANO_TEST_ALLOW_WRITES=true`` enables scenarios that persist data. Goods
  receipts, service orders and stock movements are immutable, so those
  records stay in the database: point the suite at a test branch or workspace.
  Orders opened by the tests are cancelled at the end, returning their parts.
- ``XANO_TEST_CONCURRENCY=true`` (with writes) runs the race scenarios of the
  stock ledger and the order lock; they need two free customer bikes.
"""

from __future__ import annotations

import os
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from Projeto_HarleyStore.services.entradas import EntradaMercadoriaCreate
from Projeto_HarleyStore.services.ordens_servico import (
    ItemOSCreate,
    OrdemServicoCreate,
    TransicaoStatusOS,
)
from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoClient,
    XanoPermissionError,
    XanoValidationError,
)


ROOT = Path(__file__).parents[1]
PLACEHOLDER_URL = "https://seu-workspace.xano.io/api:seu-grupo"
ROLES = ("GERENTE", "VENDEDOR", "MECANICO")
NONEXISTENT_ID = 2_000_000_000


def load_env_file(path: Path) -> dict[str, str]:
    """Parse simple ``KEY=VALUE`` lines without adding a dotenv dependency."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def live_settings() -> dict[str, str]:
    settings = load_env_file(ROOT / ".env")
    settings.update(
        {key: value for key, value in os.environ.items() if key.startswith("XANO_")}
    )
    return settings


SETTINGS = live_settings()
BASE_URL = SETTINGS.get("XANO_API_BASE_URL", "").strip()
LIVE = bool(BASE_URL) and BASE_URL != PLACEHOLDER_URL
ALLOW_WRITES = SETTINGS.get("XANO_TEST_ALLOW_WRITES", "").lower() in {"1", "true", "yes"}
CONCURRENCY = ALLOW_WRITES and SETTINGS.get("XANO_TEST_CONCURRENCY", "").lower() in {
    "1",
    "true",
    "yes",
}


@unittest.skipUnless(LIVE, "XANO_API_BASE_URL não configurada: integração ignorada.")
class XanoLiveTestCase(unittest.TestCase):
    tokens: dict[str, str] = {}

    @classmethod
    def setUpClass(cls):
        environment = {
            key: value
            for key, value in SETTINGS.items()
            if key in {"XANO_API_BASE_URL", "XANO_AUTH_API_BASE_URL"}
        }
        cls._environment = patch.dict(os.environ, environment)
        cls._environment.start()
        cls.tokens = {}

    @classmethod
    def tearDownClass(cls):
        cls._environment.stop()

    def token_for(self, role: str) -> str:
        email = SETTINGS.get(f"XANO_TEST_{role}_EMAIL")
        password = SETTINGS.get(f"XANO_TEST_{role}_PASSWORD")
        if not email or not password:
            self.skipTest(f"Credenciais de teste de {role} não configuradas.")
        if role not in self.tokens:
            with XanoClient() as client:
                self.tokens[role] = client.login(email, password)["authToken"]
        return self.tokens[role]

    def client_for(self, role: str) -> XanoClient:
        return XanoClient(token=self.token_for(role))


class XanoLiveReadTests(XanoLiveTestCase):
    def test_each_profile_logs_in_with_linked_active_employee(self):
        for role in ROLES:
            with self.subTest(role=role), self.client_for(role) as client:
                identity = client.current_user()
                self.assertIsNotNone(identity.funcionario)
                self.assertEqual(identity.funcionario.tipo, role)
                self.assertTrue(identity.funcionario.ativo)
                self.assertNotIn("password", identity.user.model_dump())

    def test_every_profile_reads_shared_resources(self):
        for role in ROLES:
            with self.subTest(role=role), self.client_for(role) as client:
                client.list_clientes()
                client.list_motos_clientes()
                client.list_produtos()
                client.list_entradas()

    def test_suppliers_and_employees_are_manager_only(self):
        for role in ("VENDEDOR", "MECANICO"):
            with self.subTest(role=role), self.client_for(role) as client:
                with self.assertRaises(XanoPermissionError):
                    client.list_fornecedores()
                with self.assertRaises(XanoPermissionError):
                    client.list_funcionarios()
        with self.client_for("GERENTE") as client:
            client.list_fornecedores()
            client.list_funcionarios()

    def test_direct_receipt_mutations_are_blocked(self):
        with self.client_for("GERENTE") as client:
            with self.assertRaises(XanoPermissionError):
                client.patch("entrada_mercadoria/1", json={"valor_total": 1})
            with self.assertRaises(XanoPermissionError):
                client.delete("entrada_mercadoria/1")
            with self.assertRaises(XanoPermissionError):
                client.post("itens_compra_estoque", json={})

    def test_non_managers_cannot_register_receipts(self):
        payload = EntradaMercadoriaCreate(
            id_fornecedor=1,
            numero_documento=f"IT-NEG-{uuid.uuid4().hex[:8]}",
            itens=[{"id_produto": 1, "quantidade": 1, "valor_unitario": Decimal("1")}],
        )
        for role in ("VENDEDOR", "MECANICO"):
            with self.subTest(role=role), self.client_for(role) as client:
                with self.assertRaises(XanoPermissionError):
                    client.registrar_entrada(payload)

    def test_public_surface_is_closed(self):
        with XanoClient() as client:
            auth_url = client._auth_base_url
            with self.assertRaises(XanoAuthenticationError):
                client.request(
                    "POST",
                    "message/send_welcome_email",
                    json={"user_id": 1},
                    authenticated=False,
                    base_url=auth_url,
                )
            for method, path in (
                ("GET", "reset/request-reset-link"),
                ("POST", "reset/magic-link-login"),
            ):
                with self.subTest(path=path), self.assertRaises(XanoPermissionError):
                    client.request(method, path, authenticated=False, base_url=auth_url)


class XanoLiveServiceOrderReadTests(XanoLiveTestCase):
    def test_every_profile_reads_the_workshop(self):
        for role in ROLES:
            with self.subTest(role=role), self.client_for(role) as client:
                ordens = client.list_ordens_servico()
                if ordens:
                    client.get_ordem_servico(ordens[0].id)
                client.list_ordens_servico(status="ABERTA")

    def test_salesperson_cannot_operate_orders(self):
        with self.client_for("VENDEDOR") as client:
            with self.assertRaises(XanoPermissionError):
                client.list_mecanicos()
            with self.assertRaises(XanoPermissionError):
                client.post(
                    "ordens_servico",
                    json={
                        "id_moto_cliente": 1,
                        "tipo_servico": "CORRETIVA",
                        "descricao_problema": "Teste de permissão",
                    },
                )
            with self.assertRaises(XanoPermissionError):
                client.post(
                    "ordens_servico/1/status",
                    json={"status_atual": "ABERTA", "status_novo": "EM_ANDAMENTO"},
                )

    def test_generic_order_mutations_are_blocked(self):
        with self.client_for("GERENTE") as client:
            with self.assertRaises(XanoPermissionError):
                client.patch("ordens_servico/1", json={"status": "CONCLUIDA"})
            with self.assertRaises(XanoPermissionError):
                client.delete("ordens_servico/1")
            with self.assertRaises(XanoPermissionError):
                client.post("itens_ordem_servico", json={})

    def test_salesperson_cannot_change_items(self):
        with self.client_for("VENDEDOR") as client:
            with self.assertRaises(XanoPermissionError):
                client.adicionar_item_ordem_servico(
                    1, ItemOSCreate(tipo_item="SERVICO", descricao="Teste", quantidade=1, valor_unitario=1)
                )
            with self.assertRaises(XanoPermissionError):
                client.remover_item_ordem_servico(1, 1)


@unittest.skipUnless(ALLOW_WRITES, "XANO_TEST_ALLOW_WRITES desativado: cenários de escrita ignorados.")
class XanoLiveWriteTestCase(XanoLiveTestCase):
    """Helpers for scenarios that persist data; defines no tests of its own."""

    def free_bikes(self, client: XanoClient, count: int = 1):
        clientes_ativos = {cliente.id for cliente in client.list_clientes() if cliente.ativo}
        em_aberto = {
            ordem.id_moto_cliente
            for status in ("ABERTA", "EM_ANDAMENTO")
            for ordem in client.list_ordens_servico(status=status)
        }
        motos = [
            moto
            for moto in client.list_motos_clientes()
            if moto.ativo and moto.id_cliente in clientes_ativos and moto.id not in em_aberto
        ]
        if len(motos) < count:
            self.skipTest(
                f"São necessárias {count} moto(s) ativa(s) de cliente ativo sem OS em aberto."
            )
        return motos[:count]

    def free_bike(self, client: XanoClient):
        return self.free_bikes(client, 1)[0]

    def reference_data(self, client: XanoClient):
        supplier = next((item for item in client.list_fornecedores() if item.ativo), None)
        product = next((item for item in client.list_produtos() if item.ativo), None)
        if supplier is None or product is None:
            self.skipTest("É necessário ao menos um fornecedor e um produto ativos.")
        return supplier, product

    def stock_of(self, client: XanoClient, product_id: int) -> int:
        return next(item.estoque_qtd for item in client.list_produtos() if item.id == product_id)

    def restocked_products(self, client: XanoClient, count: int, quantity: int):
        """Active products with at least ``quantity`` units, restocked by a receipt."""
        supplier = next((item for item in client.list_fornecedores() if item.ativo), None)
        products = [item for item in client.list_produtos() if item.ativo][:count]
        if supplier is None or len(products) < count:
            self.skipTest(f"São necessários um fornecedor e {count} produto(s) ativo(s).")
        client.registrar_entrada(
            EntradaMercadoriaCreate(
                id_fornecedor=supplier.id,
                numero_documento=f"IT-OS-{uuid.uuid4().hex[:8]}",
                itens=[
                    {"id_produto": item.id, "quantidade": quantity, "valor_unitario": Decimal("1")}
                    for item in products
                ],
            )
        )
        return [
            item for item in client.list_produtos() if item.id in {p.id for p in products}
        ]

    def open_order(self, client: XanoClient, moto=None):
        moto = moto or self.free_bike(client)
        mecanicos = client.list_mecanicos()
        if not mecanicos:
            self.skipTest("É necessário ao menos um mecânico ativo.")
        return client.abrir_ordem_servico(
            OrdemServicoCreate(
                id_moto_cliente=moto.id,
                id_mecanico=mecanicos[0].id,
                tipo_servico="CORRETIVA",
                descricao_problema=f"Teste de integração {uuid.uuid4().hex[:6]}",
            )
        )

    def cancel_quietly(self, client: XanoClient, os_id: int) -> None:
        """Free the bike and return the parts; ignores orders already closed."""
        ordem = client.get_ordem_servico(os_id)
        if ordem.status in {"ABERTA", "EM_ANDAMENTO"}:
            client.transicionar_ordem_servico(
                os_id,
                TransicaoStatusOS(
                    status_atual=ordem.status,
                    status_novo="CANCELADA",
                    observacao="Limpeza do teste de integração",
                ),
            )


class XanoLiveServiceOrderWriteTests(XanoLiveWriteTestCase):
    def test_full_lifecycle_with_rejections(self):
        with self.client_for("GERENTE") as client:
            moto = self.free_bike(client)
            mecanicos = client.list_mecanicos()
            if not mecanicos:
                self.skipTest("É necessário ao menos um mecânico ativo.")
            me = client.current_user().funcionario

            ordem = client.abrir_ordem_servico(
                OrdemServicoCreate(
                    id_moto_cliente=moto.id,
                    id_mecanico=mecanicos[0].id,
                    tipo_servico="PREVENTIVA",
                    descricao_problema=f"Teste de integração {uuid.uuid4().hex[:6]}",
                    quilometragem=100,
                )
            )
            self.assertEqual(ordem.status, "ABERTA")
            self.assertEqual(ordem.id_funcionario, me.id)
            self.assertEqual(ordem.id_cliente, moto.id_cliente)
            self.assertEqual(len(ordem.historico), 1)

            with self.assertRaises(XanoValidationError):
                client.abrir_ordem_servico(
                    OrdemServicoCreate(
                        id_moto_cliente=moto.id,
                        id_mecanico=mecanicos[0].id,
                        tipo_servico="CORRETIVA",
                        descricao_problema="Segunda OS para a mesma moto",
                    )
                )
            with self.assertRaises(XanoValidationError):
                client.post(
                    f"ordens_servico/{ordem.id}/status",
                    json={"status_atual": "ABERTA", "status_novo": "CONCLUIDA"},
                )

            iniciada = client.transicionar_ordem_servico(
                ordem.id, TransicaoStatusOS(status_atual="ABERTA", status_novo="EM_ANDAMENTO")
            )
            self.assertEqual(iniciada.status, "EM_ANDAMENTO")
            self.assertIsNotNone(iniciada.data_inicio)

            with self.assertRaises(XanoValidationError):
                client.post(
                    f"ordens_servico/{ordem.id}/status",
                    json={"status_atual": "ABERTA", "status_novo": "CANCELADA", "observacao": "conflito"},
                )
            with self.assertRaises(XanoValidationError):
                client.post(
                    f"ordens_servico/{ordem.id}/status",
                    json={"status_atual": "EM_ANDAMENTO", "status_novo": "CANCELADA"},
                )

            concluida = client.transicionar_ordem_servico(
                ordem.id, TransicaoStatusOS(status_atual="EM_ANDAMENTO", status_novo="CONCLUIDA")
            )
            self.assertEqual(concluida.status, "CONCLUIDA")
            self.assertIsNotNone(concluida.data_encerramento)
            self.assertEqual(
                [evento.status_novo for evento in concluida.historico],
                ["ABERTA", "EM_ANDAMENTO", "CONCLUIDA"],
            )
            with self.assertRaises(XanoValidationError):
                client.post(
                    f"ordens_servico/{ordem.id}/status",
                    json={"status_atual": "CONCLUIDA", "status_novo": "ABERTA"},
                )


class XanoLiveReceiptWriteTests(XanoLiveWriteTestCase):
    def test_receipt_increments_stock_and_rejects_duplicate_document(self):
        with self.client_for("GERENTE") as client:
            supplier, product = self.reference_data(client)
            employee = client.current_user().funcionario
            before = self.stock_of(client, product.id)
            payload = EntradaMercadoriaCreate(
                id_fornecedor=supplier.id,
                numero_documento=f"IT-{uuid.uuid4().hex[:10]}",
                itens=[
                    {"id_produto": product.id, "quantidade": 2, "valor_unitario": Decimal("1.50")}
                ],
            )

            detail = client.registrar_entrada(payload)

            self.assertEqual(self.stock_of(client, product.id), before + 2)
            self.assertEqual(detail.valor_total, Decimal("3.00"))
            self.assertEqual(detail.id_funcionario, employee.id)
            self.assertEqual(detail.quantidade_itens, 1)
            with self.assertRaises(XanoValidationError):
                client.registrar_entrada(payload)
            self.assertEqual(self.stock_of(client, product.id), before + 2)

    def test_invalid_item_rolls_back_the_whole_receipt(self):
        with self.client_for("GERENTE") as client:
            supplier, product = self.reference_data(client)
            before = self.stock_of(client, product.id)
            document = f"IT-RB-{uuid.uuid4().hex[:8]}"
            payload = EntradaMercadoriaCreate(
                id_fornecedor=supplier.id,
                numero_documento=document,
                itens=[
                    {"id_produto": product.id, "quantidade": 1, "valor_unitario": Decimal("1")},
                    {"id_produto": NONEXISTENT_ID, "quantidade": 1, "valor_unitario": Decimal("1")},
                ],
            )

            with self.assertRaises(XanoValidationError):
                client.registrar_entrada(payload)

            self.assertEqual(self.stock_of(client, product.id), before)
            documents = {entrada.numero_documento for entrada in client.list_entradas()}
            self.assertNotIn(document, documents)


class XanoLiveServiceOrderItemWriteTests(XanoLiveWriteTestCase):
    def test_item_cycle_moves_stock_and_totals(self):
        with self.client_for("GERENTE") as client:
            (product,) = self.restocked_products(client, 1, 3)
            before = product.estoque_qtd
            ordem = self.open_order(client)
            try:
                detalhe = client.adicionar_item_ordem_servico(
                    ordem.id, ItemOSCreate(tipo_item="PECA", id_produto=product.id, quantidade=2)
                )
                (peca,) = detalhe.itens
                self.assertEqual(peca.valor_unitario, product.preco_venda)
                self.assertEqual(peca.valor_total_item, product.preco_venda * 2)
                self.assertTrue(peca.estoque_baixado)
                self.assertEqual(detalhe.valor_pecas, product.preco_venda * 2)
                self.assertEqual(self.stock_of(client, product.id), before - 2)

                for rejected in (
                    ItemOSCreate(tipo_item="PECA", id_produto=product.id, quantidade=1),
                    ItemOSCreate(tipo_item="PECA", id_produto=NONEXISTENT_ID, quantidade=1),
                ):
                    with self.subTest(rejected=rejected), self.assertRaises(XanoValidationError):
                        client.adicionar_item_ordem_servico(ordem.id, rejected)
                self.assertEqual(self.stock_of(client, product.id), before - 2)

                detalhe = client.adicionar_item_ordem_servico(
                    ordem.id,
                    ItemOSCreate(
                        tipo_item="SERVICO",
                        descricao="Mão de obra de teste",
                        quantidade=2,
                        valor_unitario=Decimal("50.00"),
                    ),
                )
                self.assertEqual(detalhe.valor_servicos, Decimal("100"))
                self.assertEqual(detalhe.valor_total, detalhe.valor_pecas + Decimal("100"))
                self.assertEqual(self.stock_of(client, product.id), before - 2)
                listed = next(o for o in client.list_ordens_servico() if o.id == ordem.id)
                self.assertEqual(listed.valor_total, detalhe.valor_total)

                servico = next(item for item in detalhe.itens if item.tipo_item == "SERVICO")
                detalhe = client.remover_item_ordem_servico(ordem.id, servico.id)
                self.assertEqual(detalhe.valor_servicos, Decimal("0"))
                self.assertEqual(self.stock_of(client, product.id), before - 2)

                detalhe = client.remover_item_ordem_servico(ordem.id, peca.id)
                self.assertEqual(detalhe.itens, [])
                self.assertEqual(detalhe.valor_total, Decimal("0"))
                self.assertEqual(self.stock_of(client, product.id), before)

                client.adicionar_item_ordem_servico(
                    ordem.id, ItemOSCreate(tipo_item="PECA", id_produto=product.id, quantidade=1)
                )
                client.transicionar_ordem_servico(
                    ordem.id, TransicaoStatusOS(status_atual="ABERTA", status_novo="EM_ANDAMENTO")
                )
                self.assertEqual(self.stock_of(client, product.id), before - 1)
                cancelada = client.transicionar_ordem_servico(
                    ordem.id,
                    TransicaoStatusOS(
                        status_atual="EM_ANDAMENTO", status_novo="CANCELADA", observacao="Teste"
                    ),
                )
                self.assertEqual(self.stock_of(client, product.id), before)
                self.assertEqual(len(cancelada.itens), 1)
                with self.assertRaises(XanoValidationError):
                    client.adicionar_item_ordem_servico(
                        ordem.id,
                        ItemOSCreate(tipo_item="PECA", id_produto=product.id, quantidade=1),
                    )
            finally:
                self.cancel_quietly(client, ordem.id)

    def test_insufficient_balance_is_rejected_without_effect(self):
        with self.client_for("MECANICO") as client:
            product = next((item for item in client.list_produtos() if item.ativo), None)
            if product is None:
                self.skipTest("É necessário ao menos um produto ativo.")
            before = product.estoque_qtd
            ordem = self.open_order(client)
            try:
                with self.assertRaises(XanoValidationError) as context:
                    client.adicionar_item_ordem_servico(
                        ordem.id,
                        ItemOSCreate(tipo_item="PECA", id_produto=product.id, quantidade=before + 1),
                    )
                self.assertIn("Saldo insuficiente", str(context.exception))
                self.assertEqual(self.stock_of(client, product.id), before)
                self.assertEqual(client.get_ordem_servico(ordem.id).itens, [])
            finally:
                self.cancel_quietly(client, ordem.id)

    def test_concluded_order_keeps_consumption_and_freezes_items(self):
        with self.client_for("GERENTE") as client:
            (product,) = self.restocked_products(client, 1, 1)
            before = product.estoque_qtd
            ordem = self.open_order(client)
            try:
                detalhe = client.adicionar_item_ordem_servico(
                    ordem.id, ItemOSCreate(tipo_item="PECA", id_produto=product.id, quantidade=1)
                )
                client.transicionar_ordem_servico(
                    ordem.id, TransicaoStatusOS(status_atual="ABERTA", status_novo="EM_ANDAMENTO")
                )
                client.transicionar_ordem_servico(
                    ordem.id, TransicaoStatusOS(status_atual="EM_ANDAMENTO", status_novo="CONCLUIDA")
                )
                self.assertEqual(self.stock_of(client, product.id), before - 1)
                with self.assertRaises(XanoValidationError):
                    client.remover_item_ordem_servico(ordem.id, detalhe.itens[0].id)
                with self.assertRaises(XanoValidationError):
                    client.adicionar_item_ordem_servico(
                        ordem.id,
                        ItemOSCreate(
                            tipo_item="SERVICO", descricao="Tarde demais", quantidade=1, valor_unitario=1
                        ),
                    )
                self.assertEqual(self.stock_of(client, product.id), before - 1)
            finally:
                self.cancel_quietly(client, ordem.id)


@unittest.skipUnless(
    CONCURRENCY, "XANO_TEST_CONCURRENCY desativado: cenários concorrentes ignorados."
)
class XanoLiveStockConcurrencyTests(XanoLiveWriteTestCase):
    """Race conditions of D6 (stock version) and D7 (order row lock)."""

    def race(self, *calls):
        """Run the calls at the same time, each with its own client; return results or errors."""
        token = self.token_for("GERENTE")
        barrier = threading.Barrier(len(calls))

        def run(call):
            with XanoClient(token=token) as client:
                barrier.wait()
                try:
                    return call(client)
                except XanoValidationError as error:
                    return error

        with ThreadPoolExecutor(max_workers=len(calls)) as pool:
            return list(pool.map(run, calls))

    def test_two_orders_competing_for_the_whole_balance(self):
        with self.client_for("GERENTE") as client:
            (product,) = self.restocked_products(client, 1, 1)
            saldo = product.estoque_qtd
            ordens = [self.open_order(client, moto) for moto in self.free_bikes(client, 2)]
            try:
                results = self.race(
                    *[
                        lambda c, os_id=ordem.id: c.adicionar_item_ordem_servico(
                            os_id,
                            ItemOSCreate(tipo_item="PECA", id_produto=product.id, quantidade=saldo),
                        )
                        for ordem in ordens
                    ]
                )
                errors = [result for result in results if isinstance(result, XanoValidationError)]
                self.assertEqual(len(errors), 1, results)
                self.assertEqual(self.stock_of(client, product.id), 0)
                self.assertEqual(
                    sum(len(client.get_ordem_servico(ordem.id).itens) for ordem in ordens), 1
                )
            finally:
                for ordem in ordens:
                    self.cancel_quietly(client, ordem.id)
            self.assertEqual(self.stock_of(client, product.id), saldo)

    def test_item_added_while_cancelling_never_leaves_stock_behind(self):
        with self.client_for("GERENTE") as client:
            (product,) = self.restocked_products(client, 1, 1)
            before = product.estoque_qtd
            ordem = self.open_order(client)
            try:
                self.race(
                    lambda c: c.transicionar_ordem_servico(
                        ordem.id,
                        TransicaoStatusOS(
                            status_atual="ABERTA", status_novo="CANCELADA", observacao="Corrida"
                        ),
                    ),
                    lambda c: c.adicionar_item_ordem_servico(
                        ordem.id, ItemOSCreate(tipo_item="PECA", id_produto=product.id, quantidade=1)
                    ),
                )
                self.assertEqual(client.get_ordem_servico(ordem.id).status, "CANCELADA")
                self.assertEqual(self.stock_of(client, product.id), before)
            finally:
                self.cancel_quietly(client, ordem.id)


if __name__ == "__main__":
    unittest.main()
