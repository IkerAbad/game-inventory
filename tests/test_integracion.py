# -*- coding: utf-8 -*-
"""Prueba de extremo a extremo: main() con datos y juegos de mentira."""

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

import openpyxl

from inventory.cli import main


def juego(nombre, gb):
    return {"nombre": nombre, "gb": gb, "dias": 3, "unidad": "C:",
            "ruta": "C:\\" + nombre, "duplicado": False}


class PruebasIntegracion(unittest.TestCase):
    def test_main_completo(self):
        with tempfile.TemporaryDirectory() as d:
            datos = os.path.join(d, "datos")
            os.makedirs(datos)
            rutas = {
                "HOURS_JSON": os.path.join(datos, "hours.json"),
                "WISHLIST_JSON": os.path.join(datos, "wishlist.json"),
                "COMPLETED_JSON": os.path.join(datos, "completed.json"),
                "PLAYING_JSON": os.path.join(datos, "playing.json"),
            }
            with open(rutas["HOURS_JSON"], "w", encoding="utf-8") as f:
                json.dump({
                    "juego a": 10.0,
                    "juego b": None,
                    "_notas": {"juego a": "nota de prueba"},
                    "_metacritic": {"juego a": {"s": 85, "p": "PC", "n": 10}},
                    "_dificultad": {"juego a": {"h": 5, "c": 5, "ct": "consenso"}},
                }, f)
            with open(rutas["WISHLIST_JSON"], "w", encoding="utf-8") as f:
                json.dump({
                    "juegos": {"Juego C": 5.0, "Juego D": "?"},
                    "_notas": {"Juego C": "PRENSA (prueba)"},
                    "_metacritic": {}, "_steam": {}, "_dificultad": {},
                }, f)
            with open(rutas["COMPLETED_JSON"], "w", encoding="utf-8") as f:
                json.dump([], f)
            with open(rutas["PLAYING_JSON"], "w", encoding="utf-8") as f:
                json.dump(["Juego A"], f)

            salida = os.path.join(d, "salida.xlsx")
            juegos = [juego("Juego A", 2.0), juego("Juego B", 1.0)]
            with mock.patch.multiple("inventory.cli", DATA_DIR=datos, **rutas), \
                 mock.patch("inventory.cli.scan_games", return_value=(juegos, [])), \
                 mock.patch("inventory.excel.HISTORY_CSV",
                            os.path.join(datos, "history.csv")):
                with redirect_stdout(io.StringIO()) as consola:
                    rc = main(["--sin-red", "--conservar", "--salida", salida])

            self.assertEqual(rc, 0, consola.getvalue())
            self.assertTrue(os.path.exists(salida))
            self.assertTrue(os.path.exists(os.path.join(datos, "history.csv")))
            wb = openpyxl.load_workbook(salida)
            self.assertEqual(wb.sheetnames,
                             ["Games", "Space", "Summary", "Plan", "History", "Wishlist"])
            self.assertEqual(wb["Games"].max_row, 7)
            self.assertEqual(wb["Games"]["A5"].value, "Juego A")
            self.assertIn("PLAYING", wb["Games"]["F5"].value)
            self.assertEqual(wb["Games"]["H5"].value, 85)
            self.assertEqual(wb["Games"]["A6"].value, "Juego B")
            self.assertIn("NO END", wb["Games"]["F6"].value)


class PruebasAbortos(unittest.TestCase):
    def test_aborta_si_la_salida_es_una_carpeta(self):
        with tempfile.TemporaryDirectory() as d:
            datos = os.path.join(d, "datos")
            with mock.patch("inventory.cli.DATA_DIR", datos):
                with redirect_stdout(io.StringIO()):
                    rc = main(["--sin-red", "--salida", d])
            self.assertEqual(rc, 1)

    def test_aborta_si_la_salida_esta_en_datos(self):
        with tempfile.TemporaryDirectory() as d:
            datos = os.path.join(d, "datos")
            os.makedirs(datos)
            with mock.patch("inventory.cli.DATA_DIR", datos):
                with redirect_stdout(io.StringIO()):
                    rc = main(["--sin-red", "--salida",
                               os.path.join(datos, "x.xlsx")])
            self.assertEqual(rc, 1)

    def test_aborta_si_hay_otra_ejecucion(self):
        with tempfile.TemporaryDirectory() as d:
            datos = os.path.join(d, "datos")
            os.makedirs(datos)
            with mock.patch("inventory.cli.DATA_DIR", datos), \
                 mock.patch("inventory.cli.acquire_lock", return_value=None):
                with redirect_stdout(io.StringIO()):
                    rc = main(["--sin-red", "--salida",
                               os.path.join(d, "x.xlsx")])
            self.assertEqual(rc, 1)

    def test_aborta_con_json_corrupto(self):
        with tempfile.TemporaryDirectory() as d:
            datos = os.path.join(d, "datos")
            os.makedirs(datos)
            rutas = {
                "HOURS_JSON": os.path.join(datos, "hours.json"),
                "WISHLIST_JSON": os.path.join(datos, "wishlist.json"),
                "COMPLETED_JSON": os.path.join(datos, "completed.json"),
                "PLAYING_JSON": os.path.join(datos, "playing.json"),
            }
            with open(rutas["HOURS_JSON"], "w", encoding="utf-8") as f:
                f.write("{ mal")
            salida = os.path.join(d, "x.xlsx")
            with mock.patch.multiple("inventory.cli", DATA_DIR=datos, **rutas), \
                 mock.patch("inventory.cli.acquire_lock",
                            return_value=mock.MagicMock()):
                with redirect_stdout(io.StringIO()):
                    rc = main(["--sin-red", "--salida", salida])
            self.assertEqual(rc, 1)
            self.assertFalse(os.path.exists(salida))


if __name__ == "__main__":
    unittest.main()
