"""Reflex state for the workshop: service orders, their items and status machine."""

from __future__ import annotations

import unicodedata
from decimal import Decimal, InvalidOperation

import reflex as rx
from pydantic import ValidationError

from Projeto_HarleyStore.auth import AuthState, role_allows_route
from Projeto_HarleyStore.feedback import error_feedback, toast_error, toast_success
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
from Projeto_HarleyStore.services.cadastros import Produto
from Projeto_HarleyStore.services.ordens_servico import (
    STATUS_EDITAVEIS_OS,
    TRANSICOES_OS,
    HistoricoStatusOS,
    ItemOrdemServico,
    ItemOSCreate,
    OrdemServicoCreate,
    OrdemServicoDetalhe,
    OrdemServicoResumo,
    TransicaoStatusOS,
)
from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoClient,
    XanoError,
    XanoValidationError,
)
from Projeto_HarleyStore.ui_helpers import operation_is_blocked


WORKSHOP_ROUTE = "/workshop"
STATUS_FILTER_ALL = "TODAS"
STATUS_ORDER = ("ABERTA", "EM_ANDAMENTO", "CONCLUIDA", "CANCELADA")
STATUS_LABELS = {
    "ABERTA": "Aberta",
    "EM_ANDAMENTO": "Em andamento",
    "CONCLUIDA": "Concluída",
    "CANCELADA": "Cancelada",
}
TIPO_LABELS = {"PREVENTIVA": "Preventiva", "CORRETIVA": "Corretiva"}
TIPO_OPTIONS = list(TIPO_LABELS.values())
TRANSITION_ACTIONS = {
    "EM_ANDAMENTO": "Iniciar serviço",
    "CONCLUIDA": "Concluir OS",
    "CANCELADA": "Cancelar OS",
}
ITEM_TIPO_LABELS = {"PECA": "Peça", "SERVICO": "Serviço"}
PRODUTO_SEARCH_LIMIT = 8


class WorkshopFormError(ValueError):
    """Readable validation error of the workshop forms."""


def can_operate_os(role: str) -> bool:
    """Managers and mechanics open orders and move their status."""
    return role in {"GERENTE", "MECANICO"}


def allowed_transitions(status: str, role: str) -> list[dict[str, str]]:
    if not can_operate_os(role):
        return []
    return [
        {"value": target, "label": TRANSITION_ACTIONS[target]}
        for target in TRANSICOES_OS.get(status, ())
    ]


def can_edit_items(status: str, role: str) -> bool:
    """Items change only in open orders and only for managers and mechanics."""
    return can_operate_os(role) and status in STATUS_EDITAVEIS_OS


def filter_by_status(rows: list[dict[str, str]], status: str) -> list[dict[str, str]]:
    if status == STATUS_FILTER_ALL:
        return rows
    return [row for row in rows if row.get("status") == status]


def status_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts = {STATUS_FILTER_ALL: len(rows), **{status: 0 for status in STATUS_ORDER}}
    for row in rows:
        if row.get("status") in counts:
            counts[row["status"]] += 1
    return counts


def motos_do_cliente(motos: list[dict[str, str]], cliente: str) -> list[str]:
    """Options of the active bikes that belong to the selected customer."""
    if not cliente:
        return []
    cliente_id = str(option_id(cliente))
    return [
        moto["label"]
        for moto in motos
        if moto.get("id_cliente") == cliente_id and moto.get("ativo") == "true"
    ]


def _first_error(error: ValidationError) -> str:
    detail = error.errors()[0]
    field = detail.get("loc", ("",))[0] if detail.get("loc") else ""
    messages = {
        "descricao_problema": "Descreva o problema ou o serviço solicitado.",
        "quilometragem": "A quilometragem deve ser um número inteiro não negativo.",
        "tipo_servico": "Selecione o tipo de serviço.",
        "id_moto_cliente": "Selecione a moto do cliente.",
        "id_mecanico": "Selecione o mecânico responsável.",
        "quantidade": "A quantidade deve ser um número inteiro maior que zero.",
        "valor_unitario": "O valor do serviço deve ser positivo, com até duas casas decimais.",
        "descricao": "A descrição do serviço deve ter até 200 caracteres.",
    }
    if field in messages:
        return messages[field]
    return str(detail.get("msg", "")).removeprefix("Value error, ")


def build_abertura_payload(
    cliente: str,
    moto: str,
    mecanico: str,
    tipo: str,
    descricao: str,
    quilometragem: str,
    role: str,
) -> OrdemServicoCreate:
    """Convert the opening form into a validated payload or raise ``WorkshopFormError``."""
    if not cliente:
        raise WorkshopFormError("Selecione o cliente.")
    if not moto:
        raise WorkshopFormError("Selecione a moto do cliente.")
    if not mecanico and role != "MECANICO":
        raise WorkshopFormError("Informe o mecânico responsável.")
    tipos = {label: value for value, label in TIPO_LABELS.items()}
    if tipo not in tipos:
        raise WorkshopFormError("Selecione o tipo de serviço.")
    km_text = quilometragem.strip()
    try:
        km = int(km_text) if km_text else None
    except ValueError as error:
        raise WorkshopFormError(
            "A quilometragem deve ser um número inteiro não negativo."
        ) from error
    try:
        return OrdemServicoCreate(
            id_moto_cliente=option_id(moto),
            id_mecanico=option_id(mecanico) if mecanico else None,
            tipo_servico=tipos[tipo],
            descricao_problema=descricao,
            quilometragem=km,
        )
    except ValidationError as error:
        raise WorkshopFormError(_first_error(error)) from error


def build_transicao_payload(
    status_atual: str, status_novo: str, observacao: str
) -> TransicaoStatusOS:
    try:
        return TransicaoStatusOS(
            status_atual=status_atual,
            status_novo=status_novo,
            observacao=observacao.strip() or None,
        )
    except ValidationError as error:
        raise WorkshopFormError(_first_error(error)) from error


def _normalize(text: str) -> str:
    """Lowercase text without accents, for tolerant searches."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def produto_row(produto: Produto) -> dict[str, str]:
    saldo = produto.estoque_qtd
    return {
        "id": str(produto.id),
        "codigo": produto.codigo,
        "nome": produto.nome_produto,
        "saldo": str(saldo),
        "preco": format_currency(produto.preco_venda),
        "preco_valor": str(produto.preco_venda),
        "disponivel": "true" if saldo > 0 else "false",
    }


def filtrar_produtos(
    rows: list[dict[str, str]], busca: str, limite: int = PRODUTO_SEARCH_LIMIT
) -> list[dict[str, str]]:
    """Products whose code or name contain the search text, ignoring case and accents."""
    termo = _normalize(busca.strip())
    matches = [
        row
        for row in rows
        if not termo or termo in _normalize(f"{row['codigo']} {row['nome']}")
    ]
    return matches[:limite]


def _find_produto(catalogo: list[dict[str, str]], produto_id: str) -> dict[str, str] | None:
    return next((row for row in catalogo if row["id"] == produto_id), None)


def _parse_quantidade(value: str) -> int:
    message = "A quantidade deve ser um número inteiro maior que zero."
    try:
        quantidade = int(value.strip())
    except ValueError as error:
        raise WorkshopFormError(message) from error
    if quantidade <= 0:
        raise WorkshopFormError(message)
    return quantidade


def build_item_payload(
    tipo: str,
    produto_id: str,
    catalogo: list[dict[str, str]],
    quantidade: str,
    descricao: str,
    valor_unitario: str,
) -> ItemOSCreate:
    """Convert the item form into a validated payload or raise ``WorkshopFormError``.

    The balance check mirrors Xano only to give immediate feedback.
    """
    if tipo == "PECA":
        produto = _find_produto(catalogo, produto_id) if produto_id else None
        if produto is None:
            raise WorkshopFormError("Selecione o produto.")
        qtd = _parse_quantidade(quantidade)
        saldo = int(produto["saldo"])
        if qtd > saldo:
            raise WorkshopFormError(
                f"Saldo insuficiente para {produto['codigo']}: disponível {saldo}."
            )
        return ItemOSCreate(tipo_item="PECA", id_produto=int(produto_id), quantidade=qtd)
    if tipo != "SERVICO":
        raise WorkshopFormError("Escolha entre peça e serviço.")
    if not descricao.strip():
        raise WorkshopFormError("Informe a descrição do serviço.")
    qtd = _parse_quantidade(quantidade)
    if not valor_unitario.strip():
        raise WorkshopFormError("Informe o valor do serviço.")
    try:
        valor = parse_decimal(valor_unitario)
    except InvalidOperation as error:
        raise WorkshopFormError("Informe um valor numérico válido para o serviço.") from error
    try:
        return ItemOSCreate(
            tipo_item="SERVICO",
            descricao=descricao,
            quantidade=qtd,
            valor_unitario=valor,
        )
    except ValidationError as error:
        raise WorkshopFormError(_first_error(error)) from error


def preview_item_total(
    tipo: str, produto: dict[str, str] | None, quantidade: str, valor_unitario: str
) -> Decimal | None:
    """Total of the item being edited, or ``None`` while the form is incomplete."""
    try:
        qtd = int(quantidade.strip())
        if qtd <= 0:
            return None
        if tipo == "PECA":
            return Decimal(produto["preco_valor"]) * qtd if produto else None
        valor = parse_decimal(valor_unitario)
    except (ValueError, InvalidOperation):
        return None
    return valor * qtd if valor > 0 else None


def _moto_label(placa: str | None, modelo: str | None) -> str:
    parts = [part for part in (placa, modelo) if part]
    return " · ".join(parts) or EMPTY_VALUE


def os_row(ordem: OrdemServicoResumo) -> dict[str, str]:
    return {
        "id": str(ordem.id),
        "numero": f"#{ordem.id}",
        "abertura": format_datetime(ordem.data_abertura),
        "cliente": ordem.nome_cliente or EMPTY_VALUE,
        "moto": _moto_label(ordem.placa, ordem.modelo),
        "tipo": TIPO_LABELS.get(ordem.tipo_servico or "", EMPTY_VALUE),
        "mecanico": ordem.nome_mecanico or EMPTY_VALUE,
        "autor": ordem.nome_funcionario or EMPTY_VALUE,
        "descricao": ordem.descricao_problema or "",
        "status": ordem.status,
        "status_label": STATUS_LABELS[ordem.status],
        "total": format_currency(ordem.valor_total),
    }


def detalhe_row(detalhe: OrdemServicoDetalhe) -> dict[str, str]:
    row = os_row(detalhe)
    row.update(
        {
            "id_moto_cliente": str(detalhe.id_moto_cliente),
            "inicio": format_datetime(detalhe.data_inicio),
            "encerramento": format_datetime(detalhe.data_encerramento),
            "quilometragem": (
                f"{detalhe.quilometragem:,} km".replace(",", ".")
                if detalhe.quilometragem is not None
                else EMPTY_VALUE
            ),
            "motivo": detalhe.motivo_cancelamento or "",
        }
    )
    return row


def historico_row(evento: HistoricoStatusOS) -> dict[str, str]:
    return {
        "quando": format_datetime(evento.created_at),
        "de": STATUS_LABELS.get(evento.status_anterior or "", "Abertura"),
        "para": STATUS_LABELS[evento.status_novo],
        "status": evento.status_novo,
        "funcionario": evento.nome_funcionario or EMPTY_VALUE,
        "observacao": evento.observacao or "",
    }


def item_row(item: ItemOrdemServico) -> dict[str, str]:
    if item.tipo_item == "SERVICO":
        descricao = item.descricao or EMPTY_VALUE
    else:
        partes = [parte for parte in (item.codigo, item.nome_produto) if parte]
        descricao = " · ".join(partes) or EMPTY_VALUE
    return {
        "id": str(item.id),
        "tipo": item.tipo_item,
        "tipo_label": ITEM_TIPO_LABELS[item.tipo_item],
        "descricao": descricao,
        "quantidade": str(item.quantidade),
        "unitario": format_currency(item.valor_unitario),
        "total": format_currency(item.valor_total_item),
        "baixado": "true" if item.estoque_baixado else "false",
    }


def totais_row(detalhe: OrdemServicoDetalhe) -> dict[str, str]:
    """Cost summary; Xano recalculates the totals from the items on every detail."""
    total = detalhe.valor_total or Decimal("0")
    return {
        "pecas": format_currency(detalhe.valor_pecas or Decimal("0")),
        "servicos": format_currency(detalhe.valor_servicos or Decimal("0")),
        "total": format_currency(total),
        "total_valor": str(total),
    }


class WorkshopState(AuthState):
    """List, detail, opening and status transitions of service orders."""

    ordens: list[dict[str, str]] = []
    status_filter: str = STATUS_FILTER_ALL
    search_text: str = ""
    current_page: int = 1
    page_size: int = 10
    list_error: str = ""
    is_loading_list: bool = False

    detail_open: bool = False
    is_loading_detail: bool = False
    detalhe: dict[str, str] = {}
    detalhe_historico: list[dict[str, str]] = []
    detalhe_itens: list[dict[str, str]] = []
    detalhe_totais: dict[str, str] = {}
    historico_moto: list[dict[str, str]] = []

    form_open: bool = False
    form_error: str = ""
    is_saving: bool = False
    cliente: str = ""
    moto: str = ""
    mecanico: str = ""
    tipo_servico: str = ""
    descricao_problema: str = ""
    quilometragem: str = ""
    cliente_options: list[str] = []
    motos_cache: list[dict[str, str]] = []
    mecanico_options: list[str] = []

    transition_target: str = ""
    transition_note: str = ""
    transition_error: str = ""
    is_transitioning: bool = False

    catalogo_produtos: list[dict[str, str]] = []
    catalogo_error: str = ""
    item_tipo: str = "PECA"
    produto_busca: str = ""
    item_produto_id: str = ""
    item_quantidade: str = "1"
    item_descricao: str = ""
    item_valor_unitario: str = ""
    item_error: str = ""
    is_saving_item: bool = False
    item_to_remove: str = ""
    is_removing_item: bool = False

    @rx.var
    def can_operate(self) -> bool:
        return can_operate_os(self.employee_role)

    @rx.var
    def status_counts(self) -> dict[str, int]:
        return status_counts(self.ordens)

    def _filtered_rows(self) -> list[dict[str, str]]:
        return filter_rows(filter_by_status(self.ordens, self.status_filter), self.search_text)

    @rx.var
    def visible_rows(self) -> list[dict[str, str]]:
        return paginate(self._filtered_rows(), self.current_page, self.page_size)

    @rx.var
    def total_pages(self) -> int:
        return page_count(len(self._filtered_rows()), self.page_size)

    @rx.var
    def moto_options(self) -> list[str]:
        return motos_do_cliente(self.motos_cache, self.cliente)

    @rx.var
    def available_transitions(self) -> list[dict[str, str]]:
        return allowed_transitions(self.detalhe.get("status", ""), self.employee_role)

    @rx.var
    def transition_label(self) -> str:
        return TRANSITION_ACTIONS.get(self.transition_target, "")

    @rx.var
    def can_edit_items(self) -> bool:
        return can_edit_items(self.detalhe.get("status", ""), self.employee_role)

    @rx.var
    def produtos_filtrados(self) -> list[dict[str, str]]:
        return filtrar_produtos(self.catalogo_produtos, self.produto_busca)

    @rx.var
    def produto_selecionado(self) -> dict[str, str]:
        return _find_produto(self.catalogo_produtos, self.item_produto_id) or {}

    def _preview(self) -> Decimal | None:
        return preview_item_total(
            self.item_tipo,
            _find_produto(self.catalogo_produtos, self.item_produto_id),
            self.item_quantidade,
            self.item_valor_unitario,
        )

    @rx.var
    def item_preview(self) -> str:
        preview = self._preview()
        return format_currency(preview) if preview is not None else ""

    @rx.var
    def total_previsto(self) -> str:
        preview = self._preview()
        if preview is None:
            return ""
        total = Decimal(self.detalhe_totais.get("total_valor", "0"))
        return format_currency(total + preview)

    @rx.var
    def remove_message(self) -> str:
        item = next(
            (row for row in self.detalhe_itens if row["id"] == self.item_to_remove),
            None,
        )
        if item is None:
            return ""
        if item["baixado"] == "true":
            return f"Remover {item['descricao']}? A peça volta ao estoque."
        return f"Remover {item['descricao']}?"

    def _operation_blocked(self) -> bool:
        return operation_is_blocked(
            self.is_loading_list,
            self.is_saving or self.is_saving_item,
            self.is_loading_detail or self.is_transitioning or self.is_removing_item,
        )

    @rx.var
    def is_busy(self) -> bool:
        return self._operation_blocked()

    # ----- list -----

    def _reload_ordens(self, client: XanoClient) -> None:
        self.ordens = [os_row(ordem) for ordem in client.list_ordens_servico()]

    @rx.event
    def load_ordens(self):
        if self.is_loading_list:
            return None
        self.list_error = ""
        self.status_filter = STATUS_FILTER_ALL
        self.current_page = 1
        if not self.is_authenticated or not role_allows_route(
            self.employee_role, WORKSHOP_ROUTE
        ):
            return None
        self.is_loading_list = True
        try:
            with XanoClient(token=self.auth_token) as client:
                self._reload_ordens(client)
        except XanoError as error:
            self.ordens = []
            self.list_error = error_feedback(error)
            if isinstance(error, XanoAuthenticationError):
                return self._xano_error_response(error)
        finally:
            self.is_loading_list = False
        return None

    def _refresh_list(self, client: XanoClient) -> None:
        try:
            self._reload_ordens(client)
        except XanoError as error:
            self.list_error = error_feedback(error)

    @rx.event
    def set_status_filter(self, value: str) -> None:
        self.status_filter = value
        self.current_page = 1

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

    # ----- detail -----

    def _reset_transition(self) -> None:
        self.transition_target = ""
        self.transition_note = ""
        self.transition_error = ""

    def _apply_order(self, detalhe: OrdemServicoDetalhe) -> None:
        self.detalhe = detalhe_row(detalhe)
        self.detalhe_historico = [historico_row(evento) for evento in detalhe.historico]
        self.detalhe_itens = [item_row(item) for item in detalhe.itens]
        self.detalhe_totais = totais_row(detalhe)
        self.item_to_remove = ""
        self._reset_transition()

    def _apply_detail(
        self, detalhe: OrdemServicoDetalhe, historico_moto: list[OrdemServicoResumo]
    ) -> None:
        self._apply_order(detalhe)
        self.historico_moto = [
            os_row(ordem) for ordem in historico_moto if ordem.id != detalhe.id
        ]

    def _load_catalogo(self, client: XanoClient) -> None:
        """Load active products for the item form; a failure keeps the detail usable."""
        self.catalogo_error = ""
        try:
            self.catalogo_produtos = [
                produto_row(produto) for produto in client.list_produtos() if produto.ativo
            ]
        except XanoAuthenticationError:
            raise
        except XanoError as error:
            self.catalogo_produtos = []
            self.catalogo_error = error_feedback(error)

    def _load_detail(self, client: XanoClient, os_id: int) -> None:
        detalhe = client.get_ordem_servico(os_id)
        historico = client.list_ordens_servico(id_moto_cliente=detalhe.id_moto_cliente)
        self._apply_detail(detalhe, historico)
        if can_edit_items(detalhe.status, self.employee_role):
            self._load_catalogo(client)

    def _reset_item_form(self) -> None:
        self.item_tipo = "PECA"
        self.produto_busca = ""
        self.item_produto_id = ""
        self.item_quantidade = "1"
        self.item_descricao = ""
        self.item_valor_unitario = ""
        self.item_error = ""
        self.item_to_remove = ""

    @rx.event
    def open_detail(self, os_id: str):
        if self.is_loading_detail:
            return None
        self.is_loading_detail = True
        self._reset_item_form()
        try:
            with XanoClient(token=self.auth_token) as client:
                self._load_detail(client, int(os_id))
            self.detail_open = True
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.is_loading_detail = False
        return None

    @rx.event
    def close_detail(self) -> None:
        self.detail_open = False
        self._reset_transition()
        self._reset_item_form()

    # ----- opening -----

    @rx.event
    def open_create(self):
        if not can_operate_os(self.employee_role):
            return toast_error("Seu perfil pode apenas consultar ordens de serviço.")
        self.form_error = ""
        self.cliente = ""
        self.moto = ""
        self.mecanico = ""
        self.tipo_servico = ""
        self.descricao_problema = ""
        self.quilometragem = ""
        try:
            with XanoClient(token=self.auth_token) as client:
                clientes = client.list_clientes()
                motos = client.list_motos_clientes()
                mecanicos = client.list_mecanicos()
        except XanoError as error:
            return self._xano_error_response(error)
        self.cliente_options = [
            option_label(cliente.id, cliente.nome_cliente)
            for cliente in clientes
            if cliente.ativo
        ]
        self.motos_cache = [
            {
                "id": str(moto.id),
                "id_cliente": str(moto.id_cliente),
                "label": option_label(moto.id, _moto_label(moto.placa, moto.modelo)),
                "ativo": "true" if moto.ativo else "false",
            }
            for moto in motos
        ]
        self.mecanico_options = [
            option_label(mecanico.id, mecanico.nome_funcionario) for mecanico in mecanicos
        ]
        if self.employee_role == "MECANICO":
            self.mecanico = next(
                (
                    option
                    for option in self.mecanico_options
                    if option_id(option) == self.employee_id
                ),
                "",
            )
        if not self.cliente_options:
            self.form_error = "Cadastre um cliente ativo com moto antes de abrir uma OS."
        elif not self.mecanico_options:
            self.form_error = "Não há mecânicos ativos para assumir a OS."
        self.form_open = True
        return None

    @rx.event
    def close_form(self) -> None:
        self.form_open = False
        self.form_error = ""

    @rx.event
    def set_cliente(self, value: str) -> None:
        self.cliente = value
        self.moto = ""
        self.form_error = ""

    @rx.event
    def set_moto(self, value: str) -> None:
        self.moto = value
        self.form_error = ""

    @rx.event
    def set_mecanico(self, value: str) -> None:
        self.mecanico = value
        self.form_error = ""

    @rx.event
    def set_tipo_servico(self, value: str) -> None:
        self.tipo_servico = value
        self.form_error = ""

    @rx.event
    def set_descricao_problema(self, value: str) -> None:
        self.descricao_problema = value
        self.form_error = ""

    @rx.event
    def set_quilometragem(self, value: str) -> None:
        self.quilometragem = value
        self.form_error = ""

    @rx.event
    def save_os(self):
        if self._operation_blocked():
            return None
        if not can_operate_os(self.employee_role):
            self.form_error = "Seu perfil pode apenas consultar ordens de serviço."
            return toast_error(self.form_error)
        try:
            payload = build_abertura_payload(
                self.cliente,
                self.moto,
                self.mecanico,
                self.tipo_servico,
                self.descricao_problema,
                self.quilometragem,
                self.employee_role,
            )
        except WorkshopFormError as error:
            self.form_error = str(error)
            return toast_error(self.form_error)

        self.is_saving = True
        try:
            with XanoClient(token=self.auth_token) as client:
                ordem = client.abrir_ordem_servico(payload)
                self.form_open = False
                self._refresh_list(client)
            return toast_success(f"OS #{ordem.id} aberta.")
        except XanoValidationError as error:
            self.form_error = error_feedback(error)
            return toast_error(self.form_error)
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.is_saving = False

    # ----- status transitions -----

    @rx.event
    def start_transition(self, target: str) -> None:
        allowed = {
            action["value"]
            for action in allowed_transitions(
                self.detalhe.get("status", ""), self.employee_role
            )
        }
        if target not in allowed:
            return
        self.transition_target = target
        self.transition_note = ""
        self.transition_error = ""

    @rx.event
    def cancel_transition(self) -> None:
        self._reset_transition()

    @rx.event
    def set_transition_note(self, value: str) -> None:
        self.transition_note = value
        self.transition_error = ""

    @rx.event
    def confirm_transition(self):
        if self._operation_blocked():
            return None
        if not can_operate_os(self.employee_role):
            self.transition_error = "Seu perfil pode apenas consultar ordens de serviço."
            return None
        target = self.transition_target
        try:
            payload = build_transicao_payload(
                self.detalhe.get("status", ""), target, self.transition_note
            )
        except WorkshopFormError as error:
            self.transition_error = str(error)
            return None

        os_id = int(self.detalhe["id"])
        self.is_transitioning = True
        try:
            with XanoClient(token=self.auth_token) as client:
                detalhe = client.transicionar_ordem_servico(os_id, payload)
                historico = client.list_ordens_servico(
                    id_moto_cliente=detalhe.id_moto_cliente
                )
                self._apply_detail(detalhe, historico)
                self._refresh_list(client)
            return toast_success(f"OS #{os_id}: {STATUS_LABELS[target].lower()}.")
        except XanoValidationError as error:
            message = error_feedback(error)
            try:
                with XanoClient(token=self.auth_token) as client:
                    self._load_detail(client, os_id)
                    self._refresh_list(client)
            except XanoError:
                pass
            still_allowed = target in {
                action["value"]
                for action in allowed_transitions(
                    self.detalhe.get("status", ""), self.employee_role
                )
            }
            self.transition_target = target if still_allowed else ""
            self.transition_error = message
            return toast_error(message)
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.is_transitioning = False

    # ----- items -----

    @rx.event
    def set_item_tipo(self, value: str | list[str]) -> None:
        # The segmented control reports a list when configured for multiple values.
        if isinstance(value, list):
            value = value[0] if value else ""
        if value in ITEM_TIPO_LABELS:
            self.item_tipo = value
            self.item_error = ""

    @rx.event
    def set_produto_busca(self, value: str) -> None:
        self.produto_busca = value

    @rx.event
    def select_produto(self, produto_id: str) -> None:
        produto = _find_produto(self.catalogo_produtos, produto_id)
        if produto is None or produto["disponivel"] != "true":
            return
        self.item_produto_id = produto_id
        self.item_error = ""

    @rx.event
    def clear_produto(self) -> None:
        self.item_produto_id = ""
        self.item_error = ""

    @rx.event
    def set_item_quantidade(self, value: str) -> None:
        self.item_quantidade = value
        self.item_error = ""

    @rx.event
    def set_item_descricao(self, value: str) -> None:
        self.item_descricao = value
        self.item_error = ""

    @rx.event
    def set_item_valor_unitario(self, value: str) -> None:
        self.item_valor_unitario = value
        self.item_error = ""

    def _item_edit_error(self) -> str:
        if not can_operate_os(self.employee_role):
            return "Seu perfil pode apenas consultar ordens de serviço."
        if not can_edit_items(self.detalhe.get("status", ""), self.employee_role):
            return "Itens só podem ser alterados em OS aberta ou em andamento."
        return ""

    def _apply_item_change(self, client: XanoClient, detalhe: OrdemServicoDetalhe) -> None:
        self._apply_order(detalhe)
        self._load_catalogo(client)
        self._refresh_list(client)

    def _reload_after_item_error(self, os_id: int) -> None:
        """Show the real status, items and balances after Xano rejects an item change."""
        try:
            with XanoClient(token=self.auth_token) as client:
                self._apply_order(client.get_ordem_servico(os_id))
                self._load_catalogo(client)
                self._refresh_list(client)
        except XanoError:
            pass

    @rx.event
    def save_item(self):
        if self._operation_blocked():
            return None
        self.item_error = self._item_edit_error()
        if self.item_error:
            return None
        try:
            payload = build_item_payload(
                self.item_tipo,
                self.item_produto_id,
                self.catalogo_produtos,
                self.item_quantidade,
                self.item_descricao,
                self.item_valor_unitario,
            )
        except WorkshopFormError as error:
            self.item_error = str(error)
            return None

        os_id = int(self.detalhe["id"])
        self.is_saving_item = True
        try:
            with XanoClient(token=self.auth_token) as client:
                detalhe = client.adicionar_item_ordem_servico(os_id, payload)
                self._apply_item_change(client, detalhe)
            self._reset_item_form()
            return toast_success("Item incluído na OS.")
        except XanoValidationError as error:
            message = error_feedback(error)
            self._reload_after_item_error(os_id)
            self.item_error = message
            return toast_error(message)
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.is_saving_item = False

    @rx.event
    def ask_remove_item(self, item_id: str) -> None:
        if can_edit_items(self.detalhe.get("status", ""), self.employee_role):
            self.item_to_remove = item_id
            self.item_error = ""

    @rx.event
    def cancel_remove_item(self) -> None:
        self.item_to_remove = ""

    @rx.event
    def confirm_remove_item(self):
        if self._operation_blocked() or not self.item_to_remove:
            return None
        self.item_error = self._item_edit_error()
        if self.item_error:
            self.item_to_remove = ""
            return None
        os_id = int(self.detalhe["id"])
        item_id = int(self.item_to_remove)
        devolvido = any(
            row["id"] == self.item_to_remove and row["baixado"] == "true"
            for row in self.detalhe_itens
        )
        self.is_removing_item = True
        try:
            with XanoClient(token=self.auth_token) as client:
                detalhe = client.remover_item_ordem_servico(os_id, item_id)
                self._apply_item_change(client, detalhe)
            message = "Item removido da OS."
            if devolvido:
                message += " A peça voltou ao estoque."
            return toast_success(message)
        except XanoValidationError as error:
            message = error_feedback(error)
            self._reload_after_item_error(os_id)
            self.item_error = message
            return toast_error(message)
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.item_to_remove = ""
            self.is_removing_item = False
