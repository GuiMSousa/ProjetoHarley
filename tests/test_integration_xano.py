"""Integration tests against a real Xano workspace (pytest marker ``integration``).

Opt-in only: a plain ``pytest`` run never calls Xano. Every test here is skipped, with
the reason shown by ``pytest -ra``, unless ``XANO_API_BASE_URL`` is configured AND the
run is explicitly enabled with ``XANO_TEST_ALLOW_WRITES=true`` (full suite) or
``XANO_TEST_LIVE=true`` (read-only scenarios). Without credentials, each profile's
tests are skipped individually.

Settings (environment variables take precedence over ``.env``):

- ``XANO_API_BASE_URL`` / ``XANO_AUTH_API_BASE_URL``: API group base URLs;
- ``XANO_TEST_<PERFIL>_EMAIL`` / ``XANO_TEST_<PERFIL>_PASSWORD`` for
  ``GERENTE``, ``VENDEDOR`` and ``MECANICO`` (each profile is optional);
- ``XANO_TEST_LIVE=true`` runs only the read-only scenarios (marker ``integration``);
- ``XANO_TEST_ALLOW_WRITES=true`` (marker ``writes``) enables scenarios that persist data. Goods
  receipts, service orders and stock movements are immutable, so those
  records stay in the database: point the suite at a test branch or workspace.
  Orders opened by the tests are cancelled at the end, returning their parts.
  Sales are final: the sold units, customer bikes and MOTO transactions stay.
- ``XANO_TEST_CONCURRENCY=true`` (with writes, marker ``concurrency``) runs the race scenarios of the
  stock ledger, the order lock, reservations and sales; the order races need
  two free customer bikes.
"""

from __future__ import annotations

import os
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

from Projeto_HarleyStore.services.balcao import ItemVendaBalcaoCreate, VendaBalcaoCreate
from Projeto_HarleyStore.services.catalogo import ModeloMotoCreate, ModeloMotoUpdate, VariacaoCor
from Projeto_HarleyStore.services.entradas import EntradaMercadoriaCreate
from Projeto_HarleyStore.services.financeiro import FUSO_LOJA, OPERACOES_LIMITE, PeriodoFinanceiro
from Projeto_HarleyStore.services.motos import (
    CancelamentoReservaMoto,
    MotoEstoqueCreate,
    ReservaMotoCreate,
    VendaMotoCreate,
)
from Projeto_HarleyStore.services.ordens_servico import (
    ItemOSCreate,
    OrdemServicoCreate,
    TransicaoStatusOS,
)
from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoClient,
    XanoNotFoundError,
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


def enabled(name: str) -> bool:
    return SETTINGS.get(name, "").strip().lower() in {"1", "true", "yes"}


SETTINGS = live_settings()
BASE_URL = SETTINGS.get("XANO_API_BASE_URL", "").strip()
CONFIGURED = bool(BASE_URL) and BASE_URL != PLACEHOLDER_URL
ALLOW_WRITES = enabled("XANO_TEST_ALLOW_WRITES")
# Writes imply live reads; XANO_TEST_LIVE alone enables the read-only scenarios.
LIVE = CONFIGURED and (ALLOW_WRITES or enabled("XANO_TEST_LIVE"))
CONCURRENCY = LIVE and ALLOW_WRITES and enabled("XANO_TEST_CONCURRENCY")
LIVE_SKIP_REASON = (
    "Integração real desativada: defina XANO_TEST_ALLOW_WRITES=true (ou XANO_TEST_LIVE=true "
    "para só leitura) e XANO_API_BASE_URL."
)


@unittest.skipUnless(LIVE, LIVE_SKIP_REASON)
class XanoLiveTestCase(unittest.TestCase):
    tokens: ClassVar[dict[str, str]] = {}  # shared by every live test: one login per role

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

    def test_physical_deletes_are_blocked(self):
        # A nonexistent id keeps the call harmless even against a workspace without the block.
        with self.client_for("GERENTE") as client:
            for resource in (
                "clientes",
                "motos_clientes",
                "produtos",
                "fornecedores",
                "funcionarios",
                "motos",
                "transacoes",
            ):
                with self.subTest(resource=resource), self.assertRaises(XanoPermissionError):
                    client.delete(f"{resource}/{NONEXISTENT_ID}")

    def test_password_change_requires_the_current_password(self):
        """The new password sent is the current one, so no scenario changes the credentials."""
        password = SETTINGS.get("XANO_TEST_VENDEDOR_PASSWORD", "")
        if password != password.strip():
            # The endpoint before this sprint trimmed the password and would change it.
            self.skipTest("Senha de teste com espaços nas pontas.")
        with self.client_for("VENDEDOR") as client:
            auth_url = client._auth_base_url
            payloads = (
                {"password": password, "confirm_password": password},
                {
                    "current_password": f"errada-{uuid.uuid4().hex}",
                    "password": password,
                    "confirm_password": password,
                },
            )
            for payload in payloads:
                with self.subTest(fields=sorted(payload)), self.assertRaises(XanoValidationError):
                    client.request(
                        "POST", "reset/update_password", json=payload, base_url=auth_url
                    )


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


SHOWROOM_FIELDS = {
    "id",
    "nome_modelo",
    "familia",
    "descricao",
    "imagem_principal",
    "variacoes_cor",
    "destaque",
    "preco_a_partir",
    "disponiveis",
}
VIN_ALPHABET = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"


def random_vin() -> str:
    digits = uuid.uuid4().int
    return "".join(VIN_ALPHABET[(digits >> (5 * index)) % len(VIN_ALPHABET)] for index in range(17))


class XanoLiveCatalogReadTests(XanoLiveTestCase):
    def test_public_catalog_exposes_only_showroom_fields(self):
        """Runs without credentials; skipped while Change 8 is not published."""
        with XanoClient() as client:
            try:
                vitrine = client.request("GET", "catalogo", authenticated=False)
            except XanoNotFoundError:
                self.skipTest("Catálogo ainda não publicado no Xano (Change 8).")
            for modelo in vitrine:
                with self.subTest(modelo=modelo.get("nome_modelo")):
                    self.assertLessEqual(set(modelo), SHOWROOM_FIELDS)
            client.list_catalogo(familia="TOURING")

    def test_sales_are_for_sellers_and_managers_only(self):
        with self.client_for("MECANICO") as client, self.assertRaises(XanoPermissionError):
            client.list_motos_estoque()
        with self.client_for("VENDEDOR") as client:
            client.list_motos_estoque(status="DISPONIVEL")
            with self.assertRaises(XanoPermissionError):
                client.list_modelos_moto()

    def test_only_sellers_close_sales_and_unknown_units_are_not_found(self):
        """Writes nothing: the role check and the unit lookup come before any insert."""
        venda = VendaMotoCreate(
            id_moto=NONEXISTENT_ID,
            id_cliente=NONEXISTENT_ID,
            valor_venda=Decimal("1"),
            placa="ZZZ9Z99",
        )
        with self.client_for("MECANICO") as client, self.assertRaises(XanoPermissionError):
            client.vender_moto(venda)
        with self.client_for("VENDEDOR") as client, self.assertRaises(XanoNotFoundError):
            client.vender_moto(venda)


class XanoLiveSalesWriteTestCase(XanoLiveWriteTestCase):
    """Creates a model and a unit of its own; they stay in the database (no deletion)."""

    def create_unit(self, client: XanoClient):
        cor = VariacaoCor(
            nome="Teste", hex="#FF6600", imagem_url="https://placehold.co/800x500/FF6600/000000/png"
        )
        modelo = client.criar_modelo_moto(
            ModeloMotoCreate(
                nome_modelo=f"Teste integração {uuid.uuid4().hex[:8]}",
                familia="SPORT",
                preco_base=Decimal("50000"),
                imagem_principal=cor.imagem_url,
                variacoes_cor=[cor],
            )
        )
        self.addCleanup(self.retire_model, modelo.id)
        unidade = client.cadastrar_moto_estoque(
            MotoEstoqueCreate(
                id_modelo=modelo.id,
                chassi=random_vin(),
                cor="Teste",
                ano_modelo=2025,
                preco_venda=Decimal("48000"),
            )
        )
        return modelo, unidade

    def retire_model(self, modelo_id: int) -> None:
        with self.client_for("GERENTE") as client:
            client.atualizar_modelo_moto(modelo_id, ModeloMotoUpdate(ativo=False))

    def active_client_id(self, client: XanoClient) -> int:
        cliente = next((item for item in client.list_clientes() if item.ativo), None)
        if cliente is None:
            self.skipTest("É necessário ao menos um cliente ativo.")
        return cliente.id


class XanoLiveSalesWriteTests(XanoLiveSalesWriteTestCase):
    def test_reservation_cycle(self):
        with self.client_for("GERENTE") as gerente:
            modelo, unidade = self.create_unit(gerente)
            self.assertEqual((unidade.status, len(unidade.historico)), ("DISPONIVEL", 1))
            vitrine = next(item for item in gerente.list_catalogo() if item.id == modelo.id)
            self.assertEqual((vitrine.disponiveis, vitrine.preco_a_partir), (1, Decimal("48000")))
            with self.assertRaises(XanoValidationError):
                gerente.cadastrar_moto_estoque(
                    MotoEstoqueCreate(
                        id_modelo=modelo.id,
                        chassi=unidade.chassi,
                        cor="Teste",
                        ano_modelo=2025,
                        preco_venda=Decimal("1"),
                    )
                )
            cliente_id = self.active_client_id(gerente)

        with self.client_for("VENDEDOR") as vendedor:
            me = vendedor.current_user().funcionario
            reservada = vendedor.reservar_moto(
                unidade.id, ReservaMotoCreate(id_cliente=cliente_id, dias_validade=2)
            )
            self.assertEqual(
                (reservada.status, reservada.clientes_id, reservada.id_vendedor_reserva),
                ("RESERVADA", cliente_id, me.id),
            )
            self.assertIsNotNone(reservada.reservada_ate)
            with self.assertRaises(XanoValidationError):
                vendedor.reservar_moto(unidade.id, ReservaMotoCreate(id_cliente=cliente_id))
            with self.assertRaises(XanoValidationError):
                vendedor.request("POST", f"motos/{unidade.id}/reserva/cancelar", json={})

        with self.client_for("GERENTE") as gerente:
            self.assertEqual(
                next(item for item in gerente.list_catalogo() if item.id == modelo.id).disponiveis, 0
            )
            liberada = gerente.cancelar_reserva_moto(unidade.id, CancelamentoReservaMoto(motivo="Teste"))
            self.assertEqual((liberada.status, liberada.clientes_id), ("DISPONIVEL", None))
            self.assertEqual(
                [evento.status_novo for evento in liberada.historico],
                ["DISPONIVEL", "RESERVADA", "DISPONIVEL"],
            )
            with self.assertRaises(XanoPermissionError):
                gerente.request("PUT", f"motos/{unidade.id}", json={"status": "VENDIDA"})

    def test_sale_cycle_without_plate(self):
        with self.client_for("GERENTE") as gerente:
            modelo, disponivel = self.create_unit(gerente)
            _, reservada = self.create_unit(gerente)
            cliente_id = self.active_client_id(gerente)
            outro_cliente = next(
                (item.id for item in gerente.list_clientes() if item.ativo and item.id != cliente_id),
                None,
            )

        with self.client_for("VENDEDOR") as vendedor:
            venda = VendaMotoCreate(id_moto=disponivel.id, id_cliente=cliente_id, valor_venda=Decimal("47500"))
            resultado = vendedor.vender_moto(venda)
            self.assertEqual(resultado.status, "SUCESSO")
            vendida = vendedor.get_moto_estoque(disponivel.id)
            self.assertEqual((vendida.status, vendida.clientes_id), ("VENDIDA", cliente_id))
            self.assertEqual([evento.status_novo for evento in vendida.historico], ["DISPONIVEL", "VENDIDA"])
            moto_cliente = next(
                item for item in vendedor.list_motos_clientes() if item.id == resultado.id_moto_cliente
            )
            self.assertEqual(
                (moto_cliente.id_cliente, moto_cliente.chassi, moto_cliente.placa, moto_cliente.modelo),
                (cliente_id, disponivel.chassi, None, modelo.nome_modelo),
            )
            with self.assertRaisesRegex(XanoValidationError, "já foi vendida"):
                vendedor.vender_moto(venda)

            # A reserved unit goes only to its customer; a second bike without plate does not collide.
            vendedor.reservar_moto(reservada.id, ReservaMotoCreate(id_cliente=cliente_id))
            if outro_cliente is not None:
                with self.assertRaisesRegex(XanoValidationError, "reservada para outro cliente"):
                    vendedor.vender_moto(
                        VendaMotoCreate(id_moto=reservada.id, id_cliente=outro_cliente, valor_venda=Decimal("1"))
                    )
            segunda = vendedor.vender_moto(
                VendaMotoCreate(
                    id_moto=reservada.id,
                    id_cliente=cliente_id,
                    valor_venda=Decimal("46000"),
                    observacao="Teste de integração",
                )
            )
            self.assertNotEqual(segunda.id_moto_cliente, resultado.id_moto_cliente)
            self.assertEqual(vendedor.get_moto_estoque(reservada.id).status, "VENDIDA")

        with self.client_for("GERENTE") as gerente:
            vitrine = next(item for item in gerente.list_catalogo() if item.id == modelo.id)
            self.assertEqual(vitrine.disponiveis, 0)


@unittest.skipUnless(
    CONCURRENCY, "XANO_TEST_CONCURRENCY desativado: cenários concorrentes ignorados."
)
class XanoLiveStockUnitConcurrencyTests(XanoLiveSalesWriteTestCase):
    def test_two_reservations_of_the_same_unit(self):
        with self.client_for("GERENTE") as client:
            _, unidade = self.create_unit(client)
            cliente_id = self.active_client_id(client)
        results = self.race(
            *[
                lambda c: c.reservar_moto(unidade.id, ReservaMotoCreate(id_cliente=cliente_id))
                for _ in range(2)
            ]
        )
        errors = [result for result in results if isinstance(result, XanoValidationError)]
        self.assertEqual(len(errors), 1, results)
        with self.client_for("GERENTE") as client:
            detalhe = client.get_moto_estoque(unidade.id)
            self.assertEqual(detalhe.status, "RESERVADA")
            self.assertEqual(len(detalhe.historico), 2)
            client.cancelar_reserva_moto(unidade.id, CancelamentoReservaMoto(motivo="Limpeza do teste"))

    def test_two_sales_of_the_same_unit(self):
        with self.client_for("GERENTE") as client:
            _, unidade = self.create_unit(client)
            cliente_id = self.active_client_id(client)
        venda = VendaMotoCreate(id_moto=unidade.id, id_cliente=cliente_id, valor_venda=Decimal("48000"))
        results = self.race(*[lambda c: c.vender_moto(venda) for _ in range(2)])
        errors = [result for result in results if isinstance(result, XanoValidationError)]
        self.assertEqual(len(errors), 1, results)
        with self.client_for("GERENTE") as client:
            detalhe = client.get_moto_estoque(unidade.id)
            self.assertEqual([evento.status_novo for evento in detalhe.historico], ["DISPONIVEL", "VENDIDA"])
            motos_cliente = [item for item in client.list_motos_clientes() if item.chassi == unidade.chassi]
            self.assertEqual(len(motos_cliente), 1)


if __name__ == "__main__":
    unittest.main()


def periodo_de_hoje() -> PeriodoFinanceiro:
    hoje = datetime.now(FUSO_LOJA).date()
    return PeriodoFinanceiro(inicio=hoje, fim=hoje)


class XanoLiveFinanceReadTests(XanoLiveTestCase):
    """Change 10 without writes: access, immutability and period validation."""

    def test_financial_data_is_manager_only(self):
        for role in ("VENDEDOR", "MECANICO"):
            with self.subTest(role=role), self.client_for(role) as client:
                with self.assertRaises(XanoPermissionError):
                    client.resumo_financeiro(periodo_de_hoje())
                with self.assertRaises(XanoPermissionError):
                    client.request("GET", "transacoes")

    def test_manager_reads_the_summary_and_the_period_is_validated(self):
        with self.client_for("GERENTE") as client:
            hoje = datetime.now(FUSO_LOJA).date()
            resumo = client.resumo_financeiro(PeriodoFinanceiro(inicio=hoje.replace(day=1), fim=hoje))
            self.assertAlmostEqual(resumo.saldo, resumo.receitas - resumo.despesas, delta=Decimal("0.01"))
            self.assertLessEqual(len(resumo.operacoes), OPERACOES_LIMITE)
            params = periodo_de_hoje().params()
            for invalid in (
                {"inicio": params["fim"], "fim": params["inicio"]},
                {"inicio": params["inicio"] - 367 * 24 * 60 * 60 * 1000, "fim": params["fim"]},
            ):
                with self.subTest(params=invalid), self.assertRaises(XanoValidationError):
                    client.request("GET", "financeiro/resumo", params=invalid)

    def test_transactions_cannot_be_written_manually(self):
        with self.client_for("GERENTE") as client:
            for method, path in (
                ("POST", "transacoes"),
                ("PUT", f"transacoes/{NONEXISTENT_ID}"),
                ("PATCH", f"transacoes/{NONEXISTENT_ID}"),
            ):
                with self.subTest(method=method), self.assertRaises(XanoPermissionError):
                    client.request(method, path, json={"tipo_transacao": "BALCAO", "valor_total": 1})


class XanoLiveFinanceWriteTests(XanoLiveWriteTestCase):
    """Change 10 with writes: concluding an order posts its revenue exactly once."""

    def test_conclusion_posts_the_revenue_once_and_the_summary_shows_it(self):
        with self.client_for("GERENTE") as client:
            (product,) = self.restocked_products(client, 1, 1)
            ordem = self.open_order(client)
            try:
                client.adicionar_item_ordem_servico(
                    ordem.id, ItemOSCreate(tipo_item="PECA", id_produto=product.id, quantidade=1)
                )
                client.adicionar_item_ordem_servico(
                    ordem.id,
                    ItemOSCreate(
                        tipo_item="SERVICO",
                        descricao="Mão de obra de teste",
                        quantidade=1,
                        valor_unitario=Decimal("80.00"),
                    ),
                )
                client.transicionar_ordem_servico(
                    ordem.id, TransicaoStatusOS(status_atual="ABERTA", status_novo="EM_ANDAMENTO")
                )
                concluida = client.transicionar_ordem_servico(
                    ordem.id, TransicaoStatusOS(status_atual="EM_ANDAMENTO", status_novo="CONCLUIDA")
                )
            finally:
                self.cancel_quietly(client, ordem.id)

            self.assertEqual(concluida.status, "CONCLUIDA")
            self.assertIsNotNone(concluida.id_transacao)
            lancamentos = [
                operacao
                for operacao in client.resumo_financeiro(periodo_de_hoje()).operacoes
                if operacao.id_os == ordem.id
            ]
            self.assertEqual(len(lancamentos), 1)
            (lancamento,) = lancamentos
            self.assertEqual(
                (lancamento.id, lancamento.tipo, lancamento.natureza, lancamento.valor),
                (concluida.id_transacao, "ORDEM_SERVICO", "RECEITA", concluida.valor_total),
            )

    def test_orders_without_items_or_cancelled_post_nothing(self):
        with self.client_for("GERENTE") as client:
            vazia = self.open_order(client)
            try:
                client.transicionar_ordem_servico(
                    vazia.id, TransicaoStatusOS(status_atual="ABERTA", status_novo="EM_ANDAMENTO")
                )
                concluida = client.transicionar_ordem_servico(
                    vazia.id, TransicaoStatusOS(status_atual="EM_ANDAMENTO", status_novo="CONCLUIDA")
                )
            finally:
                self.cancel_quietly(client, vazia.id)
            self.assertIsNone(concluida.id_transacao)

            cancelada = self.open_order(client)
            client.transicionar_ordem_servico(
                cancelada.id,
                TransicaoStatusOS(status_atual="ABERTA", status_novo="CANCELADA", observacao="Teste"),
            )
            self.assertIsNone(client.get_ordem_servico(cancelada.id).id_transacao)


@unittest.skipUnless(
    CONCURRENCY, "XANO_TEST_CONCURRENCY desativado: cenários concorrentes ignorados."
)
class XanoLiveFinanceConcurrencyTests(XanoLiveWriteTestCase):
    def test_two_simultaneous_conclusions_post_once(self):
        with self.client_for("GERENTE") as client:
            ordem = self.open_order(client)
            client.adicionar_item_ordem_servico(
                ordem.id,
                ItemOSCreate(
                    tipo_item="SERVICO",
                    descricao="Mão de obra de teste",
                    quantidade=1,
                    valor_unitario=Decimal("10.00"),
                ),
            )
            client.transicionar_ordem_servico(
                ordem.id, TransicaoStatusOS(status_atual="ABERTA", status_novo="EM_ANDAMENTO")
            )
        concluir = TransicaoStatusOS(status_atual="EM_ANDAMENTO", status_novo="CONCLUIDA")
        results = self.race(*[lambda c: c.transicionar_ordem_servico(ordem.id, concluir) for _ in range(2)])
        errors = [result for result in results if isinstance(result, XanoValidationError)]
        self.assertEqual(len(errors), 1, results)
        with self.client_for("GERENTE") as client:
            lancamentos = [
                operacao
                for operacao in client.resumo_financeiro(periodo_de_hoje()).operacoes
                if operacao.id_os == ordem.id
            ]
            self.assertEqual(len(lancamentos), 1)


def venda_balcao(linhas, id_cliente=None, ajuste=Decimal("0")):
    """Counter sale of (product, quantity) lines with the total the seller would see.

    ``ajuste`` simulates a cart built before a price change: the total no longer matches.
    """
    total = sum((produto.preco_venda * quantidade for produto, quantidade in linhas), Decimal("0"))
    return VendaBalcaoCreate(
        chave_venda=str(uuid.uuid4()),
        id_cliente=id_cliente,
        total_esperado=(total + ajuste).quantize(Decimal("0.01")),
        itens=[ItemVendaBalcaoCreate(id_produto=produto.id, quantidade=quantidade) for produto, quantidade in linhas],
    )


class XanoLiveCounterReadTests(XanoLiveTestCase):
    """Change 11 without writes: who sells at the counter and which carts are refused."""

    def active_product(self, client: XanoClient):
        produto = next((item for item in client.list_produtos() if item.ativo), None)
        if produto is None:
            self.skipTest("É necessário ao menos um produto ativo.")
        return produto

    def test_mechanic_cannot_sell_at_the_counter(self):
        with self.client_for("MECANICO") as client:
            produto = self.active_product(client)
            with self.assertRaises(XanoPermissionError):
                client.vender_balcao(venda_balcao([(produto, 1)]))

    def test_invalid_carts_are_refused_before_any_write(self):
        with self.client_for("VENDEDOR") as client:
            item = {"id_produto": self.active_product(client).id, "quantidade": 1}
            muitos = [{"id_produto": numero, "quantidade": 1} for numero in range(1, 32)]
            for itens in ([], [item, item], muitos):
                body = {"chave_venda": str(uuid.uuid4()), "total_esperado": "1.00", "itens": itens}
                with self.subTest(itens=len(itens)), self.assertRaises(XanoValidationError):
                    client.request("POST", "balcao/vendas", json=body)


class XanoLiveCounterWriteTests(XanoLiveSalesWriteTestCase):
    """Change 11 with writes: a counter sale moves stock and posts BALCAO revenue once."""

    def test_final_consumer_sale_moves_stock_and_posts_revenue(self):
        with self.client_for("GERENTE") as gerente:
            filtro, pastilha = self.restocked_products(gerente, 2, 3)
        esperado = (filtro.preco_venda * 2 + pastilha.preco_venda).quantize(Decimal("0.01"))
        with self.client_for("VENDEDOR") as vendedor:
            recibo = vendedor.vender_balcao(venda_balcao([(filtro, 2), (pastilha, 1)]))
            self.assertEqual((recibo.valor_total, recibo.id_cliente), (esperado, None))
            self.assertEqual(
                sorted((item.id_produto, item.quantidade, item.valor_unitario) for item in recibo.itens),
                sorted([(filtro.id, 2, filtro.preco_venda), (pastilha.id, 1, pastilha.preco_venda)]),
            )
            self.assertEqual(self.stock_of(vendedor, filtro.id), filtro.estoque_qtd - 2)
            self.assertEqual(self.stock_of(vendedor, pastilha.id), pastilha.estoque_qtd - 1)
        with self.client_for("GERENTE") as gerente:
            (lancamento,) = [
                operacao
                for operacao in gerente.resumo_financeiro(periodo_de_hoje()).operacoes
                if operacao.origem == "TRANSACAO" and operacao.id == recibo.id_transacao
            ]
            self.assertEqual(
                (lancamento.tipo, lancamento.natureza, lancamento.valor, lancamento.contraparte),
                ("BALCAO", "RECEITA", esperado, None),
            )

    def test_repeated_key_returns_the_same_sale_without_a_second_exit(self):
        with self.client_for("GERENTE") as gerente:
            (produto,) = self.restocked_products(gerente, 1, 2)
            cliente_id = self.active_client_id(gerente)
        venda = venda_balcao([(produto, 1)], id_cliente=cliente_id)
        with self.client_for("VENDEDOR") as vendedor:
            primeira = vendedor.vender_balcao(venda)
            # Lost response followed by a new click: same cart, same key.
            repetida = vendedor.vender_balcao(venda)
            self.assertEqual(repetida.id_transacao, primeira.id_transacao)
            self.assertEqual(primeira.id_cliente, cliente_id)
            self.assertTrue(primeira.nome_cliente)
            self.assertEqual(self.stock_of(vendedor, produto.id), produto.estoque_qtd - 1)

    def test_insufficient_stock_and_changed_price_write_nothing(self):
        with self.client_for("GERENTE") as gerente:
            (produto,) = self.restocked_products(gerente, 1, 1)
        with self.client_for("VENDEDOR") as vendedor:
            saldo = self.stock_of(vendedor, produto.id)
            with self.assertRaises(XanoValidationError) as falta:
                vendedor.vender_balcao(venda_balcao([(produto, saldo + 1)]))
            self.assertTrue(str(falta.exception).startswith(f"Saldo insuficiente para {produto.codigo}"))
            with self.assertRaises(XanoValidationError) as preco:
                vendedor.vender_balcao(venda_balcao([(produto, 1)], ajuste=Decimal("0.01")))
            self.assertTrue(str(preco.exception).startswith("Os preços mudaram desde que o carrinho foi montado"))
            self.assertEqual(self.stock_of(vendedor, produto.id), saldo)


@unittest.skipUnless(
    CONCURRENCY, "XANO_TEST_CONCURRENCY desativado: cenários concorrentes ignorados."
)
class XanoLiveCounterConcurrencyTests(XanoLiveWriteTestCase):
    def test_two_sales_of_the_whole_balance_sell_once(self):
        with self.client_for("GERENTE") as gerente:
            (produto,) = self.restocked_products(gerente, 1, 1)
            saldo = self.stock_of(gerente, produto.id)
        vendas = [venda_balcao([(produto, saldo)]) for _ in range(2)]
        results = self.race(*[lambda client, venda=venda: client.vender_balcao(venda) for venda in vendas])
        errors = [result for result in results if isinstance(result, XanoValidationError)]
        self.assertEqual(len(errors), 1, results)
        with self.client_for("GERENTE") as gerente:
            self.assertEqual(self.stock_of(gerente, produto.id), 0)
