# -*- coding: utf-8 -*-
"""Pruebas de las piezas sin red ni disco: normalizacion, titulos y formato."""

import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from inventory.data import normalize
from inventory.cell_format import PctSteam, dif_cells, mc_cell
from inventory.i18n import set_lang
from inventory.network import _fmt_h, _hours_text, _slugs, _tokens, match_title


class NormalizeTests(unittest.TestCase):
    def test_symbols_and_case(self):
        self.assertEqual(normalize("Divinity: Original Sin 2"), "divinity original sin 2")
        self.assertEqual(normalize("  BALL x PIT  "), "ball x pit")
        self.assertEqual(normalize("Chicken Police - Paint it RED!"), "chicken police paint it red")

    def test_accepts_non_text(self):
        self.assertEqual(normalize(123), "123")
        self.assertEqual(normalize(None), "none")


class TitleTests(unittest.TestCase):
    def test_leading_the(self):
        self.assertEqual(_tokens("The Legend of Zelda"), ["legend", "of", "zelda"])

    def test_roman_numerals(self):
        self.assertEqual(_tokens("Alan Wake II"), ["alan", "wake", "2"])
        self.assertEqual(_tokens("Mega Man X"), ["mega", "man", "x"])

    def test_exact_match(self):
        self.assertEqual(match_title(["Hades"], [("a", "Hades")]), ("a", "Hades"))

    def test_match_ignores_the(self):
        self.assertEqual(match_title(["The Legend of Zelda"], [("a", "Legend of Zelda")]),
                         ("a", "Legend of Zelda"))

    def test_sequel_does_not_match_by_prefix(self):
        self.assertIsNone(match_title(["Hades"], [("a", "Hades II")]))

    def test_multiple_entries_is_ambiguous(self):
        cands = [("a", "Chicken Police"), ("b", "Chicken Police - Paint it RED!")]
        self.assertEqual(match_title(["Chicken"], cands), "ambiguo")

    def test_slugs_try_roman_and_edition(self):
        self.assertIn("alan-wake-2", _slugs("Alan Wake II"))
        self.assertIn("catherine", _slugs("Catherine Classic"))


class HoursTests(unittest.TestCase):
    def test_hours_and_half(self):
        self.assertEqual(_hours_text("21\u00bd hours"), 21.5)

    def test_minutes(self):
        self.assertEqual(_hours_text("45 minutes"), 0.8)

    def test_no_number(self):
        self.assertIsNone(_hours_text("no hay datos"))

    def test_format(self):
        self.assertEqual(_fmt_h(24.7), "24.7")


class FormatTests(unittest.TestCase):
    def setUp(self):
        set_lang("es")

    def tearDown(self):
        set_lang("en")

    def test_metascore_pc(self):
        self.assertEqual(mc_cell({"s": 85, "p": "PC", "n": 48}), (85, None))

    def test_metascore_with_platform(self):
        valor, texto = mc_cell({"s": 92, "p": "PS4", "n": 30})
        self.assertEqual(valor, 92)
        self.assertIn("PS4", texto)

    def test_steam_fallback(self):
        valor, texto = mc_cell(None, {"id": 1, "name": "Juego", "n": 1234,
                                       "desc": "histograma", "pct": 92})
        self.assertIsInstance(valor, PctSteam)
        self.assertEqual(int(valor), 92)
        self.assertEqual(valor.fmt, '"S "0"%"')
        self.assertIn("92%", texto)

    def test_difficulty_consensus(self):
        h, c, texto, inferencia = dif_cells({"h": 5, "c": 3, "ct": "consenso"})
        self.assertEqual((h, c), (5, 3))
        self.assertIn("Habilidad 5/10", texto)
        self.assertFalse(inferencia)

    def test_difficulty_inference_with_source(self):
        h, c, texto, inferencia = dif_cells(
            {"h": 4, "c": 6, "ct": "inferencia", "src": "Wikipedia"})
        self.assertEqual((h, c), (4, 6))
        self.assertIn("fuente citada", texto)
        self.assertTrue(inferencia)

    def test_difficulty_ignores_nan(self):
        h, c, texto, inferencia = dif_cells({"h": float("nan"), "c": 3, "ct": "consenso"})
        self.assertIsNone(h)
        self.assertEqual(c, 3)
        self.assertIn("Habilidad -/10", texto)

    def test_difficulty_with_odd_certainty(self):
        h, c, texto, inferencia = dif_cells({"h": 5, "c": 5, "ct": ["raro"]})
        self.assertEqual((h, c), (5, 5))
        self.assertIn("raro", texto)

    def test_metascore_ignores_nan(self):
        self.assertEqual(mc_cell({"s": float("nan"), "p": "PC"}), (None, None))

    def test_english_output(self):
        set_lang("en")
        _, _, text, _ = dif_cells({"h": 5, "c": 5, "ct": "consenso"})
        self.assertIn("Skill 5/10", text)
        _, comment = mc_cell({"s": 85, "p": "PS4", "n": 10})
        self.assertIn("Platform: PS4", comment)

    def test_metacritic_with_odd_fields(self):
        valor, texto = mc_cell({"s": 85, "p": 123, "n": "muchas", "nota": ["rara"]})
        self.assertEqual(valor, 85)
        self.assertIn("123", texto)
        self.assertIn("rara", texto)

    def test_steam_with_odd_reviews(self):
        valor, texto = mc_cell(3.14, {"pct": 92, "n": {"a": 1}, "desc": 3.14,
                                       "name": 5, "id": 1})
        self.assertEqual(int(valor), 92)
        self.assertIn("92%", texto)
        self.assertIn("0 resenas", texto)

    def test_steam_pct_out_of_range(self):
        self.assertEqual(mc_cell(None, {"pct": 200}), (None, None))
        self.assertEqual(mc_cell(None, {"pct": -1}), (None, None))

    def test_no_difficulty(self):
        self.assertEqual(dif_cells(None), (None, None, None, False))


if __name__ == "__main__":
    unittest.main()
