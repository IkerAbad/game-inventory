# -*- coding: utf-8 -*-
"""Punto de entrada: opciones, orquestacion y resumen por consola."""

import argparse
import json
import os
import shutil
import statistics
import sys

from .config import COMPLETADOS_JSON, DATOS, HORAS_JSON, JUGANDO_JSON, SALIDA, WISHLIST_JSON
from .datos import normaliza, purgar_horas
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
        return
    os.makedirs(DATOS, exist_ok=True)
    horas = json.load(open(HORAS_JSON, encoding="utf-8")) if os.path.exists(HORAS_JSON) else {}
    if os.path.exists(COMPLETADOS_JSON):
        completados = {normaliza(x) for x in json.load(open(COMPLETADOS_JSON, encoding="utf-8"))
                       if not str(x).startswith("_")}
    else:
        completados = set()
    if os.path.exists(JUGANDO_JSON):
        jugando = {normaliza(x) for x in json.load(open(JUGANDO_JSON, encoding="utf-8"))
                   if not str(x).startswith("_")}
    else:
        jugando = set()
    wl_meta, wl = {}, {}
    if os.path.exists(WISHLIST_JSON):
        wl_meta = json.load(open(WISHLIST_JSON, encoding="utf-8"))
        wl = wl_meta.get("juegos", {})
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
        j["horas"] = horas.get(k, "?")
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

    if os.path.exists(salida):
        try:
            shutil.copy2(salida, salida[:-5] + ".bak.xlsx")
        except Exception as e:
            print("Aviso: no se pudo hacer copia previa (%s)" % e)
    wb.save(salida)
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
