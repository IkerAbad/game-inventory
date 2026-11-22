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

from inventario import excel
from inventario.cli import dentro_de_datos
from inventario.config import DATOS
from inventario.datos import (depurar_horas, escribir_atomico, es_hora_valida, leer_claves,
                              leer_json, purgar_horas, tomar_bloqueo)
from inventario.escaneo import escanear
from inventario.formato import limpia_texto
from inventario.red import steam_buscar


class PruebasLeerJson(unittest.TestCase):
    def test_inexistente_devuelve_defecto(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(leer_json(os.path.join(d, "no.json"), {"x": 1}), {"x": 1})

    def test_acepta_bom(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "x.json")
            with open(ruta, "w", encoding="utf-8-sig") as f:
                json.dump({"a": 1}, f)
            self.assertEqual(leer_json(ruta, {}), {"a": 1})

    def test_corrupto_avisa_con_posicion(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "x.json")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("{ mal")
            with self.assertRaises(ValueError) as ctx:
                leer_json(ruta, {})
            self.assertIn("no es JSON valido", str(ctx.exception))
            self.assertIn("linea", str(ctx.exception))

    def test_claves_exige_lista(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "x.json")
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump({"a": 1}, f)
            with self.assertRaises(ValueError):
                leer_claves(ruta)

    def test_no_utf8(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "x.json")
            with open(ruta, "wb") as f:
                f.write(b"\xff\xfe{")
            with self.assertRaises(ValueError) as ctx:
                leer_json(ruta, {})
            self.assertIn("UTF-8", str(ctx.exception))


class PruebasDepurarHoras(unittest.TestCase):
    def test_validos(self):
        limpio, avisos = depurar_horas({"a": 12.5, "b": None, "c": "?", "_notas": {"a": "x"}})
        self.assertEqual(limpio["a"], 12.5)
        self.assertIsNone(limpio["b"])
        self.assertEqual(limpio["c"], "?")
        self.assertEqual(limpio["_notas"], {"a": "x"})
        self.assertEqual(avisos, [])

    def test_invalidos_pasan_a_sin_datos(self):
        limpio, avisos = depurar_horas(
            {"a": 0, "b": -3, "c": "doce", "d": True, "e": float("nan")})
        for k in "abcde":
            self.assertEqual(limpio[k], "?")
        self.assertEqual(len(avisos), 5)

    def test_es_hora_valida(self):
        self.assertTrue(es_hora_valida(12.5))
        self.assertTrue(es_hora_valida(1))
        self.assertFalse(es_hora_valida(0))
        self.assertFalse(es_hora_valida(-1))
        self.assertFalse(es_hora_valida(float("nan")))
        self.assertFalse(es_hora_valida(float("inf")))
        self.assertFalse(es_hora_valida(True))
        self.assertFalse(es_hora_valida("12"))
        self.assertFalse(es_hora_valida(None))


class PruebasEscritura(unittest.TestCase):
    def test_atomica_y_sin_temporales(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "x.json")
            escribir_atomico(ruta, '{"a": 1}\n')
            self.assertEqual(leer_json(ruta, {}), {"a": 1})
            self.assertEqual([n for n in os.listdir(d) if n.startswith(".tmp_")], [])

    def test_historico_ignora_filas_rotas(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "historico.csv")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("fecha,juegos,gb,horas\n")
                f.write("2026-01-01,10,100.0,50.0\n")
                f.write("no-es-fecha,10,100.0,50.0\n")
                f.write("2026-01-02,dos,100.0,50.0\n")
            original = excel.HISTORICO_CSV
            excel.HISTORICO_CSV = ruta
            try:
                with redirect_stdout(io.StringIO()):
                    filas = excel.historico([], 0.0)
            finally:
                excel.HISTORICO_CSV = original
            self.assertEqual(len(filas), 2)
            self.assertEqual(filas[0][0], "2026-01-01")
            with open(ruta, encoding="utf-8") as f:
                texto = f.read()
            self.assertNotIn("no-es-fecha", texto)
            self.assertNotIn("2026-01-02", texto)

    def test_historico_no_utf8_se_regenera(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "historico.csv")
            with open(ruta, "wb") as f:
                f.write(b"\xff\xfe")
            original = excel.HISTORICO_CSV
            excel.HISTORICO_CSV = ruta
            try:
                with redirect_stdout(io.StringIO()):
                    filas = excel.historico([], 0.0)
            finally:
                excel.HISTORICO_CSV = original
            self.assertEqual(len(filas), 1)
            self.assertTrue(os.path.exists(ruta))

    def test_libro_vacio_sin_unidades(self):
        with tempfile.TemporaryDirectory() as d:
            original = excel.HISTORICO_CSV
            excel.HISTORICO_CSV = os.path.join(d, "historico.csv")
            try:
                with mock.patch("inventario.excel.shutil.disk_usage",
                                side_effect=OSError("sin unidad")):
                    wb, TH, filas = excel.construir([], 1.0, 2.0, 4.0)
                self.assertEqual(TH, 0.0)
                self.assertEqual(wb.sheetnames,
                                 ["Juegos", "Espacio", "Resumen", "Plan", "Historico"])
                self.assertEqual(wb["Juegos"]["B5"].value, 0)
                self.assertEqual(wb["Juegos"]["F5"].value, "0 juegos")
                ruta = os.path.join(d, "x.xlsx")
                wb.save(ruta)
                self.assertTrue(os.path.exists(ruta))
            finally:
                excel.HISTORICO_CSV = original

    def test_celda_texto_no_es_formula(self):
        import openpyxl
        with tempfile.TemporaryDirectory() as d:
            wb = openpyxl.Workbook()
            c = excel.celda_texto(wb.active, 1, 1, "=1+1")
            self.assertEqual(c.data_type, "s")
            excel.celda_texto(wb.active, 1, 2, "juego normal")
            excel.celda_texto(wb.active, 1, 3, "\x01=2+2")
            ruta = os.path.join(d, "x.xlsx")
            wb.save(ruta)
            wb2 = openpyxl.load_workbook(ruta)
            self.assertEqual(wb2.active.cell(1, 1).data_type, "s")
            self.assertEqual(wb2.active.cell(1, 1).value, "=1+1")
            self.assertEqual(wb2.active.cell(1, 2).value, "juego normal")
            self.assertEqual(wb2.active.cell(1, 3).value, "=2+2")
            self.assertEqual(wb2.active.cell(1, 3).data_type, "s")

    def test_limpia_texto(self):
        self.assertEqual(limpia_texto("a\x01b\x1fc"), "abc")
        self.assertEqual(limpia_texto("linea\nnormal"), "linea\nnormal")
        self.assertEqual(len(limpia_texto("x" * 40000)), 32767)

    def test_purga_se_niega_si_falla_una_base(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("inventario.datos.BASES", [d]):
                horas = {"juego": 10, "_notas": {"juego": "x"}}
                with redirect_stdout(io.StringIO()):
                    quitadas = purgar_horas(horas, set(), [d])
                self.assertEqual(quitadas, 0)
                self.assertIn("juego", horas)
                self.assertIn("juego", horas["_notas"])

    def test_salida_dentro_de_datos(self):
        self.assertTrue(dentro_de_datos(os.path.join(DATOS, "x.xlsx")))
        self.assertTrue(dentro_de_datos(os.path.join(DATOS, "sub", "x.xlsx")))
        self.assertFalse(dentro_de_datos(os.path.join(tempfile.gettempdir(), "x.xlsx")))

    def test_bloqueo_exclusivo_entre_procesos(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            f = tomar_bloqueo(d)
            self.assertIsNotNone(f)
            codigo = ("import sys; sys.path.insert(0, %r); "
                      "from inventario.datos import tomar_bloqueo; "
                      "print(tomar_bloqueo(%r) is None)" % (RAIZ, d))
            salida = subprocess.run([sys.executable, "-c", codigo],
                                    capture_output=True, text=True)
            self.assertEqual(salida.stdout.strip(), "True", salida.stderr)
            f.close()
            f2 = tomar_bloqueo(d)
            self.assertIsNotNone(f2)
            f2.close()

    def test_steam_buscar_respuestas_raras(self):
        with mock.patch("inventario.red._json_get", return_value=[]):
            self.assertIsNone(steam_buscar(["Juego"]))
        with mock.patch("inventario.red._json_get",
                        return_value={"items": [None, 3, {"type": "app"}]}):
            self.assertIsNone(steam_buscar(["Juego"]))
        with mock.patch("inventario.red._json_get", return_value={"items": "x"}):
            self.assertIsNone(steam_buscar(["Juego"]))

    def test_escanear_ignora_bases_invalidas(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("inventario.escaneo.BASES", [None, 123, d]):
                juegos, fallos = escanear()
            self.assertIsInstance(juegos, list)
            self.assertEqual(fallos, [])

    def test_wishlist_bloques_no_dict(self):
        import openpyxl
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        excel.hoja_wishlist(wb, [], {"Juego": 10}, "origen", [], [], [], [])
        self.assertEqual(wb.sheetnames, ["Wishlist"])

    def test_horas_absurdas_no_rompen(self):
        juego = {"nombre": "Enorme", "gb": 1.0, "dias": 1, "unidad": "C:",
                 "ruta": "C:\\Enorme", "duplicado": False, "horas": 10000000.0,
                 "mc": None, "steam": None, "dif": None, "nota_h": "",
                 "completado": False, "jugando": False, "ratio": 0.0,
                 "veredicto": "Ratio medio"}
        with tempfile.TemporaryDirectory() as d:
            original = excel.HISTORICO_CSV
            excel.HISTORICO_CSV = os.path.join(d, "historico.csv")
            try:
                with mock.patch("inventario.excel.shutil.disk_usage",
                                side_effect=OSError("sin unidad")):
                    wb, TH, filas = excel.construir([juego], 1.0, 2.0, 4.0)
                self.assertEqual(TH, 10000000.0)
                ruta = os.path.join(d, "x.xlsx")
                wb.save(ruta)
                self.assertTrue(os.path.exists(ruta))
            finally:
                excel.HISTORICO_CSV = original

    def test_juego_de_cero_gb(self):
        juego = {"nombre": "Vacio", "gb": 0.0, "dias": 1, "unidad": "C:",
                 "ruta": "C:\\Vacio", "duplicado": False, "horas": 10.0,
                 "mc": None, "steam": None, "dif": None, "nota_h": "",
                 "completado": False, "jugando": False, "ratio": 0.0,
                 "veredicto": "Ratio medio"}
        with tempfile.TemporaryDirectory() as d:
            original = excel.HISTORICO_CSV
            excel.HISTORICO_CSV = os.path.join(d, "historico.csv")
            try:
                with mock.patch("inventario.excel.shutil.disk_usage",
                                side_effect=OSError("sin unidad")):
                    wb, TH, filas = excel.construir([juego], 1.0, 2.0, 4.0)
                self.assertEqual(TH, 10.0)
                ruta = os.path.join(d, "x.xlsx")
                wb.save(ruta)
                self.assertTrue(os.path.exists(ruta))
            finally:
                excel.HISTORICO_CSV = original


if __name__ == "__main__":
    unittest.main()
