# -*- coding: utf-8 -*-
"""Pruebas de las piezas sin red ni disco: normalizacion, titulos y formato."""

import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from inventario.datos import normaliza
from inventario.formato import PctSteam, dif_celdas, mc_celda
from inventario.red import _fmt_h, _horas_texto, _slugs, _tokens, casar_titulo


class PruebasNormaliza(unittest.TestCase):
    def test_simbolos_y_mayusculas(self):
        self.assertEqual(normaliza("Divinity: Original Sin 2"), "divinity original sin 2")
        self.assertEqual(normaliza("  BALL x PIT  "), "ball x pit")
        self.assertEqual(normaliza("Chicken Police - Paint it RED!"), "chicken police paint it red")

    def test_acepta_no_texto(self):
        self.assertEqual(normaliza(123), "123")
        self.assertEqual(normaliza(None), "none")


class PruebasTitulos(unittest.TestCase):
    def test_the_inicial(self):
        self.assertEqual(_tokens("The Legend of Zelda"), ["legend", "of", "zelda"])

    def test_numeros_romanos(self):
        self.assertEqual(_tokens("Alan Wake II"), ["alan", "wake", "2"])
        self.assertEqual(_tokens("Mega Man X"), ["mega", "man", "x"])

    def test_casado_exacto(self):
        self.assertEqual(casar_titulo(["Hades"], [("a", "Hades")]), ("a", "Hades"))

    def test_casado_ignora_the(self):
        self.assertEqual(casar_titulo(["The Legend of Zelda"], [("a", "Legend of Zelda")]),
                         ("a", "Legend of Zelda"))

    def test_secuela_no_casa_por_prefijo(self):
        self.assertIsNone(casar_titulo(["Hades"], [("a", "Hades II")]))

    def test_varias_fichas_es_ambiguo(self):
        cands = [("a", "Chicken Police"), ("b", "Chicken Police - Paint it RED!")]
        self.assertEqual(casar_titulo(["Chicken"], cands), "ambiguo")

    def test_slugs_prueban_romano_y_edicion(self):
        self.assertIn("alan-wake-2", _slugs("Alan Wake II"))
        self.assertIn("catherine", _slugs("Catherine Classic"))


class PruebasHoras(unittest.TestCase):
    def test_horas_y_media(self):
        self.assertEqual(_horas_texto("21\u00bd hours"), 21.5)

    def test_minutos(self):
        self.assertEqual(_horas_texto("45 minutes"), 0.8)

    def test_sin_cifra(self):
        self.assertIsNone(_horas_texto("no hay datos"))

    def test_formato(self):
        self.assertEqual(_fmt_h(24.7), "24.7")


class PruebasFormato(unittest.TestCase):
    def test_metascore_pc(self):
        self.assertEqual(mc_celda({"s": 85, "p": "PC", "n": 48}), (85, None))

    def test_metascore_con_plataforma(self):
        valor, texto = mc_celda({"s": 92, "p": "PS4", "n": 30})
        self.assertEqual(valor, 92)
        self.assertIn("PS4", texto)

    def test_steam_como_respaldo(self):
        valor, texto = mc_celda(None, {"id": 1, "name": "Juego", "n": 1234,
                                       "desc": "histograma", "pct": 92})
        self.assertIsInstance(valor, PctSteam)
        self.assertEqual(int(valor), 92)
        self.assertEqual(valor.fmt, '"S "0"%"')
        self.assertIn("92%", texto)

    def test_dificultad_consenso(self):
        h, c, texto, inferencia = dif_celdas({"h": 5, "c": 3, "ct": "consenso"})
        self.assertEqual((h, c), (5, 3))
        self.assertIn("Habilidad 5/10", texto)
        self.assertFalse(inferencia)

    def test_dificultad_inferencia_con_fuente(self):
        h, c, texto, inferencia = dif_celdas(
            {"h": 4, "c": 6, "ct": "inferencia", "src": "Wikipedia"})
        self.assertEqual((h, c), (4, 6))
        self.assertIn("fuente citada", texto)
        self.assertTrue(inferencia)

    def test_dificultad_ignora_nan(self):
        h, c, texto, inferencia = dif_celdas({"h": float("nan"), "c": 3, "ct": "consenso"})
        self.assertIsNone(h)
        self.assertEqual(c, 3)
        self.assertIn("Habilidad -/10", texto)

    def test_dificultad_con_certeza_rara(self):
        h, c, texto, inferencia = dif_celdas({"h": 5, "c": 5, "ct": ["raro"]})
        self.assertEqual((h, c), (5, 5))
        self.assertIn("raro", texto)

    def test_metascore_ignora_nan(self):
        self.assertEqual(mc_celda({"s": float("nan"), "p": "PC"}), (None, None))

    def test_sin_dificultad(self):
        self.assertEqual(dif_celdas(None), (None, None, None, False))


if __name__ == "__main__":
    unittest.main()
