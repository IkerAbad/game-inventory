# -*- coding: utf-8 -*-
"""End-to-end test: main() with fake data and games."""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import openpyxl

from inventory.cli import _preselect_lang, main
from inventory.data import read_json
from inventory.i18n import set_lang


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

    def test_main_uses_wishlist_hours(self):
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
                json.dump({"wanted game": "?"}, f)
            with open(paths["WISHLIST_JSON"], "w", encoding="utf-8") as f:
                json.dump({"juegos": {"Wanted Game": 7.0}}, f)
            with open(paths["COMPLETED_JSON"], "w", encoding="utf-8") as f:
                json.dump([], f)
            with open(paths["PLAYING_JSON"], "w", encoding="utf-8") as f:
                json.dump([], f)
            output = os.path.join(d, "output.xlsx")
            games = [fake_game("Wanted Game", 1.0)]
            with mock.patch.multiple("inventory.cli", DATA_DIR=data_dir, **paths), \
                 mock.patch("inventory.cli.scan_games", return_value=(games, [])), \
                 mock.patch("inventory.excel.HISTORY_CSV",
                            os.path.join(data_dir, "history.csv")):
                with redirect_stdout(io.StringIO()) as console:
                    rc = main(["--offline", "--keep", "--output", output])
            self.assertEqual(rc, 0, console.getvalue())
            wb = openpyxl.load_workbook(output)
            self.assertEqual(wb["Games"]["C5"].value, 7.0)
            self.assertIn("HOURS TAKEN", console.getvalue())

    def test_main_purges_orphans(self):
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
                json.dump({"installed": 10.0, "orphan": 5.0}, f)
            with open(paths["COMPLETED_JSON"], "w", encoding="utf-8") as f:
                json.dump([], f)
            with open(paths["PLAYING_JSON"], "w", encoding="utf-8") as f:
                json.dump([], f)
            output = os.path.join(d, "output.xlsx")
            games = [fake_game("Installed", 1.0)]
            with mock.patch.multiple("inventory.cli", DATA_DIR=data_dir, **paths), \
                 mock.patch("inventory.cli.scan_games", return_value=(games, [])), \
                 mock.patch("inventory.data.LIBRARIES", [data_dir]), \
                 mock.patch("inventory.data.HOURS_JSON", paths["HOURS_JSON"]), \
                 mock.patch("inventory.excel.HISTORY_CSV",
                            os.path.join(data_dir, "history.csv")):
                with redirect_stdout(io.StringIO()) as console:
                    rc = main(["--offline", "--output", output])
            self.assertEqual(rc, 0, console.getvalue())
            saved = read_json(paths["HOURS_JSON"], {})
            self.assertEqual(saved.get("installed"), 10.0)
            self.assertNotIn("orphan", saved)

    def test_version(self):
        with redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as ctx:
                main(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("game-inventory", output.getvalue())

    def test_module_entry_point(self):
        import runpy
        with mock.patch.object(sys, "argv", ["inventory", "--version"]):
            with redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    runpy.run_module("inventory", run_name="__main__")
        self.assertEqual(ctx.exception.code, 0)

    def test_lang_equals_form(self):
        self.assertEqual(_preselect_lang(["--lang=es"]), "es")
        self.assertEqual(_preselect_lang(["--lang", "en"]), "en")


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


class BranchTests(unittest.TestCase):
    def setUp(self):
        set_lang("en")

    def _run(self, d, hours=None, completed=None, playing=None, wishlist=None,
             games=None, args=None, extra=None, create_output=False, output=None,
             history=None):
        data_dir = os.path.join(d, "data")
        os.makedirs(data_dir)
        paths = {
            "HOURS_JSON": os.path.join(data_dir, "hours.json"),
            "WISHLIST_JSON": os.path.join(data_dir, "wishlist.json"),
            "COMPLETED_JSON": os.path.join(data_dir, "completed.json"),
            "PLAYING_JSON": os.path.join(data_dir, "playing.json"),
        }
        for key, value in (("HOURS_JSON", hours), ("COMPLETED_JSON", completed),
                           ("PLAYING_JSON", playing), ("WISHLIST_JSON", wishlist)):
            if value is not None:
                with open(paths[key], "w", encoding="utf-8") as f:
                    json.dump(value, f)
        out = output or os.path.join(d, "output.xlsx")
        if create_output:
            with open(out, "wb") as f:
                f.write(b"old")
        if history is not None:
            with open(os.path.join(data_dir, "history.csv"), "w",
                      encoding="utf-8") as f:
                f.write("date,games,gb,hours\n2026-11-01,1,1.0,10.0\n")
        if args is None:
            args = ["--offline", "--keep", "--output", out]
        with ExitStack() as stack:
            stack.enter_context(mock.patch.multiple("inventory.cli", DATA_DIR=data_dir, **paths))
            stack.enter_context(mock.patch("inventory.cli.scan_games",
                                           return_value=(games or [], [])))
            stack.enter_context(mock.patch("inventory.excel.HISTORY_CSV",
                                           os.path.join(data_dir, "history.csv")))
            for patch in extra or []:
                stack.enter_context(patch)
            with redirect_stdout(io.StringIO()) as console:
                rc = main(args)
        return rc, console.getvalue(), out, paths

    def test_invalid_hours_warning(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(d, hours={"bad%d" % i: 0 for i in range(12)})
        self.assertEqual(rc, 0)
        self.assertIn("invalid", console)
        self.assertIn("more", console)

    def test_autocomplete_error_does_not_abort(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "output.xlsx")
            rc, console, _, _ = self._run(
                d, args=["--keep", "--output", out],
                extra=[mock.patch("inventory.cli.autocomplete",
                                  side_effect=RuntimeError("boom"))])
        self.assertEqual(rc, 0)
        self.assertIn("interrupted", console)

    def test_no_data_duplicates_and_no_difficulty(self):
        with tempfile.TemporaryDirectory() as d:
            first = fake_game("Same", 1.0)
            second = fake_game("Same_", 1.0)
            second["duplicate"] = True
            rc, console, _, _ = self._run(d, hours={}, games=[first, second])
        self.assertEqual(rc, 0)
        self.assertIn("NO HOURS", console)
        self.assertIn("DUPLICATES", console)
        self.assertIn("NO DIFFICULTY", console)

    def test_completed_and_playing(self):
        with tempfile.TemporaryDirectory() as d:
            games = [fake_game("Done", 1.0), fake_game("Now", 1.0)]
            rc, console, _, _ = self._run(d, hours={"done": 10.0, "now": 10.0},
                                          completed=["Done"], playing=["Now"],
                                          games=games)
        self.assertEqual(rc, 0)
        self.assertIn("COMPLETED", console)
        self.assertIn("PLAYING", console)

    def test_keeps_orphan_keys(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"installed": 10.0, "orphan": 5.0},
                games=[fake_game("Installed", 1.0)])
        self.assertEqual(rc, 0)
        self.assertIn("KEYS WITHOUT A FOLDER", console)

    def test_history_delta(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(d, hours={}, history=True)
        self.assertEqual(rc, 0)
        self.assertIn("Since", console)

    def test_completed_and_playing_orphans(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={}, completed=["Gone"], playing=["Lost"])
        self.assertEqual(rc, 0)
        self.assertIn("completed.json", console)
        self.assertIn("playing.json", console)

    def test_hours_not_object(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(d, hours=[])
        self.assertEqual(rc, 1)
        self.assertIn("ABORTED", console)

    def test_wishlist_not_object(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(d, hours={}, wishlist=[])
        self.assertEqual(rc, 1)
        self.assertIn("ABORTED", console)

    def test_wishlist_games_not_object(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(d, hours={}, wishlist={"juegos": []})
        self.assertEqual(rc, 1)
        self.assertIn("ABORTED", console)

    def test_excel_locked(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, extra=[mock.patch("inventory.cli.excel_locked", return_value=True)])
        self.assertEqual(rc, 1)
        self.assertIn("open", console)

    def test_lock_error(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, extra=[mock.patch("inventory.cli.acquire_lock",
                                     side_effect=OSError("no lock"))])
        self.assertEqual(rc, 1)
        self.assertIn("lock", console)

    def test_data_dir_error(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, extra=[mock.patch("inventory.cli.os.makedirs",
                                     side_effect=OSError("no dir"))])
        self.assertEqual(rc, 1)
        self.assertIn("data folder", console)

    def test_backup_failure(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={}, create_output=True,
                extra=[mock.patch("inventory.cli.shutil.copy2",
                                  side_effect=OSError("no copy"))])
        self.assertEqual(rc, 0)
        self.assertIn("previous copy", console)

    def test_save_error(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={},
                extra=[mock.patch("openpyxl.workbook.workbook.Workbook.save",
                                  side_effect=OSError("no disk"))])
        self.assertEqual(rc, 1)
        self.assertIn("could not save", console)

    def test_output_dir_error(self):
        with tempfile.TemporaryDirectory() as d:
            blocker = os.path.join(d, "blocker")
            with open(blocker, "w", encoding="utf-8") as f:
                f.write("x")
            rc, console, _, _ = self._run(
                d, hours={}, output=os.path.join(blocker, "out.xlsx"))
        self.assertEqual(rc, 1)
        self.assertIn("Excel folder", console)


if __name__ == "__main__":
    unittest.main()
