# -*- coding: utf-8 -*-
"""Carga, formato y escritura de los JSON de datos."""

import json
import os
import re
import shutil
import tempfile

from .config import BASES, HORAS_JSON, WISHLIST_JSON

def normaliza(n):
    n = re.sub(r"[^a-z0-9]+", " ", n.lower().strip())
    return re.sub(r"\s+", " ", n).strip()


def escribir_horas(horas):
    """Reescribe horas.json con el formato de siempre (_comentario, claves, _notas)."""
    notas = horas.get("_notas") if isinstance(horas.get("_notas"), dict) else {}
    L = ["{"]
    if "_comentario" in horas:
        L.append('  "_comentario": %s,' % json.dumps(horas["_comentario"], ensure_ascii=False))
        L.append("")
    for k, v in horas.items():
        if not k.startswith("_"):
            L.append("  %s: %s," % (json.dumps(k, ensure_ascii=False), json.dumps(v)))
    L.append("")
    mc = horas.get("_metacritic") if isinstance(horas.get("_metacritic"), dict) else {}
    if mc:
        L.append('  "_metacritic": {')
        its = list(mc.items())
        for i, (k, v) in enumerate(its):
            L.append("    %s: %s%s" % (json.dumps(k, ensure_ascii=False),
                                       json.dumps(v, ensure_ascii=False),
                                       "," if i < len(its) - 1 else ""))
        L.append("  },")
        L.append("")
    stm = horas.get("_steam") if isinstance(horas.get("_steam"), dict) else {}
    if stm:
        L.append('  "_steam": {')
        its_ = list(stm.items())
        for i, (k, v) in enumerate(its_):
            L.append("    %s: %s%s" % (json.dumps(k, ensure_ascii=False),
                                       json.dumps(v, ensure_ascii=False),
                                       "," if i < len(its_) - 1 else ""))
        L.append("  },")
        L.append("")
    dfm = horas.get("_dificultad") if isinstance(horas.get("_dificultad"), dict) else {}
    if dfm:
        L.append('  "_dificultad": {')
        its_d = list(dfm.items())
        for i, (k, v) in enumerate(its_d):
            L.append("    %s: %s%s" % (json.dumps(k, ensure_ascii=False),
                                       json.dumps(v, ensure_ascii=False),
                                       "," if i < len(its_d) - 1 else ""))
        L.append("  },")
        L.append("")
    L.append('  "_notas": {')
    items = list(notas.items())
    for i, (k, t) in enumerate(items):
        L.append("    %s: %s%s" % (json.dumps(k, ensure_ascii=False),
                                   json.dumps(t, ensure_ascii=False),
                                   "," if i < len(items) - 1 else ""))
    L.append("  }")
    L.append("}")
    with open(HORAS_JSON, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def purgar_horas(horas, claves_instaladas):
    """Quita de horas.json las claves sin carpeta. Se niega si falta alguna ubicacion:
    con una unidad apagada se borrarian claves validas."""
    ausentes = [b for b in BASES if not os.path.isdir(b)]
    if ausentes:
        print("\nNO SE PURGA: no encuentro %s. Con una unidad apagada se perderian "
              "claves validas." % ", ".join(ausentes))
        return 0
    huerf = [k for k in horas if not k.startswith("_") and k not in claves_instaladas]
    for k in huerf:
        del horas[k]
    quitadas = set(huerf)
    for bl in ("_notas", "_metacritic", "_steam", "_dificultad"):
        if isinstance(horas.get(bl), dict):
            for k in [x for x in horas[bl] if x not in claves_instaladas]:
                horas[bl].pop(k, None)
                quitadas.add(k)
    if quitadas:
        _guardar_json(HORAS_JSON, escribir_horas, horas)
    return len(quitadas)


def escribir_wishlist(meta):
    """Reescribe wishlist.json con el formato de siempre (una entrada por linea)."""
    L = ["{"]
    items = list(meta.items())
    for i, (k, v) in enumerate(items):
        coma = "," if i < len(items) - 1 else ""
        if isinstance(v, dict):
            L.append("  %s: {" % json.dumps(k, ensure_ascii=False))
            its = list(v.items())
            for j, (kk, vv) in enumerate(its):
                L.append("    %s: %s%s" % (json.dumps(kk, ensure_ascii=False), json.dumps(vv, ensure_ascii=False),
                                           "," if j < len(its) - 1 else ""))
            L.append("  }" + coma)
        else:
            L.append("  %s: %s%s" % (json.dumps(k, ensure_ascii=False), json.dumps(v, ensure_ascii=False), coma))
    L.append("}")
    with open(WISHLIST_JSON, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def _guardar_json(ruta, escritor, objeto):
    """Escribe con 'escritor' y comprueba que el fichero releido es igual al objeto; si no, restaura la copia previa
    (guardada en la carpeta temporal)."""
    previo = os.path.join(tempfile.gettempdir(), "inventario_prev_" + os.path.basename(ruta))
    try:
        shutil.copy2(ruta, previo)
    except Exception:
        previo = None
    escritor(objeto)
    try:
        ok = json.load(open(ruta, encoding="utf-8")) == objeto
    except Exception:
        ok = False
    if not ok:
        print("AVISO: %s no se pudo reescribir con fidelidad; restauro la version anterior "
              "(los datos nuevos de esta pasada no se guardan)." % os.path.basename(ruta))
        if previo:
            shutil.copy2(previo, ruta)
    return ok


def _dic(d, k):
    if not isinstance(d.get(k), dict):
        d[k] = {}
    return d[k]
