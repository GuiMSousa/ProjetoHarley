import re
import unittest
from pathlib import Path

from Projeto_HarleyStore.styles.theme import (
    CARD_HOVER,
    COLORS,
    GOOGLE_FONTS_URL,
    PRIMARY_BUTTON,
    SHADOWS,
    STATUS_COLORS,
    TEXT_PAIRS,
    contrast_ratio,
)


ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "Projeto_HarleyStore"
COLOR_LITERAL = re.compile(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b|rgba?\(")


class ThemeTests(unittest.TestCase):
    def test_brand_palette(self):
        # Change 12 (Dark Industrial Premium): obsidian background, #161616 cards with a thin edge.
        self.assertEqual(
            {key: COLORS[key] for key in ("black", "graphite", "surface", "border", "orange", "text", "muted")},
            {
                "black": "#0D0D0D",
                "graphite": "#121212",
                "surface": "#161616",
                "border": "#262626",
                "orange": "#FF6600",
                "text": "#FFFFFF",
                "muted": "#A0A0A0",
            },
        )

    def test_primary_actions_glow_orange_on_hover(self):
        self.assertEqual(SHADOWS["glow"], "0 0 15px rgba(255, 102, 0, 0.25)")
        self.assertEqual(PRIMARY_BUTTON["_hover"]["box_shadow"], SHADOWS["glow"])
        self.assertEqual(CARD_HOVER["_hover"], {"border_color": COLORS["orange"], "box_shadow": SHADOWS["glow"]})

    def test_motorcycle_badges_are_matte_with_their_own_edge(self):
        # Dark background, text and border in the status color: emerald, amber and graphite.
        self.assertEqual(STATUS_COLORS["DISPONIVEL"][1], "#34D399")
        self.assertEqual(STATUS_COLORS["RESERVADA"][1], "#FBBF24")
        self.assertEqual(STATUS_COLORS["VENDIDA"][1], "#A3A3A3")
        for status in ("DISPONIVEL", "RESERVADA", "VENDIDA"):
            background, text = STATUS_COLORS[status]
            with self.subTest(status=status):
                self.assertLess(contrast_ratio(background, COLORS["black"]), 1.5)  # matte, not a solid fill
                self.assertGreaterEqual(contrast_ratio(text, COLORS["surface"]), 4.5)

    def test_contrast_ratio_matches_wcag_reference_values(self):
        self.assertAlmostEqual(contrast_ratio("#FFFFFF", "#000000"), 21.0, places=2)
        self.assertAlmostEqual(contrast_ratio("#000000", "#FF6600"), 7.15, places=2)
        self.assertAlmostEqual(contrast_ratio("#A0A0A0", "#1A1A1A"), 6.66, places=2)
        # White text on Harley orange fails AA: the primary button uses black text.
        self.assertLess(contrast_ratio("#FFFFFF", "#FF6600"), 4.5)
        self.assertEqual(PRIMARY_BUTTON["color"], COLORS["on_orange"])

    def test_every_text_pair_reaches_wcag_aa(self):
        for name, (foreground, background) in TEXT_PAIRS.items():
            with self.subTest(pair=name):
                self.assertGreaterEqual(contrast_ratio(foreground, background), 4.5)

    def test_status_palette_covers_orders_motorcycles_and_records(self):
        self.assertEqual(
            set(STATUS_COLORS),
            {
                "ABERTA",
                "EM_ANDAMENTO",
                "CONCLUIDA",
                "CANCELADA",
                "DISPONIVEL",
                "RESERVADA",
                "VENDIDA",
                "ATIVO",
                "INATIVO",
                "RECEITA",
                "DESPESA",
            },
        )

    def test_colors_live_only_in_the_theme_and_the_global_stylesheet(self):
        for path in PACKAGE.rglob("*.py"):
            relative = path.relative_to(PACKAGE).as_posix()
            if relative == "styles/theme.py":
                continue
            with self.subTest(path=relative):
                self.assertIsNone(COLOR_LITERAL.search(path.read_text(encoding="utf-8")))

    def test_global_stylesheet_applies_brand_accent_fonts_and_uppercase_headings(self):
        css = (ROOT / "assets" / "harley.css").read_text(encoding="utf-8")
        for declaration in (
            "--accent-9: #FF6600;",
            "--accent-contrast: #000000;",
            "--heading-font-family: 'Oswald'",
            "text-transform: uppercase;",
            "outline: 2px solid #FF6600;",
        ):
            with self.subTest(declaration=declaration):
                self.assertIn(declaration, css)
        self.assertIn("family=Oswald", GOOGLE_FONTS_URL)
        self.assertIn("family=Inter", GOOGLE_FONTS_URL)

    def test_app_loads_fonts_before_the_global_stylesheet(self):
        entry = (PACKAGE / "Projeto_HarleyStore.py").read_text(encoding="utf-8")
        self.assertIn('stylesheets=[GOOGLE_FONTS_URL, "/harley.css"]', entry)
        self.assertIn('rx.el.meta(name="theme-color", content=COLORS["black"])', entry)

    def test_global_stylesheet_uses_only_theme_colors(self):
        """harley.css mirrors theme.py: no color outside the token palette (no drift)."""
        css = (ROOT / "assets" / "harley.css").read_text(encoding="utf-8")
        palette = {value.upper() for value in COLORS.values() if value.startswith("#")}
        used = {value.upper() for value in re.findall(r"#[0-9A-Fa-f]{6}\b", css)}
        self.assertTrue(used)
        self.assertLessEqual(used, palette)

    def test_global_stylesheet_covers_dark_mode_motion_and_skip_link(self):
        css = (ROOT / "assets" / "harley.css").read_text(encoding="utf-8")
        for declaration in (
            "color-scheme: dark;",
            "@media (prefers-reduced-motion: reduce)",
            "font-variant-numeric: tabular-nums;",
            "touch-action: manipulation;",
            ".skip-link:focus-visible",
        ):
            with self.subTest(declaration=declaration):
                self.assertIn(declaration, css)


if __name__ == "__main__":
    unittest.main()
