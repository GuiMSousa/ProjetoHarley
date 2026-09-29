import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from reflex.state import State

from Projeto_HarleyStore.catalogo_state import (
    FAMILIA_TODAS,
    CatalogoState,
    disponibilidade_label,
    escolher_hero,
    filtrar_catalogo,
    modelo_card,
    preco_label,
)
from Projeto_HarleyStore.services.catalogo import ModeloCatalogo, VariacaoCor, catalogo_cache
from Projeto_HarleyStore.services.xano_client import XanoNotFoundError, XanoRateLimitError


def vitrine(modelo_id=3, nome="Street Glide", familia="TOURING", destaque=False, disponiveis=2):
    return ModeloCatalogo(
        id=modelo_id,
        nome_modelo=nome,
        familia=familia,
        imagem_principal=f"https://img.test/{modelo_id}.jpg",
        variacoes_cor=[
            VariacaoCor(nome="Vivid Black", hex="#0B0B0B", imagem_url=f"https://img.test/{modelo_id}-black.jpg"),
            VariacaoCor(nome="Laranja", hex="#FF6600", imagem_url=f"https://img.test/{modelo_id}-orange.jpg"),
        ],
        destaque=destaque,
        preco_a_partir=Decimal("189900"),
        disponiveis=disponiveis,
    )


CARDS = [
    modelo_card(vitrine(3, "Street Glide", "TOURING")),
    modelo_card(vitrine(4, "Fat Boy", "CRUISER", destaque=True)),
    modelo_card(vitrine(5, "Pan América", "ADVENTURE", disponiveis=0)),
]


class CatalogoRulesTests(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(preco_label(Decimal("189900")), "A partir de R$ 189.900,00")
        self.assertEqual(
            [disponibilidade_label(n) for n in (0, 1, 3)],
            ["Sob consulta", "1 disponível", "3 disponíveis"],
        )

    def test_card_projection(self):
        card = CARDS[0]
        self.assertEqual((card.id, card.nome, card.familia_label), ("3", "Street Glide", "Touring"))
        self.assertEqual(card.preco_label, "A partir de R$ 189.900,00")
        self.assertEqual([cor.hex for cor in card.cores], ["#0B0B0B", "#FF6600"])
        self.assertFalse(CARDS[2].disponivel)

    def test_local_filters_by_family_and_accent_insensitive_search(self):
        self.assertEqual(len(filtrar_catalogo(CARDS, FAMILIA_TODAS, "")), 3)
        self.assertEqual([c.id for c in filtrar_catalogo(CARDS, "CRUISER", "")], ["4"])
        self.assertEqual([c.id for c in filtrar_catalogo(CARDS, FAMILIA_TODAS, "america")], ["5"])
        self.assertEqual(filtrar_catalogo(CARDS, "SPORT", ""), [])

    def test_hero_prefers_the_featured_model(self):
        self.assertEqual(escolher_hero(CARDS).id, "4")
        self.assertEqual(escolher_hero(CARDS[:1]).id, "3")
        self.assertIsNone(escolher_hero([]))


class CatalogoStateTests(unittest.TestCase):
    def setUp(self):
        catalogo_cache.invalidate()
        self.addCleanup(catalogo_cache.invalidate)

    def make_state(self, role="", authenticated=False):
        root = State(_reflex_internal_init=True)
        state = root.get_substate(CatalogoState.get_full_name().split("."))
        state.is_authenticated = authenticated
        state.employee_role = role
        return state

    def patched_client(self):
        patcher = patch("Projeto_HarleyStore.catalogo_state.XanoClient")
        client_class = patcher.start()
        self.addCleanup(patcher.stop)
        client = MagicMock()
        client_class.return_value.__enter__.return_value = client
        return client_class, client

    def test_load_uses_the_cache_across_sessions(self):
        client_class, client = self.patched_client()
        client.list_catalogo.return_value = [vitrine(3), vitrine(4, "Fat Boy", "CRUISER", destaque=True)]
        first, second = self.make_state(), self.make_state()
        self.assertFalse(first.carregado)  # the page shows "loading", never a false empty state
        CatalogoState.load_catalogo.fn(first)
        self.assertTrue(first.carregado)
        CatalogoState.load_catalogo.fn(second)
        self.assertEqual(client.list_catalogo.call_count, 1)
        self.assertEqual([card.id for card in second.cards], ["3", "4"])
        self.assertEqual(second.hero.id, "4")
        self.assertTrue(second.tem_hero)
        client_class.assert_called_with()  # public call: no token

    def test_errors_show_a_readable_message(self):
        _, client = self.patched_client()
        for error, message in (
            (XanoNotFoundError("x", status_code=404), "Catálogo indisponível no momento."),
            (XanoRateLimitError("x", status_code=429), "Aguarde alguns segundos"),
        ):
            with self.subTest(error=type(error).__name__):
                catalogo_cache.invalidate()
                client.list_catalogo.side_effect = error
                state = self.make_state()
                CatalogoState.load_catalogo.fn(state)
                self.assertEqual(state.cards, [])
                self.assertIn(message, state.erro)
                self.assertFalse(state.is_loading_catalogo)

    def test_swatch_swaps_the_card_photo_without_calling_xano(self):
        client_class, _ = self.patched_client()
        state = self.make_state()
        state.cards = CARDS
        CatalogoState.select_cor.fn(state, "3", "Laranja", "https://img.test/3-orange.jpg")
        self.assertEqual(state.imagem_por_modelo, {"3": "https://img.test/3-orange.jpg"})
        self.assertEqual(state.cor_por_modelo, {"3": "Laranja"})
        client_class.assert_not_called()

    def test_family_tabs_accept_only_known_families(self):
        state = self.make_state()
        state.cards = CARDS
        CatalogoState.set_familia.fn(state, "CRUISER")
        self.assertEqual([card.id for card in state.cards_visiveis], ["4"])
        CatalogoState.set_familia.fn(state, "SCOOTER")
        self.assertEqual(state.familia, "CRUISER")
        CatalogoState.set_busca.fn(state, "street")
        self.assertEqual(state.cards_visiveis, [])

    def test_detail_opens_from_the_cached_cards(self):
        state = self.make_state()
        state.cards = CARDS
        CatalogoState.open_detail.fn(state, "5")
        self.assertEqual(state.detalhe.nome, "Pan América")
        CatalogoState.close_detail.fn(state)
        self.assertEqual(state.detalhe.id, "")


if __name__ == "__main__":
    unittest.main()
