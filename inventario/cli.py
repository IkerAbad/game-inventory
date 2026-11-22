# -*- coding: utf-8 -*-
"""Punto de entrada: opciones, orquestacion y resumen por consola."""

import argparse
import os
import shutil
import statistics
import sys

from .config import COMPLETADOS_JSON, DATOS, HORAS_JSON, JUGANDO_JSON, SALIDA, WISHLIST_JSON
from .datos import depurar_horas, leer_claves, leer_json, normaliza, purgar_horas
from .escaneo import bloqueado, escanear
from .excel import construir
from .formato import dif_celdas
from .red import autocompletar


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="generar_inventario",
        description="Escanea los juegos instalados, completa por red lo que falta y genera el Excel.")
    p.add_argument("--sin-red", action="store_true", help="no consulta internet")
    p.add_argument("--conservar", action="store_true",
                   help="no purga las claves de juegos desinstalados")
    p.add_argument("--salida", default=None,
                   help="ruta del Excel (por defecto, la de config.py)")
    args = p.parse_args(argv)
    salida = args.salida or SALIDA
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    if bloqueado(salida):
        print("ABORTADO: el Excel esta abierto en otro programa.")
        print("   " + salida)
        print("   Cierralo y vuelve a ejecutar. No se ha escaneado nada.")
        return 1
    try:
        os.makedirs(DATOS, exist_ok=True)
    except OSError as e:
        print("ABORTADO: no se puede crear la carpeta de datos (%s)." % e)
        return 1
    if not os.path.exists(HORAS_JSON):
        print("Aviso: no hay horas.json en datos/. Todos los juegos saldran como SIN DATOS.")
    try:
        horas = leer_json(HORAS_JSON, {})
        if not isinstance(horas, dict):
            raise ValueError("%s debe ser un objeto JSON" % HORAS_JSON)
        completados = leer_claves(COMPLETADOS_JSON)
        jugando = leer_claves(JUGANDO_JSON)
        wl_meta = leer_json(WISHLIST_JSON, {})
        if not isinstance(wl_meta, dict):
            raise ValueError("%s debe ser un objeto JSON" % WISHLIST_JSON)
        wl = wl_meta.get("juegos", {})
        if not isinstance(wl, dict):
            raise ValueError("%s: 'juegos' debe ser un objeto JSON" % WISHLIST_JSON)
    except ValueError as e:
        print("ABORTADO: " + str(e))
        print("   Revisa el fichero o restaura la copia de datos/.")
        return 1
    horas_ok, avisos_h = depurar_horas(horas)
    if avisos_h:
        print("\nAVISO: %d entradas de horas.json no son validas y se tratan como SIN DATOS:"
              % len(avisos_h))
        for a in avisos_h[:10]:
            print("   " + a)
        if len(avisos_h) > 10:
            print("   ... y %d mas" % (len(avisos_h) - 10))
    juegos = escanear()
    if not args.sin_red:
        try:
            autocompletar(juegos, horas, wl_meta)
        except Exception as e:
            print("AVISO: autocompletado interrumpido (%s: %s); se sigue con los datos que hay." % (type(e).__name__, e))
        wl = wl_meta.get("juegos", {})
    wl_num = {normaliza(t): v for t, v in wl.items()
              if isinstance(v, (int, float)) and not isinstance(v, bool)}
    mc_h = horas.get("_metacritic") if isinstance(horas.get("_metacritic"), dict) else {}
    mc_w = wl_meta.get("_metacritic") if isinstance(wl_meta.get("_metacritic"), dict) else {}
    st_h = horas.get("_steam") if isinstance(horas.get("_steam"), dict) else {}
    st_w = wl_meta.get("_steam") if isinstance(wl_meta.get("_steam"), dict) else {}
    dif_h = horas.get("_dificultad") if isinstance(horas.get("_dificultad"), dict) else {}
    dif_w = wl_meta.get("_dificultad") if isinstance(wl_meta.get("_dificultad"), dict) else {}
    desde_wl = []
    sin_datos = []
    for j in juegos:
        k = normaliza(j["nombre"])
        j["horas"] = horas_ok.get(k, "?")
        j["mc"] = mc_h.get(k)
        j["steam"] = st_h.get(k)
        j["dif"] = dif_h.get(k)
        nts_h = horas.get("_notas") if isinstance(horas.get("_notas"), dict) else {}
        j["nota_h"] = str(nts_h.get(k) or "")
        if j["horas"] == "?" and k in wl_num:
            j["horas"] = wl_num[k]
            desde_wl.append((j["nombre"], wl_num[k]))
        j["completado"] = k in completados
        j["jugando"] = k in jugando and not j["completado"]
        if j["completado"]:
            j["ratio"] = -0.5
            j["veredicto"] = "COMPLETADO - se puede borrar"
        elif j["horas"] == "?":
            j["ratio"] = -1
            j["veredicto"] = "SIN DATOS - pedir horas a Claude"
            sin_datos.append(j["nombre"])
        elif j["horas"] is None:
            j["ratio"] = 0.0
            j["veredicto"] = "SIN FINAL - decides tu"
        else:
            j["ratio"] = round(j["gb"] / j["horas"], 2)
            j["veredicto"] = "__RATIO__"
        if j["duplicado"]:
            j["veredicto"] = "DUPLICADO - borrar una copia"
        if j["jugando"]:
            j["veredicto"] = "EN CURSO - jugandolo ahora"

    rs_ = sorted(j["ratio"] for j in juegos if j["veredicto"] == "__RATIO__" and j["ratio"] > 0)
    q1_, q2_, q3_ = statistics.quantiles(rs_, n=4) if len(rs_) >= 4 else (1.0, 2.0, 4.0)
    for j in juegos:
        if j["veredicto"] == "__RATIO__":
            r = j["ratio"]
            j["veredicto"] = ("JUGAR YA - gran ratio" if r >= q3_ else
                              "Buen ratio" if r >= q2_ else
                              "Ratio medio" if r >= q1_ else
                              "Mal ratio - decidir")

    juegos.sort(key=lambda x: (not x["jugando"], -x["ratio"], -x["gb"]))

    wb, TH, filas_h = construir(
        juegos, q1_, q2_, q3_, wl=wl,
        fuente=wl_meta.get("_fuente_horas", "origen no indicado"),
        mc_w=mc_w,
        notas_w=wl_meta.get("_notas") if isinstance(wl_meta.get("_notas"), dict) else None,
        st_w=st_w, dif_w=dif_w)

    carpeta_salida = os.path.dirname(os.path.abspath(salida))
    try:
        os.makedirs(carpeta_salida, exist_ok=True)
    except OSError as e:
        print("ABORTADO: no se puede crear la carpeta del Excel (%s)." % e)
        return 1
    if os.path.exists(salida):
        base, ext = os.path.splitext(salida)
        try:
            shutil.copy2(salida, base + ".bak" + (ext or ".xlsx"))
        except Exception as e:
            print("Aviso: no se pudo hacer copia previa (%s)" % e)
    tmp = salida + ".tmp"
    try:
        wb.save(tmp)
        os.replace(tmp, salida)
    except Exception as e:
        try:
            os.remove(tmp)
        except OSError:
            pass
        print("ABORTADO: no se pudo guardar el Excel (%s). El anterior no se ha tocado." % e)
        return 1
    print("Juegos detectados: %d  |  Total: %.2f GB" % (len(juegos), sum(j["gb"] for j in juegos)))
    print("Horas pendientes: %.1f  |  A 4 h/dia: %d dias (%.2f anios)"
          % (TH, round(TH / 4), TH / 4 / 365.25))
    print("Veredicto por cuartiles de GB/h: Mal < %.2f | Medio < %.2f | Bueno < %.2f | JUGAR YA >= %.2f"
          % (q1_, q2_, q3_, q3_))
    comp = [j for j in juegos if j["completado"]]
    if comp:
        print("\nCOMPLETADOS SIN DESINSTALAR (%d, %.2f GB recuperables):"
              % (len(comp), sum(j["gb"] for j in comp)))
        for j in sorted(comp, key=lambda x: -x["gb"]):
            print("   %-42s %6.2f GB  %s" % (j["nombre"], j["gb"], j["unidad"]))
    jug = [j for j in juegos if j["jugando"]]
    if jug:
        print("\nEN CURSO (%d): %s" % (len(jug), ", ".join(j["nombre"] for j in jug)))
    if len(filas_h) > 1:
        a, b = filas_h[-2], filas_h[-1]
        print("\nDesde %s: %+.2f GB, %+.1f horas, %+d juegos"
              % (a[0], float(b[2]) - float(a[2]), float(b[3]) - float(a[3]),
                 int(b[1]) - int(a[1])))
    inst_k = {normaliza(j["nombre"]) for j in juegos}
    huerfanas = completados - inst_k
    if huerfanas:
        print("\nEn completados.json pero ya desinstalados (se pueden quitar): "
              + ", ".join(sorted(huerfanas)))
    huer_j = jugando - inst_k
    if huer_j:
        print("\nEn jugando.json pero ya desinstalados (quitalos): "
              + ", ".join(sorted(huer_j)))
    huer_h = sorted(({k for k in horas if not k.startswith("_")}
                     | {k for bl in ("_notas", "_metacritic", "_steam", "_dificultad") if isinstance(horas.get(bl), dict)
                        for k in horas[bl]}) - inst_k)
    if not args.conservar:
        q = purgar_horas(horas, inst_k)
        if q:
            print("\nLIMPIEZA: %d claves sin carpeta quitadas de horas.json: %s"
                  % (q, ", ".join(huer_h)))
    elif huer_h:
        print("\nCLAVES SIN CARPETA en horas.json (%d), juegos ya desinstalados: %s"
              % (len(huer_h), ", ".join(huer_h)))
        print("   Estan conservadas por --conservar; sin esa opcion se quitan solas (si estan todas las unidades).")
    if desde_wl:
        print("\nHORAS TOMADAS DE wishlist.json (copialas a horas.json para fijarlas):")
        for n_, v_ in desde_wl:
            print("   %-40s %s h" % (n_, v_))
    if wl:
        con_ = sum(1 for v in wl.values() if isinstance(v, (int, float)) and not isinstance(v, bool))
        sin_ = sum(1 for v in wl.values() if v == "?")
        nts_ = wl_meta.get("_notas") if isinstance(wl_meta.get("_notas"), dict) else {}
        pre_ = sum(1 for t_, v in wl.items() if isinstance(v, (int, float)) and not isinstance(v, bool)
                   and str(nts_.get(t_, "")).upper().startswith("PRENSA"))
        dup_ = sum(1 for t_ in wl if str(nts_.get(t_, "")).upper().startswith("EDICION DUPLICADA"))
        jug_ = sum(1 for t_ in wl if str(nts_.get(t_, "")).upper().startswith("YA JUGADO"))
        est_ = sum(1 for t_ in wl if str(nts_.get(t_, "")).upper().startswith("ESTIMACION"))
        print("\nWISHLIST: %d titulos | %d con horas (%d de prensa, %d estimaciones, %d ediciones duplicadas, %d ya jugados) | %d sin dato | %d sin final"
              % (len(wl), con_, pre_, est_, dup_, jug_, sin_, len(wl) - con_ - sin_))
    if sin_datos:
        print("\nSIN HORAS (%d):" % len(sin_datos))
        for n in sin_datos:
            print("   " + n)
    sin_dif = [j["nombre"] for j in juegos if not j["duplicado"]
               and dif_celdas(j.get("dif"))[0] is None and dif_celdas(j.get("dif"))[1] is None]
    if sin_dif:
        print("\nSIN DIFICULTAD (%d instalados): ponla en horas.json, bloque _dificultad ({h, c, ct, src}):" % len(sin_dif))
        for x_ in sin_dif:
            print("   " + x_)
    if wl:
        dn_ = {normaliza(k) for k in dif_w}
        wsin = [t for t in wl if t not in dif_w and normaliza(t) not in dn_]
        if wsin:
            print("\nSIN DIFICULTAD EN LA WISHLIST: %d de %d titulos (primeros: %s)"
                  % (len(wsin), len(wl), ", ".join(wsin[:5])))
    dups = [j["nombre"] for j in juegos if j["duplicado"]]
    if dups:
        print("\nDUPLICADOS: " + ", ".join(dups))
    print("\nOK: " + salida)
    return 0
