"""Changes 12, 13 and 17: motorcycle photos from Xano, the photo gallery and the detail carousel."""

import os
import unittest
from datetime import datetime, UTC
from decimal import Decimal
from unittest.mock import MagicMock, patch
from urllib.parse import unquote

from reflex.state import State

from Projeto_HarleyStore.catalogo_state import CatalogoState, fotos_com_cor, modelo_card
from Projeto_HarleyStore.services.catalogo import ModeloCatalogo, VariacaoCor
from Projeto_HarleyStore.services.motos import MotoEstoque, MotoEstoqueDetalhe
from Projeto_HarleyStore.styles.theme import COLORS
from Projeto_HarleyStore.ui_helpers import FOTO_INDISPONIVEL, get_foto_moto, get_lista_fotos_moto, indice_carrossel
from Projeto_HarleyStore.vendas_state import VendasState, moto_row

from tests.event_runner import run_event


PLACEHOLDER = "https://placehold.co/1600x1000/0B0B0B/FF6600/png?text=Fat+Boy"
REAL = "https://cdn.loja.test/fat-boy-vivid-black.webp"
# The gallery as the DTOs read it from Xano: absolute URLs on the instance origin.
GALERIA = [f"https://x8.xano.test/vault/fb/{n}.jpg" for n in range(1, 5)]


class FotoMotoTests(unittest.TestCase):
    def test_real_xano_image_wins(self):
        self.assertEqual(get_foto_moto({"nome_modelo": "Fat Boy", "imagem_principal": REAL}), REAL)
        # The main and color photos share the gallery sanitizer: https, whatever the scheme case.
        self.assertEqual(get_foto_moto({"imagem_principal": "HTTP://cdn.loja.test/fb.jpg"}), "https://cdn.loja.test/fb.jpg")
        self.assertEqual(get_foto_moto({"imagem_principal": REAL}, "http://cdn.loja.test/cor.jpg"), "https://cdn.loja.test/cor.jpg")

    def test_without_a_real_web_photo_the_neutral_image_is_used(self):
        # Placeholders, empty values and local paths (Change 17: there are no local photos).
        for imagem in (PLACEHOLDER, "", "   ", None, "/motos/fat-boy/1.fat-boy.jpg", "javascript:alert(1)"):
            with self.subTest(imagem=imagem):
                self.assertEqual(get_foto_moto({"nome_modelo": "Fat Boy", "imagem_principal": imagem}), FOTO_INDISPONIVEL)

    def test_neutral_image_is_embedded_in_the_theme_colors(self):
        svg = unquote(FOTO_INDISPONIVEL)
        self.assertTrue(svg.startswith("data:image/svg+xml,<svg"))
        for trecho in (COLORS["surface"], COLORS["muted"], "Foto indisponível"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, svg)

    def test_color_photo_replaces_the_main_image(self):
        modelo = {"nome_modelo": "Fat Boy", "imagem_principal": REAL}
        self.assertEqual(get_foto_moto(modelo, "https://cdn.loja.test/vermelho.webp"), "https://cdn.loja.test/vermelho.webp")
        # A placeholder color photo falls back to the model photo.
        self.assertEqual(get_foto_moto(modelo, PLACEHOLDER), REAL)

    def test_color_without_its_own_photo_keeps_the_model_photo(self):
        # A color photo typed outside the app is read as "" (Change 15): the model photo stays.
        modelo = {"nome_modelo": "Low Rider", "imagem_principal": REAL}
        self.assertEqual(get_foto_moto(modelo, ""), REAL)
        self.assertEqual(get_lista_fotos_moto(modelo, ""), [REAL])
        card = modelo_card(ModeloCatalogo(
            id=1, nome_modelo="Low Rider", familia="CRUISER", imagem_principal=REAL,
            variacoes_cor=[{"nome": "Preto", "hex": "000000", "imagem_url": "low-rider.png"}],
        ))
        self.assertEqual(card.cores[0].imagem_url, REAL)

    def test_dtos_and_legacy_units_are_accepted(self):
        self.assertEqual(get_foto_moto(MotoEstoque(id=1, nome_modelo="Fat Boy", imagem_principal=REAL)), REAL)
        self.assertEqual(get_foto_moto(MotoEstoque(id=2, modelo="Fat Boy")), FOTO_INDISPONIVEL)


class ListaFotosTests(unittest.TestCase):
    def test_valid_xano_gallery_wins(self):
        galeria = ["https://cdn.loja.test/1.jpg", PLACEHOLDER, "", "  https://cdn.loja.test/2.jpg  "]
        self.assertEqual(
            get_lista_fotos_moto({"nome_modelo": "Fat Boy", "imagem_principal": REAL, "galeria": galeria}),
            ["https://cdn.loja.test/1.jpg", "https://cdn.loja.test/2.jpg"],
        )

    def test_without_a_gallery_the_single_photo(self):
        self.assertEqual(get_lista_fotos_moto({"imagem_principal": REAL, "galeria": [PLACEHOLDER]}), [REAL])
        self.assertEqual(get_lista_fotos_moto({"nome_modelo": "Road King"}), [FOTO_INDISPONIVEL])

    def test_real_color_photo_leads_the_gallery(self):
        self.assertEqual(get_lista_fotos_moto({"galeria": GALERIA}, REAL), [REAL, *GALERIA])
        self.assertEqual(get_lista_fotos_moto({"galeria": GALERIA}, GALERIA[2]), GALERIA)
        self.assertEqual(get_lista_fotos_moto({"galeria": GALERIA}, PLACEHOLDER), GALERIA)

    def test_carousel_index_wraps_at_both_ends(self):
        self.assertEqual([indice_carrossel(3, 1, 4), indice_carrossel(0, -1, 4), indice_carrossel(1, 1, 4)], [0, 3, 2])
        self.assertEqual(indice_carrossel(0, 1, 0), 0)
        self.assertEqual(fotos_com_cor(["a", "b", "c"], "b"), ["b", "a", "c"])
        self.assertEqual(fotos_com_cor(["a", "b"], None), ["a", "b"])


class FotoNasTelasTests(unittest.TestCase):
    """The screens read every photo from the Xano DTOs."""

    def test_showroom_card_photo_colors_and_gallery_from_xano(self):
        with patch.dict(os.environ, {"XANO_API_BASE_URL": "https://x8.xano.test/api:Hd3aQ"}):
            modelo = ModeloCatalogo.model_validate({
                "id": 1,
                "nome_modelo": "Fat Boy",
                "familia": "CRUISER",
                "imagem_principal": REAL,
                "galeria": [f"/vault/fb/{n}.jpg" for n in range(1, 5)],
                "variacoes_cor": [{"nome": "Preto", "hex": "#1A1A1A", "imagem_url": PLACEHOLDER}],
                "preco_a_partir": "120000",
            })
        card = modelo_card(modelo)
        self.assertEqual((card.imagem, card.cores[0].imagem_url, card.fotos), (REAL, REAL, GALERIA))

    def test_model_without_photos_shows_the_neutral_image(self):
        vazio = ModeloCatalogo(
            id=2, nome_modelo="Pan America", familia="ADVENTURE", imagem_principal=None,
            galeria=None, preco_a_partir=Decimal("150000"),
        )
        self.assertEqual((vazio.imagem_principal, vazio.galeria), (None, []))
        card = modelo_card(vazio)
        self.assertEqual((card.imagem, card.fotos), (FOTO_INDISPONIVEL, [FOTO_INDISPONIVEL]))

    def test_stock_unit_row_shows_the_photo_of_its_model(self):
        unidade = MotoEstoque(
            id=9,
            nome_modelo="Street Glide",
            imagem_principal=REAL,
            cor="Vivid Black",
            variacoes_cor=[VariacaoCor(nome="Vivid Black", hex="#0B0B0B", imagem_url=PLACEHOLDER)],
        )
        agora = datetime(2026, 10, 14, tzinfo=UTC)
        self.assertEqual(moto_row(unidade, "VENDEDOR", 2, agora)["foto"], REAL)
        legado = MotoEstoque(id=10, modelo="Street Glide")
        self.assertEqual(moto_row(legado, "VENDEDOR", 2, agora)["foto"], FOTO_INDISPONIVEL)


def substate(state_class):
    return State(_reflex_internal_init=True).get_substate(state_class.get_full_name().split("."))


class CarrosselCatalogoTests(unittest.TestCase):
    def make_state(self):
        state = substate(CatalogoState)
        state.cards = [
            modelo_card(ModeloCatalogo(id=1, nome_modelo="Fat Boy", familia="CRUISER", galeria=GALERIA, preco_a_partir=Decimal("1"))),
            modelo_card(ModeloCatalogo(id=2, nome_modelo="Sportster", familia="SPORT", imagem_principal=REAL, preco_a_partir=Decimal("1"))),
        ]
        return state

    def test_navigation_wraps_and_opening_a_model_resets_the_index(self):
        state = self.make_state()
        run_event(CatalogoState.open_detail, state, "1")
        self.assertEqual((state.foto_index, state.foto_atual), (0, GALERIA[0]))
        run_event(CatalogoState.foto_anterior, state)
        self.assertEqual((state.foto_index, state.foto_atual), (3, GALERIA[3]))
        run_event(CatalogoState.proxima_foto, state)
        self.assertEqual(state.foto_index, 0)
        run_event(CatalogoState.selecionar_foto, state, 2)
        self.assertEqual(state.foto_atual, GALERIA[2])
        run_event(CatalogoState.selecionar_foto, state, 9)  # out of range: ignored
        self.assertEqual(state.foto_index, 2)
        run_event(CatalogoState.open_detail, state, "2")
        self.assertEqual((state.foto_index, state.fotos_detalhe), (0, [REAL]))

    def test_chosen_color_leads_the_carousel(self):
        state = self.make_state()
        run_event(CatalogoState.open_detail, state, "1")
        run_event(CatalogoState.selecionar_foto, state, 2)
        run_event(CatalogoState.select_cor, state, "1", "Vermelho", REAL)
        self.assertEqual((state.foto_index, state.fotos_detalhe[0], len(state.fotos_detalhe)), (0, REAL, 5))


class CarrosselVendasTests(unittest.TestCase):
    def test_opening_a_unit_loads_its_gallery_and_resets_the_index(self):
        patcher = patch("Projeto_HarleyStore.vendas_state.XanoClient")
        client_class = patcher.start()
        self.addCleanup(patcher.stop)
        client = MagicMock()
        client_class.return_value.__enter__.return_value = client
        client.get_moto_estoque.return_value = MotoEstoqueDetalhe(
            id=9,
            nome_modelo="Fat Boy",
            cor="Vermelho",
            galeria=GALERIA,
            variacoes_cor=[VariacaoCor(nome="Vermelho", hex="#8B1E1E", imagem_url=REAL)],
        )
        state = substate(VendasState)
        state.auth_token, state.is_authenticated, state.employee_role = "token", True, "VENDEDOR"
        state.foto_index = 3
        run_event(VendasState.open_detail, state, "9")
        self.assertEqual((state.foto_index, state.detalhe_fotos), (0, [REAL, *GALERIA]))
        run_event(VendasState.proxima_foto, state)
        self.assertEqual(state.foto_atual, GALERIA[0])
        run_event(VendasState.foto_anterior, state)
        run_event(VendasState.foto_anterior, state)
        self.assertEqual(state.foto_index, 4)
        run_event(VendasState.selecionar_foto, state, 1)
        self.assertEqual(state.foto_atual, GALERIA[0])


if __name__ == "__main__":
    unittest.main()
