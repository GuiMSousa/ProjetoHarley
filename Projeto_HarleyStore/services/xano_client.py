"""Small HTTP boundary between Reflex and the Xano API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx
from pydantic import TypeAdapter

from Projeto_HarleyStore.services.motos import Moto, MotoCreate, MotoUpdate
from Projeto_HarleyStore.xano_config import xano_api_base_url


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
        self._client = httpx.Client(
            base_url=xano_api_base_url(),
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> XanoClient:
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
    ) -> Any:
        headers: dict[str, str] = {}
        if authenticated:
            if not self._token:
                raise XanoAuthenticationError("A JWT is required for this request.")
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            response = self._client.request(
                method,
                path.lstrip("/"),
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
        if response.status_code == 422:
            raise XanoValidationError(
                "Xano rejected the request data.",
                status_code=response.status_code,
            )
        if response.is_error:
            raise XanoError(
                "The Xano API returned an unexpected error.",
                status_code=response.status_code,
            )
        if not response.content:
            return None
        return response.json()

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        return self.request(
            "GET", path, params=params, authenticated=authenticated
        )

    def post(
        self,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        return self.request(
            "POST", path, json=json, authenticated=authenticated
        )

    def patch(
        self,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        return self.request(
            "PATCH", path, json=json, authenticated=authenticated
        )

    def delete(
        self,
        path: str,
        *,
        authenticated: bool = True,
    ) -> Any:
        return self.request("DELETE", path, authenticated=authenticated)

    def login(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate against Xano without persisting credentials locally."""
        response = self.post(
            "auth/login",
            json={"email": email, "password": password},
            authenticated=False,
        )
        return dict(response)

    def current_user(self) -> dict[str, Any]:
        """Return the authenticated technical user and linked employee."""
        response = self.get("auth/me")
        return dict(response)

    def list_motos(self) -> list[Moto]:
        """List motos returned by the Xano motos endpoint."""
        response = self.get("motos")
        return TypeAdapter(list[Moto]).validate_python(response)

    def create_moto(self, moto: MotoCreate) -> Moto:
        """Create a moto in Xano."""
        response = self.post("motos", json=moto.model_dump())
        return Moto.model_validate(response)

    def update_moto(self, moto_id: int, moto: MotoUpdate) -> Moto:
        """Update the provided fields of a moto in Xano."""
        response = self.patch(
            f"motos/{moto_id}",
            json=moto.model_dump(exclude_unset=True),
        )
        return Moto.model_validate(response)

    def delete_moto(self, moto_id: int) -> None:
        """Delete a moto from Xano."""
        self.delete(f"motos/{moto_id}")
