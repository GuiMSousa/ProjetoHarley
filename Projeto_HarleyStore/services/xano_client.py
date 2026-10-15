"""Small HTTP boundary between Reflex and the Xano API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Self, TypeVar

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError

from Projeto_HarleyStore.services.balcao import VendaBalcaoCreate, VendaBalcaoDetalhe
from Projeto_HarleyStore.services.motos import (
    CancelamentoReservaMoto,
    MotoEstoque,
    MotoEstoqueCreate,
    MotoEstoqueDetalhe,
    MotoEstoqueUpdate,
    ReservaMotoCreate,
    VendaMotoCreate,
    VendaMotoResultado,
)
from Projeto_HarleyStore.services.catalogo import (
    ModeloCatalogo,
    ModeloMoto,
    ModeloMotoCreate,
    ModeloMotoUpdate,
)
from Projeto_HarleyStore.services.cadastros import (
    Cliente,
    ClienteCreate,
    ClienteUpdate,
    Fornecedor,
    FornecedorCreate,
    FornecedorUpdate,
    Funcionario,
    FuncionarioCreate,
    FuncionarioUpdate,
    MotoCliente,
    MotoClienteCreate,
    MotoClienteUpdate,
    Produto,
    ProdutoCreate,
    ProdutoUpdate,
)
from Projeto_HarleyStore.services.entradas import (
    EntradaMercadoriaCreate,
    EntradaMercadoriaDetalhe,
    EntradaMercadoriaResumo,
)
from Projeto_HarleyStore.services.financeiro import PeriodoFinanceiro, ResumoFinanceiro
from Projeto_HarleyStore.services.ordens_servico import (
    ItemOSCreate,
    Mecanico,
    OrdemServicoCreate,
    OrdemServicoDetalhe,
    OrdemServicoResumo,
    TransicaoStatusOS,
)
from Projeto_HarleyStore.xano_config import (
    xano_api_base_url,
    xano_auth_api_base_url,
)


ModelT = TypeVar("ModelT", bound=BaseModel)

MAX_VALIDATION_MESSAGE_LENGTH = 200


def validation_message(response: httpx.Response) -> str | None:
    """Return Xano's business validation message when it is short plain text."""
    try:
        payload = response.json()
    except ValueError:
        return None
    message = payload.get("message") if isinstance(payload, dict) else None
    if not isinstance(message, str):
        return None
    message = message.strip()
    if not message or len(message) > MAX_VALIDATION_MESSAGE_LENGTH:
        return None
    return message


class XanoError(RuntimeError):
    """Base error for failed Xano requests."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class XanoAuthenticationError(XanoError):
    """Raised when the JWT is missing or rejected by Xano."""


class XanoPermissionError(XanoError):
    """Raised when the authenticated user lacks permission."""


class XanoValidationError(XanoError):
    """Raised when Xano rejects the request payload."""


class XanoNotFoundError(XanoError):
    """Raised when the requested Xano resource does not exist."""


class XanoResponseError(XanoError):
    """Raised when a successful Xano response violates its contract."""


class XanoRateLimitError(XanoError):
    """Raised when Xano throttles the workspace (HTTP 429)."""


class AuthTokenResponse(BaseModel):
    """Minimal response returned by the Xano login endpoint."""

    authToken: str
    user_id: int | None = None


class XanoUser(BaseModel):
    """Safe technical identity returned by Xano."""

    id: int
    name: str | None = None
    email: str | None = None
    role: str | None = None
    id_funcionario: int | None = None


class XanoEmployee(BaseModel):
    """Domain employee linked to the authenticated user."""

    id: int
    nome_funcionario: str
    cargo: str | None = None
    tipo: str
    contato: str | None = None
    ativo: bool = True


class CurrentUserResponse(BaseModel):
    """Safe identity payload returned by ``auth/me``."""

    user: XanoUser
    funcionario: XanoEmployee | None = None


class XanoClient:
    """Authenticated HTTP client for the Xano API boundary."""

    def __init__(
        self,
        *,
        token: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._token = token.strip() if token else None
        self._auth_base_url = xano_auth_api_base_url()
        self._client = httpx.Client(
            base_url=xano_api_base_url(),
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
        authenticated: bool = True,
        response_model: type[ModelT] | TypeAdapter[ModelT] | None = None,
        base_url: str | None = None,
    ) -> Any:
        """Call a Xano endpoint.

        ``base_url`` targets another API group (each group has its own
        ``/api:<canonical>`` URL); by default the business group is used.
        """
        headers: dict[str, str] = {}
        url = path.lstrip("/")
        if base_url:
            url = f"{base_url.rstrip('/')}/{url}"
        if authenticated:
            if not self._token:
                raise XanoAuthenticationError("A JWT is required for this request.")
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            response = self._client.request(
                method,
                url,
                headers=headers,
                json=json,
                params=params,
            )
        except httpx.HTTPError as error:
            raise XanoError("Unable to reach the Xano API.") from error

        if response.status_code == 401:
            raise XanoAuthenticationError(
                "The Xano session is invalid or expired.",
                status_code=response.status_code,
            )
        if response.status_code == 403:
            raise XanoPermissionError(
                "The authenticated user is not allowed to perform this action.",
                status_code=response.status_code,
            )
        if response.status_code == 404:
            raise XanoNotFoundError(
                "The requested Xano resource was not found.",
                status_code=response.status_code,
            )
        if response.status_code == 429:
            raise XanoRateLimitError(
                "The Xano API rate limit was reached.",
                status_code=response.status_code,
            )
        if response.status_code in {400, 422}:
            raise XanoValidationError(
                validation_message(response) or "Xano rejected the request data.",
                status_code=response.status_code,
            )
        if response.is_error:
            raise XanoError(
                "The Xano API returned an unexpected error.",
                status_code=response.status_code,
            )
        if not response.content:
            return None
        try:
            payload = response.json()
        except ValueError as error:
            raise XanoResponseError(
                "The Xano API returned an invalid JSON response.",
                status_code=response.status_code,
            ) from error
        if response_model is None:
            return payload
        try:
            if isinstance(response_model, TypeAdapter):
                return response_model.validate_python(payload)
            return response_model.model_validate(payload)
        except ValidationError as error:
            raise XanoResponseError(
                "The Xano API returned an unexpected response payload.",
                status_code=response.status_code,
            ) from error

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        authenticated: bool = True,
        response_model: type[ModelT] | TypeAdapter[ModelT] | None = None,
        base_url: str | None = None,
    ) -> Any:
        return self.request(
            "GET",
            path,
            params=params,
            authenticated=authenticated,
            response_model=response_model,
            base_url=base_url,
        )

    def post(
        self,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
        authenticated: bool = True,
        response_model: type[ModelT] | TypeAdapter[ModelT] | None = None,
        base_url: str | None = None,
    ) -> Any:
        return self.request(
            "POST",
            path,
            json=json,
            authenticated=authenticated,
            response_model=response_model,
            base_url=base_url,
        )

    def patch(
        self,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
        authenticated: bool = True,
        response_model: type[ModelT] | TypeAdapter[ModelT] | None = None,
    ) -> Any:
        return self.request(
            "PATCH",
            path,
            json=json,
            authenticated=authenticated,
            response_model=response_model,
        )

    def delete(
        self,
        path: str,
        *,
        authenticated: bool = True,
    ) -> Any:
        return self.request("DELETE", path, authenticated=authenticated)

    def _list_resource(self, path: str, model: type[ModelT]) -> list[ModelT]:
        return self.get(path, response_model=TypeAdapter(list[model]))

    def _create_resource(
        self, path: str, payload: BaseModel, model: type[ModelT]
    ) -> ModelT:
        return self.post(
            path,
            json=payload.model_dump(mode="json"),
            response_model=model,
        )

    def _update_resource(
        self,
        path: str,
        payload: BaseModel,
        model: type[ModelT],
    ) -> ModelT:
        return self.patch(
            path,
            json=payload.model_dump(mode="json", exclude_unset=True),
            response_model=model,
        )

    def _deactivate_resource(self, path: str, model: type[ModelT]) -> ModelT:
        return self.patch(path, json={"ativo": False}, response_model=model)

    def login(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate against Xano without persisting credentials locally."""
        response = self.post(
            "auth/login",
            json={"email": email, "password": password},
            authenticated=False,
            response_model=AuthTokenResponse,
            base_url=self._auth_base_url,
        )
        return response.model_dump()

    def current_user(self) -> CurrentUserResponse:
        """Return the authenticated technical user and linked employee."""
        return self.get(
            "auth/me",
            response_model=CurrentUserResponse,
            base_url=self._auth_base_url,
        )

    def list_clientes(self) -> list[Cliente]:
        return self._list_resource("clientes", Cliente)

    def create_cliente(self, cliente: ClienteCreate) -> Cliente:
        return self._create_resource("clientes", cliente, Cliente)

    def update_cliente(self, cliente_id: int, cliente: ClienteUpdate) -> Cliente:
        return self._update_resource(f"clientes/{cliente_id}", cliente, Cliente)

    def deactivate_cliente(self, cliente_id: int) -> Cliente:
        return self._deactivate_resource(f"clientes/{cliente_id}", Cliente)

    def list_motos_clientes(self) -> list[MotoCliente]:
        return self._list_resource("motos_clientes", MotoCliente)

    def create_moto_cliente(self, moto: MotoClienteCreate) -> MotoCliente:
        return self._create_resource("motos_clientes", moto, MotoCliente)

    def update_moto_cliente(
        self, moto_id: int, moto: MotoClienteUpdate
    ) -> MotoCliente:
        return self._update_resource(f"motos_clientes/{moto_id}", moto, MotoCliente)

    def deactivate_moto_cliente(self, moto_id: int) -> MotoCliente:
        return self._deactivate_resource(f"motos_clientes/{moto_id}", MotoCliente)

    def list_produtos(self) -> list[Produto]:
        return self._list_resource("produtos", Produto)

    def create_produto(self, produto: ProdutoCreate) -> Produto:
        return self._create_resource("produtos", produto, Produto)

    def update_produto(self, produto_id: int, produto: ProdutoUpdate) -> Produto:
        return self._update_resource(f"produtos/{produto_id}", produto, Produto)

    def deactivate_produto(self, produto_id: int) -> Produto:
        return self._deactivate_resource(f"produtos/{produto_id}", Produto)

    def list_fornecedores(self) -> list[Fornecedor]:
        return self._list_resource("fornecedores", Fornecedor)

    def create_fornecedor(self, fornecedor: FornecedorCreate) -> Fornecedor:
        return self._create_resource("fornecedores", fornecedor, Fornecedor)

    def update_fornecedor(
        self, fornecedor_id: int, fornecedor: FornecedorUpdate
    ) -> Fornecedor:
        return self._update_resource(
            f"fornecedores/{fornecedor_id}", fornecedor, Fornecedor
        )

    def deactivate_fornecedor(self, fornecedor_id: int) -> Fornecedor:
        return self._deactivate_resource(f"fornecedores/{fornecedor_id}", Fornecedor)

    def list_funcionarios(self) -> list[Funcionario]:
        return self._list_resource("funcionarios", Funcionario)

    def create_funcionario(self, funcionario: FuncionarioCreate) -> Funcionario:
        return self._create_resource("funcionarios", funcionario, Funcionario)

    def update_funcionario(
        self, funcionario_id: int, funcionario: FuncionarioUpdate
    ) -> Funcionario:
        return self._update_resource(
            f"funcionarios/{funcionario_id}", funcionario, Funcionario
        )

    def deactivate_funcionario(self, funcionario_id: int) -> Funcionario:
        return self._deactivate_resource(f"funcionarios/{funcionario_id}", Funcionario)

    def list_entradas(self) -> list[EntradaMercadoriaResumo]:
        return self._list_resource("entrada_mercadoria", EntradaMercadoriaResumo)

    def get_entrada(self, entrada_id: int) -> EntradaMercadoriaDetalhe:
        return self.get(
            f"entrada_mercadoria/{entrada_id}",
            response_model=EntradaMercadoriaDetalhe,
        )

    def registrar_entrada(
        self, entrada: EntradaMercadoriaCreate
    ) -> EntradaMercadoriaDetalhe:
        """Register a goods receipt; Xano updates stock atomically."""
        return self._create_resource(
            "entrada_mercadoria", entrada, EntradaMercadoriaDetalhe
        )

    def list_ordens_servico(
        self,
        *,
        status: str | None = None,
        id_moto_cliente: int | None = None,
    ) -> list[OrdemServicoResumo]:
        """List service orders, optionally filtered by status or customer bike."""
        params = {
            key: value
            for key, value in {"status": status, "id_moto_cliente": id_moto_cliente}.items()
            if value is not None
        }
        return self.get(
            "ordens_servico",
            params=params or None,
            response_model=TypeAdapter(list[OrdemServicoResumo]),
        )

    def get_ordem_servico(self, os_id: int) -> OrdemServicoDetalhe:
        return self.get(
            f"ordens_servico/{os_id}",
            response_model=OrdemServicoDetalhe,
        )

    def abrir_ordem_servico(self, ordem: OrdemServicoCreate) -> OrdemServicoDetalhe:
        """Open a service order; Xano sets status, author, customer and date."""
        return self.post(
            "ordens_servico",
            json=ordem.model_dump(mode="json", exclude_none=True),
            response_model=OrdemServicoDetalhe,
        )

    def transicionar_ordem_servico(
        self, os_id: int, transicao: TransicaoStatusOS
    ) -> OrdemServicoDetalhe:
        """Move a service order through the status machine enforced by Xano."""
        return self.post(
            f"ordens_servico/{os_id}/status",
            json=transicao.model_dump(mode="json"),
            response_model=OrdemServicoDetalhe,
        )

    def adicionar_item_ordem_servico(
        self, os_id: int, item: ItemOSCreate
    ) -> OrdemServicoDetalhe:
        """Add a part or service; Xano prices parts and takes them out of stock."""
        return self.post(
            f"ordens_servico/{os_id}/itens",
            json=item.model_dump(mode="json", exclude_none=True),
            response_model=OrdemServicoDetalhe,
        )

    def remover_item_ordem_servico(
        self, os_id: int, item_id: int
    ) -> OrdemServicoDetalhe:
        """Remove an item; parts taken out of stock are returned by Xano."""
        return self.request(
            "DELETE",
            f"ordens_servico/{os_id}/itens/{item_id}",
            response_model=OrdemServicoDetalhe,
        )

    def list_mecanicos(self) -> list[Mecanico]:
        return self.get("oficina/mecanicos", response_model=TypeAdapter(list[Mecanico]))

    # ----- motorcycle catalog -----

    def list_catalogo(
        self, *, familia: str | None = None, busca: str | None = None
    ) -> list[ModeloCatalogo]:
        """Public showroom: callable without a session, only showroom fields."""
        params = {
            key: value for key, value in {"familia": familia, "busca": busca}.items() if value
        }
        return self.get(
            "catalogo",
            params=params or None,
            authenticated=False,
            response_model=TypeAdapter(list[ModeloCatalogo]),
        )

    def get_modelo_catalogo(self, modelo_id: int) -> ModeloCatalogo:
        return self.get(
            f"catalogo/{modelo_id}", authenticated=False, response_model=ModeloCatalogo
        )

    def list_modelos_moto(self) -> list[ModeloMoto]:
        return self.get("modelos_moto", response_model=TypeAdapter(list[ModeloMoto]))

    def criar_modelo_moto(self, modelo: ModeloMotoCreate) -> ModeloMoto:
        return self.post(
            "modelos_moto",
            json=modelo.model_dump(mode="json", exclude_none=True),
            response_model=ModeloMoto,
        )

    def atualizar_modelo_moto(self, modelo_id: int, modelo: ModeloMotoUpdate) -> ModeloMoto:
        """PATCH with only the fields set by the caller."""
        return self.patch(
            f"modelos_moto/{modelo_id}",
            json=modelo.model_dump(mode="json", exclude_unset=True),
            response_model=ModeloMoto,
        )

    # ----- stock units and reservations -----

    def list_motos_estoque(
        self, *, status: str | None = None, id_modelo: int | None = None
    ) -> list[MotoEstoque]:
        params = {
            key: value
            for key, value in {"status": status, "id_modelo": id_modelo}.items()
            if value is not None
        }
        return self.get(
            "motos", params=params or None, response_model=TypeAdapter(list[MotoEstoque])
        )

    def get_moto_estoque(self, moto_id: int) -> MotoEstoqueDetalhe:
        return self.get(f"motos/{moto_id}", response_model=MotoEstoqueDetalhe)

    def cadastrar_moto_estoque(self, moto: MotoEstoqueCreate) -> MotoEstoqueDetalhe:
        return self.post(
            "motos", json=moto.model_dump(mode="json"), response_model=MotoEstoqueDetalhe
        )

    def atualizar_moto_estoque(self, moto_id: int, moto: MotoEstoqueUpdate) -> MotoEstoqueDetalhe:
        return self.patch(
            f"motos/{moto_id}",
            json=moto.model_dump(mode="json", exclude_unset=True),
            response_model=MotoEstoqueDetalhe,
        )

    def reservar_moto(self, moto_id: int, reserva: ReservaMotoCreate) -> MotoEstoqueDetalhe:
        """Reserve an available unit; seller and expiry are set by Xano."""
        return self.post(
            f"motos/{moto_id}/reserva",
            json=reserva.model_dump(mode="json", exclude_none=True),
            response_model=MotoEstoqueDetalhe,
        )

    def cancelar_reserva_moto(
        self, moto_id: int, cancelamento: CancelamentoReservaMoto
    ) -> MotoEstoqueDetalhe:
        return self.post(
            f"motos/{moto_id}/reserva/cancelar",
            json=cancelamento.model_dump(mode="json"),
            response_model=MotoEstoqueDetalhe,
        )

    # ----- consolidated financial view -----

    def resumo_financeiro(self, periodo: PeriodoFinanceiro) -> ResumoFinanceiro:
        """Revenue (transactions) and expenses (goods receipts) of the period; GERENTE only.

        Transactions are immutable (Change 10): there is no write method for them.
        """
        return self.get(
            "financeiro/resumo", params=periodo.params(), response_model=ResumoFinanceiro
        )

    def vender_moto(self, venda: VendaMotoCreate) -> VendaMotoResultado:
        """Close the sale atomically in Xano (customer bike, MOTO transaction, VENDIDA).

        The seller comes from the JWT; an absent plate (0 km bike) is not sent.
        """
        return self.post(
            "vender_moto",
            json=venda.model_dump(mode="json", exclude_none=True),
            response_model=VendaMotoResultado,
        )

    def vender_balcao(self, venda: VendaBalcaoCreate) -> VendaBalcaoDetalhe:
        """Counter sale (GERENTE/VENDEDOR): transaction, items and stock exit in one call.

        Prices come from the products in Xano; repeating ``chave_venda`` returns the sale
        already registered instead of selling twice. Without a customer, the sale is to the
        final consumer and ``id_cliente`` is not sent.
        """
        return self.post(
            "balcao/vendas",
            json=venda.model_dump(mode="json", exclude_none=True),
            response_model=VendaBalcaoDetalhe,
        )
