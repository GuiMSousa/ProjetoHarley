"""DTOs and cache of the motorcycle catalog (commercial models shown in the showroom)."""

from __future__ import annotations

import threading
import time
from decimal import Decimal
from typing import Callable, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class VariacaoCor(BaseModel):
    """Color option of a model: display name, swatch color and the photo in that color."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    nome: str = Field(min_length=1, max_length=60)
    hex: str = Field(pattern=HEX_COLOR)
    imagem_url: str = Field(pattern=HTTPS_URL)


class ModeloMotoCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nome_modelo: str = Field(min_length=1, max_length=120)
    familia: FamiliaMoto
    descricao: str | None = Field(default=None, max_length=2000)
    preco_base: Decimal = Field(gt=0, decimal_places=2)
    imagem_principal: str = Field(pattern=HTTPS_URL)
    variacoes_cor: list[VariacaoCor] = Field(default_factory=list, max_length=MAX_CORES)
    destaque: bool = False


class ModeloMotoUpdate(BaseModel):
    """Partial edit; ``ativo = False`` removes the model from the showroom."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nome_modelo: str | None = Field(default=None, min_length=1, max_length=120)
    familia: FamiliaMoto | None = None
    descricao: str | None = Field(default=None, max_length=2000)
    preco_base: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    imagem_principal: str | None = Field(default=None, pattern=HTTPS_URL)
    variacoes_cor: list[VariacaoCor] | None = Field(default=None, max_length=MAX_CORES)
    destaque: bool | None = None
    ativo: bool | None = None


class ModeloMoto(BaseModel):
    """Model as managed by the store manager (includes inactive ones)."""

    model_config = ConfigDict(extra="ignore")

    id: int
    nome_modelo: str
    familia: FamiliaMoto
    descricao: str | None = None
    preco_base: Decimal
    imagem_principal: str
    variacoes_cor: list[VariacaoCor] = []
    destaque: bool = False
    ativo: bool = True

    @field_validator("variacoes_cor", mode="before")
    @classmethod
    def _null_cores(cls, value: object) -> object:
        return [] if value is None else value

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
    nome_modelo: str
    familia: FamiliaMoto
    descricao: str | None = None
    imagem_principal: str
    variacoes_cor: list[VariacaoCor] = []
    destaque: bool = False
    preco_a_partir: Decimal
    disponiveis: int = 0

    @field_validator("variacoes_cor", mode="before")
    @classmethod
    def _null_cores(cls, value: object) -> object:
        return [] if value is None else value

    @field_validator("destaque", mode="before")
    @classmethod
    def _null_destaque(cls, value: object) -> object:
        return False if value is None else value


T = TypeVar("T")


class TtlCache(Generic[T]):
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
