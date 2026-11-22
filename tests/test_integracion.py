# -*- coding: utf-8 -*-
"""End-to-end test: main() with fake data and games."""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import openpyxl

from inventory.cli import main


def fake_game(name, gb):
    return {"name": name, "gb": gb, "days": 3, "unit": "C:",
            "path": "C:\\" + name, "duplicate": False}


class IntegrationTests(unittest.TestCase):
    def test_full_main(self):
        with tempfile.TemporaryDirectory() as d:
            data_dir = os.path.join(d, "data_dir")
            os.makedirs(data_dir)
            paths = {
                "HOURS_JSON": os.path.join(data_dir, "hours.json"),
                "WISHLIST_JSON": os.path.join(data_dir, "wishlist.json"),
                "COMPLETED_JSON": os.path.join(data_dir, "completed.json"),
                "PLAYING_JSON": os.path.join(data_dir, "playing.json"),
            }
            with open(paths["HOURS_JSON"], "w", encoding="utf-8") as f:
                json.dump({
                    "juego a": 10.0,
                    "juego b": None,
                    "_notas": {"juego a": "nota de prueba"},
                    "_metacritic": {"juego a": {"s": 85, "p": "PC", "n": 10}},
                    "_dificultad": {"juego a": {"h": 5, "c": 5, "ct": "consenso"}},
                }, f)
            with open(paths["WISHLIST_JSON"], "w", encoding="utf-8") as f:
                json.dump({
                    "juegos": {"Juego C": 5.0, "Juego D": "?"},
                    "_notas": {"Juego C": "PRENSA (prueba)"},
                    "_metacritic": {}, "_steam": {}, "_dificultad": {},
                }, f)
            with open(paths["COMPLETED_JSON"], "w", encoding="utf-8") as f:
                json.dump([], f)
            with open(paths["PLAYING_JSON"], "w", encoding="utf-8") as f:
                json.dump(["Juego A"], f)

            output = os.path.join(d, "output.xlsx")
            games = [fake_game("Juego A", 2.0), fake_game("Juego B", 1.0)]
            with mock.patch.multiple("inventory.cli", DATA_DIR=data_dir, **paths), \
                 mock.patch("inventory.cli.scan_games", return_value=(games, [])), \
                 mock.patch("inventory.excel.HISTORY_CSV",
                            os.path.join(data_dir, "history.csv")):
                with redirect_stdout(io.StringIO()) as console:
                    rc = main(["--sin-red", "--conservar", "--output", output])

            self.assertEqual(rc, 0, console.getvalue())
            self.assertTrue(os.path.exists(output))
            self.assertTrue(os.path.exists(os.path.join(data_dir, "history.csv")))
            wb = openpyxl.load_workbook(output)
            self.assertEqual(wb.sheetnames,
                             ["Games", "Space", "Summary", "Plan", "History", "Wishlist"])
            self.assertEqual(wb["Games"].max_row, 7)
            self.assertEqual(wb["Games"]["A5"].value, "Juego A")
            self.assertIn("PLAYING", wb["Games"]["F5"].value)
            self.assertEqual(wb["Games"]["H5"].value, 85)
            self.assertEqual(wb["Games"]["A6"].value, "Juego B")
            self.assertIn("NO END", wb["Games"]["F6"].value)

    def test_full_main_spanish(self):
        with tempfile.TemporaryDirectory() as d:
            data_dir = os.path.join(d, "data")
            os.makedirs(data_dir)
            paths = {
                "HOURS_JSON": os.path.join(data_dir, "hours.json"),
                "WISHLIST_JSON": os.path.join(data_dir, "wishlist.json"),
                "COMPLETED_JSON": os.path.join(data_dir, "completed.json"),
                "PLAYING_JSON": os.path.join(data_dir, "playing.json"),
            }
            with open(paths["HOURS_JSON"], "w", encoding="utf-8") as f:
                json.dump({"juego a": 10.0}, f)
            with open(paths["COMPLETED_JSON"], "w", encoding="utf-8") as f:
                json.dump([], f)
            with open(paths["PLAYING_JSON"], "w", encoding="utf-8") as f:
                json.dump(["Juego A"], f)
            output = os.path.join(d, "output.xlsx")
            games = [fake_game("Juego A", 2.0)]
            with mock.patch.multiple("inventory.cli", DATA_DIR=data_dir, **paths), \
                 mock.patch("inventory.cli.scan_games", return_value=(games, [])), \
                 mock.patch("inventory.excel.HISTORY_CSV",
                            os.path.join(data_dir, "history.csv")):
                with redirect_stdout(io.StringIO()) as console:
                    rc = main(["--offline", "--keep", "--lang", "es",
                               "--output", output])
            self.assertEqual(rc, 0, console.getvalue())
            wb = openpyxl.load_workbook(output)
            self.assertEqual(wb.sheetnames,
                             ["Juegos", "Espacio", "Resumen", "Plan", "Historico"])
            self.assertEqual(wb["Juegos"]["A5"].value, "Juego A")
            self.assertIn("EN CURSO", wb["Juegos"]["F5"].value)

    def test_version(self):
        with redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as ctx:
                main(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("game-inventory", output.getvalue())


class AbortTests(unittest.TestCase):
    def test_aborts_when_output_is_folder(self):
        with tempfile.TemporaryDirectory() as d:
            data_dir = os.path.join(d, "data_dir")
            with mock.patch("inventory.cli.DATA_DIR", data_dir):
                with redirect_stdout(io.StringIO()):
                    rc = main(["--sin-red", "--output", d])
            self.assertEqual(rc, 1)

    def test_aborts_when_output_inside_data(self):
        with tempfile.TemporaryDirectory() as d:
            data_dir = os.path.join(d, "data_dir")
            os.makedirs(data_dir)
            with mock.patch("inventory.cli.DATA_DIR", data_dir):
                with redirect_stdout(io.StringIO()):
                    rc = main(["--sin-red", "--output",
                               os.path.join(data_dir, "x.xlsx")])
            self.assertEqual(rc, 1)

    def test_aborts_when_another_run(self):
        with tempfile.TemporaryDirectory() as d:
            data_dir = os.path.join(d, "data_dir")
            os.makedirs(data_dir)
            with mock.patch("inventory.cli.DATA_DIR", data_dir), \
                 mock.patch("inventory.cli.acquire_lock", return_value=None):
                with redirect_stdout(io.StringIO()):
                    rc = main(["--sin-red", "--output",
                               os.path.join(d, "x.xlsx")])
            self.assertEqual(rc, 1)

    def test_aborts_with_corrupt_json(self):
        with tempfile.TemporaryDirectory() as d:
            data_dir = os.path.join(d, "data_dir")
            os.makedirs(data_dir)
            paths = {
                "HOURS_JSON": os.path.join(data_dir, "hours.json"),
                "WISHLIST_JSON": os.path.join(data_dir, "wishlist.json"),
                "COMPLETED_JSON": os.path.join(data_dir, "completed.json"),
                "PLAYING_JSON": os.path.join(data_dir, "playing.json"),
            }
            with open(paths["HOURS_JSON"], "w", encoding="utf-8") as f:
                f.write("{ mal")
            output = os.path.join(d, "x.xlsx")
            with mock.patch.multiple("inventory.cli", DATA_DIR=data_dir, **paths), \
                 mock.patch("inventory.cli.acquire_lock",
                            return_value=mock.MagicMock()):
                with redirect_stdout(io.StringIO()):
                    rc = main(["--sin-red", "--output", output])
            self.assertEqual(rc, 1)
            self.assertFalse(os.path.exists(output))


if __name__ == "__main__":
    unittest.main()
