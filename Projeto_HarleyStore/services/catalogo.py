"""DTOs and cache of the motorcycle catalog (commercial models shown in the showroom)."""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from Projeto_HarleyStore.services.leitura import TextoLido, galeria_lida, lista_lida


FamiliaMoto = Literal["TOURING", "CRUISER", "ADVENTURE", "SPORT"]
FAMILIA_LABELS: dict[str, str] = {
    "TOURING": "Touring",
    "CRUISER": "Cruiser",
    "ADVENTURE": "Adventure",
    "SPORT": "Sport",
}
MAX_CORES = 12
HTTPS_URL = r"^https://\S+$"
HEX_COLOR = r"^#[0-9A-Fa-f]{6}$"


class VariacaoCorCreate(BaseModel):
    """Color option written by the manager: display name, swatch color and the photo in that color."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    nome: str = Field(min_length=1, max_length=60)
    hex: str = Field(pattern=HEX_COLOR)
    imagem_url: str = Field(pattern=HTTPS_URL)


class VariacaoCor(BaseModel):
    """Color option as read from Xano (Change 15): tolerant, but never an unsafe value.

    A color typed outside the app keeps its name; an invalid swatch color or a photo URL that
    is not http(s) reads as empty (no swatch; the model photo is shown).
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    nome: TextoLido = ""
    hex: TextoLido = ""
    imagem_url: TextoLido = ""

    @field_validator("hex")
    @classmethod
    def _hex_valido(cls, value: str) -> str:
        return value if re.match(HEX_COLOR, value) else ""

    @field_validator("imagem_url")
    @classmethod
    def _url_segura(cls, value: str) -> str:
        # Only web photos reach an <img> (Change 17: there are no local photos): never javascript:, data:.
        return value if value.startswith(("https://", "http://")) else ""


class ModeloMotoCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nome_modelo: str = Field(min_length=1, max_length=120)
    familia: FamiliaMoto
    descricao: str | None = Field(default=None, max_length=2000)
    preco_base: Decimal = Field(gt=0, decimal_places=2)
    imagem_principal: str = Field(pattern=HTTPS_URL)
    variacoes_cor: list[VariacaoCorCreate] = Field(default_factory=list, max_length=MAX_CORES)
    destaque: bool = False


class ModeloMotoUpdate(BaseModel):
    """Partial edit; ``ativo = False`` removes the model from the showroom."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nome_modelo: str | None = Field(default=None, min_length=1, max_length=120)
    familia: FamiliaMoto | None = None
    descricao: str | None = Field(default=None, max_length=2000)
    preco_base: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    imagem_principal: str | None = Field(default=None, pattern=HTTPS_URL)
    variacoes_cor: list[VariacaoCorCreate] | None = Field(default=None, max_length=MAX_CORES)
    destaque: bool | None = None
    ativo: bool | None = None


class ModeloMoto(BaseModel):
    """Model as managed by the store manager (includes inactive ones).

    Display fields are tolerant (Change 15); ModeloMotoCreate/Update validate what is written.
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    nome_modelo: TextoLido = ""
    familia: FamiliaMoto
    descricao: str | None = None
    preco_base: Decimal | None = None
    imagem_principal: TextoLido = ""
    variacoes_cor: list[VariacaoCor] = []
    destaque: bool = False
    ativo: bool = True

    @field_validator("variacoes_cor", mode="before")
    @classmethod
    def _null_cores(cls, value: object) -> object:
        return lista_lida(value, (dict, BaseModel))

    @field_validator("destaque", mode="before")
    @classmethod
    def _null_destaque(cls, value: object) -> object:
        return False if value is None else value

    @field_validator("ativo", mode="before")
    @classmethod
    def _null_ativo(cls, value: object) -> object:
        return True if value is None else value


class ModeloCatalogo(BaseModel):
    """Showroom projection: only public fields, availability and the "from" price."""

    model_config = ConfigDict(extra="ignore")

    id: int
    nome_modelo: TextoLido = ""
    familia: FamiliaMoto
    descricao: str | None = None
    # Optional: without it (or with a placeholder) the page shows the neutral image (get_foto_moto).
    imagem_principal: str | None = None
    # Carousel photos (Change 17): Xano sends the /vault/ paths, read here as absolute URLs.
    galeria: list[str] = []
    variacoes_cor: list[VariacaoCor] = []
    destaque: bool = False
    # Null when the model has neither an available unit nor a base price: "Preço sob consulta".
    preco_a_partir: Decimal | None = None
    disponiveis: int = 0

    @field_validator("variacoes_cor", mode="before")
    @classmethod
    def _null_cores(cls, value: object) -> object:
        return lista_lida(value, (dict, BaseModel))

    @field_validator("galeria", mode="before")
    @classmethod
    def _null_galeria(cls, value: object) -> object:
        return galeria_lida(value)

    @field_validator("destaque", mode="before")
    @classmethod
    def _null_destaque(cls, value: object) -> object:
        return False if value is None else value


class TtlCache[T]:
    """Process-wide value with a time to live, shared by every Reflex session.

    The public showroom goes through the same Reflex backend for every visitor;
    caching the catalog keeps page loads below the Xano rate limit (HTTP 429).
    """

    def __init__(self, ttl_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._value: T | None = None
        self._expires_at = 0.0

    def get(self, loader: Callable[[], T]) -> T:
        with self._lock:
            if self._value is not None and self._clock() < self._expires_at:
                return self._value
        value = loader()
        with self._lock:
            self._value = value
            self._expires_at = self._clock() + self._ttl
        return value

    def invalidate(self) -> None:
        with self._lock:
            self._value = None
            self._expires_at = 0.0


CATALOGO_TTL_SECONDS = 60
catalogo_cache: TtlCache[list[ModeloCatalogo]] = TtlCache(CATALOGO_TTL_SECONDS)
