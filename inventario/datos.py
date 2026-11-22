# -*- coding: utf-8 -*-
"""Carga, formato y escritura de los JSON de datos."""

import json
import math
import os
import re
import shutil
import tempfile

from .config import BASES, HORAS_JSON, WISHLIST_JSON

def normaliza(n):
    n = re.sub(r"[^a-z0-9]+", " ", str(n).lower().strip())
    return re.sub(r"\s+", " ", n).strip()


def es_hora_valida(v):
    """True para una duracion util: numero finito entre 0 y 1.000.000 de horas (no vale bool)."""
    return (isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(v) and 0 < v <= 1000000)


def leer_json(ruta, defecto):
    """Lee un JSON UTF-8, con o sin BOM. Devuelve 'defecto' si no existe.
    Lanza ValueError con la ruta y la posicion si el fichero esta corrupto."""
    if not os.path.exists(ruta):
        return defecto
    try:
        with open(ruta, encoding="utf-8-sig") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError("%s no es JSON valido (linea %d, columna %d): %s"
                         % (ruta, e.lineno, e.colno, e.msg)) from e
    except UnicodeDecodeError as e:
        raise ValueError("%s no esta en UTF-8: %s" % (ruta, e)) from e
    except OSError as e:
        raise ValueError("no se puede leer %s: %s" % (ruta, e)) from e


def leer_claves(ruta):
    """Claves de un JSON que debe ser una lista de titulos (completados, jugando)."""
    datos = leer_json(ruta, [])
    if not isinstance(datos, list):
        raise ValueError("%s debe ser una lista de titulos" % ruta)
    return {normaliza(x) for x in datos if not str(x).startswith("_")}


def depurar_horas(horas):
    """Devuelve (horas limpias, avisos). Un valor que no sea un numero positivo, null o '?'
    pasa a '?' para que no rompa los calculos. No modifica el fichero."""
    limpias, avisos = {}, []
    for k, v in horas.items():
        if k.startswith("_"):
            limpias[k] = v
        elif v is None or v == "?":
            limpias[k] = v
        elif es_hora_valida(v):
            limpias[k] = v
        else:
            limpias[k] = "?"
            avisos.append("%s = %r" % (k, v))
    return limpias, avisos


def tomar_bloqueo(carpeta):
    """Bloqueo exclusivo no bloqueante para evitar dos ejecuciones a la vez.
    Devuelve el fichero abierto (hay que mantenerlo vivo) o None si ya esta ocupado."""
    f = open(os.path.join(carpeta, ".bloqueo"), "a+b")
    try:
        if os.name == "nt":
            import msvcrt
            if os.fstat(f.fileno()).st_size == 0:
                f.write(b"x")
                f.flush()
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


def limpiar_temporales(carpeta):
    """Borra restos .tmp_* de escrituras interrumpidas. Llamar solo con el bloqueo tomado."""
    try:
        nombres = os.listdir(carpeta)
    except OSError:
        return
    for n in nombres:
        if n.startswith(".tmp_"):
            try:
                os.remove(os.path.join(carpeta, n))
            except OSError:
                pass


def escribir_atomico(ruta, texto):
    """Escribe en un temporal de la misma carpeta y lo renombra. Si falla a mitad,
    el fichero original queda intacto."""
    carpeta = os.path.dirname(os.path.abspath(ruta))
    fd, tmp = tempfile.mkstemp(dir=carpeta, prefix=".tmp_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(texto)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, ruta)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def escribir_horas(horas):
    """Reescribe horas.json con el formato de siempre (_comentario, claves, _notas)."""
    notas = horas.get("_notas") if isinstance(horas.get("_notas"), dict) else {}
    horas["_notas"] = notas      # el objeto debe coincidir con lo que se escribe (verificacion de _guardar_json)
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
    conocidos = {"_comentario", "_metacritic", "_steam", "_dificultad", "_notas"}
    for k, v in horas.items():
        if k.startswith("_") and k not in conocidos:
            L.append("  %s: %s," % (json.dumps(k, ensure_ascii=False),
                                    json.dumps(v, ensure_ascii=False)))
            L.append("")
    L.append('  "_notas": {')
    items = list(notas.items())
    for i, (k, t) in enumerate(items):
        L.append("    %s: %s%s" % (json.dumps(k, ensure_ascii=False),
                                   json.dumps(t, ensure_ascii=False),
                                   "," if i < len(items) - 1 else ""))
    L.append("  }")
    L.append("}")
    escribir_atomico(HORAS_JSON, "\n".join(L) + "\n")


def purgar_horas(horas, claves_instaladas, bases_fallidas=(), forzar=False):
    """Quita de horas.json las claves sin carpeta. Se niega si falta alguna ubicacion,
    si alguna no se pudo leer o si se querria borrar mas de la mitad de un golpe."""
    problemas = []
    ausentes = [b for b in BASES if isinstance(b, str) and b and not os.path.isdir(b)]
    if ausentes:
        problemas.append("no encuentro " + ", ".join(ausentes))
    if bases_fallidas:
        problemas.append("no se pudo leer " + ", ".join(bases_fallidas))
    if problemas:
        print("\nNO SE PURGA: %s. Con una unidad apagada o sin permiso se perderian "
              "claves validas." % "; ".join(problemas))
        return 0
    total = sum(1 for k in horas if not k.startswith("_"))
    huerf = [k for k in horas if not k.startswith("_") and k not in claves_instaladas]
    if not forzar and total >= 10 and len(huerf) > total // 2:
        print("\nNO SE PURGA: se quitarian %d de %d claves (mas de la mitad). Revisa que "
              "las unidades esten bien y repite con --forzar-purga si es correcto."
              % (len(huerf), total))
        return 0
    for k in huerf:
        del horas[k]
    quitadas = set(huerf)
    for bl in ("_notas", "_metacritic", "_steam", "_dificultad"):
        if isinstance(horas.get(bl), dict):
            for k in [x for x in horas[bl] if x not in claves_instaladas]:
                horas[bl].pop(k, None)
                quitadas.add(k)
    if quitadas:
        try:
            shutil.copy2(HORAS_JSON, HORAS_JSON + ".bak")
        except OSError:
            pass
        try:
            _guardar_json(HORAS_JSON, escribir_horas, horas)
        except OSError as e:
            print("AVISO: no se pudo escribir horas.json (%s)." % e)
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
    escribir_atomico(WISHLIST_JSON, "\n".join(L) + "\n")


def _mismo(a, b):
    """Igualdad de datos JSON tolerante con NaN (nan != nan en Python)."""
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_mismo(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_mismo(x, y) for x, y in zip(a, b))
    return a == b


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
        ok = _mismo(leer_json(ruta, None), objeto)
    except ValueError:
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
