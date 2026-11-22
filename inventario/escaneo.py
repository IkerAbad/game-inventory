# -*- coding: utf-8 -*-
"""Escaneo de las carpetas de juegos instalados."""

import os

from .config import BASES, EXCLUIR, SUELTOS
from .datos import normaliza

def tam_gb(p):
    t = 0
    for r, d, f in os.walk(p):
        for x in f:
            try:
                t += os.path.getsize(os.path.join(r, x))
            except Exception:
                pass
    return t / 1024 ** 3


def dias_instalado(p):
    """Dias desde que existe la carpeta. Usa la fecha mas antigua disponible."""
    import time
    try:
        st = os.stat(p)
        t = min(st.st_ctime, st.st_mtime)
        return int((time.time() - t) / 86400)
    except Exception:
        return ""


def escanear():
    out, vistos = [], set()
    for base in BASES:
        if not os.path.isdir(base):
            continue
        u = base[0]
        try:
            nombres = sorted(os.listdir(base))
        except OSError as e:
            print("Aviso: no se puede leer %s (%s); se omite." % (base, e))
            continue
        for n in nombres:
            p = os.path.join(base, n)
            if not os.path.isdir(p) or normaliza(n) in EXCLUIR:
                continue
            clave = normaliza(n)
            dup = clave in vistos
            vistos.add(clave)
            out.append({"nombre": n, "gb": round(tam_gb(p), 2), "dias": dias_instalado(p),
                        "unidad": u + ":", "ruta": p, "duplicado": dup})
    for p in SUELTOS:
        if os.path.isdir(p):
            out.append({"nombre": os.path.basename(p), "gb": round(tam_gb(p), 2),
                        "dias": dias_instalado(p),
                        "unidad": p[0] + ":", "ruta": p, "duplicado": False})
    return out


def bloqueado(ruta):
    """True si el Excel esta abierto: fichero de bloqueo ~$ o handle exclusivo."""
    if not os.path.exists(ruta):
        return False
    lock = os.path.join(os.path.dirname(ruta), "~$" + os.path.basename(ruta))
    if os.path.exists(lock):
        return True
    try:
        os.rename(ruta, ruta)
        return False
    except (IOError, OSError, PermissionError):
        return True
