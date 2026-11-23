# -*- coding: utf-8 -*-
"""Tests for the pieces that need no network or disk: normalization, titles and formatting."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from inventory.data import normalize
from inventory.cell_format import PctSteam, dif_cells, dif_write, mc_cell, mc_comment
from inventory.i18n import get_lang, set_lang, t
from inventory.network import _fmt_h, _hours_text, _slugs, _tokens, match_title
from inventory.text import normalize as shared_normalize


class NormalizeTests(unittest.TestCase):
    def test_symbols_and_case(self):
        self.assertEqual(normalize("Divinity: Original Sin 2"), "divinity original sin 2")

    def test_shared_text_module(self):
        self.assertEqual(shared_normalize("  A   B!  "), "a b")
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
        value, texto = mc_cell({"s": 92, "p": "PS4", "n": 30})
        self.assertEqual(value, 92)
        self.assertIn("PS4", texto)

    def test_steam_fallback(self):
        value, texto = mc_cell(None, {"id": 1, "name": "Juego", "n": 1234,
                                       "desc": "histograma", "pct": 92})
        self.assertIsInstance(value, PctSteam)
        self.assertEqual(int(value), 92)
        self.assertEqual(value.fmt, '"S "0"%"')
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

    def test_metascore_without_data(self):
        value, text = mc_cell({"s": "s/n", "p": "PC", "n": 5})
        self.assertIsNone(value)
        self.assertIn("Sin Metascore", text)

    def test_steam_text_and_prefix(self):
        value, text = mc_cell(None, {"pct": 92, "n": 100, "desc": "d",
                                     "name": "G", "id": 1, "pref": "R",
                                     "txt": "nota"})
        self.assertIsInstance(value, PctSteam)
        self.assertEqual(value.fmt, '"R "0')
        self.assertEqual(text, "Sin Metascore en Metacritic.\nnota")

    def test_difficulty_partial(self):
        h, c, text, inference = dif_cells({"h": 5, "ct": "fuente"})
        self.assertEqual(h, 5)
        self.assertIsNone(c)
        self.assertFalse(inference)
        self.assertIn("respaldada por la fuente citada", text)

    def test_i18n_fallback(self):
        with self.assertRaises(ValueError):
            set_lang("fr")
        set_lang("en")
        self.assertEqual(t("missing.key"), "missing.key")

    def test_metascore_without_dict(self):
        self.assertEqual(mc_cell(3.14), (None, None))

    def test_metascore_reviews_only(self):
        value, text = mc_cell({"s": 85, "n": 10})
        self.assertEqual(value, 85)
        self.assertIsNone(text)

    def test_difficulty_empty(self):
        self.assertEqual(dif_cells({}), (None, None, None, False))

    def test_language_getter(self):
        set_lang("es")
        self.assertEqual(get_lang(), "es")
        set_lang("en")

    def test_metascore_no_data_note(self):
        value, text = mc_cell({"p": "PC"})
        self.assertIsNone(value)
        self.assertIn("sin dato", text)

    def test_metascore_slash_with_note(self):
        value, text = mc_cell({"s": "s/n", "p": "PC", "n": 5, "nota": "rara"})
        self.assertIsNone(value)
        self.assertIn("rara", text)
        self.assertIn("5 resenas", text)

    def test_comment_and_difficulty_write(self):
        import openpyxl
        self.assertEqual(mc_comment("hola").text.splitlines()[0], "Metacritic")
        h, c, text, inference = dif_cells({"h": 5, "c": 5, "ct": "consenso",
                                           "nota": "nota"})
        self.assertEqual((h, c), (5, 5))
        self.assertIn("nota", text)
        wb = openpyxl.Workbook()
        dif_write(wb.active, 1, 1, {"h": 5, "c": 5, "ct": "inferencia", "src": "x"})
        self.assertTrue(wb.active.cell(1, 1).font.italic)

    def test_metacritic_with_odd_fields(self):
        value, texto = mc_cell({"s": 85, "p": 123, "n": "muchas", "nota": ["rara"]})
        self.assertEqual(value, 85)
        self.assertIn("123", texto)
        self.assertIn("rara", texto)

    def test_steam_with_odd_reviews(self):
        value, texto = mc_cell(3.14, {"pct": 92, "n": {"a": 1}, "desc": 3.14,
                                       "name": 5, "id": 1})
        self.assertEqual(int(value), 92)
        self.assertIn("92%", texto)
        self.assertIn("0 resenas", texto)

    def test_steam_pct_out_of_range(self):
        self.assertEqual(mc_cell(None, {"pct": 200}), (None, None))
        self.assertEqual(mc_cell(None, {"pct": -1}), (None, None))

    def test_no_difficulty(self):
        self.assertEqual(dif_cells(None), (None, None, None, False))


if __name__ == "__main__":
    unittest.main()


