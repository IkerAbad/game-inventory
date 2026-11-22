# -*- coding: utf-8 -*-
"""Formato de celdas: Metacritic, Steam y dificultad."""

# Prefijo de la celda cuando la nota es el % de resenas positivas de Steam.

MC_FMT_STEAM = '"S "0"%"'


class PctSteam(int):
    """Nota de respaldo (% de resenas positivas en Steam u otra fuente 0-100): en la celda es un numero normal
    (se ordena con los Metascores). fmt = formato de la celda (prefijo S por defecto)."""
    fmt = MC_FMT_STEAM


def mc_celda(e, st=None):
    """Entrada de _metacritic ({s, p, n, nota}) -> (valor de celda, comentario o None).
    s: numero = Metascore; "s/n" = Metacritic no publica Metascore; null = sin dato.
    st: entrada de _steam ({id, name, n, pct, desc}); solo se usa si no hay Metascore numerico:
    la celda lleva el numero 92 (PctSteam) con formato 'S 92%' (porcentaje de resenas positivas en Steam, otra escala)."""
    if (isinstance(st, dict) and isinstance(st.get("pct"), int)
            and not (isinstance(e, dict) and isinstance(e.get("s"), (int, float)))):
        nota_mc = (e.get("nota") or "").strip() if isinstance(e, dict) else ""
        txt = ("Sin Metascore en Metacritic%s.\nSteam: %d%% de resenas positivas (%s resenas, %s). Ficha: %s (app %s)."
               % ((" (" + nota_mc + ")") if nota_mc else "", st["pct"],
                  "{:,}".format(st.get("n") or 0).replace(",", "."), st.get("desc") or "?",
                  st.get("name") or "?", st.get("id")))
        v_ = PctSteam(st["pct"])
        if st.get("pref"):
            v_.fmt = '"%s "0' % st["pref"] if st["pref"] != "S" else MC_FMT_STEAM
        if st.get("txt"):
            txt = "Sin Metascore en Metacritic%s.\n%s" % ((" (" + nota_mc + ")") if nota_mc else "", st["txt"])
        return v_, txt
    if not isinstance(e, dict):
        return None, None
    s, n = e.get("s"), e.get("n")
    p = (e.get("p") or "").strip()
    nota = (e.get("nota") or "").strip()
    lin = []
    if p and p != "?":
        lin.append("Plataforma: " + p + (" (%d resenas)" % n if isinstance(n, int) else ""))
    elif isinstance(n, int):
        lin.append("%d resenas" % n)
    if s is None and not nota:
        nota = "sin dato"
    if nota:
        lin.append(nota)
    com = "\n".join(lin) if lin and (p not in ("PC", "") or nota) else None
    if isinstance(s, str):
        # 's/n' (sin Metascore y sin Steam): la celda queda vacia para que al ordenar no suba un texto; la razon va en el comentario
        lin2 = ["Sin Metascore en Metacritic%s y sin ficha utilizable en Steam." % (" (%d resenas)" % n if isinstance(n, int) else "")]
        if nota:
            lin2.append(nota)
        return None, "\n".join(lin2)
    return s, com


def mc_comentario(txt):
    from openpyxl.comments import Comment
    c = Comment("Metacritic\n" + txt, "Inventario")
    c.width = 270
    c.height = 60 + 15 * (txt.count("\n") + len(txt) // 38)
    return c


def nota_comentario(txt):
    from openpyxl.comments import Comment
    c = Comment("Horas\n" + txt, "Inventario")
    c.width = 330
    c.height = 70 + 15 * (txt.count("\n") + len(txt) // 48)
    return c


def mc_formato(ws, rango, c1):
    """Color por nota: >=75 verde, 50-74 amarillo, <50 rojo (Metascore y % Steam por igual). Ignora texto (s/n)."""
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.styles import PatternFill, Font
    for cond, bg, fg in (("AND(ISNUMBER({c}),{c}>=75)", "C8E6C9", "1B5E20"),
                         ("AND(ISNUMBER({c}),{c}>=50,{c}<75)", "FFF9C4", "7A4F01"),
                         ("AND(ISNUMBER({c}),{c}<50)", "FFCDD2", "B71C1C")):
        ws.conditional_formatting.add(
            rango,
            FormulaRule(formula=[cond.format(c=c1)],
                        fill=PatternFill("solid", start_color=bg, end_color=bg),
                        font=Font(bold=True, color=fg)))


DIF_CERT = {"fuente": "respaldada por la fuente citada",
            "consenso": "consenso de la comunidad citado (etiquetas de usuarios de Steam, foros); el numero exacto es escala mia",
            "inferencia": "inferencia mia, sin fuente (certeza baja)"}


def dif_celdas(e):
    """Entrada de _dificultad ({h, c, ct, src, nota}) -> (habilidad, complejidad, comentario o None, es_inferencia).
    h = Habilidad 0-10 (reflejos, castigo, exigencia de ejecucion); c = Complejidad 0-10 (reglas, sistemas, curva de
    aprendizaje); ct = certeza: fuente | consenso | inferencia. Un eje a null queda vacio."""
    if not isinstance(e, dict):
        return None, None, None, False
    num = lambda v: v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    h, c = num(e.get("h")), num(e.get("c"))
    if h is None and c is None:
        return None, None, None, False
    ct = e.get("ct") or "inferencia"
    fmt = lambda v: "-" if v is None else ("%g" % v)
    cert = DIF_CERT.get(ct, str(ct))
    if ct == "inferencia" and e.get("src"):
        cert = "inferencia mia a partir de la fuente citada (certeza baja)"
    lin = ["Habilidad %s/10  |  Complejidad %s/10" % (fmt(h), fmt(c)),
           "Certeza: " + cert]
    if e.get("src"):
        lin.append("Fuente: " + str(e["src"]))
    if e.get("nota"):
        lin.append(str(e["nota"]))
    return h, c, "\n".join(lin), ct == "inferencia"


def dif_comentario(txt):
    from openpyxl.comments import Comment
    c = Comment("Dificultad\n" + txt, "Inventario")
    c.width = 330
    c.height = 70 + 15 * (txt.count("\n") + len(txt) // 48)
    return c


def dif_escribir(ws, r, c0, e):
    """Habilidad en la columna c0 y Complejidad en c0+1 de la fila r; cursiva naranja si es inferencia; comentario con certeza y fuente."""
    from openpyxl.styles import Font
    h, c, txt, inf = dif_celdas(e)
    for col, v in ((c0, h), (c0 + 1, c)):
        cel = ws.cell(r, col, v)
        if txt:
            cel.comment = dif_comentario(txt)
        if inf and v is not None:
            cel.font = Font(italic=True, color="C2410C")


def dif_formato(ws, rango):
    """Escala de color 0-10: verde (facil) -> amarillo -> rojo (dificil). Informativo."""
    from openpyxl.formatting.rule import ColorScaleRule
    ws.conditional_formatting.add(
        rango,
        ColorScaleRule(start_type="num", start_value=0, start_color="C8E6C9",
                       mid_type="num", mid_value=5, mid_color="FFF9C4",
                       end_type="num", end_value=10, end_color="FFCDD2"))
