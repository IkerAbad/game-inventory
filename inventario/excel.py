# -*- coding: utf-8 -*-
"""Excel: hojas, estilos, graficos y comparativas."""

import os
import re
import shutil

from .config import HISTORICO_CSV
from .datos import escribir_atomico, es_hora_valida, normaliza
from .formato import (PctSteam, dif_escribir, dif_formato, limpia_texto, mc_celda,
                      mc_comentario, mc_formato, nota_comentario)


def celda_texto(ws, fila, col, valor, formato=None):
    """Escribe un texto y evita que Excel lo trate como formula si empieza por '='."""
    if isinstance(valor, str):
        valor = limpia_texto(valor)
    cel = ws.cell(fila, col, valor)
    if isinstance(valor, str) and valor.startswith("="):
        cel.data_type = "s"
    if formato:
        cel.number_format = formato
    return cel

def historico(juegos, TH):
    """Registra una fila por dia en historico.csv y devuelve la serie completa.
    Las filas corruptas se avisan y se descartan. La escritura es atomica."""
    import csv, datetime, io, math
    hoy = datetime.date.today().isoformat()
    fila = [hoy, len(juegos), round(sum(j["gb"] for j in juegos), 2), round(TH, 1)]
    filas = []
    if os.path.exists(HISTORICO_CSV):
        try:
            with open(HISTORICO_CSV, newline="", encoding="utf-8-sig") as f:
                for r in csv.reader(f):
                    if not r or r[0] == "fecha":
                        continue
                    if len(r) < 4:
                        print("Aviso: fila incompleta ignorada en historico.csv: %r" % (r,))
                        continue
                    try:
                        datetime.date.fromisoformat(r[0])
                        int(r[1])
                        vals = [float(r[2]), float(r[3])]
                    except ValueError:
                        print("Aviso: fila invalida ignorada en historico.csv: %r" % (r,))
                        continue
                    if not all(math.isfinite(v) for v in vals):
                        print("Aviso: fila invalida ignorada en historico.csv: %r" % (r,))
                        continue
                    filas.append(r)
        except OSError as e:
            print("Aviso: no se puede leer historico.csv (%s); se empieza de cero." % e)
    filas = [r for r in filas if r[0] != hoy]
    filas.append([str(x) for x in fila])
    filas.sort(key=lambda r: r[0])
    s = io.StringIO()
    w = csv.writer(s)
    w.writerow(["fecha", "juegos", "gb", "horas"])
    w.writerows(filas)
    try:
        escribir_atomico(HISTORICO_CSV, s.getvalue())
    except OSError as e:
        print("Aviso: no se pudo escribir historico.csv (%s); el Excel se genera igual." % e)
    return filas


def hoja_historico(wb, filas):
    import datetime
    from openpyxl.styles import Font
    from openpyxl.chart import LineChart, Reference
    from openpyxl.utils import get_column_letter

    ws = wb.create_sheet("Historico")
    ws["A2"] = "Una fila por dia de ejecucion. Compara el ritmo real con el teorico."
    ws["A2"].font = Font(italic=True, size=9)
    for i, c in enumerate(["Fecha", "Juegos", "GB totales", "Horas pendientes",
                           "Delta GB", "Delta horas"], 1):
        ws.cell(4, i, c)
    prev = None
    for k, r in enumerate(filas):
        f = 5 + k
        y, m, d = (int(x) for x in r[0].split("-"))
        ws.cell(f, 1, datetime.date(y, m, d)).number_format = "DD/MM/YYYY"
        ws.cell(f, 2, int(r[1]))
        ws.cell(f, 3, float(r[2])).number_format = "#,##0.00"
        ws.cell(f, 4, float(r[3])).number_format = "#,##0.0"
        if prev:
            ws.cell(f, 5, round(float(r[2]) - float(prev[2]), 2)).number_format = "+#,##0.00;-#,##0.00;0"
            ws.cell(f, 6, round(float(r[3]) - float(prev[3]), 1)).number_format = "+#,##0.0;-#,##0.0;0"
        prev = r
    for i, a in enumerate([14, 10, 13, 17, 12, 13], 1):
        ws.column_dimensions[get_column_letter(i)].width = a
    ws.freeze_panes = "A5"

    n = len(filas)
    g = LineChart()
    g.title = "Evolucion del backlog"
    g.y_axis.title = "GB / horas"
    g.x_axis.title = "Fecha"
    g.add_data(Reference(ws, min_col=3, max_col=4, min_row=4, max_row=4 + n),
               titles_from_data=True)
    g.set_categories(Reference(ws, min_col=1, min_row=5, max_row=4 + n))
    g.height, g.width = 10, 24
    ws.add_chart(g, "H5")

    g2 = LineChart()
    g2.title = "Numero de juegos instalados"
    g2.y_axis.title = "Juegos"
    g2.add_data(Reference(ws, min_col=2, min_row=4, max_row=4 + n), titles_from_data=True)
    g2.set_categories(Reference(ws, min_col=1, min_row=5, max_row=4 + n))
    g2.height, g2.width, g2.legend = 8, 24, None
    ws.add_chart(g2, "H27")
    return ws


PALETA = {
    "EN CURSO - jugandolo ahora":       ("004D40", "B2DFDB"),
    "JUGAR YA - gran ratio":            ("1B5E20", "C8E6C9"),
    "Buen ratio":                       ("0D47A1", "BBDEFB"),
    "Ratio medio":                      ("E65100", "FFE0B2"),
    "Mal ratio - decidir":              ("616161", "EEEEEE"),
    "SIN FINAL - decides tu":          ("37474F", "CFD8DC"),
    "COMPLETADO - se puede borrar":     ("4A148C", "E1BEE7"),
    "SIN DATOS - pedir horas a Claude": ("F57F17", "FFF9C4"),
    "DUPLICADO - borrar una copia":     ("B71C1C", "FFCDD2"),
}
AZUL_OSC = "1F2A37"
BANDA = "F7F9FC"


def embellecer(wb, juegos):
    """Aplica estilo visual a las cuatro hojas."""
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.formatting.rule import ColorScaleRule, DataBarRule, CellIsRule

    fina = Side(style="thin", color="D6DCE4")
    borde = Border(left=fina, right=fina, top=fina, bottom=fina)
    blanco = Font(color="FFFFFF", bold=True, size=10)
    relleno_cab = PatternFill("solid", fgColor=AZUL_OSC)
    centro = Alignment(horizontal="center", vertical="center")

    def titulo(ws, celda, txt, ancho):
        ws.merge_cells("%s1:%s1" % (celda, ancho))
        c = ws["%s1" % celda]
        c.value = txt
        c.font = Font(bold=True, size=15, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=AZUL_OSC)
        c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[1].height = 26

    def cabecera(ws, fila, c1, c2):
        for i in range(c1, c2 + 1):
            cel = ws.cell(fila, i)
            cel.font = blanco
            cel.fill = relleno_cab
            cel.alignment = centro
            cel.border = borde
        ws.row_dimensions[fila].height = 20

    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = False

    # ------------------------------------------------------------- JUEGOS
    ws = wb["Juegos"]
    ws.sheet_properties.tabColor = "1B5E20"
    titulo(ws, "A", "INVENTARIO DE JUEGOS  ·  GB liberados por hora jugada", "K")
    ws["A2"].font = Font(italic=True, size=9, color="6B7280")
    cabecera(ws, 4, 1, 11)
    n = len(juegos)
    nf = max(n + 4, 5)      # rango valido aunque no haya juegos
    for i, j in enumerate(juegos):
        r = i + 5
        banda = PatternFill("solid", fgColor=BANDA) if i % 2 else None
        for c in range(1, 12):
            cel = ws.cell(r, c)
            cel.border = borde
            if banda:
                cel.fill = banda
            if c in (2, 3, 4, 5, 7, 8, 9, 10):
                cel.alignment = Alignment(horizontal="center")
        ws.cell(r, 2).number_format = "0.00"
        ws.cell(r, 4).number_format = "0.00"
        ws.cell(r, 11).font = Font(size=8, color="9AA3AF")
        fg, bg = PALETA.get(j["veredicto"], ("000000", "FFFFFF"))
        v = ws.cell(r, 6)
        v.fill = PatternFill("solid", fgColor=bg)
        v.font = Font(bold=True, size=9, color=fg)
        v.alignment = Alignment(horizontal="center")
    ws.conditional_formatting.add(
        "B5:B%d" % nf,
        DataBarRule(start_type="num", start_value=0, end_type="max", color="5B8FF9"))
    ws.conditional_formatting.add(
        "D5:D%d" % nf,
        ColorScaleRule(start_type="num", start_value=0, start_color="FFFFFF",
                       mid_type="num", mid_value=2, mid_color="A5D6A7",
                       end_type="max", end_color="1B5E20"))
    ws.conditional_formatting.add(
        "G5:G%d" % nf,
        CellIsRule(operator="greaterThan", formula=["180"],
                   fill=PatternFill("solid", fgColor="FFE0B2"),
                   font=Font(bold=True, color="7A4F01")))

    # ------------------------------------------------------------ ESPACIO
    mc_formato(wb["Juegos"], "H5:H%d" % nf, "H5")
    dif_formato(wb["Juegos"], "I5:J%d" % nf)

    ws = wb["Espacio"]
    ws.sheet_properties.tabColor = "0D47A1"
    titulo(ws, "A", "ESPACIO POR UNIDAD", "E")
    cabecera(ws, 3, 1, 5)
    ult_esp = max(ws.max_row, 4)    # rango valido aunque no se lea ninguna unidad
    for r in range(4, ws.max_row + 1):
        for c in range(1, 6):
            cel = ws.cell(r, c)
            cel.border = borde
            cel.alignment = centro
            if c in (2, 3, 5):
                cel.number_format = "#,##0.00"
        ws.cell(r, 4).number_format = "0.0"
    ws.conditional_formatting.add(
        "D4:D%d" % ult_esp,
        CellIsRule(operator="lessThan", formula=["5"],
                   fill=PatternFill("solid", fgColor="FFCDD2"),
                   font=Font(bold=True, color="B71C1C")))
    ws.conditional_formatting.add(
        "D4:D%d" % ult_esp,
        CellIsRule(operator="between", formula=["5", "15"],
                   fill=PatternFill("solid", fgColor="FFE0B2")))

    # ------------------------------------------------------------ RESUMEN
    ws = wb["Resumen"]
    ws.sheet_properties.tabColor = "E65100"
    titulo(ws, "A", "RESUMEN DEL BACKLOG", "D")
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 15
    for r in range(3, 13):
        ws.cell(r, 1).border = borde
        b = ws.cell(r, 2)
        b.border = borde
        b.alignment = Alignment(horizontal="center")
        if r % 2:
            ws.cell(r, 1).fill = PatternFill("solid", fgColor=BANDA)
            b.fill = PatternFill("solid", fgColor=BANDA)
    for r in (6, 12):
        ws.cell(r, 1).font = Font(bold=True, color="FFFFFF")
        ws.cell(r, 1).fill = PatternFill("solid", fgColor="374151")
        ws.cell(r, 2).font = Font(bold=True, size=12, color="1B5E20")
        ws.cell(r, 2).fill = PatternFill("solid", fgColor="E8F5E9")
    for r in range(14, 20):
        ws.cell(r, 1).border = borde
        ws.cell(r, 2).border = borde
        ws.cell(r, 2).alignment = Alignment(horizontal="center")
    ws["A14"].font = Font(bold=True, color="7A4F01")
    ws["A14"].fill = PatternFill("solid", fgColor="FFF2CC")
    from openpyxl.worksheet.datavalidation import DataValidation
    dv = DataValidation(type="list", formula1='"1,2,3,4,5,6,8,10,12"', allow_blank=False,
                        showErrorMessage=True)
    dv.errorTitle = "Valor no valido"
    dv.error = "Elige un numero de horas de la lista."
    ws.add_data_validation(dv)
    dv.add(ws["B14"])
    cabecera(ws, 21, 1, 4)
    for r in range(22, 28):
        for c in range(1, 5):
            cel = ws.cell(r, c)
            cel.border = borde
            cel.alignment = centro
            if r % 2:
                cel.fill = PatternFill("solid", fgColor=BANDA)
    ws.cell(25, 1).fill = PatternFill("solid", fgColor="FFF2CC")
    ws.cell(25, 1).font = Font(bold=True)
    ws.column_dimensions.group("H", "J", hidden=True)
    ws.column_dimensions.group("X", "AA", hidden=True)

    # ---------------------------------------------------------- HISTORICO
    ws = wb["Historico"]
    ws.sheet_properties.tabColor = "00838F"
    titulo(ws, "A", "HISTORICO  ·  evolucion del backlog", "F")
    ws["A2"].font = Font(italic=True, size=9, color="6B7280")
    cabecera(ws, 4, 1, 6)
    for r in range(5, ws.max_row + 1):
        for c in range(1, 7):
            cel = ws.cell(r, c)
            cel.border = borde
            cel.alignment = centro
            if (r - 5) % 2:
                cel.fill = PatternFill("solid", fgColor=BANDA)
    if ws.max_row >= 5:
        for col in ("E", "F"):
            ws.conditional_formatting.add(
                "%s5:%s%d" % (col, col, ws.max_row),
                CellIsRule(operator="greaterThan", formula=["0"],
                           font=Font(bold=True, color="B71C1C")))
            ws.conditional_formatting.add(
                "%s5:%s%d" % (col, col, ws.max_row),
                CellIsRule(operator="lessThan", formula=["0"],
                           font=Font(bold=True, color="1B5E20")))

    # --------------------------------------------------------------- PLAN
    ws = wb["Plan"]
    ws.sheet_properties.tabColor = "4A148C"
    titulo(ws, "A", "PLAN POR ORDEN DE RATIO  ·  cuanto espacio liberas y cuando", "L")
    ws["A2"].font = Font(italic=True, size=9, color="6B7280")
    cabecera(ws, 4, 1, 12)
    ult = ws.max_row
    ult_cf = max(ult, 5)    # rango valido aunque no haya pendientes
    for r in range(5, ult + 1):
        for c in range(1, 13):
            cel = ws.cell(r, c)
            cel.border = borde
            cel.alignment = centro
            if (r - 5) % 2:
                cel.fill = PatternFill("solid", fgColor=BANDA)
        ws.cell(r, 2).alignment = Alignment(horizontal="left", indent=1)
        ws.cell(r, 6).number_format = "0.00"
        ws.cell(r, 7).number_format = "#,##0.00"
    ws.conditional_formatting.add(
        "H5:H%d" % ult_cf,
        DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1,
                    color="7E57C2"))
    ws.conditional_formatting.add(
        "F5:F%d" % ult_cf,
        DataBarRule(start_type="num", start_value=0, end_type="max", color="5B8FF9"))

    # ------------------------------------------------------------ GRAFICOS
    mc_formato(wb["Plan"], "J5:J%d" % ult_cf, "J5")
    dif_formato(wb["Plan"], "K5:L%d" % ult_cf)

    COLORES = ["2E7D32", "1565C0", "EF6C00", "6A1B9A", "C62828", "00838F"]
    for hoja in wb.worksheets:
        for g in getattr(hoja, "_charts", []):
            g.style = 2
            for k, s in enumerate(g.series):
                col = COLORES[k % len(COLORES)]
                if type(g).__name__ == "PieChart":
                    from openpyxl.chart.series import DataPoint
                    from openpyxl.chart.shapes import GraphicalProperties
                    for i, cp in enumerate(COLORES):
                        s.dPt.append(DataPoint(idx=i, spPr=GraphicalProperties(solidFill=cp)))
                    continue
                s.graphicalProperties.solidFill = col
                s.graphicalProperties.line.solidFill = col
                s.graphicalProperties.line.width = 22000
                s.smooth = False


def pulir(wb, juegos):
    """Segunda pasada: tipografia, filtros, totales, impresion y ejes."""
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.worksheet.properties import PageSetupProperties

    FUENTE = "Segoe UI"
    n = len(juegos)

    for ws in wb.worksheets:
        for fila in ws.iter_rows():
            for c in fila:
                f = c.font
                if f is not None and f.name != FUENTE:
                    c.font = Font(name=FUENTE, size=f.size, bold=f.bold,
                                  italic=f.italic, color=f.color,
                                  underline=f.underline)

    grueso = Side(style="medium", color=AZUL_OSC)

    ws = wb["Juegos"]
    ws.auto_filter.ref = "A4:K%d" % (n + 4)
    ws.freeze_panes = "A5"
    for r in range(5, n + 5):
        ws.cell(r, 2).alignment = Alignment(horizontal="right", indent=1)
        ws.cell(r, 4).alignment = Alignment(horizontal="right", indent=1)
        ws.row_dimensions[r].height = 16
    tr = n + 5
    ws.cell(tr, 1, "TOTAL VISIBLE (respeta el filtro)")
    if n:
        ws.cell(tr, 2, "=SUBTOTAL(109,B5:B%d)" % (n + 4)).number_format = "#,##0.00"
        ws.cell(tr, 4, "=SUBTOTAL(101,D5:D%d)" % (n + 4)).number_format = "0.00"
        ws.cell(tr, 6, '=SUBTOTAL(103,A5:A%d)&" juegos"' % (n + 4))
        ws.cell(tr, 7, "=SUBTOTAL(101,G5:G%d)" % (n + 4)).number_format = "0"
        ws.cell(tr, 8, '=IFERROR(SUBTOTAL(101,H5:H%d),"")' % (n + 4)).number_format = "0"
        ws.cell(tr, 9, '=IFERROR(SUBTOTAL(101,I5:I%d),"")' % (n + 4)).number_format = "0.0"
        ws.cell(tr, 10, '=IFERROR(SUBTOTAL(101,J5:J%d),"")' % (n + 4)).number_format = "0.0"
    else:
        ws.cell(tr, 2, 0).number_format = "#,##0.00"
        ws.cell(tr, 4, 0).number_format = "0.00"
        ws.cell(tr, 6, "0 juegos")
        ws.cell(tr, 7, 0).number_format = "0"
        ws.cell(tr, 8, 0).number_format = "0"
        ws.cell(tr, 9, 0).number_format = "0.0"
        ws.cell(tr, 10, 0).number_format = "0.0"
    for c in range(1, 12):
        cel = ws.cell(tr, c)
        cel.fill = PatternFill("solid", fgColor="374151")
        cel.font = Font(name=FUENTE, bold=True, color="FFFFFF", size=10)
        cel.border = Border(top=grueso)
        if c in (2, 4):
            cel.alignment = Alignment(horizontal="right", indent=1)
        elif c in (6, 7, 8, 9, 10):
            cel.alignment = Alignment(horizontal="center")
    ws.row_dimensions[tr].height = 20

    ws = wb["Plan"]
    ult = ws.max_row
    ws.auto_filter.ref = "A4:L%d" % ult
    oro = PatternFill("solid", fgColor="FFF4D6")
    verde = PatternFill("solid", fgColor="B2DFDB")
    nc = getattr(wb, "_en_curso", 0)
    for r in range(5, min(5 + nc, ult + 1)):
        for c in range(1, 13):
            ws.cell(r, c).fill = verde
        ws.cell(r, 2).font = Font(name=FUENTE, bold=True, color="004D40")
        ws.cell(r, 1).border = Border(left=grueso)
    for r in range(5 + nc, min(10 + nc, ult + 1)):
        for c in range(1, 13):
            ws.cell(r, c).fill = oro
        ws.cell(r, 2).font = Font(name=FUENTE, bold=True, color="7A4F01")
        ws.cell(r, 1).border = Border(left=grueso)
    for r in range(5, ult + 1):
        ws.row_dimensions[r].height = 16

    for ws in wb.worksheets:
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
        ws.print_options.horizontalCentered = True
    wb["Juegos"].print_title_rows = "4:4"
    wb["Plan"].print_title_rows = "4:4"

    for hoja in wb.worksheets:
        for g in getattr(hoja, "_charts", []):
            g.roundedCorners = False
            g.visible_cells_only = False
            dl = getattr(g, "dataLabels", None)
            if dl is not None:
                dl.showSerName = False
                dl.showCatName = False
                dl.showLegendKey = False
                if dl.showPercent is None:
                    dl.showPercent = False
            for t in (g.title, getattr(getattr(g, "y_axis", None), "title", None),
                      getattr(getattr(g, "x_axis", None), "title", None)):
                if t is not None and hasattr(t, "overlay"):
                    t.overlay = False
            try:
                g.gapWidth = 45
            except Exception:
                pass
            if hasattr(g, "y_axis"):
                g.y_axis.numFmt = "#,##0"
                g.y_axis.delete = False
                g.x_axis.majorGridlines = None
                g.x_axis.delete = False



def hojas_extra(wb, juegos):
    """Anade las hojas Resumen y Plan con los graficos."""
    import datetime
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    from openpyxl.chart import BarChart, PieChart, LineChart, Reference
    from openpyxl.chart.label import DataLabelList

    CAB = PatternFill("solid", fgColor="333333")

    def cab(ws, fila, cols, ancho=None):
        for i, c in enumerate(cols, 1):
            cel = ws.cell(fila, i, c)
            cel.font = Font(bold=True, color="FFFFFF")
            cel.fill = CAB
            cel.alignment = Alignment(horizontal="center")
        if ancho:
            for i, a in enumerate(ancho, 1):
                ws.column_dimensions[get_column_letter(i)].width = a

    fin = [j for j in juegos if isinstance(j["horas"], (int, float)) and not j["completado"]]
    inf = [j for j in juegos if j["horas"] is None and not j["completado"]]
    com = [j for j in juegos if j["completado"]]
    TH = sum(j["horas"] for j in fin)
    TGB = sum(j["gb"] for j in juegos)
    GBF = sum(j["gb"] for j in fin)
    GBC = sum(j["gb"] for j in com)
    hoy = datetime.date.today()

    # ---------------------------------------------------------------- RESUMEN
    ws = wb.create_sheet("Resumen")
    ws["A1"] = "RESUMEN DEL BACKLOG"
    ws["A1"].font = Font(bold=True, size=14)

    datos = [
        ("Juegos totales", len(juegos), None),
        ("Pendientes con final", len(fin), None),
        ("Sin final (infinitos)", len(inf), None),
        ("HORAS PENDIENTES (solo con final)", round(TH, 1), "0.0"),
        ("GB totales instalados", round(TGB, 2), "0.00"),
        ("GB liberables al terminarlos", round(GBF, 2), "0.00"),
        ("Media GB/hora del backlog", round(GBF / TH, 3) if TH else 0, "0.000"),
        ("Horas medias por juego", round(TH / len(fin), 1) if fin else 0, "0.0"),
        ("Completados sin desinstalar", len(com), None),
        ("GB recuperables YA (completados)", round(GBC, 2), "0.00"),
    ]
    for i, (k, v, fmt) in enumerate(datos, 3):
        ws.cell(i, 1, k).font = Font(bold=(i == 6))
        c = ws.cell(i, 2, v)
        if fmt:
            c.number_format = fmt
        if i == 6:
            c.font = Font(bold=True, size=12)

    ws["A14"] = "HORAS POR DIA (editable)"
    ws["A14"].font = Font(bold=True)
    ws["B14"] = 4
    ws["B14"].fill = PatternFill("solid", fgColor="FFF2CC")
    ws["B14"].font = Font(bold=True)
    ws["A15"] = "Dias necesarios"
    ws["B15"] = "=ROUND($B$6/$B$14,0)"
    ws["A16"] = "Semanas"
    ws["B16"] = "=ROUND($B$15/7,1)"
    ws["A17"] = "Meses (30,44 dias)"
    ws["B17"] = "=ROUND($B$15/30.44,1)"
    ws["A18"] = "Anios"
    ws["B18"] = "=ROUND($B$15/365.25,2)"
    ws["A19"] = "Fecha estimada de fin"
    ws["B19"] = "=TODAY()+$B$15"
    ws["B19"].number_format = "DD/MM/YYYY"

    cab(ws, 21, ["Ritmo h/dia", "Dias", "Anios", "Fecha de fin"],
        [36, 14, 12, 14])
    for i, r in enumerate([1, 2, 3, 4, 6, 8], 22):
        d = int(round(TH / r))
        ws.cell(i, 1, r)
        ws.cell(i, 2, d)
        ws.cell(i, 3, round(d / 365.25, 2)).number_format = "0.00"
        ws.cell(i, 4, hoy + datetime.timedelta(days=d)).number_format = "DD/MM/YYYY"

    # tablas auxiliares para graficos (columnas H-I)
    cats = ["JUGAR YA - gran ratio", "Buen ratio", "Ratio medio", "Mal ratio - decidir"]
    ws["H2"] = "Categoria"
    ws["I2"] = "Horas"
    ws["J2"] = "GB"
    for i, c in enumerate(cats, 3):
        sub = [j for j in fin if j["veredicto"] == c]
        ws.cell(i, 8, c.split(" - ")[0])
        ws.cell(i, 9, round(sum(j["horas"] for j in sub), 1))
        ws.cell(i, 10, round(sum(j["gb"] for j in sub), 2))

    ws["H9"] = "Unidad"
    ws["I9"] = "GB"
    uni = {}
    for j in juegos:
        uni[j["unidad"]] = uni.get(j["unidad"], 0) + j["gb"]
    for i, u in enumerate(sorted(uni), 10):
        ws.cell(i, 8, u)
        ws.cell(i, 9, round(uni[u], 2))

    ws["H16"] = "Juego"
    ws["I16"] = "Horas"
    top = sorted(fin, key=lambda x: -x["horas"])[:15]
    for i, j in enumerate(top, 17):
        celda_texto(ws, i, 8, j["nombre"][:32])
        ws.cell(i, 9, j["horas"])
    ws.column_dimensions["H"].width = 34

    g1 = BarChart()
    g1.type = "col"
    g1.title = "Dias para acabar el backlog segun ritmo"
    g1.y_axis.title = "Dias"
    g1.x_axis.title = "Horas al dia"
    g1.add_data(Reference(ws, min_col=2, min_row=21, max_row=27), titles_from_data=True)
    g1.set_categories(Reference(ws, min_col=1, min_row=22, max_row=27))
    g1.dataLabels = DataLabelList()
    g1.dataLabels.showVal = True
    g1.height, g1.width, g1.legend = 8, 16, None
    ws.add_chart(g1, "A29")

    g2 = BarChart()
    g2.type = "col"
    g2.title = "Horas pendientes por categoria de ratio"
    g2.y_axis.title = "Horas"
    g2.add_data(Reference(ws, min_col=9, min_row=2, max_row=6), titles_from_data=True)
    g2.set_categories(Reference(ws, min_col=8, min_row=3, max_row=6))
    g2.dataLabels = DataLabelList()
    g2.dataLabels.showVal = True
    g2.height, g2.width, g2.legend = 8, 16, None
    ws.add_chart(g2, "L29")

    if uni:
        g3 = PieChart()
        g3.title = "Reparto de GB instalados por unidad"
        g3.add_data(Reference(ws, min_col=9, min_row=9, max_row=9 + len(uni)), titles_from_data=True)
        g3.set_categories(Reference(ws, min_col=8, min_row=10, max_row=9 + len(uni)))
        g3.dataLabels = DataLabelList()
        g3.dataLabels.showPercent = True
        g3.height, g3.width = 9, 13
        ws.add_chart(g3, "A47")

    if top:
        g4 = BarChart()
        g4.type = "bar"
        g4.title = "Los 15 juegos que mas horas te quedan"
        g4.x_axis.title = "Horas"
        g4.add_data(Reference(ws, min_col=9, min_row=16, max_row=16 + len(top)), titles_from_data=True)
        g4.set_categories(Reference(ws, min_col=8, min_row=17, max_row=16 + len(top)))
        g4.height, g4.width, g4.legend = 12, 16, None
        ws.add_chart(g4, "L47")

    # ------------------------------------------------------------------- PLAN
    wp = wb.create_sheet("Plan")
    wp["A1"] = "PLAN POR ORDEN DE RATIO - cuanto espacio liberas y cuando"
    wp["A1"].font = Font(bold=True, size=13)
    wp["A2"] = "Solo pendientes con final, orden descendente de GB/hora. Ritmo: Resumen!B14. Metacritic: informativo, no entra en el orden. Habilidad y Complejidad (0-10): informativas, tampoco entran en el orden; cursiva naranja = inferencia mia sin fuente. 'S 92%' = sin Metascore: % de resenas positivas en Steam, como numero para ordenar junto a los Metascores (otra escala); 'R 80' = nota de una sola resena."
    wp["A2"].font = Font(italic=True, size=9)
    cab(wp, 4, ["#", "Juego", "Unidad", "Horas", "Horas acum.", "GB", "GB acum.",
                "% GB liberado", "Fecha de fin", "Metacritic", "Habilidad", "Complejidad"],
        [6, 42, 11, 10, 16, 10, 13, 18, 17, 14, 11, 13])

    ha = gb = 0.0
    en_curso = sum(1 for j in fin if j.get("jugando"))
    wb._en_curso = en_curso
    for i, j in enumerate(fin, 1):
        ha += j["horas"]
        gb += j["gb"]
        r = i + 4
        wp.cell(r, 1, i)
        celda_texto(wp, r, 2, j["nombre"])
        wp.cell(r, 3, j["unidad"])
        wp.cell(r, 4, j["horas"])
        wp.cell(r, 5, round(ha, 1))
        wp.cell(r, 6, j["gb"])
        wp.cell(r, 7, round(gb, 2))
        wp.cell(r, 8, round(gb / GBF, 4) if GBF else 0).number_format = "0.0%"
        c = wp.cell(r, 9, "=TODAY()+ROUND(E%d/Resumen!$B$14,0)" % r)
        c.number_format = "DD/MM/YYYY"
        v_mc, t_mc = mc_celda(j.get("mc"), j.get("steam"))
        cmc = wp.cell(r, 10, v_mc)
        if isinstance(v_mc, PctSteam):
            cmc.number_format = v_mc.fmt
        if t_mc:
            cmc.comment = mc_comentario(t_mc)
        dif_escribir(wp, r, 11, j.get("dif"))
    wp.freeze_panes = "A5"

    if fin:
        g5 = LineChart()
        g5.title = "GB liberados acumulados frente a horas invertidas"
        g5.y_axis.title = "GB acumulados"
        g5.x_axis.title = "Horas acumuladas"
        g5.add_data(Reference(wp, min_col=7, min_row=4, max_row=4 + len(fin)), titles_from_data=True)
        g5.set_categories(Reference(wp, min_col=5, min_row=5, max_row=4 + len(fin)))
        g5.height, g5.width, g5.legend = 10, 24, None
        wp.add_chart(g5, "N5")

    # --- escenarios de fin de backlog: 2, 4 y 6 h/dia sobre el calendario ---
    RITMOS = [2, 4, 6]
    meses = int(TH / (min(RITMOS) * 30.44)) + 2
    ws.cell(2, 24, "Fecha")
    for k, r in enumerate(RITMOS):
        ws.cell(2, 25 + k, "%d h/dia" % r)
    for m in range(meses + 1):
        f = 3 + m
        ws.cell(f, 24, hoy + datetime.timedelta(days=int(m * 30.44))).number_format = "MMM-YY"
        for k, r in enumerate(RITMOS):
            ws.cell(f, 25 + k, round(max(0.0, TH - r * 30.44 * m), 1))
    for i in range(24, 28):
        ws.column_dimensions[get_column_letter(i)].width = 11

    g6 = LineChart()
    g6.title = "Escenarios de fin de backlog: horas que te quedan"
    g6.y_axis.title = "Horas pendientes"
    g6.x_axis.title = "Mes"
    g6.add_data(Reference(ws, min_col=25, max_col=27, min_row=2, max_row=3 + meses),
                titles_from_data=True)
    g6.set_categories(Reference(ws, min_col=24, min_row=3, max_row=3 + meses))
    g6.height, g6.width = 10, 26
    ws.add_chart(g6, "A73")

    return TH


def hoja_wishlist(wb, juegos, wl, fuente, mc=None, notas=None, st=None, dif=None):
    """Hoja Wishlist: catalogo con horas, marca los ya instalados y compara con el backlog."""
    import difflib
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.chart import BarChart, Reference
    from openpyxl.chart.label import DataLabelList
    from openpyxl.formatting.rule import DataBarRule, CellIsRule

    mc = mc or {}
    mcn = {normaliza(k): v for k, v in mc.items()}
    st = st or {}
    stn = {normaliza(k): v for k, v in st.items()}
    dif = dif or {}
    difn = {normaliza(k): v for k, v in dif.items()}
    notas = notas or {}
    notan = {normaliza(k): v for k, v in notas.items()}
    nota_de = lambda t: str(notas.get(t) or notan.get(normaliza(t)) or "")
    es_prensa = lambda t: nota_de(t).upper().startswith("PRENSA")
    es_dup = lambda t: nota_de(t).upper().startswith("EDICION DUPLICADA")
    es_jug = lambda t: nota_de(t).upper().startswith("YA JUGADO")
    es_est = lambda t: nota_de(t).upper().startswith("ESTIMACION")
    inst = [normaliza(j["nombre"]) for j in juegos]
    inst_set = set(inst)

    def ya_instalado(t):
        k = normaliza(t)
        if k in inst_set:
            return True
        for i in inst:
            sm = difflib.SequenceMatcher(None, k, i)
            if sm.real_quick_ratio() >= 0.9 and sm.quick_ratio() >= 0.9 and sm.ratio() >= 0.9:
                return True
        return False

    es_num = es_hora_valida
    filas = []
    for t, v in wl.items():
        if ya_instalado(t):
            filas.append((t, v if es_num(v) else None, "YA INSTALADO"))
        elif v is None:
            filas.append((t, None, "sin final"))
        elif es_num(v):
            filas.append((t, v, "ya jugado" if es_jug(t) else
                          "edicion duplicada" if es_dup(t) else
                          "estimacion" if es_est(t) else
                          "con horas (prensa)" if es_prensa(t) else "con horas"))
        else:
            filas.append((t, None, "sin dato"))
    orden = {"YA INSTALADO": 0, "con horas": 1, "con horas (prensa)": 2, "estimacion": 2.5, "sin final": 3, "sin dato": 4,
             "edicion duplicada": 5, "ya jugado": 6}
    filas.sort(key=lambda r: (orden[r[2]], -(r[1] or 0), r[0].lower()))

    n = len(filas)
    last = 4 + n
    ws = wb.create_sheet("Wishlist")
    ws.sheet_properties.tabColor = "AD1457"

    fina = Side(style="thin", color="D6DCE4")
    borde = Border(left=fina, right=fina, top=fina, bottom=fina)
    cab_fill = PatternFill("solid", fgColor=AZUL_OSC)
    cab_font = Font(bold=True, color="FFFFFF", size=10)
    centro = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A1:I1")
    ws["A1"] = "WISHLIST  ·  catalogo y comparativa con el backlog instalado"
    ws["A1"].font = Font(bold=True, size=15, color="FFFFFF")
    ws["A1"].fill = cab_fill
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 26
    ws["A2"] = ("%d titulos de Backloggd. Horas de historia principal: %s. "
                "Vacio = sin dato todavia. 'con horas (prensa)' = cubiq.ru, NO HowLongToBeat: certeza media o baja "
                "(detalle en el comentario de la celda de horas). 'edicion duplicada' = misma campana que otra entrada: "
                "se muestra pero NO suma en los totales; 'ya jugado' = ya completado, tampoco suma. 'estimacion' = sin duracion de campana publicada: mediana del tiempo jugado por los autores de resenas en Steam (o analogia con un juego similar si no esta lanzado), certeza muy baja, no entra en 'Horas con dato' y solo suma en la fila ESTIMADO. Metacritic: Metascore (PC si existe); "
                "vacio = sin Metascore ni ficha de Steam (el comentario lo explica); 'S 92%%' = sin Metascore: %% de resenas positivas en Steam, guardado como numero para ordenar junto a los Metascores y con los mismos colores (otra escala, comparacion aproximada); comentario si es de otra plataforma o dudosa. "
                "Habilidad y Complejidad (0-10): informativas; cursiva naranja = inferencia mia sin fuente (certeza baja); el comentario da fuente y certeza." % (n, str(fuente).rstrip(".")))
    ws["A2"].font = Font(italic=True, size=9, color="6B7280")

    for c, t in enumerate(["Titulo", "Horas", "Estado", "Metacritic", "Habilidad", "Complejidad"], 1):
        ws.cell(4, c, t)
    for r, (t, h, est) in enumerate(filas, 5):
        celda_texto(ws, r, 1, t)
        ws.cell(r, 2, h).number_format = "0.0"
        nt = nota_de(t)
        if nt and (nt.upper().startswith(("PRENSA", "ESTIMACION", "SIN DATO", "DECISION", "EDICION DUPLICADA", "YA JUGADO")) or "certeza" in nt.lower()):
            ws.cell(r, 2).comment = nota_comentario(nt)
        ws.cell(r, 3, est)
        v_mc, t_mc = mc_celda(mc.get(t) or mcn.get(normaliza(t)), st.get(t) or stn.get(normaliza(t)))
        cmc = ws.cell(r, 4, v_mc)
        if isinstance(v_mc, PctSteam):
            cmc.number_format = v_mc.fmt
        if t_mc:
            cmc.comment = mc_comentario(t_mc)
        dif_escribir(ws, r, 5, dif.get(t) or difn.get(normaliza(t)))
        for c in range(1, 7):
            cel = ws.cell(r, c)
            cel.border = borde
            if (r - 5) % 2:
                cel.fill = PatternFill("solid", fgColor=BANDA)
            if c > 1:
                cel.alignment = centro
        ws.cell(r, 1).alignment = Alignment(horizontal="left", indent=1)
    ws.freeze_panes = "A5"
    ws.auto_filter.ref = "A4:F%d" % last

    stats = [
        ('="Titulos en la wishlist ("&COUNTIF(C5:C%d,"edicion duplicada")&" duplicadas, "&COUNTIF(C5:C%d,"ya jugado")&" ya jugados)"' % (last, last),
         "=COUNTA(A5:A%d)" % last, "0"),
        ("Ya instalados (quitar de la wishlist)", '=COUNTIF(C5:C%d,"YA INSTALADO")' % last, "0"),
        ("Pendientes de comprar (sin duplicadas ni jugados)",
         '=G5-G6-COUNTIF(C5:C%d,"edicion duplicada")-COUNTIF(C5:C%d,"ya jugado")' % (last, last), "0"),
        ('="   con horas (HLTB o prensa; "&COUNTIF(C5:C%d,"con horas (prensa)")&" de prensa)"' % last,
         '=COUNTIF(C5:C%d,"con horas*")' % last, "0"),
        ("   sin dato todavia", '=COUNTIF(C5:C%d,"sin dato")' % last, "0"),
        ("   sin final (infinitos)", '=COUNTIF(C5:C%d,"sin final")' % last, "0"),
        ("Horas con dato (HLTB o prensa)", '=SUMIF(C5:C%d,"con horas*",B5:B%d)' % (last, last), "#,##0.0"),
        ("Media por juego con dato", "=IF(G8=0,0,ROUND(G11/G8,1))", "0.0"),
        ('="ESTIMADO: sin dato + "&COUNTIF(C5:C%d,"estimacion")&" con estimacion"' % last,
         '=ROUND(G9*G12,1)+SUMIF(C5:C%d,"estimacion",B5:B%d)' % (last, last), "#,##0.0"),
        ("Total wishlist (con dato + estimado)", "=G11+G13", "#,##0.0"),
        ("Horas pendientes del backlog instalado", "=Resumen!B6", "#,##0.0"),
        ("Backlog total si compras toda la wishlist", "=G14+G15", "#,##0.0"),
        ("Veces el backlog instalado", "=IF(G15=0,0,ROUND(G14/G15,1))", "0.0"),
        ("Dias al ritmo de Resumen!B14", "=ROUND(G16/Resumen!B14,0)", "#,##0"),
        ("Anios", "=ROUND(G18/365.25,1)", "0.0"),
    ]
    ws["H4"], ws["I4"] = "COMPARATIVA", "Valor"
    for c in ("H4", "I4"):
        ws[c].font, ws[c].fill, ws[c].alignment, ws[c].border = cab_font, cab_fill, centro, borde
    for c in range(1, 7):
        cel = ws.cell(4, c)
        cel.font, cel.fill, cel.alignment, cel.border = cab_font, cab_fill, centro, borde
    for i, (lab, f, fmt) in enumerate(stats, 5):
        a, b = ws.cell(i, 8, lab), ws.cell(i, 9, re.sub(r"(?<![A-Za-z!$])G(\d+)", r"I\1", f))
        b.number_format = fmt
        b.alignment = Alignment(horizontal="right", indent=1)
        a.border = b.border = borde
        if i % 2:
            a.fill = b.fill = PatternFill("solid", fgColor=BANDA)
    for fila_est in (13,):
        for c in (8, 9):
            ws.cell(fila_est, c).fill = PatternFill("solid", fgColor="FFF2CC")
            ws.cell(fila_est, c).font = Font(italic=True, bold=True, color="7A4F01")
    for fila_key in (16,):
        for c in (8, 9):
            ws.cell(fila_key, c).fill = PatternFill("solid", fgColor="E8F5E9")
            ws.cell(fila_key, c).font = Font(bold=True, color="1B5E20")

    # tabla auxiliar del grafico (J:L), agrupada y contraida
    ws["J4"], ws["K4"], ws["L4"] = ("Backlog instalado (pendiente)", "Wishlist con dato",
                                    "Wishlist estimada (sin dato)")
    ws["J5"], ws["K5"], ws["L5"] = "=I15", "=I11", "=I13"
    g = BarChart()
    g.type = "col"
    g.grouping = "stacked"
    g.overlap = 100
    g.title = "Horas: backlog instalado frente a wishlist"
    g.y_axis.title = "Horas"
    g.add_data(Reference(ws, min_col=10, max_col=12, min_row=4, max_row=5), titles_from_data=True)
    g.dataLabels = DataLabelList()
    g.dataLabels.showVal = True
    g.height, g.width = 10, 17
    ws.add_chart(g, "H22")

    for col, a in zip("ABCDEFGHI", [54, 11, 17, 14, 11, 13, 3, 54, 14]):
        ws.column_dimensions[col].width = a
    ws.column_dimensions.group("J", "L", hidden=True)

    ws.conditional_formatting.add(
        "C5:C%d" % last,
        CellIsRule(operator="equal", formula=['"YA INSTALADO"'],
                   fill=PatternFill("solid", fgColor="FFE0B2"),
                   font=Font(bold=True, color="7A4F01")))
    ws.conditional_formatting.add(
        "C5:C%d" % last,
        CellIsRule(operator="equal", formula=['"sin dato"'],
                   font=Font(color="9AA3AF")))
    ws.conditional_formatting.add(
        "C5:C%d" % last,
        CellIsRule(operator="equal", formula=['"con horas (prensa)"'],
                   font=Font(color="B7791F", italic=True)))
    ws.conditional_formatting.add(
        "C5:C%d" % last,
        CellIsRule(operator="equal", formula=['"estimacion"'],
                   font=Font(color="C2410C", italic=True)))
    ws.conditional_formatting.add(
        "C5:C%d" % last,
        CellIsRule(operator="equal", formula=['"edicion duplicada"'],
                   font=Font(color="9AA3AF", italic=True)))
    ws.conditional_formatting.add(
        "C5:C%d" % last,
        CellIsRule(operator="equal", formula=['"ya jugado"'],
                   font=Font(color="9AA3AF", italic=True)))
    ws.conditional_formatting.add(
        "B5:B%d" % last,
        DataBarRule(start_type="num", start_value=0, end_type="max", color="AD1457"))
    mc_formato(ws, "D5:D%d" % last, "D5")
    dif_formato(ws, "E5:F%d" % last)


def construir(juegos, q1, q2, q3, wl=None, fuente="origen no indicado",
              mc_w=None, notas_w=None, st_w=None, dif_w=None):
    """Crea el libro completo y devuelve (wb, TH, filas del historico)."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Juegos"
    ws["A1"] = "INVENTARIO DE JUEGOS - GB liberados por hora jugada"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = ("Tamanos MEDIDOS en disco. Horas ESTIMADAS (HowLongToBeat). "
                "GB/hora vacio = sin final o sin datos. "
                f"Veredicto por cuartiles del GB/h de esta lista (hoy: Mal < {q1:.2f}, Medio < {q2:.2f}, Bueno < {q3:.2f}, JUGAR YA >= {q3:.2f}). "
                "Metacritic: Metascore (PC si existe), informativo, no entra en el veredicto; vacio = sin Metascore ni ficha de Steam (el comentario lo explica); "
                "'S 92%' = sin Metascore: % de resenas positivas en Steam, guardado como numero (92) para ordenar junto a los Metascores y con los mismos colores; otra escala, comparacion aproximada; la media de la fila TOTAL incluye ambos; 'R 80' = nota de una sola resena (0-100), solo si no hay Metascore ni Steam (ver comentario). "
                "Regenerar con py generar_inventario.py desde la carpeta del proyecto")
    ws["A2"].value += (" Habilidad y Complejidad (0-10): informativas, no entran en el veredicto; "
                       "Habilidad = reflejos, castigo, exigencia de ejecucion; Complejidad = reglas, sistemas, curva de aprendizaje y razonamiento (puzles, deduccion); "
                       "cursiva naranja = inferencia mia sin fuente (certeza baja); el comentario de la celda da la fuente y la certeza.")
    ws["A2"].font = Font(italic=True, size=9)

    for i, c in enumerate(["Juego", "GB", "Horas", "GB/hora", "Unidad", "Veredicto",
                           "Dias instalado", "Metacritic", "Habilidad", "Complejidad", "Ruta"], 1):
        cel = ws.cell(4, i, c)
        cel.font = Font(bold=True, color="FFFFFF")
        cel.fill = PatternFill("solid", fgColor="333333")
        cel.alignment = Alignment(horizontal="center")

    for r, j in enumerate(juegos, 5):
        celda_texto(ws, r, 1, j["nombre"])
        ws.cell(r, 2, j["gb"])
        ws.cell(r, 3, "infinitas" if j["horas"] is None else j["horas"])
        if str(j.get("nota_h", "")).upper().startswith("ESTIMACION"):
            ws.cell(r, 3).comment = nota_comentario(j["nota_h"])
            ws.cell(r, 3).font = Font(italic=True, color="C2410C")
        ws.cell(r, 4, j["ratio"] if j["ratio"] > 0 else "")
        ws.cell(r, 5, j["unidad"])
        ws.cell(r, 6, j["veredicto"])
        ws.cell(r, 7, j["dias"])
        v_mc, t_mc = mc_celda(j.get("mc"), j.get("steam"))
        cmc = ws.cell(r, 8, v_mc)
        if isinstance(v_mc, PctSteam):
            cmc.number_format = v_mc.fmt
        if t_mc:
            cmc.comment = mc_comentario(t_mc)
        dif_escribir(ws, r, 9, j.get("dif"))
        celda_texto(ws, r, 11, j["ruta"])

    for i, a in enumerate([44, 11, 11, 12, 12, 30, 17, 14, 11, 13, 58], 1):
        ws.column_dimensions[get_column_letter(i)].width = a
    ws.freeze_panes = "A5"
    ws.auto_filter.ref = "A4:K%d" % (len(juegos) + 4)

    w2 = wb.create_sheet("Espacio")
    w2["A1"] = "ESPACIO POR UNIDAD"
    w2["A1"].font = Font(bold=True, size=13)
    w2.append([])
    w2.append(["Unidad", "Libre GB", "Total GB", "% libre", "Juegos GB"])
    tot = {}
    for j in juegos:
        tot[j["unidad"]] = tot.get(j["unidad"], 0) + j["gb"]
    for u in ["C:", "D:", "E:", "F:"]:
        try:
            t, us, li = shutil.disk_usage(u + "\\")
            w2.append([u, round(li / 1024**3, 1), round(t / 1024**3, 1),
                       round(li / t * 100, 1) if t else 0, round(tot.get(u, 0), 2)])
        except Exception:
            pass
    for i, a in enumerate([10, 12, 12, 10, 12], 1):
        w2.column_dimensions[get_column_letter(i)].width = a

    TH = hojas_extra(wb, juegos)
    filas_h = historico(juegos, TH)
    hoja_historico(wb, filas_h)
    if wl:
        hoja_wishlist(wb, juegos, wl, fuente, mc_w, notas_w, st_w, dif_w)
    embellecer(wb, juegos)
    pulir(wb, juegos)
    return wb, TH, filas_h
