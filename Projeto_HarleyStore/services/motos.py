"""DTOs for the Xano motos resource."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MotoBase(BaseModel):
    """Fields shared by moto create and update payloads."""

    clientes_id: int | None = Field(default=None, gt=0)
    marca: str | None = Field(default=None, min_length=1)
    modelo: str | None = Field(default=None, min_length=1)


class MotoCreate(MotoBase):
    """Payload used to create a moto."""


class MotoUpdate(BaseModel):
    """Partial payload used to update a moto."""

    clientes_id: int | None = Field(default=None, gt=0)
    marca: str | None = Field(default=None, min_length=1)
    modelo: str | None = Field(default=None, min_length=1)


class Moto(MotoBase):
    """Moto returned by the Xano API."""

    model_config = ConfigDict(extra="ignore")

    id: int
    created_at: datetime | None = None
