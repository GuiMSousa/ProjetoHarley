"""Reflex state for the basic registration screens."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

import reflex as rx
from pydantic import ValidationError

from Projeto_HarleyStore.auth import AuthState, role_allows_route
from Projeto_HarleyStore.listing import (
    filter_rows,
    option_id,
    option_label,
    page_count,
    paginate,
)
from Projeto_HarleyStore.services.cadastros import (
    ClienteCreate,
    ClienteUpdate,
    FornecedorCreate,
    FornecedorUpdate,
    FuncionarioCreate,
    FuncionarioUpdate,
    MotoClienteCreate,
    MotoClienteUpdate,
    ProdutoCreate,
    ProdutoUpdate,
)
from Projeto_HarleyStore.feedback import error_feedback, toast_error, toast_success
from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoClient,
    XanoError,
    XanoValidationError,
)
from Projeto_HarleyStore.ui_helpers import operation_is_blocked


SECTION_ROUTES = {
    "clientes": "/cadastros/clientes",
    "motos_clientes": "/cadastros/motos-clientes",
    "produtos": "/cadastros/produtos",
    "fornecedores": "/cadastros/fornecedores",
    "funcionarios": "/cadastros/funcionarios",
}


class CadastrosState(AuthState):
    """Shared state for cadastro lists, forms, and permissions."""

    active_section: str = "clientes"
    search_text: str = ""
    current_page: int = 1
    page_size: int = 8
    form_open: bool = False
    editing_id: str = ""
    form_error: str = ""
    form_data: dict[str, str] = {}
    list_error: str = ""
    is_loading_list: bool = False
    is_saving: bool = False
    is_deactivating: bool = False

    clientes: list[dict[str, str]] = []
    motos_clientes: list[dict[str, str]] = []
    produtos: list[dict[str, str]] = []
    fornecedores: list[dict[str, str]] = []
    funcionarios: list[dict[str, str]] = []

    @rx.var
    def client_options(self) -> list[str]:
        return [
            option_label(row["id"], row["primary"])
            for row in self.clientes
            if row.get("ativo") == "Ativo"
        ]

    @rx.var
    def can_write_active(self) -> bool:
        if self.active_section in {"clientes", "motos_clientes"}:
            return self.employee_role in {"GERENTE", "VENDEDOR"}
        return self.employee_role == "GERENTE"

    def _section_rows(self, section: str) -> list[dict[str, str]]:
        return {
            "clientes": self.clientes,
            "motos_clientes": self.motos_clientes,
            "produtos": self.produtos,
            "fornecedores": self.fornecedores,
            "funcionarios": self.funcionarios,
        }.get(section, [])

    @rx.var
    def visible_rows(self) -> list[dict[str, str]]:
        rows = filter_rows(self._section_rows(self.active_section), self.search_text)
        return paginate(rows, self.current_page, self.page_size)

    @rx.var
    def total_pages(self) -> int:
        rows = filter_rows(self._section_rows(self.active_section), self.search_text)
        return page_count(len(rows), self.page_size)

    @rx.event
    def set_section(self, section: str) -> None:
        self.active_section = section
        self.search_text = ""
        self.current_page = 1
        self.form_open = False
        self.form_error = ""

    @rx.var
    def is_busy(self) -> bool:
        return operation_is_blocked(
            self.is_loading_list,
            self.is_saving,
            self.is_deactivating,
        )

    @rx.event
    def set_search_text(self, value: str) -> None:
        self.search_text = value
        self.current_page = 1

    @rx.event
    def previous_page(self) -> None:
        self.current_page = max(1, self.current_page - 1)

    @rx.event
    def next_page(self) -> None:
        self.current_page = min(self.total_pages, self.current_page + 1)

    @rx.event
    def set_form_field(self, field: str, value: str) -> None:
        self.form_data = {**self.form_data, field: value}
        self.form_error = ""

    def _rows(self, values: list[Any], primary: str, secondary: str, tertiary: str) -> list[dict[str, str]]:
        rows = []
        for item in values:
            row = {
                key: str(value if value is not None else "")
                for key, value in item.model_dump(mode="json").items()
            }
            row.update(
                {
                    "id": str(item.id),
                    "primary": str(getattr(item, primary, "")),
                    "secondary": str(getattr(item, secondary, "")),
                    "tertiary": str(getattr(item, tertiary, "")),
                    "ativo": "Ativo" if item.ativo else "Inativo",
                    "ativo_value": "true" if item.ativo else "false",
                }
            )
            rows.append(row)
        return rows

    def _load_section(self, section: str) -> None:
        with XanoClient(token=self.auth_token) as client:
            if section == "clientes":
                self.clientes = self._rows(client.list_clientes(), "nome_cliente", "cpf_cnpj", "telefone")
            elif section == "motos_clientes":
                self.clientes = self._rows(client.list_clientes(), "nome_cliente", "cpf_cnpj", "telefone")
                self.motos_clientes = self._rows(client.list_motos_clientes(), "modelo", "placa", "chassi")
            elif section == "produtos":
                self.produtos = self._rows(client.list_produtos(), "codigo", "nome_produto", "preco_venda")
            elif section == "fornecedores":
                self.fornecedores = self._rows(client.list_fornecedores(), "nome_fornecedor", "cnpj", "contato")
            elif section == "funcionarios":
                self.funcionarios = self._rows(client.list_funcionarios(), "nome_funcionario", "tipo", "cargo")

    def _clear_section_rows(self, section: str) -> None:
        """Never keep rows from a previous load next to a load error."""
        if section in {"clientes", "motos_clientes"}:
            self.clientes = []
        if section == "motos_clientes":
            self.motos_clientes = []
        elif section == "produtos":
            self.produtos = []
        elif section == "fornecedores":
            self.fornecedores = []
        elif section == "funcionarios":
            self.funcionarios = []

    def _load(self, section: str):
        if self.is_loading_list:
            return None
        self.set_section(section)
        self.list_error = ""
        if not self.is_authenticated or not role_allows_route(
            self.employee_role, SECTION_ROUTES[section]
        ):
            return None
        self.is_loading_list = True
        try:
            self._load_section(section)
        except XanoError as error:
            self._clear_section_rows(section)
            self.list_error = error_feedback(error)
            if isinstance(error, XanoAuthenticationError):
                return self._xano_error_response(error)
        finally:
            self.is_loading_list = False
        return None

    def _refresh_after_mutation(self, section: str) -> None:
        """Reload a list after a successful write without masking the write result."""
        try:
            self._load_section(section)
        except XanoError as error:
            self.list_error = error_feedback(error)

    @rx.event
    def load_clientes(self):
        return self._load("clientes")

    @rx.event
    def load_motos_clientes(self):
        return self._load("motos_clientes")

    @rx.event
    def load_produtos(self):
        return self._load("produtos")

    @rx.event
    def load_fornecedores(self):
        return self._load("fornecedores")

    @rx.event
    def load_funcionarios(self):
        return self._load("funcionarios")

    def _new_form(self, section: str) -> None:
        self.set_section(section)
        self.editing_id = ""
        self.form_error = ""
        self.form_data = {
            "ativo": "true",
            "nome_cliente": "",
            "cpf_cnpj": "",
            "telefone": "",
            "email": "",
            "endereco": "",
            "id_cliente": "",
            "modelo": "",
            "placa": "",
            "chassi": "",
            "codigo": "",
            "nome_produto": "",
            "descricao": "",
            "categoria": "",
            "estoque_qtd": "0",
            "preco_venda": "",
            "nome_fornecedor": "",
            "cnpj": "",
            "contato": "",
            "nome_funcionario": "",
            "cargo": "",
            "tipo": "",
        }
        self.form_open = True

    @rx.event
    def open_create(self, section: str) -> None:
        if not self._can_write(section):
            self.form_error = "Seu perfil não pode criar este cadastro."
            return
        self._new_form(section)

    @rx.event
    def open_edit(self, section: str, record_id: str) -> None:
        if not self._can_write(section):
            self.form_error = "Seu perfil não pode editar este cadastro."
            return
        self.set_section(section)
        self.editing_id = record_id
        self.form_error = ""
        rows = self._section_rows(section)
        selected = next((row for row in rows if row.get("id") == record_id), {})
        self.form_data = {
            key: value
            for key, value in selected.items()
            if key not in {"primary", "secondary", "tertiary", "ativo_value"}
        }
        self.form_data["ativo"] = selected.get("ativo_value", "true")
        if section == "motos_clientes" and self.form_data.get("id_cliente"):
            client_id = self.form_data["id_cliente"]
            client_name = next(
                (
                    row["primary"]
                    for row in self.clientes
                    if row.get("id") == client_id
                ),
                "",
            )
            self.form_data["id_cliente"] = option_label(client_id, client_name)
        self.form_open = True

    @rx.event
    def close_form(self) -> None:
        self.form_open = False
        self.form_error = ""

    def _can_write(self, section: str) -> bool:
        return (
            self.employee_role in {"GERENTE", "VENDEDOR"}
            if section in {"clientes", "motos_clientes"}
            else self.employee_role == "GERENTE"
        )

    def _payload(self) -> tuple[Any, Any]:
        data = self.form_data
        if self.active_section == "clientes":
            model = ClienteUpdate if self.editing_id else ClienteCreate
            return model(**data), model
        if self.active_section == "motos_clientes":
            payload = dict(data)
            payload["id_cliente"] = option_id(payload["id_cliente"])
            model = MotoClienteUpdate if self.editing_id else MotoClienteCreate
            return model(**payload), model
        if self.active_section == "produtos":
            payload = dict(data)
            if self.editing_id:
                # Stock balance changes only through stock movements.
                payload.pop("estoque_qtd", None)
            elif "estoque_qtd" in payload:
                payload["estoque_qtd"] = int(payload["estoque_qtd"])
            if "preco_venda" in payload:
                payload["preco_venda"] = Decimal(payload["preco_venda"])
            model = ProdutoUpdate if self.editing_id else ProdutoCreate
            return model(**payload), model
        if self.active_section == "fornecedores":
            model = FornecedorUpdate if self.editing_id else FornecedorCreate
            return model(**data), model
        model = FuncionarioUpdate if self.editing_id else FuncionarioCreate
        return model(**data), model

    @rx.event
    def save_form(self):
        if operation_is_blocked(
            self.is_loading_list,
            self.is_saving,
            self.is_deactivating,
        ):
            return
        if not self._can_write(self.active_section):
            self.form_error = "Seu perfil não pode alterar este cadastro."
            return toast_error(self.form_error)
        self.is_saving = True
        try:
            payload, _ = self._payload()
            with XanoClient(token=self.auth_token) as client:
                if self.active_section == "clientes":
                    if self.editing_id:
                        client.update_cliente(int(self.editing_id), payload)
                    else:
                        client.create_cliente(payload)
                elif self.active_section == "motos_clientes":
                    if self.editing_id:
                        client.update_moto_cliente(int(self.editing_id), payload)
                    else:
                        client.create_moto_cliente(payload)
                elif self.active_section == "produtos":
                    if self.editing_id:
                        client.update_produto(int(self.editing_id), payload)
                    else:
                        client.create_produto(payload)
                elif self.active_section == "fornecedores":
                    if self.editing_id:
                        client.update_fornecedor(int(self.editing_id), payload)
                    else:
                        client.create_fornecedor(payload)
                else:
                    if self.editing_id:
                        client.update_funcionario(int(self.editing_id), payload)
                    else:
                        client.create_funcionario(payload)
            section = self.active_section
            self.form_open = False
            self._refresh_after_mutation(section)
            return toast_success("Cadastro salvo com sucesso.")
        except (ValidationError, ValueError, InvalidOperation) as error:
            self.form_error = "Revise os campos obrigatórios e os valores informados."
            return toast_error(self.form_error)
        except XanoValidationError as error:
            self.form_error = error_feedback(error)
            return toast_error(self.form_error)
        except XanoError as error:
            self.form_error = error_feedback(error)
            return self._xano_error_response(error)
        finally:
            self.is_saving = False

    @rx.event
    def deactivate(self, section: str, record_id: str):
        if operation_is_blocked(
            self.is_loading_list,
            self.is_saving,
            self.is_deactivating,
        ):
            return
        if not self._can_write(section):
            return toast_error("Seu perfil não pode desativar este cadastro.")
        self.is_deactivating = True
        try:
            with XanoClient(token=self.auth_token) as client:
                if section == "clientes":
                    client.deactivate_cliente(int(record_id))
                elif section == "motos_clientes":
                    client.deactivate_moto_cliente(int(record_id))
                elif section == "produtos":
                    client.deactivate_produto(int(record_id))
                elif section == "fornecedores":
                    client.deactivate_fornecedor(int(record_id))
                else:
                    client.deactivate_funcionario(int(record_id))
            self._refresh_after_mutation(section)
            return toast_success("Registro desativado.")
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.is_deactivating = False
