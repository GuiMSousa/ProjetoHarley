"""Changes 12 and 13: motorcycle photos, the photo gallery and the detail carousel."""

import tempfile
import unittest
from datetime import datetime, UTC
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from reflex.state import State

from Projeto_HarleyStore import ui_helpers
from Projeto_HarleyStore.catalogo_state import CatalogoState, fotos_com_cor, modelo_card
from Projeto_HarleyStore.services.catalogo import ModeloCatalogo, VariacaoCor
from Projeto_HarleyStore.services.motos import MotoEstoque, MotoEstoqueDetalhe
from Projeto_HarleyStore.ui_helpers import get_foto_moto, get_lista_fotos_moto, indice_carrossel
from Projeto_HarleyStore.vendas_state import VendasState, moto_row

from tests.event_runner import run_event


PLACEHOLDER = "https://placehold.co/1600x1000/0B0B0B/FF6600/png?text=Fat+Boy"
REAL = "https://cdn.loja.test/fat-boy-vivid-black.webp"
FAT_BOY = [f"/motos/fat-boy/{n}.fat-boy.jpg" for n in range(1, 5)]


class PastaTemporariaTestCase(unittest.TestCase):
    """assets/motos replaced by a temporary folder with the given files."""

    arquivos: tuple[str, ...] = ()

    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        motos = Path(pasta.name)
        for nome in self.arquivos:
            (motos / nome).parent.mkdir(parents=True, exist_ok=True)
            (motos / nome).write_bytes(b"img")
        patcher = patch.object(ui_helpers, "MOTOS_DIR", motos)
        patcher.start()
        self.addCleanup(patcher.stop)


class FotoMotoTests(PastaTemporariaTestCase):
    arquivos = (
        "fat-boy/1.fat-boy.jpg",
        "fat-boy/3.fat-boy.jpg",
        "fat-boy/default_fat_boy.png",
        "road-king/default_road_king.png",
    )

    def test_real_xano_image_wins(self):
        self.assertEqual(get_foto_moto({"nome_modelo": "Fat Boy", "imagem_principal": REAL}), REAL)

    def test_placeholder_or_missing_image_uses_the_first_local_photo(self):
        for imagem in (PLACEHOLDER, "", "   ", None):
            with self.subTest(imagem=imagem):
                self.assertEqual(
                    get_foto_moto({"nome_modelo": "Fat Boy", "imagem_principal": imagem}),
                    "/motos/fat-boy/1.fat-boy.jpg",
                )
        # The slug ignores case, accents and punctuation.
        self.assertEqual(get_foto_moto({"nome_modelo": "  FAT bóy! "}), "/motos/fat-boy/1.fat-boy.jpg")

    def test_without_local_photos_the_default_art_is_used(self):
        self.assertEqual(get_foto_moto({"nome_modelo": "Road King"}), "/motos/road-king/default_road_king.png")
        self.assertEqual(
            get_foto_moto({"nome_modelo": "Road King", "imagem_principal": PLACEHOLDER}),
            "/motos/road-king/default_road_king.png",
        )

    def test_model_without_any_local_art(self):
        # The remote placeholder beats a broken image; without it, the expected default path.
        self.assertEqual(get_foto_moto({"nome_modelo": "Low Rider", "imagem_principal": PLACEHOLDER}), PLACEHOLDER)
        self.assertEqual(get_foto_moto({"nome_modelo": "Low Rider"}), "/motos/low-rider/default_low_rider.png")

    def test_color_photo_replaces_the_main_image(self):
        modelo = {"nome_modelo": "Fat Boy", "imagem_principal": REAL}
        self.assertEqual(get_foto_moto(modelo, "https://cdn.loja.test/vermelho.webp"), "https://cdn.loja.test/vermelho.webp")
        self.assertEqual(get_foto_moto(modelo, PLACEHOLDER), "/motos/fat-boy/1.fat-boy.jpg")

    def test_color_without_its_own_photo_keeps_the_model_photo(self):
        # A color photo typed outside the app is read as "" (Change 15): never the missing default art.
        modelo = {"nome_modelo": "Low Rider", "imagem_principal": REAL}
        self.assertEqual(get_foto_moto(modelo, ""), REAL)
        self.assertEqual(get_lista_fotos_moto(modelo, ""), [REAL])
        card = modelo_card(ModeloCatalogo(
            id=1, nome_modelo="Low Rider", familia="CRUISER", imagem_principal=REAL,
            variacoes_cor=[{"nome": "Preto", "hex": "000000", "imagem_url": "low-rider.png"}],
        ))
        self.assertEqual(card.cores[0].imagem_url, REAL)

    def test_dtos_and_legacy_units_are_accepted(self):
        self.assertEqual(get_foto_moto(MotoEstoque(id=1, nome_modelo="Fat Boy")), "/motos/fat-boy/1.fat-boy.jpg")
        self.assertEqual(get_foto_moto(MotoEstoque(id=2, modelo="Fat Boy")), "/motos/fat-boy/1.fat-boy.jpg")


class ListaFotosTests(PastaTemporariaTestCase):
    arquivos = (*[f"fat-boy/{n}.fat-boy.jpg" for n in range(1, 5)], "sportster/2.sportster.jpg", "road-king/default_road_king.png")

    def test_valid_xano_gallery_wins(self):
        galeria = ["https://cdn.loja.test/1.jpg", PLACEHOLDER, "", "  https://cdn.loja.test/2.jpg  "]
        self.assertEqual(
            get_lista_fotos_moto({"nome_modelo": "Fat Boy", "galeria": galeria}),
            ["https://cdn.loja.test/1.jpg", "https://cdn.loja.test/2.jpg"],
        )

    def test_local_gallery_in_order_with_only_the_existing_files(self):
        self.assertEqual(get_lista_fotos_moto({"nome_modelo": "Fat Boy", "galeria": [PLACEHOLDER]}), FAT_BOY)
        self.assertEqual(get_lista_fotos_moto({"nome_modelo": "Sportster"}), ["/motos/sportster/2.sportster.jpg"])

    def test_without_a_gallery_the_single_photo_or_default_art(self):
        self.assertEqual(get_lista_fotos_moto({"nome_modelo": "Road King"}), ["/motos/road-king/default_road_king.png"])
        self.assertEqual(get_lista_fotos_moto({"nome_modelo": "Low Rider", "imagem_principal": REAL}), [REAL])

    def test_real_color_photo_leads_the_gallery(self):
        self.assertEqual(get_lista_fotos_moto({"nome_modelo": "Fat Boy"}, REAL), [REAL, *FAT_BOY])
        self.assertEqual(get_lista_fotos_moto({"nome_modelo": "Fat Boy"}, PLACEHOLDER), FAT_BOY)

    def test_carousel_index_wraps_at_both_ends(self):
        self.assertEqual([indice_carrossel(3, 1, 4), indice_carrossel(0, -1, 4), indice_carrossel(1, 1, 4)], [0, 3, 2])
        self.assertEqual(indice_carrossel(0, 1, 0), 0)
        self.assertEqual(fotos_com_cor(["a", "b", "c"], "b"), ["b", "a", "c"])
        self.assertEqual(fotos_com_cor(["a", "b"], None), ["a", "b"])


class FotoNasTelasTests(unittest.TestCase):
    """Uses the photos shipped in assets/motos/<slug>/."""

    def test_showroom_card_photo_colors_and_gallery(self):
        card = modelo_card(
            ModeloCatalogo(
                id=1,
                nome_modelo="Fat Boy",
                familia="CRUISER",
                imagem_principal=PLACEHOLDER,
                variacoes_cor=[VariacaoCor(nome="Preto", hex="#1A1A1A", imagem_url=PLACEHOLDER)],
                preco_a_partir=Decimal("120000"),
            )
        )
        self.assertEqual((card.imagem, card.cores[0].imagem_url), (FAT_BOY[0], FAT_BOY[0]))
        self.assertEqual(card.fotos, FAT_BOY)

    def test_catalog_dto_accepts_a_missing_image_and_maps_the_gallery(self):
        vazio = ModeloCatalogo(
            id=2, nome_modelo="Pan America", familia="ADVENTURE", imagem_principal=None,
            galeria=None, preco_a_partir=Decimal("150000"),
        )
        self.assertEqual((vazio.imagem_principal, vazio.galeria), (None, []))
        self.assertEqual(modelo_card(vazio).imagem, "/motos/pan-america/1.pan-america.jpg")
        xano = ModeloCatalogo(
            id=3, nome_modelo="Pan America", familia="ADVENTURE",
            galeria=["https://cdn.loja.test/pa-1.jpg"], preco_a_partir=Decimal("150000"),
        )
        self.assertEqual(modelo_card(xano).fotos, ["https://cdn.loja.test/pa-1.jpg"])

    def test_stock_unit_row_shows_the_photo_of_its_model(self):
        unidade = MotoEstoque(
            id=9,
            nome_modelo="Street Glide",
            cor="Vivid Black",
            variacoes_cor=[VariacaoCor(nome="Vivid Black", hex="#0B0B0B", imagem_url=PLACEHOLDER)],
        )
        row = moto_row(unidade, "VENDEDOR", 2, datetime(2026, 10, 14, tzinfo=UTC))
        self.assertEqual(row["foto"], "/motos/street-glide/1.street-glide.jpg")


def substate(state_class):
    return State(_reflex_internal_init=True).get_substate(state_class.get_full_name().split("."))


class CarrosselCatalogoTests(unittest.TestCase):
    def make_state(self):
        state = substate(CatalogoState)
        state.cards = [
            modelo_card(ModeloCatalogo(id=1, nome_modelo="Fat Boy", familia="CRUISER", preco_a_partir=Decimal("1"))),
            modelo_card(ModeloCatalogo(id=2, nome_modelo="Sportster", familia="SPORT", preco_a_partir=Decimal("1"))),
        ]
        return state

    def test_navigation_wraps_and_opening_a_model_resets_the_index(self):
        state = self.make_state()
        run_event(CatalogoState.open_detail, state, "1")
        self.assertEqual((state.foto_index, state.foto_atual), (0, FAT_BOY[0]))
        run_event(CatalogoState.foto_anterior, state)
        self.assertEqual((state.foto_index, state.foto_atual), (3, FAT_BOY[3]))
        run_event(CatalogoState.proxima_foto, state)
        self.assertEqual(state.foto_index, 0)
        run_event(CatalogoState.selecionar_foto, state, 2)
        self.assertEqual(state.foto_atual, FAT_BOY[2])
        run_event(CatalogoState.selecionar_foto, state, 9)  # out of range: ignored
        self.assertEqual(state.foto_index, 2)
        run_event(CatalogoState.open_detail, state, "2")
        self.assertEqual(state.foto_index, 0)

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
            variacoes_cor=[VariacaoCor(nome="Vermelho", hex="#8B1E1E", imagem_url=REAL)],
        )
        state = substate(VendasState)
        state.auth_token, state.is_authenticated, state.employee_role = "token", True, "VENDEDOR"
        state.foto_index = 3
        run_event(VendasState.open_detail, state, "9")
        self.assertEqual((state.foto_index, state.detalhe_fotos), (0, [REAL, *FAT_BOY]))
        run_event(VendasState.proxima_foto, state)
        self.assertEqual(state.foto_atual, FAT_BOY[0])
        run_event(VendasState.foto_anterior, state)
        run_event(VendasState.foto_anterior, state)
        self.assertEqual(state.foto_index, 4)
        run_event(VendasState.selecionar_foto, state, 1)
        self.assertEqual(state.foto_atual, FAT_BOY[0])


if __name__ == "__main__":
    unittest.main()
