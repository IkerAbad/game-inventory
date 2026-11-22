# -*- coding: utf-8 -*-
"""Pruebas de robustez: JSON con BOM o corrupto, horas invalidas y escritura atomica."""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from inventory import excel
from inventory.cli import inside_data
from inventory.config import DATA_DIR
from inventory.i18n import set_lang
from inventory.data import (_save_json, clean_hours, write_atomic, write_hours,
                              is_valid_hours, read_keys, read_json, clean_temp_files,
                              purge_hours, acquire_lock)
from inventory.scan import scan_games
from inventory.cell_format import clean_text
from inventory.network import steam_search


class ReadJsonTests(unittest.TestCase):
    def test_missing_returns_default(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(read_json(os.path.join(d, "no.json"), {"x": 1}), {"x": 1})

    def test_accepts_bom(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "x.json")
            with open(ruta, "w", encoding="utf-8-sig") as f:
                json.dump({"a": 1}, f)
            self.assertEqual(read_json(ruta, {}), {"a": 1})

    def test_corrupt_reports_position(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "x.json")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("{ mal")
            with self.assertRaises(ValueError) as ctx:
                read_json(ruta, {})
            self.assertIn("not valid JSON", str(ctx.exception))
            self.assertIn("line", str(ctx.exception))

    def test_keys_require_list(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "x.json")
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump({"a": 1}, f)
            with self.assertRaises(ValueError):
                read_keys(ruta)

    def test_no_utf8(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "x.json")
            with open(ruta, "wb") as f:
                f.write(b"\xff\xfe{")
            with self.assertRaises(ValueError) as ctx:
                read_json(ruta, {})
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
            ruta = os.path.join(d, "x.json")
            write_atomic(ruta, '{"a": 1}\n')
            self.assertEqual(read_json(ruta, {}), {"a": 1})
            self.assertEqual([n for n in os.listdir(d) if n.startswith(".tmp_")], [])

    def test_save_json_tolerates_nan(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "x.json")

            def escritor(obj):
                with open(ruta, "w", encoding="utf-8") as f:
                    json.dump(obj, f)

            self.assertTrue(_save_json(ruta, escritor, {"a": float("nan")}))

    def test_hours_keeps_unknown_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "hours.json")
            with mock.patch("inventory.data.HOURS_JSON", ruta):
                write_hours({"juego": 10, "_raro": {"a": 1}})
            self.assertEqual(read_json(ruta, {})["_raro"], {"a": 1})

    def test_history_ignores_broken_rows(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "history.csv")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("fecha,juegos,gb,horas\n")
                f.write("2026-01-01,10,100.0,50.0\n")
                f.write("no-es-fecha,10,100.0,50.0\n")
                f.write("2026-01-02,dos,100.0,50.0\n")
            original = excel.HISTORY_CSV
            excel.HISTORY_CSV = ruta
            try:
                with redirect_stdout(io.StringIO()):
                    filas = excel.append_history([], 0.0)
            finally:
                excel.HISTORY_CSV = original
            self.assertEqual(len(filas), 2)
            self.assertEqual(filas[0][0], "2026-01-01")
            with open(ruta, encoding="utf-8") as f:
                texto = f.read()
            self.assertNotIn("no-es-fecha", texto)
            self.assertNotIn("2026-01-02", texto)
            self.assertTrue(os.path.exists(ruta + ".corrupto"))
            with open(ruta + ".corrupto", encoding="utf-8") as f:
                self.assertIn("no-es-fecha", f.read())

    def test_history_non_utf8_is_regenerated(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "history.csv")
            with open(ruta, "wb") as f:
                f.write(b"\xff\xfe")
            original = excel.HISTORY_CSV
            excel.HISTORY_CSV = ruta
            try:
                with redirect_stdout(io.StringIO()):
                    filas = excel.append_history([], 0.0)
            finally:
                excel.HISTORY_CSV = original
            self.assertEqual(len(filas), 1)
            self.assertTrue(os.path.exists(ruta))
            self.assertTrue(os.path.exists(ruta + ".corrupto"))
            with open(ruta + ".corrupto", "rb") as f:
                self.assertEqual(f.read(), b"\xff\xfe")

    def test_empty_workbook_without_drives(self):
        with tempfile.TemporaryDirectory() as d:
            original = excel.HISTORY_CSV
            excel.HISTORY_CSV = os.path.join(d, "history.csv")
            try:
                with mock.patch("inventory.excel.shutil.disk_usage",
                                side_effect=OSError("sin unidad")):
                    wb, TH, filas = excel.build_workbook([], 1.0, 2.0, 4.0)
                self.assertEqual(TH, 0.0)
                self.assertEqual(wb.sheetnames,
                                 ["Games", "Space", "Summary", "Plan", "History"])
                self.assertEqual(wb["Games"]["B5"].value, 0)
                self.assertEqual(wb["Games"]["F5"].value, "0 games")
                ruta = os.path.join(d, "x.xlsx")
                wb.save(ruta)
                self.assertTrue(os.path.exists(ruta))
            finally:
                excel.HISTORY_CSV = original

    def test_text_cell_is_not_formula(self):
        import openpyxl
        with tempfile.TemporaryDirectory() as d:
            wb = openpyxl.Workbook()
            c = excel.text_cell(wb.active, 1, 1, "=1+1")
            self.assertEqual(c.data_type, "s")
            excel.text_cell(wb.active, 1, 2, "juego normal")
            excel.text_cell(wb.active, 1, 3, "\x01=2+2")
            ruta = os.path.join(d, "x.xlsx")
            wb.save(ruta)
            wb2 = openpyxl.load_workbook(ruta)
            self.assertEqual(wb2.active.cell(1, 1).data_type, "s")
            self.assertEqual(wb2.active.cell(1, 1).value, "=1+1")
            self.assertEqual(wb2.active.cell(1, 2).value, "juego normal")
            self.assertEqual(wb2.active.cell(1, 3).value, "=2+2")
            self.assertEqual(wb2.active.cell(1, 3).data_type, "s")

    def test_clean_text(self):
        self.assertEqual(clean_text("a\x01b\x1fc"), "abc")
        self.assertEqual(clean_text("linea\nnormal"), "linea\nnormal")
        self.assertEqual(len(clean_text("x" * 40000)), 32767)

    def test_clean_temp_files(self):
        with tempfile.TemporaryDirectory() as d:
            viejo = os.path.join(d, ".tmp_resto.tmp")
            with open(viejo, "w", encoding="utf-8") as f:
                f.write("x")
            with open(os.path.join(d, "hours.json"), "w", encoding="utf-8") as f:
                f.write("{}")
            clean_temp_files(d)
            self.assertFalse(os.path.exists(viejo))
            self.assertTrue(os.path.exists(os.path.join(d, "hours.json")))

    def test_purge_refuses_on_failed_base(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("inventory.data.LIBRARIES", [d]):
                horas = {"juego": 10, "_notas": {"juego": "x"}}
                with redirect_stdout(io.StringIO()):
                    quitadas = purge_hours(horas, set(), [d], force=True)
                self.assertEqual(quitadas, 0)
                self.assertIn("juego", horas)
                self.assertIn("juego", horas["_notas"])

    def test_purge_guarded_by_majority(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "hours.json")
            horas = {"juego %d" % i: 10 for i in range(12)}
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(horas, f)
            instaladas = {"juego 0", "juego 1"}
            with mock.patch("inventory.data.LIBRARIES", [d]), \
                 mock.patch("inventory.data.HOURS_JSON", ruta):
                with redirect_stdout(io.StringIO()):
                    quitadas = purge_hours(dict(horas), instaladas)
                self.assertEqual(quitadas, 0)
                self.assertEqual(len(read_json(ruta, {})), 12)
                with redirect_stdout(io.StringIO()):
                    quitadas = purge_hours(dict(horas), instaladas, force=True)
            self.assertEqual(quitadas, 10)
            self.assertEqual(len(read_json(ruta, {})), 3)  # 2 claves + _notas

    def test_purge_keeps_previous_copy(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "hours.json")
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump({"juego": 10}, f)
            with mock.patch("inventory.data.LIBRARIES", [d]), \
                 mock.patch("inventory.data.HOURS_JSON", ruta):
                with redirect_stdout(io.StringIO()):
                    quitadas = purge_hours({"juego": 10}, set())
            self.assertEqual(quitadas, 1)
            self.assertTrue(os.path.exists(ruta + ".bak"))
            with open(ruta + ".bak", encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"juego": 10})
            self.assertEqual(read_json(ruta, None), {"_notas": {}})

    def test_output_inside_data(self):
        self.assertTrue(inside_data(os.path.join(DATA_DIR, "x.xlsx")))
        self.assertTrue(inside_data(os.path.join(DATA_DIR, "sub", "x.xlsx")))
        self.assertFalse(inside_data(os.path.join(tempfile.gettempdir(), "x.xlsx")))

    def test_exclusive_lock_between_processes(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            f = acquire_lock(d)
            self.assertIsNotNone(f)
            codigo = ("import sys; sys.path.insert(0, %r); "
                      "from inventory.data import acquire_lock; "
                      "print(acquire_lock(%r) is None)" % (RAIZ, d))
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
                juegos, fallos = scan_games()
            self.assertIsInstance(juegos, list)
            self.assertEqual(fallos, [])

    def test_wishlist_non_dict_blocks(self):
        import openpyxl
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        excel.wishlist_sheet(wb, [], {"Juego": 10}, "origen", [], [], [], [])
        self.assertEqual(wb.sheetnames, ["Wishlist"])

    def test_absurd_hours_do_not_break(self):
        juego = {"nombre": "Enorme", "gb": 1.0, "dias": 1, "unidad": "C:",
                 "ruta": "C:\\Enorme", "duplicado": False, "horas": 10000000.0,
                 "mc": None, "steam": None, "dif": None, "nota_h": "",
                 "completado": False, "jugando": False, "ratio": 0.0,
                 "verdict": "medium"}
        with tempfile.TemporaryDirectory() as d:
            original = excel.HISTORY_CSV
            excel.HISTORY_CSV = os.path.join(d, "history.csv")
            try:
                with mock.patch("inventory.excel.shutil.disk_usage",
                                side_effect=OSError("sin unidad")):
                    wb, TH, filas = excel.build_workbook([juego], 1.0, 2.0, 4.0)
                self.assertEqual(TH, 10000000.0)
                ruta = os.path.join(d, "x.xlsx")
                wb.save(ruta)
                self.assertTrue(os.path.exists(ruta))
            finally:
                excel.HISTORY_CSV = original

    def test_zero_gb_game(self):
        juego = {"nombre": "Vacio", "gb": 0.0, "dias": 1, "unidad": "C:",
                 "ruta": "C:\\Vacio", "duplicado": False, "horas": 10.0,
                 "mc": None, "steam": None, "dif": None, "nota_h": "",
                 "completado": False, "jugando": False, "ratio": 0.0,
                 "verdict": "medium"}
        with tempfile.TemporaryDirectory() as d:
            original = excel.HISTORY_CSV
            excel.HISTORY_CSV = os.path.join(d, "history.csv")
            try:
                with mock.patch("inventory.excel.shutil.disk_usage",
                                side_effect=OSError("sin unidad")):
                    wb, TH, filas = excel.build_workbook([juego], 1.0, 2.0, 4.0)
                self.assertEqual(TH, 10.0)
                ruta = os.path.join(d, "x.xlsx")
                wb.save(ruta)
                self.assertTrue(os.path.exists(ruta))
            finally:
                excel.HISTORY_CSV = original


if __name__ == "__main__":
    unittest.main()


