"""Reflex state for goods receipts (entradas de mercadoria)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import reflex as rx
from pydantic import ValidationError

from Projeto_HarleyStore.auth import AuthState, role_allows_route
from Projeto_HarleyStore.cadastros_state import operation_is_blocked
from Projeto_HarleyStore.feedback import error_feedback
from Projeto_HarleyStore.formatting import (
    EMPTY_VALUE,
    format_currency,
    format_datetime,
    parse_decimal,
)
from Projeto_HarleyStore.listing import (
    filter_rows,
    option_id,
    option_label,
    page_count,
    paginate,
)
from Projeto_HarleyStore.services.entradas import (
    EntradaMercadoriaCreate,
    EntradaMercadoriaResumo,
    ItemEntrada,
)
from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoClient,
    XanoError,
    XanoValidationError,
)


ENTRADAS_ROUTE = "/estoque/entradas"


class EntradaFormError(ValueError):
    """Readable validation error of the goods receipt form."""


def can_register_entrada(role: str) -> bool:
    return role == "GERENTE"


def empty_item() -> dict[str, str]:
    return {"produto": "", "quantidade": "", "valor_unitario": ""}


def add_item_row(items: list[dict[str, str]]) -> list[dict[str, str]]:
    return [*items, empty_item()]


def remove_item_row(items: list[dict[str, str]], index: int) -> list[dict[str, str]]:
    """Remove an item, always keeping at least one row in the form."""
    if len(items) <= 1 or not 0 <= index < len(items):
        return items
    return [item for position, item in enumerate(items) if position != index]


def update_item_row(
    items: list[dict[str, str]], index: int, field: str, value: str
) -> list[dict[str, str]]:
    return [
        {**item, field: value} if position == index else item
        for position, item in enumerate(items)
    ]


def estimate_total(items: list[dict[str, str]]) -> Decimal:
    """Preview of the receipt total; Xano recalculates the persisted value."""
    total = Decimal("0")
    for item in items:
        try:
            total += int(item.get("quantidade", "")) * parse_decimal(
                item.get("valor_unitario", "")
            )
        except (ValueError, InvalidOperation):
            continue
    return total


def _validation_text(error: ValidationError) -> str:
    detail = error.errors()[0]
    location = detail.get("loc", ())
    if location[:1] == ("id_fornecedor",):
        return "Selecione um fornecedor."
    if location[:1] == ("numero_documento",):
        return "Informe o número do documento."
    if location == ("itens",):
        return "Adicione ao menos um item."
    if len(location) >= 3 and location[0] == "itens":
        position = int(location[1]) + 1
        if location[2] == "quantidade":
            return f"Item {position}: a quantidade deve ser maior que zero."
        if location[2] == "valor_unitario":
            return f"Item {position}: o preço de custo deve ser maior que zero."
        return f"Item {position}: selecione um produto."
    return str(detail.get("msg", "")).removeprefix("Value error, ")


def build_entrada_payload(
    fornecedor: str,
    numero_documento: str,
    items: list[dict[str, str]],
) -> EntradaMercadoriaCreate:
    """Convert form values into the validated payload or raise ``EntradaFormError``."""
    if not fornecedor:
        raise EntradaFormError("Selecione um fornecedor.")
    parsed_items = []
    for position, item in enumerate(items, start=1):
        if not item.get("produto"):
            raise EntradaFormError(f"Item {position}: selecione um produto.")
        try:
            parsed_items.append(
                {
                    "id_produto": option_id(item["produto"]),
                    "quantidade": int(item.get("quantidade", "")),
                    "valor_unitario": parse_decimal(item.get("valor_unitario", "")),
                }
            )
        except (ValueError, InvalidOperation) as error:
            raise EntradaFormError(
                f"Item {position}: informe quantidade inteira e preço de custo numérico."
            ) from error
    try:
        return EntradaMercadoriaCreate(
            id_fornecedor=option_id(fornecedor),
            numero_documento=numero_documento,
            itens=parsed_items,
        )
    except ValidationError as error:
        raise EntradaFormError(_validation_text(error)) from error


def entrada_row(entrada: EntradaMercadoriaResumo) -> dict[str, str]:
    return {
        "id": str(entrada.id),
        "data": format_datetime(entrada.data_entrada),
        "documento": entrada.numero_documento or EMPTY_VALUE,
        "fornecedor": entrada.nome_fornecedor or EMPTY_VALUE,
        "responsavel": entrada.nome_funcionario or EMPTY_VALUE,
        "itens": str(entrada.quantidade_itens),
        "total": format_currency(entrada.valor_total),
    }


def item_row(item: ItemEntrada) -> dict[str, str]:
    return {
        "codigo": item.codigo or EMPTY_VALUE,
        "produto": item.nome_produto or EMPTY_VALUE,
        "quantidade": str(item.quantidade),
        "valor_unitario": format_currency(item.valor_unitario),
        "subtotal": format_currency(item.valor_total_item),
    }


class EntradasState(AuthState):
    """History, detail and master-detail form of goods receipts."""

    entradas: list[dict[str, str]] = []
    search_text: str = ""
    current_page: int = 1
    page_size: int = 8
    list_error: str = ""
    is_loading_list: bool = False

    detail_open: bool = False
    is_loading_detail: bool = False
    detalhe: dict[str, str] = {}
    detalhe_itens: list[dict[str, str]] = []

    form_open: bool = False
    is_saving: bool = False
    form_error: str = ""
    fornecedor: str = ""
    numero_documento: str = ""
    itens_form: list[dict[str, str]] = []
    fornecedor_options: list[str] = []
    produto_options: list[str] = []

    @rx.var
    def can_register(self) -> bool:
        return can_register_entrada(self.employee_role)

    @rx.var
    def visible_rows(self) -> list[dict[str, str]]:
        rows = filter_rows(self.entradas, self.search_text)
        return paginate(rows, self.current_page, self.page_size)

    @rx.var
    def total_pages(self) -> int:
        return page_count(len(filter_rows(self.entradas, self.search_text)), self.page_size)

    @rx.var
    def total_previsto(self) -> str:
        return format_currency(estimate_total(self.itens_form))

    @rx.var
    def is_busy(self) -> bool:
        return operation_is_blocked(
            self.is_loading_list,
            self.is_saving,
            self.is_loading_detail,
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

    def _reload_entradas(self, client: XanoClient) -> None:
        self.entradas = [entrada_row(entrada) for entrada in client.list_entradas()]
        self.current_page = 1

    @rx.event
    def load_entradas(self):
        if self.is_loading_list:
            return None
        self.list_error = ""
        if not self.is_authenticated or not role_allows_route(
            self.employee_role, ENTRADAS_ROUTE
        ):
            return None
        self.is_loading_list = True
        try:
            with XanoClient(token=self.auth_token) as client:
                self._reload_entradas(client)
        except XanoError as error:
            self.entradas = []
            self.list_error = error_feedback(error)
            if isinstance(error, XanoAuthenticationError):
                return self._xano_error_response(error)
        finally:
            self.is_loading_list = False
        return None

    @rx.event
    def open_detail(self, entrada_id: str):
        if self.is_loading_detail:
            return None
        self.is_loading_detail = True
        self.detalhe = {}
        self.detalhe_itens = []
        try:
            with XanoClient(token=self.auth_token) as client:
                detalhe = client.get_entrada(int(entrada_id))
            self.detalhe = entrada_row(detalhe)
            self.detalhe_itens = [item_row(item) for item in detalhe.itens]
            self.detail_open = True
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.is_loading_detail = False
        return None

    @rx.event
    def close_detail(self) -> None:
        self.detail_open = False

    @rx.event
    def open_create(self):
        if not can_register_entrada(self.employee_role):
            return rx.toast(
                "Somente o gerente pode registrar entradas de mercadoria.",
                level="error",
                position="top-right",
            )
        self.form_error = ""
        self.fornecedor = ""
        self.numero_documento = ""
        self.itens_form = [empty_item()]
        try:
            with XanoClient(token=self.auth_token) as client:
                fornecedores = client.list_fornecedores()
                produtos = client.list_produtos()
        except XanoError as error:
            return self._xano_error_response(error)
        self.fornecedor_options = [
            option_label(fornecedor.id, fornecedor.nome_fornecedor)
            for fornecedor in fornecedores
            if fornecedor.ativo
        ]
        self.produto_options = [
            option_label(produto.id, f"{produto.codigo} · {produto.nome_produto}")
            for produto in produtos
            if produto.ativo
        ]
        if not self.fornecedor_options:
            self.form_error = "Cadastre um fornecedor ativo antes de registrar uma entrada."
        elif not self.produto_options:
            self.form_error = "Cadastre um produto ativo antes de registrar uma entrada."
        self.form_open = True
        return None

    @rx.event
    def close_form(self) -> None:
        self.form_open = False
        self.form_error = ""

    @rx.event
    def set_fornecedor(self, value: str) -> None:
        self.fornecedor = value
        self.form_error = ""

    @rx.event
    def set_numero_documento(self, value: str) -> None:
        self.numero_documento = value
        self.form_error = ""

    @rx.event
    def add_item(self) -> None:
        self.itens_form = add_item_row(self.itens_form)

    @rx.event
    def remove_item(self, index: int) -> None:
        self.itens_form = remove_item_row(self.itens_form, index)

    @rx.event
    def set_item_field(self, index: int, field: str, value: str) -> None:
        self.itens_form = update_item_row(self.itens_form, index, field, value)
        self.form_error = ""

    @rx.event
    def save_entrada(self):
        if operation_is_blocked(
            self.is_loading_list,
            self.is_saving,
            self.is_loading_detail,
        ):
            return None
        if not can_register_entrada(self.employee_role):
            self.form_error = "Somente o gerente pode registrar entradas de mercadoria."
            return rx.toast(self.form_error, level="error", position="top-right")
        try:
            payload = build_entrada_payload(
                self.fornecedor, self.numero_documento, self.itens_form
            )
        except EntradaFormError as error:
            self.form_error = str(error)
            return rx.toast(self.form_error, level="error", position="top-right")

        self.is_saving = True
        try:
            with XanoClient(token=self.auth_token) as client:
                client.registrar_entrada(payload)
                self.form_open = False
                try:
                    self._reload_entradas(client)
                except XanoError as error:
                    self.list_error = error_feedback(error)
            return rx.toast(
                "Entrada registrada. Estoque atualizado.",
                level="success",
                position="top-right",
            )
        except XanoValidationError as error:
            self.form_error = error_feedback(error)
            return rx.toast(self.form_error, level="error", position="top-right")
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.is_saving = False
