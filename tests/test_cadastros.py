import os
import unittest
from decimal import Decimal
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from Projeto_HarleyStore.services.cadastros import (
    ClienteCreate,
    FornecedorCreate,
    FuncionarioCreate,
    MotoClienteCreate,
    ProdutoCreate,
    ProdutoUpdate,
)
from Projeto_HarleyStore.services.xano_client import XanoClient


class CadastrosTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {"XANO_API_BASE_URL": "https://xano.test/api:test"},
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    def test_dtos_enforce_domain_values(self):
        with self.assertRaises(ValidationError):
            ProdutoCreate(
                codigo="P1",
                nome_produto="Pastilha",
                categoria="Freio",
                preco_venda=0,
            )
        with self.assertRaises(ValidationError):
            ProdutoCreate(
                codigo="P-1",
                nome_produto="Pastilha",
                categoria="Freio",
                preco_venda=10,
            )
        with self.assertRaises(ValidationError):
            FuncionarioCreate(
                nome_funcionario="Pessoa",
                cargo="Cargo",
                tipo="INVALIDO",
            )

    def test_dtos_cover_all_registration_resources(self):
        self.assertEqual(ClienteCreate(nome_cliente="Ana", cpf_cnpj="123").nome_cliente, "Ana")
        self.assertEqual(MotoClienteCreate(id_cliente=1, modelo="Iron", placa="ABC1D23", chassi="CH1").id_cliente, 1)
        self.assertEqual(FornecedorCreate(nome_fornecedor="Fornecedor", cnpj="123").cnpj, "123")
        self.assertEqual(
            FuncionarioCreate(nome_funcionario="Mec", cargo="Oficina", tipo="MECANICO").tipo,
            "MECANICO",
        )

    def test_client_methods_use_resource_paths_and_soft_delete(self):
        requests = []

        def handler(request):
            requests.append((request.method, request.url.path, request.read()))
            if request.method == "GET":
                return httpx.Response(
                    200,
                    json=[
                        {
                            "id": 1,
                            "nome_cliente": "Ana",
                            "cpf_cnpj": "123",
                            "ativo": True,
                        }
                    ],
                )
            return httpx.Response(
                200,
                json={
                    "id": 1,
                    "nome_cliente": "Ana",
                    "cpf_cnpj": "123",
                    "ativo": False,
                },
            )

        with XanoClient(
            token="jwt",
            transport=httpx.MockTransport(handler),
        ) as client:
            clientes = client.list_clientes()
            cliente = client.deactivate_cliente(1)

        self.assertEqual(clientes[0].id, 1)
        self.assertFalse(cliente.ativo)
        self.assertEqual(requests[0][0:2], ("GET", "/api:test/clientes"))
        self.assertEqual(requests[1][0:2], ("PATCH", "/api:test/clientes/1"))
        self.assertIn(b'"ativo":false', requests[1][2])

    def test_product_update_does_not_accept_stock_balance(self):
        update = ProdutoUpdate(nome_produto="Filtro", estoque_qtd=999)
        self.assertNotIn("estoque_qtd", update.model_dump(exclude_unset=True))
        self.assertNotIn("estoque_qtd", ProdutoUpdate.model_fields)

    def test_product_create_serializes_decimal_payload(self):
        captured = {}

        def handler(request):
            captured["body"] = request.read()
            return httpx.Response(
                200,
                json={
                    "id": 4,
                    "codigo": "SKU4",
                    "nome_produto": "Filtro",
                    "categoria": "Motor",
                    "estoque_qtd": 2,
                    "preco_venda": 45.5,
                    "ativo": True,
                },
            )

        with XanoClient(
            token="jwt",
            transport=httpx.MockTransport(handler),
        ) as client:
            product = client.create_produto(
                ProdutoCreate(
                    codigo="SKU4",
                    nome_produto="Filtro",
                    categoria="Motor",
                    estoque_qtd=2,
                    preco_venda=Decimal("45.50"),
                )
            )

        self.assertEqual(product.codigo, "SKU4")
        self.assertIn(b'"codigo":"SKU4"', captured["body"])
        self.assertIn(b'"preco_venda":"45.50"', captured["body"])


if __name__ == "__main__":
    unittest.main()
