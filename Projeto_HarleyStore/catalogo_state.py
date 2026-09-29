"""Reflex state of the public motorcycle showroom (/catalogo)."""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import reflex as rx

from Projeto_HarleyStore.auth import AuthState
from Projeto_HarleyStore.feedback import error_feedback
from Projeto_HarleyStore.formatting import format_currency
from Projeto_HarleyStore.listing import normalize_text
from Projeto_HarleyStore.services.catalogo import (
    FAMILIA_LABELS,
    ModeloCatalogo,
    catalogo_cache,
)
from Projeto_HarleyStore.services.xano_client import XanoClient, XanoError, XanoNotFoundError


CATALOGO_ROUTE = "/catalogo"
FAMILIA_TODAS = "TODAS"
FAMILIA_TABS: tuple[tuple[str, str], ...] = ((FAMILIA_TODAS, "Todas"), *FAMILIA_LABELS.items())


@dataclasses.dataclass
class CorCard:
    nome: str = ""
    hex: str = ""
    imagem_url: str = ""


@dataclasses.dataclass
class ModeloCard:
    id: str = ""
    nome: str = ""
    familia: str = ""
    familia_label: str = ""
    descricao: str = ""
    imagem: str = ""
    preco_label: str = ""
    disponibilidade: str = ""
    disponivel: bool = False
    destaque: bool = False
    cores: list[CorCard] = dataclasses.field(default_factory=list)


def preco_label(valor: Decimal) -> str:
    return f"A partir de {format_currency(valor)}"


def disponibilidade_label(disponiveis: int) -> str:
    if disponiveis <= 0:
        return "Sob consulta"
    return "1 disponível" if disponiveis == 1 else f"{disponiveis} disponíveis"


def modelo_card(modelo: ModeloCatalogo) -> ModeloCard:
    return ModeloCard(
        id=str(modelo.id),
        nome=modelo.nome_modelo,
        familia=modelo.familia,
        familia_label=FAMILIA_LABELS[modelo.familia],
        descricao=modelo.descricao or "",
        imagem=modelo.imagem_principal,
        preco_label=preco_label(modelo.preco_a_partir),
        disponibilidade=disponibilidade_label(modelo.disponiveis),
        disponivel=modelo.disponiveis > 0,
        destaque=modelo.destaque,
        cores=[CorCard(nome=cor.nome, hex=cor.hex, imagem_url=cor.imagem_url) for cor in modelo.variacoes_cor],
    )


def filtrar_catalogo(cards: list[ModeloCard], familia: str, busca: str) -> list[ModeloCard]:
    """Local filters over the cached catalog (no extra Xano call)."""
    termo = normalize_text(busca.strip())
    return [
        card
        for card in cards
        if (familia == FAMILIA_TODAS or card.familia == familia)
        and (not termo or termo in normalize_text(card.nome))
    ]


def escolher_hero(cards: list[ModeloCard]) -> ModeloCard | None:
    """The featured model leads the hero; without one, the first model does."""
    return next((card for card in cards if card.destaque), cards[0] if cards else None)


def _fetch_catalogo() -> list[ModeloCatalogo]:
    with XanoClient() as client:
        return client.list_catalogo()


class CatalogoState(AuthState):
    """Showroom cards, family tabs, local search and the per-card color choice."""

    cards: list[ModeloCard] = []
    familia: str = FAMILIA_TODAS
    busca: str = ""
    imagem_por_modelo: dict[str, str] = {}
    cor_por_modelo: dict[str, str] = {}
    detalhe_id: str = ""
    is_loading_catalogo: bool = False
    # False until the first load ends, so the empty state never flashes before the data.
    carregado: bool = False
    erro: str = ""

    @rx.var
    def cards_visiveis(self) -> list[ModeloCard]:
        return filtrar_catalogo(self.cards, self.familia, self.busca)

    @rx.var
    def hero(self) -> ModeloCard:
        return escolher_hero(self.cards) or ModeloCard()

    @rx.var
    def tem_hero(self) -> bool:
        return bool(self.cards)

    @rx.var
    def detalhe(self) -> ModeloCard:
        return next((card for card in self.cards if card.id == self.detalhe_id), ModeloCard())

    @rx.event
    def load_catalogo(self):
        if self.is_loading_catalogo:
            return
        self.is_loading_catalogo = True
        self.erro = ""
        try:
            self.cards = [modelo_card(modelo) for modelo in catalogo_cache.get(_fetch_catalogo)]
        except XanoNotFoundError:
            self.cards = []
            self.erro = "Catálogo indisponível no momento."
        except XanoError as error:
            self.cards = []
            self.erro = error_feedback(error)
        finally:
            self.is_loading_catalogo = False
            self.carregado = True

    @rx.event
    def set_familia(self, value: str) -> None:
        if value == FAMILIA_TODAS or value in FAMILIA_LABELS:
            self.familia = value

    @rx.event
    def set_busca(self, value: str) -> None:
        self.busca = value

    @rx.event
    def select_cor(self, modelo_id: str, nome: str, imagem_url: str) -> None:
        """Swap the card photo for the chosen color (no Xano call)."""
        self.imagem_por_modelo = {**self.imagem_por_modelo, modelo_id: imagem_url}
        self.cor_por_modelo = {**self.cor_por_modelo, modelo_id: nome}

    @rx.event
    def open_detail(self, modelo_id: str) -> None:
        self.detalhe_id = modelo_id

    @rx.event
    def close_detail(self) -> None:
        self.detalhe_id = ""
