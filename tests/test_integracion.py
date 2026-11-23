# -*- coding: utf-8 -*-
"""End-to-end test: main() with fake data and games."""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import openpyxl

from inventory.cli import _preselect_lang, main, open_file, run
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

    def test_help_english(self):
        with redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as ctx:
                main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("Scan installed games", output.getvalue())
        self.assertIn("examples:", output.getvalue())

    def test_help_spanish(self):
        with redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as ctx:
                main(["--lang", "es", "--help"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("Escanea los juegos instalados", output.getvalue())
        self.assertIn("ejemplos:", output.getvalue())

    def test_run_returns_main_result(self):
        with mock.patch("inventory.cli.main", return_value=7):
            self.assertEqual(run(["--version"]), 7)

    def test_run_catches_keyboard_interrupt(self):
        with mock.patch("inventory.cli.main", side_effect=KeyboardInterrupt):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(run([]), 130)
        self.assertIn("Cancelled", output.getvalue())

    def test_negative_top_is_rejected(self):
        with redirect_stderr(io.StringIO()) as error:
            with self.assertRaises(SystemExit) as ctx:
                main(["--top", "-1"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("--top", error.getvalue())

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

    def test_lang_from_environment(self):
        with mock.patch.dict(os.environ, {"GAME_INVENTORY_LANG": "es"}):
            self.assertEqual(_preselect_lang([]), "es")
        with mock.patch.dict(os.environ, {"GAME_INVENTORY_LANG": "fr"}):
            self.assertEqual(_preselect_lang([]), "en")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_preselect_lang([]), "en")

    def test_main_uses_environment_language(self):
        try:
            with mock.patch.dict(os.environ, {"GAME_INVENTORY_LANG": "es"}):
                with redirect_stdout(io.StringIO()) as output:
                    with self.assertRaises(SystemExit):
                        main(["--help"])
        finally:
            set_lang("en")
        self.assertIn("Escanea los juegos instalados", output.getvalue())


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
             history=None, config=None):
        data_dir = os.path.join(d, "data")
        os.makedirs(data_dir)
        paths = {
            "HOURS_JSON": os.path.join(data_dir, "hours.json"),
            "WISHLIST_JSON": os.path.join(data_dir, "wishlist.json"),
            "COMPLETED_JSON": os.path.join(data_dir, "completed.json"),
            "PLAYING_JSON": os.path.join(data_dir, "playing.json"),
            "CONFIG_JSON": os.path.join(data_dir, "config.json"),
        }
        for key, value in (("HOURS_JSON", hours), ("COMPLETED_JSON", completed),
                           ("PLAYING_JSON", playing), ("WISHLIST_JSON", wishlist)):
            if value is not None:
                with open(paths[key], "w", encoding="utf-8") as f:
                    json.dump(value, f)
        if config is not None:
            with open(paths["CONFIG_JSON"], "w", encoding="utf-8") as f:
                if isinstance(config, str):
                    f.write(config)
                else:
                    json.dump(config, f)
        out = output or os.path.join(d, "output.xlsx")
        if create_output:
            with open(out, "wb") as f:
                f.write(b"old")
        if history is not None:
            with open(os.path.join(data_dir, "history.csv"), "w",
                      encoding="utf-8") as f:
                f.write(history if isinstance(history, str)
                        else "date,games,gb,hours\n2026-11-01,1,1.0,10.0\n")
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

    def test_progress_messages(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"installed": 10.0}, games=[fake_game("Installed", 1.0)])
        self.assertEqual(rc, 0)
        self.assertIn("Scanning game folders", console)
        self.assertNotIn("Completing data from the network", console)
        self.assertNotIn("TOP PICKS", console)

    def test_top_option(self):
        games = [fake_game("A", 1.0), fake_game("B", 1.0),
                 fake_game("C", 1.0), fake_game("D", 1.0)]
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out.xlsx")
            rc, console, _, _ = self._run(
                d, hours={"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0}, games=games,
                args=["--offline", "--keep", "--top", "2", "--output", out])
        self.assertEqual(rc, 0)
        self.assertIn("TOP PICKS", console)
        self.assertIn("1. A", console)

    def test_top_option_in_dry_run(self):
        games = [fake_game("A", 1.0), fake_game("B", 1.0),
                 fake_game("C", 1.0), fake_game("D", 1.0)]
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0}, games=games,
                args=["--offline", "--keep", "--top", "1", "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertIn("TOP PICKS", console)
        self.assertIn("DRY RUN", console)

    def test_top_option_without_picks(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"only": 1.0}, games=[fake_game("Only", 1.0)],
                args=["--offline", "--keep", "--top", "3", "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertNotIn("TOP PICKS", console)

    def test_network_progress_message(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"installed": 10.0}, games=[fake_game("Installed", 1.0)],
                args=["--keep", "--output", os.path.join(d, "out.xlsx")],
                extra=[mock.patch("inventory.cli.autocomplete")])
        self.assertEqual(rc, 0)
        self.assertIn("Completing data from the network", console)

    def test_open_option_without_error(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out.xlsx")
            with mock.patch("inventory.cli.open_file", return_value=None) as opener:
                rc, console, _, _ = self._run(
                    d, hours={"installed": 10.0},
                    games=[fake_game("Installed", 1.0)],
                    args=["--offline", "--keep", "--open", "--output", out])
        self.assertEqual(rc, 0)
        opener.assert_called_once_with(out)
        self.assertIn("Opened", console)

    def test_open_option_with_error(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out.xlsx")
            with mock.patch("inventory.cli.open_file",
                            return_value=OSError("no app")):
                rc, console, _, _ = self._run(
                    d, hours={"installed": 10.0},
                    games=[fake_game("Installed", 1.0)],
                    args=["--offline", "--keep", "--open", "--output", out])
        self.assertEqual(rc, 0)
        self.assertIn("could not open", console)

    def test_open_spanish_alias(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out.xlsx")
            with mock.patch("inventory.cli.open_file", return_value=None) as opener:
                rc, _, _, _ = self._run(
                    d, hours={"installed": 10.0},
                    games=[fake_game("Installed", 1.0)],
                    args=["--offline", "--keep", "--abrir", "--output", out])
        self.assertEqual(rc, 0)
        opener.assert_called_once_with(out)

    def test_open_file_without_error(self):
        if hasattr(os, "startfile"):
            patch = mock.patch("inventory.cli.os.startfile", create=True)
        else:
            patch = mock.patch("inventory.cli.subprocess.Popen")
        with patch:
            self.assertIsNone(open_file("out.xlsx"))

    def test_open_file_returns_oserror(self):
        if hasattr(os, "startfile"):
            patch = mock.patch("inventory.cli.os.startfile",
                               side_effect=OSError("no app"), create=True)
        else:
            patch = mock.patch("inventory.cli.subprocess.Popen",
                               side_effect=OSError("no app"))
        with patch:
            error = open_file("out.xlsx")
        self.assertIsInstance(error, OSError)

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "output.xlsx")
            rc, console, _, _ = self._run(
                d, hours={"installed": 10.0}, games=[fake_game("Installed", 1.0)],
                args=["--offline", "--keep", "--dry-run", "--output", out])
            self.assertEqual(rc, 0)
            self.assertFalse(os.path.exists(out))
            self.assertFalse(os.path.exists(os.path.join(d, "data", "history.csv")))
            self.assertIn("DRY RUN", console)

    def test_check_data_ok(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"game": 10.0}, completed=[], playing=[],
                wishlist={"juegos": {"Game": 10.0}}, args=["--check-data"])
        self.assertEqual(rc, 0)
        self.assertIn("DATA CHECK", console)
        self.assertIn("Wishlist", console)
        self.assertIn("Config: 0", console)
        self.assertIn("Metadata keys without a game", console)
        self.assertIn("no rows yet", console)

    def test_check_data_counts_config_overrides(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"game": 10.0}, completed=[], playing=[],
                wishlist={"juegos": {}}, config={"libraries": ["D:/Games"],
                                                 "output": "C:/out.xlsx"},
                args=["--check-data"])
        self.assertEqual(rc, 0)
        self.assertIn("Config: 2 overrides", console)

    def test_check_data_with_broken_config(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"game": 10.0}, completed=[], playing=[],
                wishlist={"juegos": {}}, config="{broken",
                args=["--check-data"])
        self.assertEqual(rc, 1)
        self.assertIn("ABORTED", console)

    def test_check_data_with_config_that_is_not_an_object(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"game": 10.0}, completed=[], playing=[],
                wishlist={"juegos": {}}, config=[],
                args=["--check-data"])
        self.assertEqual(rc, 1)
        self.assertIn("ABORTED", console)

    def test_check_data_reports_metadata_duplicates_and_history(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d,
                hours={"game": 10.0,
                       "_notas": {"game": "source", "gone": "old"},
                       "_dificultad": {"game": {"h": 99}},
                       "_steam": {"game": {"pct": 90}}},
                completed=[], playing=[],
                wishlist={"juegos": {"Game": 10.0, "game": "?", "Other": 5.0},
                          "_notas": {"Gone": "old"}},
                history="date,games,gb,hours\n2026-11-01,2,10.0,5.0\n"
                        "2026-11-02,3,11.0,6.0\nbad\n",
                args=["--check-data"])
        self.assertEqual(rc, 0)
        self.assertIn("hours 1 | wishlist 1", console)
        self.assertIn("Stale in hours: gone | wishlist: Gone", console)
        self.assertIn("metacritic 0 | steam 0 | difficulty 1", console)
        self.assertIn("repeated after normalization: 1", console)
        self.assertIn("2 days, last 2026-11-02 (1 bad rows)", console)

    def test_check_data_reports_key_problems_and_missing_titles(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d,
                hours={"Game!": 10.0, "game": 20.0, "hades": 5.0},
                completed=["Hades"], playing=["Gone"],
                wishlist={"juegos": {}}, config={"libs": []},
                args=["--check-data"])
        self.assertEqual(rc, 0)
        self.assertIn("Unknown config keys (1): libs", console)
        self.assertIn("Unnormalized keys in hours.json (1): Game!", console)
        self.assertIn("Keys that collide after normalization (2): Game!, game", console)
        self.assertIn("completed - | playing gone", console)

    def test_check_data_reports_completed_and_playing_overlap(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"hades": 10.0}, completed=["Hades"],
                playing=["hades"], wishlist={"juegos": {}},
                args=["--check-data", "--strict"])
        self.assertEqual(rc, 1)
        self.assertIn("Completed and playing at the same time (1): hades", console)

    def test_check_data_counts_reachable_libraries(self):
        with tempfile.TemporaryDirectory() as d:
            missing = os.path.join(d, "missing")
            rc, console, _, _ = self._run(
                d, hours={"game": 10.0}, completed=[], playing=[],
                wishlist={"juegos": {}},
                config={"libraries": [d, missing], "loose_paths": [d]},
                args=["--check-data"])
        self.assertEqual(rc, 0)
        self.assertIn("Libraries: 2 of 3 folders reachable", console)

    def test_check_data_rejects_output_inside_data(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"game": 10.0}, completed=[], playing=[],
                wishlist={"juegos": {}},
                config={"output": os.path.join(d, "data", "out.xlsx")},
                args=["--check-data", "--strict"])
        self.assertEqual(rc, 1)
        self.assertIn("Output points inside data/", console)

    def test_check_data_reports_repeated_and_future_history_dates(self):
        history = ("date,games,gb,hours\n"
                   "2026-11-01,1,1.0,10.0\n"
                   "2026-11-01,2,2.0,20.0\n"
                   "2999-01-01,3,3.0,30.0\n")
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"game": 10.0}, completed=[], playing=[],
                wishlist={"juegos": {}}, history=history,
                args=["--check-data", "--strict"])
        self.assertEqual(rc, 1)
        self.assertIn("History dates: 1 repeated | 1 in the future", console)

    def test_check_data_reports_bad_blocks_and_unsorted_history(self):
        history = ("date,games,gb,hours\n"
                   "2026-11-02,1,1.0,10.0\n"
                   "2026-11-01,1,1.0,10.0\n")
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"game": 10.0, "_notas": []}, completed=[],
                playing=[], wishlist={"juegos": {}}, history=history,
                args=["--check-data", "--strict"])
        self.assertEqual(rc, 1)
        self.assertIn("Metadata blocks that are not objects (1): _notas", console)
        self.assertIn("History rows are not sorted by date", console)
        self.assertIn("Warnings: 2", console)

    def test_check_data_strict_with_warnings(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"game": 0}, completed=[], playing=[],
                wishlist={"juegos": {}}, args=["--check-data", "--strict"])
        self.assertEqual(rc, 1)
        self.assertIn("STRICT: 1 warnings", console)

    def test_check_data_strict_without_warnings(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"game": 10.0}, completed=[], playing=[],
                wishlist={"juegos": {}}, args=["--check-data", "--strict"])
        self.assertEqual(rc, 0)
        self.assertNotIn("STRICT", console)

    def test_check_data_spanish(self):
        try:
            with tempfile.TemporaryDirectory() as d:
                rc, console, _, _ = self._run(
                    d, hours={"game": 10.0}, completed=[], playing=[],
                    wishlist={"juegos": {}},
                    args=["--lang", "es", "--check-data"])
        finally:
            set_lang("en")
        self.assertEqual(rc, 0)
        self.assertIn("COMPROBACION DE DATOS", console)
        self.assertIn("Config: 0 ajustes", console)

    def test_check_data_corrupt(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(d, hours=[], args=["--check-data"])
        self.assertEqual(rc, 1)
        self.assertIn("ABORTED", console)

    def test_check_data_prints_warnings(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"bad%d" % i: 0 for i in range(12)},
                completed=[], playing=[], wishlist={"juegos": {}},
                args=["--check-data"])
        self.assertEqual(rc, 0)
        self.assertIn("12 warnings", console)

    def test_check_data_wishlist_not_an_object(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"game": 10.0}, completed=[], playing=[],
                wishlist=[], args=["--check-data"])
        self.assertEqual(rc, 1)
        self.assertIn("ABORTED", console)

    def test_check_data_wishlist_games_not_an_object(self):
        with tempfile.TemporaryDirectory() as d:
            rc, console, _, _ = self._run(
                d, hours={"game": 10.0}, completed=[], playing=[],
                wishlist={"juegos": []}, args=["--check-data"])
        self.assertEqual(rc, 1)
        self.assertIn("ABORTED", console)

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
