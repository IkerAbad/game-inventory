# -*- coding: utf-8 -*-
"""Rutas y ajustes. Unico sitio donde se cambian las unidades y la salida."""

import os

# Carpetas que se escanean (una entrada por biblioteca de juegos).
BASES = [
    r"C:\Matrix Games",
    r"C:\Program Files (x86)\Steam\steamapps\common",
    r"D:\Games",
    r"E:\Games",
    r"E:\SteamLibrary\steamapps\common",
    r"F:\Games",
]
# Instalaciones sueltas fuera de las carpetas anteriores.
SUELTOS = [
    r"C:\Program Files\PRAGMATA",
    r"C:\Program Files\Stellar Blade",
    r"C:\Program Files (x86)\Diablo II Resurrected",
    r"C:\Battlestate Games",
]
EXCLUIR = {"steamworks shared", "steam controller configs", "emuladores"}

# Raiz del repositorio (el paquete vive en <raiz>/inventario).
AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Los datos personales viven en datos/ y no se versionan (ver .gitignore).
DATOS = os.path.join(AQUI, "datos")
HORAS_JSON = os.path.join(DATOS, "horas.json")
COMPLETADOS_JSON = os.path.join(DATOS, "completados.json")
JUGANDO_JSON = os.path.join(DATOS, "jugando.json")
HISTORICO_CSV = os.path.join(DATOS, "historico.csv")
WISHLIST_JSON = os.path.join(DATOS, "wishlist.json")
SALIDA = r"C:\Users\ikerf\Desktop\Juegos\Inventario juegos GB por hora.xlsx"

# Autocompletado por red.
UA_WEB = "InventarioJuegos/1.0 (uso personal; sin automatizacion masiva)"
MAX_PETICIONES = 600
REINTENTO_DIAS = 30


