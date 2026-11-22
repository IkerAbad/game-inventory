# -*- coding: utf-8 -*-
"""Network layer tests with simulated responses (no real requests)."""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from inventory.i18n import set_lang
from inventory.network import (autocomplete, deku_item, deku_search, mc_search,
                               resolve_hours, steam_estimate, steam_manifests,
                               steam_reviews, steam_search, tag_hours)


class NetworkTests(unittest.TestCase):
    def setUp(self):
        set_lang("en")

    def test_deku_search_and_item(self):
        search_html = "<a href='/items/hades'><h6>Hades &amp; Friends</h6></a>"
        with mock.patch("inventory.network.http_get", return_value=(200, search_html)):
            self.assertEqual(deku_search("Hades"), [("/items/hades", "Hades & Friends")])
        item_html = "<strong>Main Story:</strong> 21\u00bd hours</span>"
        with mock.patch("inventory.network.http_get", return_value=(200, item_html)):
            self.assertEqual(deku_item("/items/hades"), 21.5)
        with mock.patch("inventory.network.http_get", return_value=(404, "")):
            self.assertIsNone(deku_item("/items/hades"))

    def test_tag_hours(self):
        meta = ('<meta name="description" content="Hades (2020). '
                'About 21.5 hours to beat the main story.">')
        with mock.patch("inventory.network.http_get", return_value=(200, meta)):
            self.assertEqual(tag_hours(["Hades"]), (21.5, "Hades", "2020"))
        sequel = ('<meta name="description" content="Hades II (2024). '
                  'About 30 hours to beat the main story.">')
        with mock.patch("inventory.network.http_get", return_value=(200, sequel)):
            self.assertIsNone(tag_hours(["Hades"]))

    def test_steam_search(self):
        payload = {"items": [{"type": "app", "id": 1, "name": "Hades"},
                             {"type": "dlc", "id": 2, "name": "Hades DLC"}]}
        with mock.patch("inventory.network._json_get", return_value=payload):
            self.assertEqual(steam_search(["Hades"]), (1, "Hades"))
        with mock.patch("inventory.network._json_get",
                        return_value={"items": [None, 3, {"type": "app"}]}):
            self.assertIsNone(steam_search(["Hades"]))

    def test_steam_reviews(self):
        payload = {"results": {"rollups": [
            {"recommendations_up": 90, "recommendations_down": 10}]}}
        with mock.patch("inventory.network._json_get", return_value=payload):
            self.assertEqual(steam_reviews(1), (100, 90))
        small = {"results": {"rollups": [
            {"recommendations_up": 5, "recommendations_down": 1}]}}
        with mock.patch("inventory.network._json_get", return_value=small):
            self.assertEqual(steam_reviews(1), (6, None))

    def test_steam_estimate(self):
        html = "".join("<div>%d hrs on record</div>" % (10 + i) for i in range(5))
        with mock.patch("inventory.network.http_get", return_value=(200, html)):
            result = steam_estimate(1)
        self.assertEqual(result, (12.0, 10, [5, 5]))

    def test_mc_search_single_platform(self):
        html = ('<title>Hades Reviews - Metacritic</title>'
                '"gamePlatform":["PC"]'
                '"name":"Metascore","ratingValue":92,"reviewCount":30')
        with mock.patch("inventory.network.http_get", return_value=(200, html)):
            entry = mc_search(["Hades"])
        self.assertEqual(entry["s"], 92)
        self.assertEqual(entry["p"], "PC")
        self.assertEqual(entry["n"], 30)

    def test_mc_search_falls_back_to_console(self):
        base = ('<title>Hades Reviews - Metacritic</title>'
                '"gamePlatform":["PC","PS5"]')

        def fake_get(url, **kwargs):
            if "critic-reviews/?platform=pc" in url:
                return 200, "Showing 12 Critic Review"
            if "critic-reviews/?platform=ps5" in url:
                return 200, ('title="Metascore 90 out of 100" '
                             "Showing 5 Critic Review")
            return 200, base

        with mock.patch("inventory.network.http_get", side_effect=fake_get):
            entry = mc_search(["Hades"])
        self.assertEqual(entry["s"], 90)
        self.assertEqual(entry["p"], "PS5")
        self.assertEqual(entry["n"], 5)

    def test_resolve_hours_deku_then_estimate(self):
        with mock.patch("inventory.network.deku_search",
                        return_value=[("/items/hades", "Hades")]), \
             mock.patch("inventory.network.deku_item", return_value=21.0):
            result = resolve_hours(["Hades"], lambda: (1, "Hades"), "22/11/2026", False)
        self.assertEqual(result["value"], 21.0)
        self.assertEqual(result["source"], "Deku/HLTB")

        with mock.patch("inventory.network.deku_search", return_value=[]), \
             mock.patch("inventory.network.tag_hours", return_value=None), \
             mock.patch("inventory.network.steam_estimate",
                        return_value=(8.5, 10, [5, 5])):
            result = resolve_hours(["Hades"], lambda: (1, "Hades"), "22/11/2026", False)
        self.assertEqual(result["value"], 8.5)
        self.assertIn("ESTIMACION", result["source"])

    def test_autocomplete_fills_hours_and_notes(self):
        game = {"name": "Hades", "duplicate": False}
        hours = {}
        wishlist = {}
        resolved = {"value": 10.0, "nota": "test note", "source": "test",
                    "ambiguous": None}
        with mock.patch("inventory.network.steam_manifests", return_value={}), \
             mock.patch("inventory.network.resolve_hours", return_value=resolved), \
             mock.patch("inventory.network.mc_search",
                        return_value={"s": 90, "p": "PC", "n": 10}), \
             mock.patch("inventory.network._save_json") as save:
            with redirect_stdout(io.StringIO()):
                autocomplete([game], hours, wishlist)
        self.assertEqual(hours["hades"], 10.0)
        self.assertEqual(hours["_notas"]["hades"], "test note")
        self.assertEqual(hours["_metacritic"]["hades"]["s"], 90)
        self.assertTrue(save.called)

    def test_autocomplete_fills_wishlist(self):
        meta = {"juegos": {"Hades": "?"}}
        resolved = {"value": 10.0, "nota": "test note", "source": "test",
                    "ambiguous": None}
        with mock.patch("inventory.network.steam_manifests", return_value={}), \
             mock.patch("inventory.network.resolve_hours", return_value=resolved), \
             mock.patch("inventory.network.mc_search",
                        return_value={"s": 90, "p": "PC", "n": 10}), \
             mock.patch("inventory.network._save_json") as save:
            with redirect_stdout(io.StringIO()):
                autocomplete([], {}, meta)
        self.assertEqual(meta["juegos"]["Hades"], 10.0)
        self.assertEqual(meta["_notas"]["Hades"], "test note")
        self.assertIn("_actualizado", meta)
        self.assertTrue(save.called)

    def test_steam_manifests_parses_acf(self):
        with tempfile.TemporaryDirectory() as d:
            acf = os.path.join(d, "appmanifest_123.acf")
            with open(acf, "w", encoding="utf-8") as f:
                f.write('"AppState" { "appid" "123" "installdir" "Hades" "name" "Hades" }')
            base = os.path.join(d, "steamapps", "common")
            with mock.patch("inventory.network.LIBRARIES", [base]), \
                 mock.patch("inventory.network.glob.glob", return_value=[acf]):
                manifests = steam_manifests()
            self.assertEqual(manifests.get("hades"), (123, "Hades"))


if __name__ == "__main__":
    unittest.main()
