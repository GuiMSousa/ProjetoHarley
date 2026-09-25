"""Integration tests against a real Xano workspace.

The suite is skipped unless ``XANO_API_BASE_URL`` is configured in the
environment or in the project ``.env`` file, so the offline suite stays green.

Settings (environment variables take precedence over ``.env``):

- ``XANO_API_BASE_URL`` / ``XANO_AUTH_API_BASE_URL``: API group base URLs;
- ``XANO_TEST_<PERFIL>_EMAIL`` / ``XANO_TEST_<PERFIL>_PASSWORD`` for
  ``GERENTE``, ``VENDEDOR`` and ``MECANICO`` (each profile is optional);
- ``XANO_TEST_ALLOW_WRITES=true`` enables scenarios that persist data. Goods
  receipts are immutable, so those records stay in the database: point the
  suite at a test branch or workspace.
"""

from __future__ import annotations

import os
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from Projeto_HarleyStore.services.entradas import EntradaMercadoriaCreate
from Projeto_HarleyStore.services.ordens_servico import (
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


@unittest.skipUnless(ALLOW_WRITES, "XANO_TEST_ALLOW_WRITES desativado: cenários de escrita ignorados.")
class XanoLiveServiceOrderWriteTests(XanoLiveTestCase):
    def free_bike(self, client: XanoClient):
        clientes_ativos = {cliente.id for cliente in client.list_clientes() if cliente.ativo}
        em_aberto = {
            ordem.id_moto_cliente
            for status in ("ABERTA", "EM_ANDAMENTO")
            for ordem in client.list_ordens_servico(status=status)
        }
        moto = next(
            (
                moto
                for moto in client.list_motos_clientes()
                if moto.ativo and moto.id_cliente in clientes_ativos and moto.id not in em_aberto
            ),
            None,
        )
        if moto is None:
            self.skipTest("É necessária uma moto ativa de cliente ativo sem OS em aberto.")
        return moto

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


@unittest.skipUnless(ALLOW_WRITES, "XANO_TEST_ALLOW_WRITES desativado: cenários de escrita ignorados.")
class XanoLiveReceiptWriteTests(XanoLiveTestCase):
    def reference_data(self, client: XanoClient):
        supplier = next((item for item in client.list_fornecedores() if item.ativo), None)
        product = next((item for item in client.list_produtos() if item.ativo), None)
        if supplier is None or product is None:
            self.skipTest("É necessário ao menos um fornecedor e um produto ativos.")
        return supplier, product

    def stock_of(self, client: XanoClient, product_id: int) -> int:
        return next(item.estoque_qtd for item in client.list_produtos() if item.id == product_id)

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


if __name__ == "__main__":
    unittest.main()
