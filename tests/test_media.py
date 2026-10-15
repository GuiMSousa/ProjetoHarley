"""Change 12: motorcycle photos (Xano image, local photo, default art) and where they are used."""

import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from Projeto_HarleyStore import ui_helpers
from Projeto_HarleyStore.catalogo_state import modelo_card
from Projeto_HarleyStore.services.catalogo import ModeloCatalogo, VariacaoCor
from Projeto_HarleyStore.services.motos import MotoEstoque
from Projeto_HarleyStore.ui_helpers import get_foto_moto
from Projeto_HarleyStore.vendas_state import moto_row


PLACEHOLDER = "https://placehold.co/1600x1000/0B0B0B/FF6600/png?text=Fat+Boy"
REAL = "https://cdn.loja.test/fat-boy-vivid-black.webp"


class FotoMotoTests(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        motos = Path(pasta.name)
        for nome in ("fat-boy.jpg", "default_fat_boy.png", "default_road_king.png"):
            (motos / nome).write_bytes(b"img")
        patcher = patch.object(ui_helpers, "MOTOS_DIR", motos)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_real_xano_image_wins(self):
        self.assertEqual(get_foto_moto({"nome_modelo": "Fat Boy", "imagem_principal": REAL}), REAL)

    def test_placeholder_or_missing_image_uses_the_local_photo(self):
        for imagem in (PLACEHOLDER, "", "   ", None):
            with self.subTest(imagem=imagem):
                self.assertEqual(get_foto_moto({"nome_modelo": "Fat Boy", "imagem_principal": imagem}), "/motos/fat-boy.jpg")
        # The slug ignores case, accents and punctuation.
        self.assertEqual(get_foto_moto({"nome_modelo": "  FAT bóy! "}), "/motos/fat-boy.jpg")

    def test_without_the_real_photo_the_default_art_is_used(self):
        self.assertEqual(get_foto_moto({"nome_modelo": "Road King"}), "/motos/default_road_king.png")
        self.assertEqual(
            get_foto_moto({"nome_modelo": "Road King", "imagem_principal": PLACEHOLDER}),
            "/motos/default_road_king.png",
        )

    def test_model_without_any_local_art(self):
        # The remote placeholder beats a broken image; without it, the expected default path.
        self.assertEqual(get_foto_moto({"nome_modelo": "Low Rider", "imagem_principal": PLACEHOLDER}), PLACEHOLDER)
        self.assertEqual(get_foto_moto({"nome_modelo": "Low Rider"}), "/motos/default_low_rider.png")

    def test_color_photo_replaces_the_main_image(self):
        modelo = {"nome_modelo": "Fat Boy", "imagem_principal": REAL}
        self.assertEqual(get_foto_moto(modelo, "https://cdn.loja.test/vermelho.webp"), "https://cdn.loja.test/vermelho.webp")
        self.assertEqual(get_foto_moto(modelo, PLACEHOLDER), "/motos/fat-boy.jpg")

    def test_dtos_and_legacy_units_are_accepted(self):
        self.assertEqual(get_foto_moto(MotoEstoque(id=1, nome_modelo="Fat Boy")), "/motos/fat-boy.jpg")
        self.assertEqual(get_foto_moto(MotoEstoque(id=2, modelo="Fat Boy")), "/motos/fat-boy.jpg")


class FotoNasTelasTests(unittest.TestCase):
    """Uses the photos shipped in assets/motos."""

    def test_showroom_card_and_colors_fall_back_to_the_local_photo(self):
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
        self.assertEqual((card.imagem, card.cores[0].imagem_url), ("/motos/fat-boy.jpg", "/motos/fat-boy.jpg"))

    def test_catalog_dto_accepts_a_missing_image_and_prepares_the_gallery(self):
        modelo = ModeloCatalogo(
            id=2, nome_modelo="Pan America", familia="ADVENTURE", imagem_principal=None,
            galeria=None, preco_a_partir=Decimal("150000"),
        )
        self.assertEqual((modelo.imagem_principal, modelo.galeria), (None, []))
        self.assertEqual(modelo_card(modelo).imagem, "/motos/pan-america.jpg")

    def test_stock_unit_row_shows_the_photo_of_its_model(self):
        unidade = MotoEstoque(
            id=9,
            nome_modelo="Street Glide",
            cor="Vivid Black",
            variacoes_cor=[VariacaoCor(nome="Vivid Black", hex="#0B0B0B", imagem_url=PLACEHOLDER)],
        )
        row = moto_row(unidade, "VENDEDOR", 2, datetime(2026, 10, 14, tzinfo=timezone.utc))
        self.assertEqual(row["foto"], "/motos/street-glide.jpg")


if __name__ == "__main__":
    unittest.main()
