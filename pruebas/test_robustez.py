# -*- coding: utf-8 -*-
"""Pruebas de robustez: JSON con BOM o corrupto, horas invalidas y escritura atomica."""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from inventario import excel
from inventario.datos import depurar_horas, escribir_atomico, leer_claves, leer_json


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


if __name__ == "__main__":
    unittest.main()
