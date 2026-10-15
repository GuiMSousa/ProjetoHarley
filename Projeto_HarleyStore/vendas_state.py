"""Reflex state of /vendas: stock units, reservations, sales and catalog management."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import InvalidOperation

import reflex as rx
from pydantic import ValidationError

from Projeto_HarleyStore.auth import AuthState, role_allows_route
from Projeto_HarleyStore.feedback import (
    error_feedback,
    toast_error,
    toast_success,
    validation_feedback,
)
from Projeto_HarleyStore.formatting import (
    EMPTY_VALUE,
    format_currency,
    format_datetime,
    parse_decimal,
)
from Projeto_HarleyStore.listing import normalize_text, option_id, option_label
from Projeto_HarleyStore.services.catalogo import (
    FAMILIA_LABELS,
    ModeloMoto,
    ModeloMotoCreate,
    ModeloMotoUpdate,
    catalogo_cache,
)
from Projeto_HarleyStore.services.motos import (
    DIAS_RESERVA_PADRAO,
    STATUS_MOTO_LABELS,
    CancelamentoReservaMoto,
    HistoricoStatusMoto,
    MotoEstoque,
    MotoEstoqueCreate,
    MotoEstoqueDetalhe,
    MotoEstoqueUpdate,
    ReservaMotoCreate,
    VendaMotoCreate,
)
from Projeto_HarleyStore.services.xano_client import (
    XanoAuthenticationError,
    XanoClient,
    XanoError,
    XanoNotFoundError,
    XanoPermissionError,
    XanoValidationError,
)
from Projeto_HarleyStore.ui_helpers import (
    get_foto_moto,
    get_lista_fotos_moto,
    indice_carrossel,
    operation_is_blocked,
)


VENDAS_ROUTE = "/vendas"
ABA_ESTOQUE = "ESTOQUE"
ABAS_STATUS = ("DISPONIVEL", "RESERVADA", "VENDIDA")
SELLER_ROLES = frozenset({"GERENTE", "VENDEDOR"})
FAMILIA_BY_LABEL = {label: value for value, label in FAMILIA_LABELS.items()}
FAMILIA_OPTIONS = list(FAMILIA_LABELS.values())
FIELD_MESSAGES = {
    "id_cliente": "Selecione o cliente.",
    "dias_validade": "A validade deve ser de 1 a 30 dias.",
    "observacao": "A observação deve ter até 500 caracteres.",
    "motivo": "Informe o motivo do cancelamento (até 500 caracteres).",
    "nome_modelo": "Informe o nome do modelo (até 120 caracteres).",
    "familia": "Selecione a família.",
    "descricao": "A descrição deve ter até 2000 caracteres.",
    "preco_base": "O preço base deve ser positivo, com até duas casas decimais.",
    "imagem_principal": "A imagem principal deve ser uma URL https.",
    "variacoes_cor": "Revise as cores: nome, cor no formato #RRGGBB e foto https (até 12 cores).",
    "id_modelo": "Selecione o modelo.",
    "chassi": "O chassi deve ter 17 caracteres (VIN, sem as letras I, O e Q).",
    "cor": "Informe a cor.",
    "ano_modelo": "Ano do modelo inválido.",
    "preco_venda": "O preço de venda deve ser positivo, com até duas casas decimais.",
    "valor_venda": "Informe o valor da venda: maior que zero, com até duas casas decimais.",
    "placa": "Placa inválida: use ABC1234 ou ABC1D23, ou deixe em branco para moto 0 km.",
}


class VendasFormError(ValueError):
    """Readable validation error of the sales forms."""


# ----- rules -----


def can_sell(role: str) -> bool:
    return role in SELLER_ROLES


def can_manage_catalog(role: str) -> bool:
    return role == "GERENTE"


def agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def reserva_vencida(reservada_ate: datetime | None, agora: datetime) -> bool:
    return reservada_ate is not None and reservada_ate < agora


def can_cancel_reservation(moto: MotoEstoque, role: str, employee_id: int, agora: datetime) -> bool:
    """Who reserved, a manager or, after expiry, any seller (mirrors Xano)."""
    if moto.status != "RESERVADA" or not can_sell(role):
        return False
    return (
        role == "GERENTE"
        or moto.id_vendedor_reserva == employee_id
        or reserva_vencida(moto.reservada_ate, agora)
    )


def can_sell_unit(moto: MotoEstoque, role: str) -> bool:
    """Seller or manager, unit with chassis and not sold yet (mirrors Xano).

    A reserved unit stays sellable, but only to the reservation customer.
    """
    return can_sell(role) and moto.status in {"DISPONIVEL", "RESERVADA"} and bool(moto.chassi)


def venda_ainda_possivel(row: dict[str, str] | None, cliente: str) -> bool:
    """Whether a refreshed row may still be sold to the chosen customer (``option_label``)."""
    if row is None or row["pode_vender"] != "true":
        return False
    return row["status"] == "DISPONIVEL" or (bool(cliente) and row["id_cliente"] == str(option_id(cliente)))


def _cor_hex(moto: MotoEstoque) -> str:
    return next((cor.hex for cor in moto.variacoes_cor if cor.nome == moto.cor), "")


def _imagem_cor(moto: MotoEstoque) -> str | None:
    return next((cor.imagem_url for cor in moto.variacoes_cor if cor.nome == moto.cor), None)


def _foto(moto: MotoEstoque) -> str:
    """Photo of the unit's color when the model has one, else the model photo (Change 12)."""
    return get_foto_moto(moto, _imagem_cor(moto))


def moto_row(moto: MotoEstoque, role: str, employee_id: int, agora: datetime) -> dict[str, str]:
    reservada = moto.status == "RESERVADA"
    return {
        "id": str(moto.id),
        "id_modelo": str(moto.id_modelo or ""),
        "modelo": moto.nome_modelo or moto.modelo or "Sem modelo",
        "familia": FAMILIA_LABELS.get(moto.familia or "", EMPTY_VALUE),
        "cor": moto.cor or EMPTY_VALUE,
        "cor_valor": moto.cor or "",
        "cor_hex": _cor_hex(moto),
        "foto": _foto(moto),
        "chassi": moto.chassi or EMPTY_VALUE,
        "chassi_valor": moto.chassi or "",
        "chassi_curto": f"…{moto.chassi[-6:]}" if moto.chassi else EMPTY_VALUE,
        "ano": str(moto.ano_modelo) if moto.ano_modelo else EMPTY_VALUE,
        "ano_valor": str(moto.ano_modelo or ""),
        "preco": format_currency(moto.preco_venda),
        "preco_valor": str(moto.preco_venda or ""),
        "status": moto.status,
        "status_label": STATUS_MOTO_LABELS[moto.status],
        "cliente": moto.nome_cliente or EMPTY_VALUE,
        "id_cliente": str(moto.clientes_id or ""),
        "vendedor": moto.nome_vendedor or EMPTY_VALUE,
        "validade": format_datetime(moto.reservada_ate) if reservada else EMPTY_VALUE,
        "vencida": "true" if reservada and reserva_vencida(moto.reservada_ate, agora) else "false",
        "pode_reservar": (
            "true" if moto.status == "DISPONIVEL" and moto.id_modelo and can_sell(role) else "false"
        ),
        "pode_cancelar": "true" if can_cancel_reservation(moto, role, employee_id, agora) else "false",
        "pode_vender": "true" if can_sell_unit(moto, role) else "false",
    }


def historico_moto_row(evento: HistoricoStatusMoto) -> dict[str, str]:
    return {
        "quando": format_datetime(evento.created_at),
        "de": STATUS_MOTO_LABELS.get(evento.status_anterior or "", "Cadastro"),
        "para": STATUS_MOTO_LABELS[evento.status_novo],
        "status": evento.status_novo,
        "funcionario": evento.nome_funcionario or EMPTY_VALUE,
        "observacao": evento.observacao or "",
    }


def filtrar_motos(
    rows: list[dict[str, str]], aba: str, modelo_id: str, busca: str
) -> list[dict[str, str]]:
    termo = normalize_text(busca.strip())
    return [
        row
        for row in rows
        if (aba == ABA_ESTOQUE or row["status"] == aba)
        and (not modelo_id or row["id_modelo"] == modelo_id)
        and (not termo or termo in normalize_text(f"{row['modelo']} {row['chassi']} {row['cliente']}"))
    ]


def status_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts = {status: 0 for status in ABAS_STATUS}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return counts


def modelo_row(modelo: ModeloMoto) -> dict[str, str]:
    return {
        "id": str(modelo.id),
        "nome": modelo.nome_modelo,
        "familia": FAMILIA_LABELS[modelo.familia],
        "preco_base": format_currency(modelo.preco_base),
        "cores": f"{len(modelo.variacoes_cor)} cor(es)",
        "destaque": "Destaque" if modelo.destaque else "",
        "status": "ATIVO" if modelo.ativo else "INATIVO",
        "ativo": "Ativo" if modelo.ativo else "Inativo",
        "ativo_valor": "true" if modelo.ativo else "false",
    }


def modelo_form(modelo: ModeloMoto | None = None) -> dict[str, str]:
    if modelo is None:
        return {
            "nome_modelo": "",
            "familia": "",
            "descricao": "",
            "preco_base": "",
            "imagem_principal": "",
            "destaque": "false",
        }
    return {
        "nome_modelo": modelo.nome_modelo,
        "familia": FAMILIA_LABELS[modelo.familia],
        "descricao": modelo.descricao or "",
        "preco_base": str(modelo.preco_base),
        "imagem_principal": modelo.imagem_principal,
        "destaque": "true" if modelo.destaque else "false",
    }


def empty_cor() -> dict[str, str]:
    return {"nome": "", "hex": "", "imagem_url": ""}


def _parse_decimal(value: str, field: str):
    try:
        return parse_decimal(value)
    except InvalidOperation as error:
        raise VendasFormError(FIELD_MESSAGES[field]) from error


def _parse_int(value: str, field: str) -> int:
    try:
        return int(value.strip())
    except ValueError as error:
        raise VendasFormError(FIELD_MESSAGES[field]) from error


def build_reserva_payload(cliente: str, dias: str, observacao: str) -> ReservaMotoCreate:
    if not cliente:
        raise VendasFormError(FIELD_MESSAGES["id_cliente"])
    dias_validade = _parse_int(dias or str(DIAS_RESERVA_PADRAO), "dias_validade")
    try:
        return ReservaMotoCreate(
            id_cliente=option_id(cliente),
            dias_validade=dias_validade,
            observacao=observacao.strip() or None,
        )
    except ValidationError as error:
        raise VendasFormError(validation_feedback(error, FIELD_MESSAGES)) from error


def build_cancelamento_payload(motivo: str) -> CancelamentoReservaMoto:
    try:
        return CancelamentoReservaMoto(motivo=motivo)
    except ValidationError as error:
        raise VendasFormError(validation_feedback(error, FIELD_MESSAGES)) from error


def valor_inicial_venda(preco_valor: str) -> str:
    """The unit price, typed like the form expects it (``189900,00``); blank without a price."""
    return f"{parse_decimal(preco_valor):.2f}".replace(".", ",") if preco_valor else ""


def build_venda_payload(
    moto_id: str, cliente: str, valor: str, placa: str, observacao: str
) -> VendaMotoCreate:
    if not cliente:
        raise VendasFormError(FIELD_MESSAGES["id_cliente"])
    valor_venda = _parse_decimal(valor, "valor_venda")
    try:
        return VendaMotoCreate(
            id_moto=int(moto_id),
            id_cliente=option_id(cliente),
            valor_venda=valor_venda,
            placa=placa,
            observacao=observacao,
        )
    except ValidationError as error:
        raise VendasFormError(validation_feedback(error, FIELD_MESSAGES)) from error


def build_modelo_payload(
    form: dict[str, str], cores: list[dict[str, str]], editing: bool
) -> ModeloMotoCreate | ModeloMotoUpdate:
    if form.get("familia", "") not in FAMILIA_BY_LABEL:
        raise VendasFormError(FIELD_MESSAGES["familia"])
    data = {
        "nome_modelo": form.get("nome_modelo", ""),
        "familia": FAMILIA_BY_LABEL[form["familia"]],
        "descricao": form.get("descricao", "").strip() or None,
        "preco_base": _parse_decimal(form.get("preco_base", ""), "preco_base"),
        "imagem_principal": form.get("imagem_principal", ""),
        # Blank rows of the color editor are ignored.
        "variacoes_cor": [cor for cor in cores if any(value.strip() for value in cor.values())],
        "destaque": form.get("destaque") == "true",
    }
    try:
        return ModeloMotoUpdate(**data) if editing else ModeloMotoCreate(**data)
    except ValidationError as error:
        raise VendasFormError(validation_feedback(error, FIELD_MESSAGES)) from error


def build_moto_payload(form: dict[str, str], editing: bool) -> MotoEstoqueCreate | MotoEstoqueUpdate:
    data = {
        "chassi": form.get("chassi", ""),
        "cor": form.get("cor", ""),
        "ano_modelo": _parse_int(form.get("ano_modelo", ""), "ano_modelo"),
        "preco_venda": _parse_decimal(form.get("preco_venda", ""), "preco_venda"),
    }
    try:
        if editing:
            return MotoEstoqueUpdate(**data)
        if not form.get("modelo"):
            raise VendasFormError(FIELD_MESSAGES["id_modelo"])
        return MotoEstoqueCreate(id_modelo=option_id(form["modelo"]), **data)
    except ValidationError as error:
        raise VendasFormError(validation_feedback(error, FIELD_MESSAGES)) from error


# ----- state -----


class VendasState(AuthState):
    """Stock units by status, reservations and (for managers) models and units."""

    motos: list[dict[str, str]] = []
    aba: str = "DISPONIVEL"
    filtro_modelo: str = ""
    busca: str = ""
    list_error: str = ""
    is_loading_list: bool = False

    detail_open: bool = False
    detalhe: dict[str, str] = {}
    detalhe_historico: list[dict[str, str]] = []
    detalhe_fotos: list[str] = []
    foto_index: int = 0
    is_loading_detail: bool = False

    reserva_moto_id: str = ""
    reserva_cliente: str = ""
    reserva_dias: str = str(DIAS_RESERVA_PADRAO)
    reserva_observacao: str = ""
    reserva_error: str = ""
    cliente_options: list[str] = []
    is_reserving: bool = False

    cancel_moto_id: str = ""
    cancel_motivo: str = ""
    cancel_error: str = ""
    is_cancelling: bool = False

    venda_moto_id: str = ""
    venda_cliente: str = ""
    venda_cliente_fixo: bool = False
    venda_valor: str = ""
    venda_placa: str = ""
    venda_observacao: str = ""
    venda_error: str = ""
    is_selling: bool = False

    modelos: list[dict[str, str]] = []
    cores_por_modelo: dict[str, list[dict[str, str]]] = {}
    modelo_form_open: bool = False
    modelo_editing_id: str = ""
    modelo_dados: dict[str, str] = {}
    modelo_cores: list[dict[str, str]] = []
    modelo_error: str = ""
    is_saving_modelo: bool = False

    moto_form_open: bool = False
    moto_editing_id: str = ""
    moto_dados: dict[str, str] = {}
    moto_error: str = ""
    is_saving_moto: bool = False

    @rx.var
    def can_manage(self) -> bool:
        return can_manage_catalog(self.employee_role)

    @rx.var
    def visible_rows(self) -> list[dict[str, str]]:
        return filtrar_motos(self.motos, self.aba, self.filtro_modelo, self.busca)

    @rx.var
    def counts(self) -> dict[str, int]:
        return status_counts(filtrar_motos(self.motos, ABA_ESTOQUE, self.filtro_modelo, ""))

    @rx.var
    def filtro_modelo_nome(self) -> str:
        return next(
            (row["modelo"] for row in self.motos if row["id_modelo"] == self.filtro_modelo),
            "",
        )

    @rx.var
    def modelo_options(self) -> list[str]:
        return [
            option_label(row["id"], row["nome"])
            for row in self.modelos
            if row["ativo_valor"] == "true"
        ]

    @rx.var
    def cor_options(self) -> list[str]:
        modelo = self.moto_dados.get("modelo", "")
        modelo_id = str(option_id(modelo)) if modelo else self.moto_dados.get("id_modelo", "")
        return [cor["nome"] for cor in self.cores_por_modelo.get(modelo_id, [])]

    @rx.var
    def venda_resumo(self) -> dict[str, str]:
        """Row of the unit being sold, for the summary at the top of the sale modal."""
        moto_id = self.venda_moto_id
        return next((row for row in self.motos if row["id"] == moto_id), {})

    def _row(self, moto_id: str) -> dict[str, str] | None:
        return next((row for row in self.motos if row["id"] == moto_id), None)

    def _operation_blocked(self) -> bool:
        return operation_is_blocked(
            self.is_loading_list,
            self.is_reserving
            or self.is_cancelling
            or self.is_selling
            or self.is_saving_modelo
            or self.is_saving_moto,
            self.is_loading_detail,
        )

    @rx.var
    def is_busy(self) -> bool:
        return self._operation_blocked()

    # ----- list -----

    def _reload(self, client: XanoClient) -> None:
        agora = agora_utc()
        self.motos = [
            moto_row(moto, self.employee_role, self.employee_id, agora)
            for moto in client.list_motos_estoque()
        ]
        if can_manage_catalog(self.employee_role):
            modelos = client.list_modelos_moto()
            self.modelos = [modelo_row(modelo) for modelo in modelos]
            self.cores_por_modelo = {
                str(modelo.id): [cor.model_dump() for cor in modelo.variacoes_cor]
                for modelo in modelos
            }

    def _refresh(self, client: XanoClient) -> None:
        try:
            self._reload(client)
        except XanoError as error:
            self.list_error = error_feedback(error)

    @rx.event
    def load_vendas(self):
        if self.is_loading_list:
            return None
        self.list_error = ""
        self.busca = ""
        self.aba = "DISPONIVEL"
        self.filtro_modelo = self.router.url.query_parameters.get("modelo", "")
        if not self.is_authenticated or not role_allows_route(self.employee_role, VENDAS_ROUTE):
            return None
        self.is_loading_list = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                self._reload(client)
        except XanoError as error:
            self.motos = []
            self.list_error = error_feedback(error)
            if isinstance(error, XanoAuthenticationError):
                return self._xano_error_response(error)
        finally:
            self.is_loading_list = False
        return None

    @rx.event
    def set_aba(self, value: str) -> None:
        if value in ABAS_STATUS or (value == ABA_ESTOQUE and can_manage_catalog(self.employee_role)):
            self.aba = value

    @rx.event
    def set_busca(self, value: str) -> None:
        self.busca = value

    @rx.event
    def clear_filtro_modelo(self) -> None:
        self.filtro_modelo = ""

    # ----- detail -----

    def _apply_detail(self, detalhe: MotoEstoqueDetalhe) -> None:
        self.detalhe = moto_row(detalhe, self.employee_role, self.employee_id, agora_utc())
        self.detalhe_historico = [historico_moto_row(evento) for evento in detalhe.historico]
        self.detalhe_fotos = get_lista_fotos_moto(detalhe, _imagem_cor(detalhe))
        self.foto_index = 0

    @rx.var
    def foto_atual(self) -> str:
        fotos = self.detalhe_fotos
        return fotos[self.foto_index] if 0 <= self.foto_index < len(fotos) else (fotos[0] if fotos else "")

    @rx.event
    def proxima_foto(self) -> None:
        self.foto_index = indice_carrossel(self.foto_index, 1, len(self.detalhe_fotos))

    @rx.event
    def foto_anterior(self) -> None:
        self.foto_index = indice_carrossel(self.foto_index, -1, len(self.detalhe_fotos))

    @rx.event
    def selecionar_foto(self, index: int) -> None:
        if 0 <= index < len(self.detalhe_fotos):
            self.foto_index = index

    @rx.event
    def open_detail(self, moto_id: str):
        if self._operation_blocked():
            return None
        self.is_loading_detail = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                self._apply_detail(client.get_moto_estoque(int(moto_id)))
            self.detail_open = True
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.is_loading_detail = False
        return None

    @rx.event
    def close_detail(self) -> None:
        self.detail_open = False

    # ----- reservation -----

    @rx.event
    def open_reserva(self, moto_id: str):
        if not can_sell(self.employee_role):
            return toast_error("Seu perfil não pode reservar motos.")
        if self._operation_blocked():
            return None
        self.is_loading_detail = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                clientes = client.list_clientes()
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.is_loading_detail = False
        self.cliente_options = [
            option_label(cliente.id, cliente.nome_cliente) for cliente in clientes if cliente.ativo
        ]
        self.detail_open = False  # opened from the detail panel: the form takes its place
        self.reserva_moto_id = moto_id
        self.reserva_cliente = ""
        self.reserva_dias = str(DIAS_RESERVA_PADRAO)
        self.reserva_observacao = ""
        self.reserva_error = "" if self.cliente_options else "Cadastre um cliente ativo antes de reservar."
        return None

    @rx.event
    def close_reserva(self) -> None:
        self.reserva_moto_id = ""
        self.reserva_error = ""

    @rx.event
    def set_reserva_cliente(self, value: str) -> None:
        self.reserva_cliente = value
        self.reserva_error = ""

    @rx.event
    def set_reserva_dias(self, value: str) -> None:
        self.reserva_dias = value
        self.reserva_error = ""

    @rx.event
    def set_reserva_observacao(self, value: str) -> None:
        self.reserva_observacao = value
        self.reserva_error = ""

    @rx.event
    def confirm_reserva(self):
        if self._operation_blocked() or not self.reserva_moto_id:
            return None
        try:
            payload = build_reserva_payload(
                self.reserva_cliente, self.reserva_dias, self.reserva_observacao
            )
        except VendasFormError as error:
            self.reserva_error = str(error)
            return None
        moto_id = int(self.reserva_moto_id)
        self.is_reserving = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                detalhe = client.reservar_moto(moto_id, payload)
                catalogo_cache.invalidate()
                self._refresh(client)
            self.reserva_moto_id = ""
            if self.detail_open:
                self._apply_detail(detalhe)
            return toast_success("Moto reservada.")
        except XanoValidationError as error:
            self.reserva_error = error_feedback(error)
            try:
                with XanoClient(token=self.auth_token) as client:
                    self._refresh(client)
            except XanoError:
                pass
            return toast_error(self.reserva_error)
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.is_reserving = False

    # ----- cancellation -----

    @rx.event
    def open_cancelamento(self, moto_id: str) -> None:
        self.cancel_moto_id = moto_id
        self.cancel_motivo = ""
        self.cancel_error = ""

    @rx.event
    def close_cancelamento(self) -> None:
        self.cancel_moto_id = ""
        self.cancel_error = ""

    @rx.event
    def set_cancel_motivo(self, value: str) -> None:
        self.cancel_motivo = value
        self.cancel_error = ""

    @rx.event
    def confirm_cancelamento(self):
        if self._operation_blocked() or not self.cancel_moto_id:
            return None
        try:
            payload = build_cancelamento_payload(self.cancel_motivo)
        except VendasFormError as error:
            self.cancel_error = str(error)
            return None
        moto_id = int(self.cancel_moto_id)
        self.is_cancelling = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                detalhe = client.cancelar_reserva_moto(moto_id, payload)
                catalogo_cache.invalidate()
                self._refresh(client)
            self.cancel_moto_id = ""
            if self.detail_open:
                self._apply_detail(detalhe)
            return toast_success("Reserva cancelada. A moto voltou a ficar disponível.")
        except XanoValidationError as error:
            self.cancel_error = error_feedback(error)
            return toast_error(self.cancel_error)
        except XanoError as error:
            if error.status_code == 403:
                self.cancel_error = error_feedback(error)
                return toast_error(self.cancel_error)
            return self._xano_error_response(error)
        finally:
            self.is_cancelling = False

    # ----- sale -----

    @rx.event
    def open_venda(self, moto_id: str):
        if not can_sell(self.employee_role):
            return toast_error("Seu perfil não pode vender motos.")
        row = self._row(moto_id)
        if row is None or row["pode_vender"] != "true":
            return toast_error("Esta moto não está disponível para venda.")
        if row["status"] == "RESERVADA":
            # A reserved unit is sold only to the reservation customer (mirrors Xano).
            cliente = option_label(row["id_cliente"], row["cliente"])
            self.cliente_options = [cliente]
            self.venda_cliente = cliente
            self.venda_cliente_fixo = True
        else:
            if self._operation_blocked():
                return None
            self.is_loading_detail = True
            yield  # render the busy state before the Xano call
            try:
                with XanoClient(token=self.auth_token) as client:
                    clientes = client.list_clientes()
            except XanoError as error:
                return self._xano_error_response(error)
            finally:
                self.is_loading_detail = False
            self.cliente_options = [
                option_label(cliente.id, cliente.nome_cliente) for cliente in clientes if cliente.ativo
            ]
            self.venda_cliente = ""
            self.venda_cliente_fixo = False
        self.detail_open = False  # opened from the detail panel: the form takes its place
        self.venda_moto_id = moto_id
        self.venda_valor = valor_inicial_venda(row["preco_valor"])
        self.venda_placa = ""
        self.venda_observacao = ""
        self.venda_error = "" if self.cliente_options else "Cadastre um cliente ativo antes de vender."
        return None

    @rx.event
    def close_venda(self) -> None:
        self.venda_moto_id = ""
        self.venda_error = ""

    @rx.event
    def set_venda_cliente(self, value: str) -> None:
        if not self.venda_cliente_fixo:
            self.venda_cliente = value
        self.venda_error = ""

    @rx.event
    def set_venda_valor(self, value: str) -> None:
        self.venda_valor = value
        self.venda_error = ""

    @rx.event
    def set_venda_placa(self, value: str) -> None:
        self.venda_placa = value
        self.venda_error = ""

    @rx.event
    def set_venda_observacao(self, value: str) -> None:
        self.venda_observacao = value
        self.venda_error = ""

    @rx.event
    def confirm_venda(self):
        if self._operation_blocked() or not self.venda_moto_id:
            return None
        try:
            payload = build_venda_payload(
                self.venda_moto_id,
                self.venda_cliente,
                self.venda_valor,
                self.venda_placa,
                self.venda_observacao,
            )
        except VendasFormError as error:
            self.venda_error = str(error)
            return None
        self.is_selling = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                client.vender_moto(payload)
                catalogo_cache.invalidate()
                self._refresh(client)
            self.venda_moto_id = ""
            return toast_success("Venda concluída: a moto foi registrada para o cliente.")
        except (XanoValidationError, XanoNotFoundError) as error:
            # Usually another employee changed the unit first: show its new status.
            message = error_feedback(error)
            try:
                with XanoClient(token=self.auth_token) as client:
                    self._refresh(client)
            except XanoError:
                pass
            if venda_ainda_possivel(self._row(self.venda_moto_id), self.venda_cliente):
                self.venda_error = message
            else:
                self.venda_moto_id = ""
            return toast_error(message)
        except XanoPermissionError as error:
            self.venda_error = error_feedback(error)
            return toast_error(self.venda_error)
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.is_selling = False

    # ----- catalog management (manager) -----

    @rx.event
    def open_modelo_create(self) -> None:
        if not can_manage_catalog(self.employee_role):
            return
        self.modelo_editing_id = ""
        self.modelo_dados = modelo_form()
        self.modelo_cores = [empty_cor()]
        self.modelo_error = ""
        self.modelo_form_open = True

    @rx.event
    def open_modelo_edit(self, modelo_id: str):
        if not can_manage_catalog(self.employee_role):
            return None
        try:
            with XanoClient(token=self.auth_token) as client:
                modelo = next(
                    (item for item in client.list_modelos_moto() if str(item.id) == modelo_id),
                    None,
                )
        except XanoError as error:
            return self._xano_error_response(error)
        if modelo is None:
            return toast_error("Modelo não encontrado.")
        self.modelo_editing_id = modelo_id
        self.modelo_dados = modelo_form(modelo)
        self.modelo_cores = [cor.model_dump() for cor in modelo.variacoes_cor] or [empty_cor()]
        self.modelo_error = ""
        self.modelo_form_open = True
        return None

    @rx.event
    def close_modelo_form(self) -> None:
        self.modelo_form_open = False
        self.modelo_error = ""

    @rx.event
    def set_modelo_field(self, field: str, value: str) -> None:
        self.modelo_dados = {**self.modelo_dados, field: value}
        self.modelo_error = ""

    @rx.event
    def set_modelo_destaque(self, value: bool) -> None:
        self.modelo_dados = {**self.modelo_dados, "destaque": "true" if value else "false"}

    @rx.event
    def add_cor(self) -> None:
        self.modelo_cores = [*self.modelo_cores, empty_cor()]

    @rx.event
    def remove_cor(self, index: int) -> None:
        self.modelo_cores = [cor for position, cor in enumerate(self.modelo_cores) if position != index]

    @rx.event
    def set_cor_field(self, index: int, field: str, value: str) -> None:
        self.modelo_cores = [
            {**cor, field: value} if position == index else cor
            for position, cor in enumerate(self.modelo_cores)
        ]
        self.modelo_error = ""

    @rx.event
    def save_modelo(self):
        if self._operation_blocked() or not can_manage_catalog(self.employee_role):
            return None
        editing = bool(self.modelo_editing_id)
        try:
            payload = build_modelo_payload(self.modelo_dados, self.modelo_cores, editing)
        except VendasFormError as error:
            self.modelo_error = str(error)
            return None
        self.is_saving_modelo = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                if editing:
                    client.atualizar_modelo_moto(int(self.modelo_editing_id), payload)
                else:
                    client.criar_modelo_moto(payload)
                catalogo_cache.invalidate()
                self._refresh(client)
            self.modelo_form_open = False
            return toast_success("Modelo salvo.")
        except XanoValidationError as error:
            self.modelo_error = error_feedback(error)
            return toast_error(self.modelo_error)
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.is_saving_modelo = False

    @rx.event
    def toggle_modelo_ativo(self, modelo_id: str, ativo: str):
        if self._operation_blocked() or not can_manage_catalog(self.employee_role):
            return None
        self.is_saving_modelo = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                client.atualizar_modelo_moto(int(modelo_id), ModeloMotoUpdate(ativo=ativo != "true"))
                catalogo_cache.invalidate()
                self._refresh(client)
            return toast_success(
                "Modelo retirado do catálogo." if ativo == "true" else "Modelo de volta ao catálogo."
            )
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.is_saving_modelo = False

    @rx.event
    def open_moto_create(self) -> None:
        if not can_manage_catalog(self.employee_role):
            return
        self.moto_editing_id = ""
        self.moto_dados = {"modelo": "", "chassi": "", "cor": "", "ano_modelo": "", "preco_venda": ""}
        self.moto_error = ""
        self.moto_form_open = True

    @rx.event
    def open_moto_edit(self, moto_id: str) -> None:
        if not can_manage_catalog(self.employee_role):
            return
        row = self._row(moto_id)
        if row is None:
            return
        self.moto_editing_id = moto_id
        self.moto_dados = {
            "id_modelo": row["id_modelo"],
            "chassi": row["chassi_valor"],
            "cor": row["cor_valor"],
            "ano_modelo": row["ano_valor"],
            "preco_venda": row["preco_valor"],
        }
        self.moto_error = ""
        self.moto_form_open = True

    @rx.event
    def close_moto_form(self) -> None:
        self.moto_form_open = False
        self.moto_error = ""

    @rx.event
    def set_moto_field(self, field: str, value: str) -> None:
        dados = {**self.moto_dados, field: value}
        if field == "modelo":
            dados["cor"] = ""
        self.moto_dados = dados
        self.moto_error = ""

    @rx.event
    def save_moto(self):
        if self._operation_blocked() or not can_manage_catalog(self.employee_role):
            return None
        editing = bool(self.moto_editing_id)
        try:
            payload = build_moto_payload(self.moto_dados, editing)
        except VendasFormError as error:
            self.moto_error = str(error)
            return None
        self.is_saving_moto = True
        yield  # render the busy state before the Xano call
        try:
            with XanoClient(token=self.auth_token) as client:
                if editing:
                    client.atualizar_moto_estoque(int(self.moto_editing_id), payload)
                else:
                    client.cadastrar_moto_estoque(payload)
                catalogo_cache.invalidate()
                self._refresh(client)
            self.moto_form_open = False
            return toast_success("Unidade salva.")
        except XanoValidationError as error:
            self.moto_error = error_feedback(error)
            return toast_error(self.moto_error)
        except XanoError as error:
            return self._xano_error_response(error)
        finally:
            self.is_saving_moto = False
