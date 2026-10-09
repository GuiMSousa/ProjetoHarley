"""Reflex state of /balcao: counter sale of parts (Change 11)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import reflex as rx
from pydantic import ValidationError

from Projeto_HarleyStore.auth import AuthState, role_allows_route
from Projeto_HarleyStore.feedback import (
    error_feedback,
    toast_error,
    toast_success,
    validation_feedback,
)
from Projeto_HarleyStore.formatting import EMPTY_VALUE, format_currency, format_datetime
from Projeto_HarleyStore.listing import filtrar_produtos, option_id, option_label, produto_row
from Projeto_HarleyStore.services.balcao import (
    MAX_ITENS_VENDA,
    ItemVendaBalcaoCreate,
    VendaBalcaoCreate,
    VendaBalcaoDetalhe,
)
from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoClient,
    XanoError,
    XanoPermissionError,
    XanoValidationError,
)
from Projeto_HarleyStore.ui_helpers import operation_is_blocked


BALCAO_ROUTE = "/balcao"
CONSUMIDOR_FINAL = "Consumidor final"
TODAS_CATEGORIAS = "Todas as categorias"
BALCAO_SEARCH_LIMIT = 20
CENTAVO = Decimal("0.01")
# Product fields copied into a cart line (price and balance refreshed on every reload).
CART_FIELDS = ("id", "codigo", "nome", "saldo", "preco", "preco_valor")
FIELD_MESSAGES = {
    "chave_venda": "Atualize a página para iniciar uma nova venda.",
    "id_cliente": "Selecione o cliente.",
    "total_esperado": "O total da venda deve ser maior que zero.",
    "itens": f"A venda deve ter de 1 a {MAX_ITENS_VENDA} itens.",
}


class BalcaoFormError(ValueError):
    """Readable validation error of the counter cart."""


def nova_chave() -> str:
    """Key of a new cart: Xano returns the sale already registered when a key repeats."""
    return str(uuid.uuid4())


def _parse_quantidade(texto: str) -> int | None:
    try:
        quantidade = int(texto.strip())
    except ValueError:
        return None
    return quantidade if quantidade > 0 else None


def _subtotal(linha: dict[str, str]) -> Decimal | None:
    quantidade = _parse_quantidade(linha["quantidade"])
    return None if quantidade is None else Decimal(linha["preco_valor"]) * quantidade


def _com_quantidade(linha: dict[str, str], quantidade: str) -> dict[str, str]:
    atualizada = {**linha, "quantidade": quantidade}
    subtotal = _subtotal(atualizada)
    atualizada["subtotal"] = EMPTY_VALUE if subtotal is None else format_currency(subtotal)
    return atualizada


def produtos_visiveis(
    catalogo: list[dict[str, str]], categoria: str, busca: str
) -> list[dict[str, str]]:
    """Every product of the category whose code or name matches the search (no limit)."""
    rows = (
        catalogo
        if categoria in ("", TODAS_CATEGORIAS)
        else [row for row in catalogo if row["categoria"] == categoria]
    )
    return filtrar_produtos(rows, busca, limite=len(rows))


def adicionar_item(
    carrinho: list[dict[str, str]], produto: dict[str, str], quantidade: int = 1
) -> list[dict[str, str]]:
    """Add a product to the cart; adding it again sums the quantities (one line per product).

    Raises ``BalcaoFormError`` above the loaded balance or beyond the item limit.
    """
    atual = next((linha for linha in carrinho if linha["id"] == produto["id"]), None)
    if atual is None and len(carrinho) >= MAX_ITENS_VENDA:
        raise BalcaoFormError(f"A venda pode ter no máximo {MAX_ITENS_VENDA} itens.")
    total = quantidade + ((_parse_quantidade(atual["quantidade"]) or 0) if atual else 0)
    saldo = int(produto["saldo"])
    if total > saldo:
        raise BalcaoFormError(f"Saldo insuficiente para {produto['codigo']}: disponível {saldo}.")
    linha = _com_quantidade({field: produto[field] for field in CART_FIELDS}, str(total))
    if atual is None:
        return [*carrinho, linha]
    return [linha if item["id"] == produto["id"] else item for item in carrinho]


def alterar_quantidade(
    carrinho: list[dict[str, str]], produto_id: str, texto: str
) -> list[dict[str, str]]:
    """Keep the digits the seller typed; the subtotal shows only for a valid quantity."""
    digitos = "".join(char for char in texto if char.isdigit())[:6]
    return [
        _com_quantidade(linha, digitos) if linha["id"] == produto_id else linha
        for linha in carrinho
    ]


def remover_item(carrinho: list[dict[str, str]], produto_id: str) -> list[dict[str, str]]:
    return [linha for linha in carrinho if linha["id"] != produto_id]


def sincronizar_carrinho(
    carrinho: list[dict[str, str]], catalogo: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Refresh prices and balances from the reloaded catalog; products no longer sold leave."""
    por_id = {produto["id"]: produto for produto in catalogo}
    return [
        _com_quantidade(
            {field: por_id[linha["id"]][field] for field in CART_FIELDS}, linha["quantidade"]
        )
        for linha in carrinho
        if linha["id"] in por_id
    ]


def total_carrinho(carrinho: list[dict[str, str]]) -> Decimal:
    """Sum of the valid lines, as Xano will charge them (two decimal places)."""
    total = sum((_subtotal(linha) or Decimal(0) for linha in carrinho), Decimal(0))
    return total.quantize(CENTAVO)


def cliente_id(cliente: str) -> int | None:
    return None if cliente in ("", CONSUMIDOR_FINAL) else option_id(cliente)


def cliente_nome(cliente: str) -> str:
    """Customer name without the id prefix of the select option."""
    return CONSUMIDOR_FINAL if cliente in ("", CONSUMIDOR_FINAL) else cliente.split(" - ", 1)[-1]


def build_venda_payload(
    carrinho: list[dict[str, str]], cliente: str, chave: str
) -> VendaBalcaoCreate:
    """Validate the cart and build the sale, or raise ``BalcaoFormError``.

    The balance check mirrors Xano only to give immediate feedback.
    """
    if not carrinho:
        raise BalcaoFormError("Adicione ao menos uma peça ao carrinho.")
    if len(carrinho) > MAX_ITENS_VENDA:
        raise BalcaoFormError(f"A venda pode ter no máximo {MAX_ITENS_VENDA} itens.")
    itens = []
    for linha in carrinho:
        quantidade = _parse_quantidade(linha["quantidade"])
        if quantidade is None:
            raise BalcaoFormError(
                f"Informe a quantidade de {linha['codigo']}: um número inteiro maior que zero."
            )
        if quantidade > int(linha["saldo"]):
            raise BalcaoFormError(
                f"Saldo insuficiente para {linha['codigo']}: disponível {linha['saldo']}."
            )
        itens.append(ItemVendaBalcaoCreate(id_produto=int(linha["id"]), quantidade=quantidade))
    try:
        return VendaBalcaoCreate(
            chave_venda=chave,
            id_cliente=cliente_id(cliente),
            total_esperado=total_carrinho(carrinho),
            itens=itens,
        )
    except ValidationError as error:
        raise BalcaoFormError(validation_feedback(error, FIELD_MESSAGES)) from error


def recibo_view(
    detalhe: VendaBalcaoDetalhe,
) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Receipt header and lines, formatted for the receipt panel."""
    if detalhe.nome_cliente:
        cliente = detalhe.nome_cliente
    elif detalhe.id_cliente is None:
        cliente = CONSUMIDOR_FINAL
    else:
        cliente = f"Cliente #{detalhe.id_cliente}"
    resumo = {
        "numero": str(detalhe.id_transacao),
        "data": format_datetime(detalhe.data_transacao),
        "cliente": cliente,
        "vendedor": detalhe.nome_funcionario or EMPTY_VALUE,
        "total": format_currency(detalhe.valor_total),
    }
    linhas = [
        {
            "id": str(item.id_produto),
            "produto": " · ".join(parte for parte in (item.codigo, item.nome_produto) if parte)
            or f"Produto #{item.id_produto}",
            "quantidade": str(item.quantidade),
            "preco": format_currency(item.valor_unitario),
            "subtotal": format_currency(item.valor_total_item),
        }
        for item in detalhe.itens
    ]
    return resumo, linhas


class BalcaoState(AuthState):
    """Product search, cart, optional customer, confirmation and receipt of /balcao."""

    catalogo: list[dict[str, str]] = []
    categoria: str = TODAS_CATEGORIAS
    busca: str = ""
    carrinho: list[dict[str, str]] = []
    cliente_options: list[str] = [CONSUMIDOR_FINAL]
    cliente: str = CONSUMIDOR_FINAL
    chave_venda: str = ""
    form_error: str = ""
    list_error: str = ""
    confirm_open: bool = False
    recibo: dict[str, str] = {}
    recibo_itens: list[dict[str, str]] = []
    is_loading_list: bool = False
    is_selling: bool = False

    @rx.var
    def categorias(self) -> list[str]:
        return [TODAS_CATEGORIAS, *sorted({produto["categoria"] for produto in self.catalogo})]

    @rx.var
    def resultados(self) -> list[dict[str, str]]:
        return produtos_visiveis(self.catalogo, self.categoria, self.busca)[:BALCAO_SEARCH_LIMIT]

    @rx.var
    def resultados_truncados(self) -> bool:
        return len(produtos_visiveis(self.catalogo, self.categoria, self.busca)) > BALCAO_SEARCH_LIMIT

    @rx.var
    def total(self) -> str:
        return format_currency(total_carrinho(self.carrinho))

    @rx.var
    def itens_no_carrinho(self) -> int:
        return len(self.carrinho)

    @rx.var
    def cliente_selecionado(self) -> str:
        return cliente_nome(self.cliente)

    @rx.var
    def recibo_open(self) -> bool:
        return bool(self.recibo)

    def _operation_blocked(self) -> bool:
        return operation_is_blocked(self.is_loading_list, self.is_selling, False)

    @rx.var
    def is_busy(self) -> bool:
        return self._operation_blocked()

    def _reload(self, client: XanoClient) -> None:
        self.catalogo = [produto_row(produto) for produto in client.list_produtos() if produto.ativo]
        self.cliente_options = [
            CONSUMIDOR_FINAL,
            *(option_label(cliente.id, cliente.nome_cliente) for cliente in client.list_clientes() if cliente.ativo),
        ]
        if self.cliente not in self.cliente_options:
            self.cliente = CONSUMIDOR_FINAL
        self.carrinho = sincronizar_carrinho(self.carrinho, self.catalogo)

    def _refresh(self, client: XanoClient) -> None:
        try:
            self._reload(client)
        except XanoError as error:
            self.list_error = error_feedback(error)

    @rx.event
    def load_balcao(self):
        if self.is_loading_list:
            return None
        self.list_error = ""
        self.busca = ""
        self.categoria = TODAS_CATEGORIAS
        if not self.chave_venda:
            self.chave_venda = nova_chave()
        if not self.is_authenticated or not role_allows_route(self.employee_role, BALCAO_ROUTE):
            return None
        self.is_loading_list = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                self._reload(client)
        except XanoError as error:
            self.catalogo = []
            self.list_error = error_feedback(error)
            if isinstance(error, XanoAuthenticationError):
                return self._xano_error_response(error)
        finally:
            self.is_loading_list = False
        return None

    @rx.event
    def set_busca(self, value: str) -> None:
        self.busca = value

    @rx.event
    def set_categoria(self, value: str) -> None:
        self.categoria = value

    @rx.event
    def adicionar(self, produto_id: str):
        produto = next((row for row in self.catalogo if row["id"] == produto_id), None)
        if produto is None:
            return toast_error("Produto não encontrado. Atualize a lista.")
        try:
            self.carrinho = adicionar_item(self.carrinho, produto)
        except BalcaoFormError as error:
            return toast_error(str(error))
        self.form_error = ""
        return None

    @rx.event
    def set_quantidade(self, produto_id: str, value: str) -> None:
        self.carrinho = alterar_quantidade(self.carrinho, produto_id, value)
        self.form_error = ""

    @rx.event
    def remover(self, produto_id: str) -> None:
        self.carrinho = remover_item(self.carrinho, produto_id)
        self.form_error = ""

    @rx.event
    def set_cliente(self, value: str) -> None:
        self.cliente = value
        self.form_error = ""

    @rx.event
    def limpar_carrinho(self) -> None:
        if self._operation_blocked():
            return
        self.carrinho = []
        self.cliente = CONSUMIDOR_FINAL
        self.chave_venda = nova_chave()
        self.form_error = ""
        self.confirm_open = False

    @rx.event
    def abrir_confirmacao(self):
        if self._operation_blocked():
            return None
        try:
            build_venda_payload(self.carrinho, self.cliente, self.chave_venda or nova_chave())
        except BalcaoFormError as error:
            self.form_error = str(error)
            return toast_error(self.form_error)
        self.form_error = ""
        self.confirm_open = True
        return None

    @rx.event
    def fechar_confirmacao(self) -> None:
        if not self.is_selling:
            self.confirm_open = False

    @rx.event
    def confirmar_venda(self):
        # A second click (or a click after the panel closed) is ignored: one sale per cart.
        if self._operation_blocked() or not self.confirm_open:
            return None
        if not self.chave_venda:
            self.chave_venda = nova_chave()
        try:
            payload = build_venda_payload(self.carrinho, self.cliente, self.chave_venda)
        except BalcaoFormError as error:
            self.form_error = str(error)
            self.confirm_open = False
            return toast_error(self.form_error)
        self.is_selling = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                detalhe = client.vender_balcao(payload)
                self.recibo, self.recibo_itens = recibo_view(detalhe)
                self.carrinho = []
                self.cliente = CONSUMIDOR_FINAL
                self.chave_venda = nova_chave()
                self.confirm_open = False
                self._refresh(client)
            return toast_success(f"Venda #{detalhe.id_transacao} registrada.")
        except XanoValidationError as error:
            # Balance, price or a concurrent sale: reload so the seller reviews the cart.
            self.form_error = error_feedback(error)
            self.confirm_open = False
            try:
                with XanoClient(token=self.auth_token) as client:
                    self._refresh(client)
            except XanoError:
                pass
            return toast_error(self.form_error)
        except XanoPermissionError as error:
            self.form_error = error_feedback(error)
            self.confirm_open = False
            return toast_error(self.form_error)
        except XanoError as error:
            # Lost response or timeout: the cart keeps its key, so a retry returns the sale
            # already registered instead of selling twice.
            self.confirm_open = False
            return self._xano_error_response(error)
        finally:
            self.is_selling = False

    @rx.event
    def fechar_recibo(self) -> None:
        self.recibo = {}
        self.recibo_itens = []
