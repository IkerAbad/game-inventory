# -*- coding: utf-8 -*-
"""Robustness tests: JSON with BOM or corrupt, invalid hours and atomic writes."""

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

from inventory import excel
from inventory.cli import _stale_keys, inside_data
from inventory.config import DATA_DIR, _data_root
from inventory.i18n import set_lang
from inventory.data import (_save_json, _same, clean_hours, write_atomic, write_hours,
                              write_wishlist, is_valid_hours, read_keys, read_json,
                              clean_temp_files, purge_hours, acquire_lock)
from inventory.scan import days_installed, excel_locked, scan_games
from inventory.cell_format import clean_text
from inventory.network import steam_search


class ReadJsonTests(unittest.TestCase):
    def test_missing_returns_default(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(read_json(os.path.join(d, "no.json"), {"x": 1}), {"x": 1})

    def test_accepts_bom(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.json")
            with open(path, "w", encoding="utf-8-sig") as f:
                json.dump({"a": 1}, f)
            self.assertEqual(read_json(path, {}), {"a": 1})

    def test_corrupt_reports_position(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{ mal")
            with self.assertRaises(ValueError) as ctx:
                read_json(path, {})
            self.assertIn("not valid JSON", str(ctx.exception))
            self.assertIn("line", str(ctx.exception))

    def test_keys_require_list(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"a": 1}, f)
            with self.assertRaises(ValueError):
                read_keys(path)

    def test_keys_accept_list(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(["Game A", 123, "_meta"], f)
            self.assertEqual(read_keys(path), {"game a", "123"})

    def test_no_utf8(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.json")
            with open(path, "wb") as f:
                f.write(b"\xff\xfe{")
            with self.assertRaises(ValueError) as ctx:
                read_json(path, {})
            self.assertIn("UTF-8", str(ctx.exception))


class CleanHoursTests(unittest.TestCase):
    def test_valid(self):
        limpio, avisos = clean_hours({"a": 12.5, "b": None, "c": "?", "_notas": {"a": "x"}})
        self.assertEqual(limpio["a"], 12.5)
        self.assertIsNone(limpio["b"])
        self.assertEqual(limpio["c"], "?")
        self.assertEqual(limpio["_notas"], {"a": "x"})
        self.assertEqual(avisos, [])

    def test_invalid_become_no_data(self):
        limpio, avisos = clean_hours(
            {"a": 0, "b": -3, "c": "doce", "d": True, "e": float("nan")})
        for k in "abcde":
            self.assertEqual(limpio[k], "?")
        self.assertEqual(len(avisos), 5)
        limpio, avisos = clean_hours({"f": 1000001})
        self.assertEqual(limpio["f"], "?")
        self.assertEqual(len(avisos), 1)

    def test_is_valid_hours(self):
        self.assertTrue(is_valid_hours(12.5))
        self.assertTrue(is_valid_hours(1))
        self.assertTrue(is_valid_hours(1000000))
        self.assertFalse(is_valid_hours(1000001))
        self.assertFalse(is_valid_hours(0))
        self.assertFalse(is_valid_hours(-1))
        self.assertFalse(is_valid_hours(float("nan")))
        self.assertFalse(is_valid_hours(float("inf")))
        self.assertFalse(is_valid_hours(True))
        self.assertFalse(is_valid_hours("12"))
        self.assertFalse(is_valid_hours(None))


class WriteTests(unittest.TestCase):
    def setUp(self):
        set_lang("en")

    def test_atomic_and_no_temp_files(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.json")
            write_atomic(path, '{"a": 1}\n')
            self.assertEqual(read_json(path, {}), {"a": 1})
            self.assertEqual([n for n in os.listdir(d) if n.startswith(".tmp_")], [])

    def test_save_json_tolerates_nan(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.json")

            def escritor(obj):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(obj, f)

            self.assertTrue(_save_json(path, escritor, {"a": float("nan")}))

    def test_save_json_restores_on_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"a": 1}, f)

            def bad_writer(obj):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"b": 2}, f)

            with redirect_stdout(io.StringIO()):
                ok = _save_json(path, bad_writer, {"a": 1})
            self.assertFalse(ok)
            self.assertEqual(read_json(path, {}), {"a": 1})

    def test_hours_keeps_unknown_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "hours.json")
            with mock.patch("inventory.data.HOURS_JSON", path):
                write_hours({"game": 10, "_raro": {"a": 1}})
            self.assertEqual(read_json(path, {})["_raro"], {"a": 1})

    def test_hours_writes_all_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "hours.json")
            with mock.patch("inventory.data.HOURS_JSON", path):
                write_hours({"_comentario": "comment", "game": 10.0,
                             "_metacritic": {"game": {"s": 90}},
                             "_steam": {"game": {"pct": 90}},
                             "_dificultad": {"game": {"h": 5}},
                             "_notas": {"game": "note"},
                             "_raro": {"a": 1}})
            data = read_json(path, {})
            self.assertEqual(data["_comentario"], "comment")
            self.assertEqual(data["_metacritic"]["game"]["s"], 90)
            self.assertEqual(data["_steam"]["game"]["pct"], 90)
            self.assertEqual(data["_dificultad"]["game"]["h"], 5)
            self.assertEqual(data["_notas"]["game"], "note")
            self.assertEqual(data["_raro"], {"a": 1})

    def test_read_json_directory(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                read_json(d, {})

    def test_purge_refuses_missing_library(self):
        with tempfile.TemporaryDirectory() as d:
            hours = {"game": 10}
            with mock.patch("inventory.data.LIBRARIES",
                            [os.path.join(d, "missing")]):
                with redirect_stdout(io.StringIO()):
                    removed = purge_hours(hours, set())
            self.assertEqual(removed, 0)
            self.assertEqual(hours, {"game": 10})

    def test_clean_temp_files_missing_folder(self):
        with tempfile.TemporaryDirectory() as d:
            clean_temp_files(os.path.join(d, "missing"))

    def test_clean_temp_files_remove_error(self):
        with tempfile.TemporaryDirectory() as d:
            leftover = os.path.join(d, ".tmp_left")
            with open(leftover, "w", encoding="utf-8") as f:
                f.write("x")
            with mock.patch("inventory.data.os.remove", side_effect=OSError("x")):
                clean_temp_files(d)
            self.assertTrue(os.path.exists(leftover))

    def test_write_atomic_fsync_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.txt")
            with mock.patch("inventory.data.os.fsync", side_effect=OSError("x")):
                write_atomic(path, "hello")
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "hello")

    def test_write_atomic_replace_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.txt")
            with mock.patch("inventory.data.os.replace", side_effect=OSError("x")):
                with self.assertRaises(OSError):
                    write_atomic(path, "hello")
            self.assertEqual([n for n in os.listdir(d) if n.startswith(".tmp_")], [])

    def test_write_atomic_replace_and_unlink_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.txt")
            with mock.patch("inventory.data.os.replace", side_effect=OSError("x")), \
                 mock.patch("inventory.data.os.unlink", side_effect=OSError("y")):
                with self.assertRaises(OSError):
                    write_atomic(path, "hello")
            self.assertFalse(os.path.exists(path))

    def test_purge_removes_block_keys(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "hours.json")
            hours = {"game": 10.0, "other": 5.0,
                     "_notas": {"game": "a", "other": "b"}}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(hours, f)
            with mock.patch("inventory.data.LIBRARIES", [d]), \
                 mock.patch("inventory.data.HOURS_JSON", path):
                with redirect_stdout(io.StringIO()):
                    removed = purge_hours(dict(hours), {"game"})
            data = read_json(path, {})
            self.assertEqual(removed, 1)
            self.assertNotIn("other", data)
            self.assertEqual(data["_notas"], {"game": "a"})

    def test_purge_backup_failure(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "hours.json")
            hours = {"game": 10.0, "orphan": 5.0}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(hours, f)
            with mock.patch("inventory.data.LIBRARIES", [d]), \
                 mock.patch("inventory.data.HOURS_JSON", path), \
                 mock.patch("inventory.data.shutil.copy2", side_effect=OSError("x")):
                with redirect_stdout(io.StringIO()):
                    removed = purge_hours(dict(hours), {"game"})
            self.assertEqual(removed, 1)
            self.assertIn("game", read_json(path, {}))

    def test_purge_write_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "hours.json")
            hours = {"game": 10.0, "orphan": 5.0}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(hours, f)
            with mock.patch("inventory.data.LIBRARIES", [d]), \
                 mock.patch("inventory.data.HOURS_JSON", path), \
                 mock.patch("inventory.data._save_json", side_effect=OSError("x")):
                with redirect_stdout(io.StringIO()) as output:
                    removed = purge_hours(dict(hours), {"game"})
            self.assertEqual(removed, 1)
            self.assertIn("could not write", output.getvalue())

    def test_save_json_invalid_written(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"a": 1}, f)

            def bad_writer(obj):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("{bad")

            with redirect_stdout(io.StringIO()):
                ok = _save_json(path, bad_writer, {"a": 1})
            self.assertFalse(ok)
            self.assertEqual(read_json(path, {}), {"a": 1})

    def test_same_containers(self):
        self.assertTrue(_same([1, 2], [1, 2]))
        self.assertFalse(_same([1], [1, 2]))
        self.assertTrue(_same({"a": [1]}, {"a": [1]}))
        self.assertFalse(_same({"a": 1}, {"a": 2}))

    def test_history_ignores_broken_rows(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "history.csv")
            with open(path, "w", encoding="utf-8") as f:
                f.write("fecha,games,gb,hours\n")
                f.write("2026-01-01,10,100.0,50.0\n")
                f.write("no-es-fecha,10,100.0,50.0\n")
                f.write("2026-01-02,dos,100.0,50.0\n")
            original = excel.HISTORY_CSV
            excel.HISTORY_CSV = path
            try:
                with redirect_stdout(io.StringIO()):
                    filas = excel.append_history([], 0.0)
            finally:
                excel.HISTORY_CSV = original
            self.assertEqual(len(filas), 2)
            self.assertEqual(filas[0][0], "2026-01-01")
            with open(path, encoding="utf-8") as f:
                texto = f.read()
            self.assertNotIn("no-es-fecha", texto)
            self.assertNotIn("2026-01-02", texto)
            self.assertTrue(os.path.exists(path + ".corrupto"))
            with open(path + ".corrupto", encoding="utf-8") as f:
                self.assertIn("no-es-fecha", f.read())

    def test_history_non_utf8_is_regenerated(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "history.csv")
            with open(path, "wb") as f:
                f.write(b"\xff\xfe")
            original = excel.HISTORY_CSV
            excel.HISTORY_CSV = path
            try:
                with redirect_stdout(io.StringIO()):
                    filas = excel.append_history([], 0.0)
            finally:
                excel.HISTORY_CSV = original
            self.assertEqual(len(filas), 1)
            self.assertTrue(os.path.exists(path))
            self.assertTrue(os.path.exists(path + ".corrupto"))
            with open(path + ".corrupto", "rb") as f:
                self.assertEqual(f.read(), b"\xff\xfe")

    def test_read_history_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            rows, problems = excel.read_history(os.path.join(d, "none.csv"))
        self.assertEqual(rows, [])
        self.assertEqual(problems, [])

    def test_read_history_reports_each_bad_row(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "history.csv")
            with open(path, "w", encoding="utf-8") as f:
                f.write("date,games,gb,hours\n")
                f.write("2026-01-01,10,100.0,50.0\n")
                f.write("2026-01-02,10,inf,50.0\n")
                f.write("2026-01-03,10,100.0\n")
                f.write("bad,10,100.0,50.0\n")
            rows, problems = excel.read_history(path)
        self.assertEqual([r[0] for r in rows], ["2026-01-01"])
        self.assertEqual([kind for kind, _ in problems],
                         ["invalid", "incomplete", "invalid"])

    def test_read_history_unreadable_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "history.csv")
            with open(path, "w", encoding="utf-8") as f:
                f.write("date,games,gb,hours\n")
            with mock.patch("builtins.open", side_effect=OSError("locked")):
                rows, problems = excel.read_history(path)
        self.assertEqual(rows, [])
        self.assertEqual(problems, [("read", "locked")])

    def test_empty_workbook_without_drives(self):
        with tempfile.TemporaryDirectory() as d:
            original = excel.HISTORY_CSV
            excel.HISTORY_CSV = os.path.join(d, "history.csv")
            try:
                with mock.patch("inventory.excel.shutil.disk_usage",
                                side_effect=OSError("no drive")):
                    wb, TH, filas = excel.build_workbook([], 1.0, 2.0, 4.0)
                self.assertEqual(TH, 0.0)
                self.assertEqual(wb.sheetnames,
                                 ["Games", "Space", "Summary", "Plan", "History"])
                self.assertEqual(wb["Games"]["B5"].value, 0)
                self.assertEqual(wb["Games"]["F5"].value, "0 games")
                path = os.path.join(d, "x.xlsx")
                wb.save(path)
                self.assertTrue(os.path.exists(path))
            finally:
                excel.HISTORY_CSV = original

    def test_text_cell_is_not_formula(self):
        import openpyxl
        with tempfile.TemporaryDirectory() as d:
            wb = openpyxl.Workbook()
            c = excel.text_cell(wb.active, 1, 1, "=1+1")
            self.assertEqual(c.data_type, "s")
            excel.text_cell(wb.active, 1, 2, "normal game")
            excel.text_cell(wb.active, 1, 3, "\x01=2+2")
            path = os.path.join(d, "x.xlsx")
            wb.save(path)
            wb2 = openpyxl.load_workbook(path)
            self.assertEqual(wb2.active.cell(1, 1).data_type, "s")
            self.assertEqual(wb2.active.cell(1, 1).value, "=1+1")
            self.assertEqual(wb2.active.cell(1, 2).value, "normal game")
            self.assertEqual(wb2.active.cell(1, 3).value, "=2+2")
            self.assertEqual(wb2.active.cell(1, 3).data_type, "s")

    def test_clean_text(self):
        self.assertEqual(clean_text("a\x01b\x1fc"), "abc")
        self.assertEqual(clean_text("linea\nnormal"), "linea\nnormal")
        self.assertEqual(len(clean_text("x" * 40000)), 32767)

    def test_clean_temp_files(self):
        with tempfile.TemporaryDirectory() as d:
            old = os.path.join(d, ".tmp_resto.tmp")
            with open(old, "w", encoding="utf-8") as f:
                f.write("x")
            with open(os.path.join(d, "hours.json"), "w", encoding="utf-8") as f:
                f.write("{}")
            clean_temp_files(d)
            self.assertFalse(os.path.exists(old))
            self.assertTrue(os.path.exists(os.path.join(d, "hours.json")))

    def test_purge_refuses_on_failed_base(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("inventory.data.LIBRARIES", [d]):
                hours = {"game": 10, "_notas": {"game": "x"}}
                with redirect_stdout(io.StringIO()):
                    quitadas = purge_hours(hours, set(), [d], force=True)
                self.assertEqual(quitadas, 0)
                self.assertIn("game", hours)
                self.assertIn("game", hours["_notas"])

    def test_purge_guarded_by_majority(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "hours.json")
            hours = {"game %d" % i: 10 for i in range(12)}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(hours, f)
            installed = {"game 0", "game 1"}
            with mock.patch("inventory.data.LIBRARIES", [d]), \
                 mock.patch("inventory.data.HOURS_JSON", path):
                with redirect_stdout(io.StringIO()):
                    quitadas = purge_hours(dict(hours), installed)
                self.assertEqual(quitadas, 0)
                self.assertEqual(len(read_json(path, {})), 12)
                with redirect_stdout(io.StringIO()):
                    quitadas = purge_hours(dict(hours), installed, force=True)
            self.assertEqual(quitadas, 10)
            self.assertEqual(len(read_json(path, {})), 3)  # 2 keys + _notas

    def test_purge_keeps_previous_copy(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "hours.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"game": 10}, f)
            with mock.patch("inventory.data.LIBRARIES", [d]), \
                 mock.patch("inventory.data.HOURS_JSON", path):
                with redirect_stdout(io.StringIO()):
                    quitadas = purge_hours({"game": 10}, set())
            self.assertEqual(quitadas, 1)
            self.assertTrue(os.path.exists(path + ".bak"))
            with open(path + ".bak", encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"game": 10})
            self.assertEqual(read_json(path, None), {"_notas": {}})

    def test_write_wishlist_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "wishlist.json")
            with mock.patch("inventory.data.WISHLIST_JSON", path):
                write_wishlist({"juegos": {"Hades": 10.0, "Other": "?"},
                                "_notas": {"Hades": "note"}})
            data = read_json(path, {})
            self.assertEqual(data["juegos"]["Hades"], 10.0)
            self.assertEqual(data["juegos"]["Other"], "?")
            self.assertEqual(data["_notas"]["Hades"], "note")

    def test_output_inside_data(self):
        self.assertTrue(inside_data(os.path.join(DATA_DIR, "x.xlsx")))
        self.assertTrue(inside_data(os.path.join(DATA_DIR, "sub", "x.xlsx")))
        self.assertFalse(inside_data(os.path.join(tempfile.gettempdir(), "x.xlsx")))
        with mock.patch("inventory.cli.os.path.commonpath", side_effect=ValueError):
            self.assertFalse(inside_data("x"))

    def test_stale_keys_with_wrong_types(self):
        self.assertEqual(_stale_keys(None, {}), 0)
        self.assertEqual(_stale_keys({}, []), 0)
        self.assertEqual(_stale_keys({"_notas": {"gone": "x"}}, {"kept": 1.0}), 1)

    def test_exclusive_lock_between_processes(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            f = acquire_lock(d)
            self.assertIsNotNone(f)
            codigo = ("import sys; sys.path.insert(0, %r); "
                      "from inventory.data import acquire_lock; "
                      "print(acquire_lock(%r) is None)" % (ROOT, d))
            salida = subprocess.run([sys.executable, "-c", codigo],
                                    capture_output=True, text=True)
            self.assertEqual(salida.stdout.strip(), "True", salida.stderr)
            f.close()
            f2 = acquire_lock(d)
            self.assertIsNotNone(f2)
            f2.close()

    def test_steam_search_odd_responses(self):
        with mock.patch("inventory.network._json_get", return_value=[]):
            self.assertIsNone(steam_search(["Juego"]))
        with mock.patch("inventory.network._json_get",
                        return_value={"items": [None, 3, {"type": "app"}]}):
            self.assertIsNone(steam_search(["Juego"]))
        with mock.patch("inventory.network._json_get", return_value={"items": "x"}):
            self.assertIsNone(steam_search(["Juego"]))

    def test_scan_ignores_invalid_libraries(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("inventory.scan.LIBRARIES", [None, 123, d]):
                games, failures = scan_games()
            self.assertIsInstance(games, list)
            self.assertEqual(failures, [])

    def test_wishlist_non_dict_blocks(self):
        import openpyxl
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        excel.wishlist_sheet(wb, [], {"Juego": 10}, "origen", [], [], [], [])
        self.assertEqual(wb.sheetnames, ["Wishlist"])

    def test_absurd_hours_do_not_break(self):
        juego = {"name": "Enorme", "gb": 1.0, "days": 1, "unit": "C:",
                 "path": "C:\\Enorme", "duplicate": False, "hours": 10000000.0,
                 "mc": None, "steam": None, "dif": None, "note": "",
                 "completed": False, "playing": False, "ratio": 0.0,
                 "verdict": "medium"}
        with tempfile.TemporaryDirectory() as d:
            original = excel.HISTORY_CSV
            excel.HISTORY_CSV = os.path.join(d, "history.csv")
            try:
                with mock.patch("inventory.excel.shutil.disk_usage",
                                side_effect=OSError("no drive")):
                    wb, TH, filas = excel.build_workbook([juego], 1.0, 2.0, 4.0)
                self.assertEqual(TH, 10000000.0)
                path = os.path.join(d, "x.xlsx")
                wb.save(path)
                self.assertTrue(os.path.exists(path))
            finally:
                excel.HISTORY_CSV = original

    def test_zero_gb_game(self):
        juego = {"name": "Vacio", "gb": 0.0, "days": 1, "unit": "C:",
                 "path": "C:\\Vacio", "duplicate": False, "hours": 10.0,
                 "mc": None, "steam": None, "dif": None, "note": "",
                 "completed": False, "playing": False, "ratio": 0.0,
                 "verdict": "medium"}
        with tempfile.TemporaryDirectory() as d:
            original = excel.HISTORY_CSV
            excel.HISTORY_CSV = os.path.join(d, "history.csv")
            try:
                with mock.patch("inventory.excel.shutil.disk_usage",
                                side_effect=OSError("no drive")):
                    wb, TH, filas = excel.build_workbook([juego], 1.0, 2.0, 4.0)
                self.assertEqual(TH, 10.0)
                path = os.path.join(d, "x.xlsx")
                wb.save(path)
                self.assertTrue(os.path.exists(path))
            finally:
                excel.HISTORY_CSV = original


class ConfigTests(unittest.TestCase):
    def test_data_root_prefers_project_data(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "data"))
            self.assertEqual(_data_root(d, "elsewhere"), d)

    def test_data_root_accepts_git_checkout(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".git"))
            self.assertEqual(_data_root(d, "elsewhere"), d)

    def test_data_root_falls_back_to_cwd(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(_data_root(d, "elsewhere"), "elsewhere")


class ScanTests(unittest.TestCase):
    def setUp(self):
        set_lang("en")

    def test_scan_finds_a_game(self):
        with tempfile.TemporaryDirectory() as d:
            game_dir = os.path.join(d, "Fake Game")
            os.makedirs(game_dir)
            with open(os.path.join(game_dir, "file.bin"), "wb") as f:
                f.write(b"x" * 1024)
            with mock.patch("inventory.scan.LIBRARIES", [d]), \
                 mock.patch("inventory.scan.LOOSE_PATHS", []):
                games, failed = scan_games()
            self.assertEqual(failed, [])
            self.assertEqual(len(games), 1)
            self.assertEqual(games[0]["name"], "Fake Game")
            self.assertEqual(games[0]["unit"], d[0] + ":")
            self.assertEqual(games[0]["path"], game_dir)
            self.assertFalse(games[0]["duplicate"])

    def test_scan_marks_duplicates_and_loose_paths(self):
        with tempfile.TemporaryDirectory() as d:
            first = os.path.join(d, "Same Game")
            second = os.path.join(d, "Same_Game")
            os.makedirs(first)
            os.makedirs(second)
            with mock.patch("inventory.scan.LIBRARIES", [d]), \
                 mock.patch("inventory.scan.LOOSE_PATHS", [first]):
                games, failed = scan_games()
            self.assertEqual(failed, [])
            self.assertTrue(any(g["duplicate"] for g in games))
            self.assertTrue(any(g["path"] == first for g in games))

    def test_scan_excludes_known_folders(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "emuladores"))
            os.makedirs(os.path.join(d, "Game"))
            with mock.patch("inventory.scan.LIBRARIES", [d]), \
                 mock.patch("inventory.scan.LOOSE_PATHS", []):
                games, failed = scan_games()
            self.assertEqual(failed, [])
            self.assertEqual([g["name"] for g in games], ["Game"])

    def test_scan_reports_unreadable_library(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("inventory.scan.LIBRARIES", [d]), \
                 mock.patch("inventory.scan.LOOSE_PATHS", []), \
                 mock.patch("inventory.scan.os.listdir", side_effect=OSError("no")):
                with redirect_stdout(io.StringIO()):
                    games, failed = scan_games()
            self.assertEqual(games, [])
            self.assertEqual(failed, [d])

    def test_scan_survives_size_errors(self):
        with tempfile.TemporaryDirectory() as d:
            game_dir = os.path.join(d, "Game")
            os.makedirs(game_dir)
            with open(os.path.join(game_dir, "file.bin"), "wb") as f:
                f.write(b"x")
            with mock.patch("inventory.scan.LIBRARIES", [d]), \
                 mock.patch("inventory.scan.LOOSE_PATHS", []), \
                 mock.patch("inventory.scan.os.path.getsize", side_effect=OSError("x")):
                games, failed = scan_games()
            self.assertEqual(failed, [])
            self.assertEqual(games[0]["gb"], 0.0)

    def test_days_installed_survives_stat_error(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("inventory.scan.os.stat", side_effect=OSError("x")):
                self.assertEqual(days_installed(d), "")

    def test_excel_locked(self):
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "x.xlsx")
            with open(target, "w", encoding="utf-8") as f:
                f.write("x")
            self.assertFalse(excel_locked(target))
            with open(os.path.join(d, "~$x.xlsx"), "w", encoding="utf-8") as f:
                f.write("x")
            self.assertTrue(excel_locked(target))
            os.remove(os.path.join(d, "~$x.xlsx"))
            with mock.patch("inventory.scan.os.rename", side_effect=OSError("locked")):
                self.assertTrue(excel_locked(target))


if __name__ == "__main__":
    unittest.main()


