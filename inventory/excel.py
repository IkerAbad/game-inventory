# -*- coding: utf-8 -*-
"""Excel workbook: sheets, styles, charts and comparisons."""

import os
import re
import shutil

from .cell_format import (PctSteam, clean_text, dif_format, dif_write, mc_cell,
                          mc_comment, mc_format, note_comment)
from .config import HISTORY_CSV
from .data import is_valid_hours, normalize, write_atomic
from .i18n import t


def sheet(key):
    """Translated sheet name."""
    return t("sheet." + key)


def text_cell(ws, row, col, value, fmt=None):
    """Write text and keep Excel from treating it as a formula when it starts with '='."""
    if isinstance(value, str):
        value = clean_text(value)
    cell = ws.cell(row, col, value)
    if isinstance(value, str) and value.startswith("="):
        cell.data_type = "s"
    if fmt:
        cell.number_format = fmt
    return cell


def read_history(path=None):
    """Read history.csv. Return (rows, problems): problems hold (kind, payload) where kind
    is 'incomplete', 'invalid' or 'read'. Missing file: no rows, no problems."""
    import csv
    import datetime
    import math

    path = HISTORY_CSV if path is None else path
    rows, problems = [], []
    if not os.path.exists(path):
        return rows, problems
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            for r in csv.reader(f):
                if not r or r[0] in ("fecha", "date"):
                    continue
                if len(r) < 4:
                    problems.append(("incomplete", r))
                    continue
                try:
                    datetime.date.fromisoformat(r[0])
                    int(r[1])
                    values = [float(r[2]), float(r[3])]
                except ValueError:
                    problems.append(("invalid", r))
                    continue
                if not all(math.isfinite(v) for v in values):
                    problems.append(("invalid", r))
                    continue
                rows.append(r)
    except (OSError, UnicodeDecodeError) as e:
        problems.append(("read", str(e)))
    return rows, problems


def append_history(games, total_hours):
    """Add one row per day to history.csv and return the whole series.
    Bad rows are reported and skipped. The write is atomic."""
    import csv
    import datetime
    import io

    today = datetime.date.today().isoformat()
    row = [today, len(games), round(sum(j["gb"] for j in games), 2), round(total_hours, 1)]
    rows, problems = read_history()
    backup_needed = bool(problems)
    for kind, payload in problems:
        if kind == "read":
            print(t("data.history_read", error=payload))
        else:
            print(t("data.history_%s" % kind, row=payload))
    rows = [r for r in rows if r[0] != today]
    rows.append([str(x) for x in row])
    rows.sort(key=lambda r: r[0])
    if backup_needed and os.path.exists(HISTORY_CSV):
        try:
            shutil.copy2(HISTORY_CSV, HISTORY_CSV + ".corrupto")
        except OSError:
            pass
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["date", "games", "gb", "hours"])
    writer.writerows(rows)
    try:
        write_atomic(HISTORY_CSV, out.getvalue())
    except OSError as e:
        print(t("data.history_write", error=e))
    return rows


def history_sheet(wb, rows):
    import datetime
    from openpyxl.chart import LineChart, Reference
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    ws = wb.create_sheet(sheet("history"))
    ws["A2"] = t("text.history_hint")
    ws["A2"].font = Font(italic=True, size=9)
    for i, name in enumerate([t("col.date"), t("col.games"), t("col.history_gb"),
                              t("col.pending_hours"), t("col.delta_gb"),
                              t("col.delta_hours")], 1):
        ws.cell(4, i, name)
    prev = None
    for k, r in enumerate(rows):
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

    n = len(rows)
    chart = LineChart()
    chart.title = t("chart.history_backlog")
    chart.y_axis.title = t("axis.gb") + " / " + t("axis.hours")
    chart.x_axis.title = t("axis.date")
    chart.add_data(Reference(ws, min_col=3, max_col=4, min_row=4, max_row=4 + n),
                   titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=1, min_row=5, max_row=4 + n))
    chart.height, chart.width = 10, 24
    ws.add_chart(chart, "H5")

    chart2 = LineChart()
    chart2.title = t("chart.history_games")
    chart2.y_axis.title = t("axis.games")
    chart2.add_data(Reference(ws, min_col=2, min_row=4, max_row=4 + n), titles_from_data=True)
    chart2.set_categories(Reference(ws, min_col=1, min_row=5, max_row=4 + n))
    chart2.height, chart2.width, chart2.legend = 8, 24, None
    ws.add_chart(chart2, "H27")
    return ws


PALETTE = {
    "playing":   ("004D40", "B2DFDB"),
    "great":     ("1B5E20", "C8E6C9"),
    "good":      ("0D47A1", "BBDEFB"),
    "medium":    ("E65100", "FFE0B2"),
    "bad":       ("616161", "EEEEEE"),
    "no_end":    ("37474F", "CFD8DC"),
    "completed": ("4A148C", "E1BEE7"),
    "no_data":   ("F57F17", "FFF9C4"),
    "duplicate": ("B71C1C", "FFCDD2"),
}
DARK_BLUE = "1F2A37"
STRIPE = "F7F9FC"


def style_workbook(wb, games):
    """Apply visual styling to every sheet."""
    from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, DataBarRule
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    thin = Side(style="thin", color="D6DCE4")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    white = Font(color="FFFFFF", bold=True, size=10)
    header_fill = PatternFill("solid", fgColor=DARK_BLUE)
    center = Alignment(horizontal="center", vertical="center")

    def title_bar(ws, cell, text, width):
        ws.merge_cells("%s1:%s1" % (cell, width))
        c = ws["%s1" % cell]
        c.value = text
        c.font = Font(bold=True, size=15, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=DARK_BLUE)
        c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[1].height = 26

    def header_row(ws, row, first_col, last_col):
        for i in range(first_col, last_col + 1):
            cell = ws.cell(row, i)
            cell.font = white
            cell.fill = header_fill
            cell.alignment = center
            cell.border = border
        ws.row_dimensions[row].height = 20

    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = False

    # ---------------------------------------------------------------- GAMES
    ws = wb[sheet("games")]
    ws.sheet_properties.tabColor = "1B5E20"
    title_bar(ws, "A", t("title.games"), "K")
    ws["A2"].font = Font(italic=True, size=9, color="6B7280")
    header_row(ws, 4, 1, 11)
    n = len(games)
    max_range = max(n + 4, 5)      # valid range even with no games
    for i, j in enumerate(games):
        row = i + 5
        stripe = PatternFill("solid", fgColor=STRIPE) if i % 2 else None
        for c in range(1, 12):
            cell = ws.cell(row, c)
            cell.border = border
            if stripe:
                cell.fill = stripe
            if c in (2, 3, 4, 5, 7, 8, 9, 10):
                cell.alignment = Alignment(horizontal="center")
        ws.cell(row, 2).number_format = "0.00"
        ws.cell(row, 4).number_format = "0.00"
        ws.cell(row, 11).font = Font(size=8, color="9AA3AF")
        fg, bg = PALETTE.get(j["verdict"], ("000000", "FFFFFF"))
        v = ws.cell(row, 6)
        v.fill = PatternFill("solid", fgColor=bg)
        v.font = Font(bold=True, size=9, color=fg)
        v.alignment = Alignment(horizontal="center")
    ws.conditional_formatting.add(
        "B5:B%d" % max_range,
        DataBarRule(start_type="num", start_value=0, end_type="max", color="5B8FF9"))
    ws.conditional_formatting.add(
        "D5:D%d" % max_range,
        ColorScaleRule(start_type="num", start_value=0, start_color="FFFFFF",
                       mid_type="num", mid_value=2, mid_color="A5D6A7",
                       end_type="max", end_color="1B5E20"))
    ws.conditional_formatting.add(
        "G5:G%d" % max_range,
        CellIsRule(operator="greaterThan", formula=["180"],
                   fill=PatternFill("solid", fgColor="FFE0B2"),
                   font=Font(bold=True, color="7A4F01")))

    # ---------------------------------------------------------------- SPACE
    mc_format(wb[sheet("games")], "H5:H%d" % max_range, "H5")
    dif_format(wb[sheet("games")], "I5:J%d" % max_range)

    ws = wb[sheet("space")]
    ws.sheet_properties.tabColor = "0D47A1"
    title_bar(ws, "A", t("title.space"), "E")
    header_row(ws, 3, 1, 5)
    space_range = max(ws.max_row, 4)    # valid range even if no drive is readable
    for row in range(4, ws.max_row + 1):
        for c in range(1, 6):
            cell = ws.cell(row, c)
            cell.border = border
            cell.alignment = center
            if c in (2, 3, 5):
                cell.number_format = "#,##0.00"
        ws.cell(row, 4).number_format = "0.0"
    ws.conditional_formatting.add(
        "D4:D%d" % space_range,
        CellIsRule(operator="lessThan", formula=["5"],
                   fill=PatternFill("solid", fgColor="FFCDD2"),
                   font=Font(bold=True, color="B71C1C")))
    ws.conditional_formatting.add(
        "D4:D%d" % space_range,
        CellIsRule(operator="between", formula=["5", "15"],
                   fill=PatternFill("solid", fgColor="FFE0B2")))

    # -------------------------------------------------------------- SUMMARY
    ws = wb[sheet("summary")]
    ws.sheet_properties.tabColor = "E65100"
    title_bar(ws, "A", t("title.summary"), "D")
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 15
    for row in range(3, 13):
        ws.cell(row, 1).border = border
        b = ws.cell(row, 2)
        b.border = border
        b.alignment = Alignment(horizontal="center")
        if row % 2:
            ws.cell(row, 1).fill = PatternFill("solid", fgColor=STRIPE)
            b.fill = PatternFill("solid", fgColor=STRIPE)
    for row in (6, 12):
        ws.cell(row, 1).font = Font(bold=True, color="FFFFFF")
        ws.cell(row, 1).fill = PatternFill("solid", fgColor="374151")
        ws.cell(row, 2).font = Font(bold=True, size=12, color="1B5E20")
        ws.cell(row, 2).fill = PatternFill("solid", fgColor="E8F5E9")
    for row in range(14, 20):
        ws.cell(row, 1).border = border
        ws.cell(row, 2).border = border
        ws.cell(row, 2).alignment = Alignment(horizontal="center")
    ws["A14"].font = Font(bold=True, color="7A4F01")
    ws["A14"].fill = PatternFill("solid", fgColor="FFF2CC")
    from openpyxl.worksheet.datavalidation import DataValidation
    dv = DataValidation(type="list", formula1='"1,2,3,4,5,6,8,10,12"', allow_blank=False,
                        showErrorMessage=True)
    dv.errorTitle = t("summary.bad_value")
    dv.error = t("summary.choose_hours")
    ws.add_data_validation(dv)
    dv.add(ws["B14"])
    header_row(ws, 21, 1, 4)
    for row in range(22, 28):
        for c in range(1, 5):
            cell = ws.cell(row, c)
            cell.border = border
            cell.alignment = center
            if row % 2:
                cell.fill = PatternFill("solid", fgColor=STRIPE)
    ws.cell(25, 1).fill = PatternFill("solid", fgColor="FFF2CC")
    ws.cell(25, 1).font = Font(bold=True)
    ws.column_dimensions.group("H", "J", hidden=True)
    ws.column_dimensions.group("X", "AA", hidden=True)

    # -------------------------------------------------------------- HISTORY
    ws = wb[sheet("history")]
    ws.sheet_properties.tabColor = "00838F"
    title_bar(ws, "A", t("title.history"), "F")
    ws["A2"].font = Font(italic=True, size=9, color="6B7280")
    header_row(ws, 4, 1, 6)
    for row in range(5, ws.max_row + 1):
        for c in range(1, 7):
            cell = ws.cell(row, c)
            cell.border = border
            cell.alignment = center
            if (row - 5) % 2:
                cell.fill = PatternFill("solid", fgColor=STRIPE)
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

    # ----------------------------------------------------------------- PLAN
    ws = wb[sheet("plan")]
    ws.sheet_properties.tabColor = "4A148C"
    title_bar(ws, "A", t("title.plan"), "L")
    ws["A2"].font = Font(italic=True, size=9, color="6B7280")
    header_row(ws, 4, 1, 12)
    ws.freeze_panes = "A5"
    last = ws.max_row
    last_cf = max(last, 5)    # valid range even with no pending games
    for row in range(5, last + 1):
        for c in range(1, 13):
            cell = ws.cell(row, c)
            cell.border = border
            cell.alignment = center
            if (row - 5) % 2:
                cell.fill = PatternFill("solid", fgColor=STRIPE)
        ws.cell(row, 2).alignment = Alignment(horizontal="left", indent=1)
        ws.cell(row, 6).number_format = "0.00"
        ws.cell(row, 7).number_format = "#,##0.00"
    ws.conditional_formatting.add(
        "H5:H%d" % last_cf,
        DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1,
                    color="7E57C2"))
    ws.conditional_formatting.add(
        "F5:F%d" % last_cf,
        DataBarRule(start_type="num", start_value=0, end_type="max", color="5B8FF9"))

    # --------------------------------------------------------------- CHARTS
    mc_format(wb[sheet("plan")], "J5:J%d" % last_cf, "J5")
    dif_format(wb[sheet("plan")], "K5:L%d" % last_cf)

    colors = ["2E7D32", "1565C0", "EF6C00", "6A1B9A", "C62828", "00838F"]
    for ws in wb.worksheets:
        for chart in getattr(ws, "_charts", []):
            chart.style = 2
            for k, series in enumerate(chart.series):
                color = colors[k % len(colors)]
                if type(chart).__name__ == "PieChart":
                    from openpyxl.chart.series import DataPoint
                    from openpyxl.chart.shapes import GraphicalProperties
                    for i, point_color in enumerate(colors):
                        series.dPt.append(DataPoint(idx=i, spPr=GraphicalProperties(solidFill=point_color)))
                    continue
                series.graphicalProperties.solidFill = color
                series.graphicalProperties.line.solidFill = color
                series.graphicalProperties.line.width = 22000
                series.smooth = False


def polish_workbook(wb, games):
    """Second pass: typography, filters, totals, print setup and axes."""
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.worksheet.properties import PageSetupProperties

    font_name = "Segoe UI"
    n = len(games)

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                f = cell.font
                if f is not None and f.name != font_name:
                    cell.font = Font(name=font_name, size=f.size, bold=f.bold,
                                     italic=f.italic, color=f.color,
                                     underline=f.underline)

    thick = Side(style="medium", color=DARK_BLUE)

    ws = wb[sheet("games")]
    ws.auto_filter.ref = "A4:K%d" % (n + 4)
    ws.freeze_panes = "A5"
    for row in range(5, n + 5):
        ws.cell(row, 2).alignment = Alignment(horizontal="right", indent=1)
        ws.cell(row, 4).alignment = Alignment(horizontal="right", indent=1)
        ws.row_dimensions[row].height = 16
    total_row = n + 5
    ws.cell(total_row, 1, t("row.total"))
    if n:
        ws.cell(total_row, 2, "=SUBTOTAL(109,B5:B%d)" % (n + 4)).number_format = "#,##0.00"
        ws.cell(total_row, 4, "=SUBTOTAL(101,D5:D%d)" % (n + 4)).number_format = "0.00"
        ws.cell(total_row, 6, '=SUBTOTAL(103,A5:A%d)&" %s"' % (n + 4, t("row.games")))
        ws.cell(total_row, 7, "=SUBTOTAL(101,G5:G%d)" % (n + 4)).number_format = "0"
        ws.cell(total_row, 8, '=IFERROR(SUBTOTAL(101,H5:H%d),"")' % (n + 4)).number_format = "0"
        ws.cell(total_row, 9, '=IFERROR(SUBTOTAL(101,I5:I%d),"")' % (n + 4)).number_format = "0.0"
        ws.cell(total_row, 10, '=IFERROR(SUBTOTAL(101,J5:J%d),"")' % (n + 4)).number_format = "0.0"
    else:
        ws.cell(total_row, 2, 0).number_format = "#,##0.00"
        ws.cell(total_row, 4, 0).number_format = "0.00"
        ws.cell(total_row, 6, "0 " + t("row.games"))
        ws.cell(total_row, 7, 0).number_format = "0"
        ws.cell(total_row, 8, 0).number_format = "0"
        ws.cell(total_row, 9, 0).number_format = "0.0"
        ws.cell(total_row, 10, 0).number_format = "0.0"
    for c in range(1, 12):
        cell = ws.cell(total_row, c)
        cell.fill = PatternFill("solid", fgColor="374151")
        cell.font = Font(name=font_name, bold=True, color="FFFFFF", size=10)
        cell.border = Border(top=thick)
        if c in (2, 4):
            cell.alignment = Alignment(horizontal="right", indent=1)
        elif c in (6, 7, 8, 9, 10):
            cell.alignment = Alignment(horizontal="center")
    ws.row_dimensions[total_row].height = 20

    ws = wb[sheet("plan")]
    last = ws.max_row
    ws.auto_filter.ref = "A4:L%d" % last
    gold = PatternFill("solid", fgColor="FFF4D6")
    green = PatternFill("solid", fgColor="B2DFDB")
    in_progress = getattr(wb, "_in_progress", 0)
    for row in range(5, min(5 + in_progress, last + 1)):
        for c in range(1, 13):
            ws.cell(row, c).fill = green
        ws.cell(row, 2).font = Font(name=font_name, bold=True, color="004D40")
        ws.cell(row, 1).border = Border(left=thick)
    for row in range(5 + in_progress, min(10 + in_progress, last + 1)):
        for c in range(1, 13):
            ws.cell(row, c).fill = gold
        ws.cell(row, 2).font = Font(name=font_name, bold=True, color="7A4F01")
        ws.cell(row, 1).border = Border(left=thick)
    for row in range(5, last + 1):
        ws.row_dimensions[row].height = 16

    for ws in wb.worksheets:
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
        ws.print_options.horizontalCentered = True
    wb[sheet("games")].print_title_rows = "4:4"
    wb[sheet("plan")].print_title_rows = "4:4"

    for ws in wb.worksheets:
        for chart in getattr(ws, "_charts", []):
            chart.roundedCorners = False
            chart.visible_cells_only = False
            labels = getattr(chart, "dataLabels", None)
            if labels is not None:
                labels.showSerName = False
                labels.showCatName = False
                labels.showLegendKey = False
                if labels.showPercent is None:
                    labels.showPercent = False
            for title in (chart.title,
                          getattr(getattr(chart, "y_axis", None), "title", None),
                          getattr(getattr(chart, "x_axis", None), "title", None)):
                if title is not None and hasattr(title, "overlay"):
                    title.overlay = False
            try:
                chart.gapWidth = 45
            except Exception:
                pass
            if hasattr(chart, "y_axis"):
                chart.y_axis.numFmt = "#,##0"
                chart.y_axis.delete = False
                chart.x_axis.majorGridlines = None
                chart.x_axis.delete = False

    from openpyxl.worksheet.properties import PageSetupProperties
    for ws in wb.worksheets:
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
        ws.print_options.horizontalCentered = True


def extra_sheets(wb, games):
    """Add the Summary and Plan sheets with their charts."""
    import datetime
    from openpyxl.chart import BarChart, LineChart, PieChart, Reference
    from openpyxl.chart.label import DataLabelList
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    header_fill = PatternFill("solid", fgColor="333333")

    def header(ws, row, columns, widths=None):
        for i, name in enumerate(columns, 1):
            cell = ws.cell(row, i, name)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        if widths:
            for i, width in enumerate(widths, 1):
                ws.column_dimensions[get_column_letter(i)].width = width

    with_end = [j for j in games if isinstance(j["hours"], (int, float)) and not j["completed"]]
    no_end = [j for j in games if j["hours"] is None and not j["completed"]]
    completed = [j for j in games if j["completed"]]
    total_hours = sum(j["hours"] for j in with_end)
    total_gb = sum(j["gb"] for j in games)
    free_gb = sum(j["gb"] for j in with_end)
    completed_gb = sum(j["gb"] for j in completed)
    today = datetime.date.today()

    # -------------------------------------------------------------- SUMMARY
    ws = wb.create_sheet(sheet("summary"))
    ws["A1"] = t("title.summary")
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = t("sum.generated", date=today.isoformat())
    ws["A2"].font = Font(italic=True, size=9, color="6B7280")

    data = [
        (t("sum.games"), len(games), None),
        (t("sum.with_end"), len(with_end), None),
        (t("sum.no_end"), len(no_end), None),
        (t("sum.hours"), round(total_hours, 1), "0.0"),
        (t("sum.gb"), round(total_gb, 2), "0.00"),
        (t("sum.gb_free"), round(free_gb, 2), "0.00"),
        (t("sum.avg_gb"), round(free_gb / total_hours, 3) if total_hours else 0, "0.000"),
        (t("sum.avg_hours"), round(total_hours / len(with_end), 1) if with_end else 0, "0.0"),
        (t("sum.completed"), len(completed), None),
        (t("sum.gb_now"), round(completed_gb, 2), "0.00"),
    ]
    for i, (label, value, fmt) in enumerate(data, 3):
        ws.cell(i, 1, label).font = Font(bold=(i == 6))
        cell = ws.cell(i, 2, value)
        if fmt:
            cell.number_format = fmt
        if i == 6:
            cell.font = Font(bold=True, size=12)

    ws["A14"] = t("sum.hours_day")
    ws["A14"].font = Font(bold=True)
    ws["B14"] = 4
    ws["B14"].fill = PatternFill("solid", fgColor="FFF2CC")
    ws["B14"].font = Font(bold=True)
    ws["A15"] = t("sum.days_needed")
    ws["B15"] = "=ROUND($B$6/$B$14,0)"
    ws["A16"] = t("sum.weeks")
    ws["B16"] = "=ROUND($B$15/7,1)"
    ws["A17"] = t("sum.months")
    ws["B17"] = "=ROUND($B$15/30.44,1)"
    ws["A18"] = t("sum.years")
    ws["B18"] = "=ROUND($B$15/365.25,2)"
    ws["A19"] = t("sum.end")
    ws["B19"] = "=TODAY()+$B$15"
    ws["B19"].number_format = "DD/MM/YYYY"

    header(ws, 21, [t("col.rate"), t("col.days_short"), t("col.years"), t("col.end_date")],
           [36, 14, 12, 14])
    for i, rate in enumerate([1, 2, 3, 4, 6, 8], 22):
        days = int(round(total_hours / rate))
        ws.cell(i, 1, rate)
        ws.cell(i, 2, days)
        ws.cell(i, 3, round(days / 365.25, 2)).number_format = "0.00"
        try:
            end = today + datetime.timedelta(days=days)
        except (OverflowError, ValueError):
            end = ""
        ws.cell(i, 4, end).number_format = "DD/MM/YYYY"

    # chart helper tables (columns H-J)
    categories = ["great", "good", "medium", "bad"]
    ws["H2"] = t("sum.category")
    ws["I2"] = t("col.hours")
    ws["J2"] = t("col.gb")
    for i, code in enumerate(categories, 3):
        subset = [j for j in with_end if j["verdict"] == code]
        ws.cell(i, 8, t("verdict.short." + code))
        ws.cell(i, 9, round(sum(j["hours"] for j in subset), 1))
        ws.cell(i, 10, round(sum(j["gb"] for j in subset), 2))

    ws["H9"] = t("col.unit")
    ws["I9"] = t("col.gb")
    units = {}
    for j in games:
        units[j["unit"]] = units.get(j["unit"], 0) + j["gb"]
    for i, unit in enumerate(sorted(units), 10):
        ws.cell(i, 8, unit)
        ws.cell(i, 9, round(units[unit], 2))

    ws["H16"] = t("col.game")
    ws["I16"] = t("col.hours")
    top = sorted(with_end, key=lambda x: -x["hours"])[:15]
    for i, j in enumerate(top, 17):
        text_cell(ws, i, 8, j["name"][:32])
        ws.cell(i, 9, j["hours"])
    ws.column_dimensions["H"].width = 34

    chart1 = BarChart()
    chart1.type = "col"
    chart1.title = t("chart.days_pace")
    chart1.y_axis.title = t("axis.days")
    chart1.x_axis.title = t("axis.hours_day")
    chart1.add_data(Reference(ws, min_col=2, min_row=21, max_row=27), titles_from_data=True)
    chart1.set_categories(Reference(ws, min_col=1, min_row=22, max_row=27))
    chart1.dataLabels = DataLabelList()
    chart1.dataLabels.showVal = True
    chart1.height, chart1.width, chart1.legend = 8, 16, None
    ws.add_chart(chart1, "A29")

    chart2 = BarChart()
    chart2.type = "col"
    chart2.title = t("chart.hours_ratio")
    chart2.y_axis.title = t("axis.hours")
    chart2.add_data(Reference(ws, min_col=9, min_row=2, max_row=6), titles_from_data=True)
    chart2.set_categories(Reference(ws, min_col=8, min_row=3, max_row=6))
    chart2.dataLabels = DataLabelList()
    chart2.dataLabels.showVal = True
    chart2.height, chart2.width, chart2.legend = 8, 16, None
    ws.add_chart(chart2, "L29")

    if units:
        chart3 = PieChart()
        chart3.title = t("chart.gb_drive")
        chart3.add_data(Reference(ws, min_col=9, min_row=9, max_row=9 + len(units)),
                        titles_from_data=True)
        chart3.set_categories(Reference(ws, min_col=8, min_row=10, max_row=9 + len(units)))
        chart3.dataLabels = DataLabelList()
        chart3.dataLabels.showPercent = True
        chart3.height, chart3.width = 9, 13
        ws.add_chart(chart3, "A47")

    if top:
        chart4 = BarChart()
        chart4.type = "bar"
        chart4.title = t("chart.top15")
        chart4.x_axis.title = t("axis.hours")
        chart4.add_data(Reference(ws, min_col=9, min_row=16, max_row=16 + len(top)),
                        titles_from_data=True)
        chart4.set_categories(Reference(ws, min_col=8, min_row=17, max_row=16 + len(top)))
        chart4.height, chart4.width, chart4.legend = 12, 16, None
        ws.add_chart(chart4, "L47")

    # ----------------------------------------------------------------- PLAN
    wp = wb.create_sheet(sheet("plan"))
    wp["A1"] = t("title.plan")
    wp["A1"].font = Font(bold=True, size=13)
    wp["A2"] = t("text.plan_header")
    wp["A2"].font = Font(italic=True, size=9)
    header(wp, 4, [t("col.number"), t("col.game"), t("col.unit"), t("col.hours"),
                   t("col.hours_cum"), t("col.gb"), t("col.gb_cum"),
                   t("col.percent_gb"), t("col.end_date"), t("col.metacritic"),
                   t("col.skill"), t("col.complexity")],
           [6, 42, 11, 10, 16, 10, 13, 18, 17, 14, 11, 13])

    hours_acc = gb_acc = 0.0
    in_progress = sum(1 for j in with_end if j.get("playing"))
    wb._in_progress = in_progress
    for i, j in enumerate(with_end, 1):
        hours_acc += j["hours"]
        gb_acc += j["gb"]
        row = i + 4
        wp.cell(row, 1, i)
        text_cell(wp, row, 2, j["name"])
        wp.cell(row, 3, j["unit"])
        wp.cell(row, 4, j["hours"])
        wp.cell(row, 5, round(hours_acc, 1))
        wp.cell(row, 6, j["gb"])
        wp.cell(row, 7, round(gb_acc, 2))
        wp.cell(row, 8, round(gb_acc / free_gb, 4) if free_gb else 0).number_format = "0.0%"
        c = wp.cell(row, 9, "=TODAY()+ROUND(E%d/%s!$B$14,0)" % (row, sheet("summary")))
        c.number_format = "DD/MM/YYYY"
        value, comment = mc_cell(j.get("mc"), j.get("steam"))
        mc_cell_obj = wp.cell(row, 10, value)
        if isinstance(value, PctSteam):
            mc_cell_obj.number_format = value.fmt
        if comment:
            mc_cell_obj.comment = mc_comment(comment)
        dif_write(wp, row, 11, j.get("dif"))
    wp.freeze_panes = "A5"

    if with_end:
        chart5 = LineChart()
        chart5.title = t("chart.gb_vs_hours")
        chart5.y_axis.title = t("axis.gb_cum")
        chart5.x_axis.title = t("axis.hours_cum")
        chart5.add_data(Reference(wp, min_col=7, min_row=4, max_row=4 + len(with_end)),
                        titles_from_data=True)
        chart5.set_categories(Reference(wp, min_col=5, min_row=5, max_row=4 + len(with_end)))
        chart5.height, chart5.width, chart5.legend = 10, 24, None
        wp.add_chart(chart5, "N5")

    # --- backlog end scenarios: 2, 4 and 6 h/day over the calendar ---
    rates = [2, 4, 6]
    months = min(int(total_hours / (min(rates) * 30.44)) + 2, 600)
    ws.cell(2, 24, t("col.date"))
    for k, rate in enumerate(rates):
        ws.cell(2, 25 + k, t("summary.rate_label", n=rate))
    for m in range(months + 1):
        row = 3 + m
        ws.cell(row, 24, today + datetime.timedelta(days=int(m * 30.44))).number_format = "MMM-YY"
        for k, rate in enumerate(rates):
            ws.cell(row, 25 + k, round(max(0.0, total_hours - rate * 30.44 * m), 1))
    for i in range(24, 28):
        ws.column_dimensions[get_column_letter(i)].width = 11

    chart6 = LineChart()
    chart6.title = t("chart.scenarios")
    chart6.y_axis.title = t("col.pending_hours")
    chart6.x_axis.title = t("axis.month")
    chart6.add_data(Reference(ws, min_col=25, max_col=27, min_row=2, max_row=3 + months),
                    titles_from_data=True)
    chart6.set_categories(Reference(ws, min_col=24, min_row=3, max_row=3 + months))
    chart6.height, chart6.width = 10, 26
    ws.add_chart(chart6, "A73")

    return total_hours


def wishlist_sheet(wb, games, wl, source, mc=None, notes=None, st=None, dif=None):
    """Wishlist sheet: catalog with hours, installed flag and backlog comparison."""
    import difflib
    from openpyxl.chart import BarChart, Reference
    from openpyxl.chart.label import DataLabelList
    from openpyxl.formatting.rule import CellIsRule, DataBarRule
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    mc = mc if isinstance(mc, dict) else {}
    mc_norm = {normalize(k): v for k, v in mc.items()}
    st = st if isinstance(st, dict) else {}
    st_norm = {normalize(k): v for k, v in st.items()}
    dif = dif if isinstance(dif, dict) else {}
    dif_norm = {normalize(k): v for k, v in dif.items()}
    notes = notes if isinstance(notes, dict) else {}
    notes_norm = {normalize(k): v for k, v in notes.items()}
    note_for = lambda title: str(notes.get(title) or notes_norm.get(normalize(title)) or "")
    is_press = lambda title: note_for(title).upper().startswith("PRENSA")
    is_duplicate = lambda title: note_for(title).upper().startswith("EDICION DUPLICADA")
    is_played = lambda title: note_for(title).upper().startswith("YA JUGADO")
    is_estimate = lambda title: note_for(title).upper().startswith("ESTIMACION")
    installed = [normalize(j["name"]) for j in games]
    installed_set = set(installed)

    def is_installed(title):
        key = normalize(title)
        if key in installed_set:
            return True
        for name in installed:
            sm = difflib.SequenceMatcher(None, key, name)
            if sm.real_quick_ratio() >= 0.9 and sm.quick_ratio() >= 0.9 and sm.ratio() >= 0.9:
                return True
        return False

    rows = []
    for title, value in wl.items():
        if is_installed(title):
            rows.append((title, value if is_valid_hours(value) else None, "installed"))
        elif value is None:
            rows.append((title, None, "no_end"))
        elif is_valid_hours(value):
            rows.append((title, value, "played" if is_played(title) else
                         "duplicate" if is_duplicate(title) else
                         "estimate" if is_estimate(title) else
                         "press" if is_press(title) else "hours"))
        else:
            rows.append((title, None, "no_data"))
    order = {"installed": 0, "hours": 1, "press": 2, "estimate": 2.5, "no_end": 3,
             "no_data": 4, "duplicate": 5, "played": 6}
    rows.sort(key=lambda r: (order[r[2]], -(r[1] or 0), r[0].lower()))

    n = len(rows)
    last = 4 + n
    ws = wb.create_sheet(sheet("wishlist"))
    ws.sheet_properties.tabColor = "AD1457"

    thin = Side(style="thin", color="D6DCE4")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill = PatternFill("solid", fgColor=DARK_BLUE)
    header_font = Font(bold=True, color="FFFFFF", size=10)
    center = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A1:I1")
    ws["A1"] = t("title.wishlist")
    ws["A1"].font = Font(bold=True, size=15, color="FFFFFF")
    ws["A1"].fill = header_fill
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 26
    ws["A2"] = t("text.wishlist_header", n=n, source=str(source).rstrip("."))
    ws["A2"].font = Font(italic=True, size=9, color="6B7280")

    for c, name in enumerate([t("col.title"), t("col.hours"), t("col.status"),
                              t("col.metacritic"), t("col.skill"),
                              t("col.complexity")], 1):
        ws.cell(4, c, name)
    for row, (title, hours, status) in enumerate(rows, 5):
        text_cell(ws, row, 1, title)
        ws.cell(row, 2, hours).number_format = "0.0"
        note = note_for(title)
        if note and (note.upper().startswith(("PRENSA", "ESTIMACION", "SIN DATO", "DECISION",
                                              "EDICION DUPLICADA", "YA JUGADO"))
                     or "certeza" in note.lower()):
            ws.cell(row, 2).comment = note_comment(note)
        ws.cell(row, 3, t("status." + status))
        value, comment = mc_cell(mc.get(title) or mc_norm.get(normalize(title)),
                                 st.get(title) or st_norm.get(normalize(title)))
        cell = ws.cell(row, 4, value)
        if isinstance(value, PctSteam):
            cell.number_format = value.fmt
        if comment:
            cell.comment = mc_comment(comment)
        dif_write(ws, row, 5, dif.get(title) or dif_norm.get(normalize(title)))
        for c in range(1, 7):
            cel = ws.cell(row, c)
            cel.border = border
            if (row - 5) % 2:
                cel.fill = PatternFill("solid", fgColor=STRIPE)
            if c > 1:
                cel.alignment = center
        ws.cell(row, 1).alignment = Alignment(horizontal="left", indent=1)
    ws.freeze_panes = "A5"
    ws.auto_filter.ref = "A4:F%d" % last

    duplicate = t("status.duplicate")
    played = t("status.played")
    installed_label = t("status.installed")
    no_data = t("status.no_data")
    no_end = t("status.no_end")
    press = t("status.press")
    estimate = t("status.estimate")
    hours_label = t("status.hours")
    summary_sheet = sheet("summary")
    stats = [
        ('="%s ("&COUNTIF(C5:C%d,"%s")&"%s"&COUNTIF(C5:C%d,"%s")&"%s"'
         % (t("wish.titles"), last, duplicate, t("wish.dups_mid"), last, played,
            t("wish.played_end")),
         "=COUNTA(A5:A%d)" % last, "0"),
        (t("wish.installed"), '=COUNTIF(C5:C%d,"%s")' % (last, installed_label), "0"),
        (t("wish.pending"),
         '=G5-G6-COUNTIF(C5:C%d,"%s")-COUNTIF(C5:C%d,"%s")' % (last, duplicate, last, played), "0"),
        ('="%s"&COUNTIF(C5:C%d,"%s")&"%s"'
         % (t("wish.with_hours_prefix"), last, press, t("wish.press_suffix")),
         '=COUNTIF(C5:C%d,"%s*")' % (last, hours_label), "0"),
        (t("wish.no_data"), '=COUNTIF(C5:C%d,"%s")' % (last, no_data), "0"),
        (t("wish.no_end"), '=COUNTIF(C5:C%d,"%s")' % (last, no_end), "0"),
        (t("wish.hours_data"), '=SUMIF(C5:C%d,"%s*",B5:B%d)' % (last, hours_label, last), "#,##0.0"),
        (t("wish.avg"), "=IF(G8=0,0,ROUND(G11/G8,1))", "0.0"),
        ('="%s"&COUNTIF(C5:C%d,"%s")&"%s"'
         % (t("wish.estimate_prefix"), last, estimate, t("wish.estimate_suffix")),
         '=ROUND(G9*G12,1)+SUMIF(C5:C%d,"%s",B5:B%d)' % (last, estimate, last), "#,##0.0"),
        (t("wish.total"), "=G11+G13", "#,##0.0"),
        (t("wish.backlog"), "=%s!B6" % summary_sheet, "#,##0.0"),
        (t("wish.backlog_total"), "=G14+G15", "#,##0.0"),
        (t("wish.times"), "=IF(G15=0,0,ROUND(G14/G15,1))", "0.0"),
        (t("wish.days", sheet=summary_sheet), "=ROUND(G16/%s!B14,0)" % summary_sheet, "#,##0"),
        (t("wish.years"), "=ROUND(G18/365.25,1)", "0.0"),
    ]
    ws["H4"], ws["I4"] = t("wish.comparison"), t("wish.value")
    for c in ("H4", "I4"):
        ws[c].font, ws[c].fill, ws[c].alignment, ws[c].border = header_font, header_fill, center, border
    for c in range(1, 7):
        cell = ws.cell(4, c)
        cell.font, cell.fill, cell.alignment, cell.border = header_font, header_fill, center, border
    for i, (label, formula, fmt) in enumerate(stats, 5):
        a = ws.cell(i, 8, label)
        b = ws.cell(i, 9, re.sub(r"(?<![A-Za-z!$])G(\d+)", r"I\1", formula))
        b.number_format = fmt
        b.alignment = Alignment(horizontal="right", indent=1)
        a.border = b.border = border
        if i % 2:
            a.fill = b.fill = PatternFill("solid", fgColor=STRIPE)
    for row in (13,):
        for c in (8, 9):
            ws.cell(row, c).fill = PatternFill("solid", fgColor="FFF2CC")
            ws.cell(row, c).font = Font(italic=True, bold=True, color="7A4F01")
    for row in (16,):
        for c in (8, 9):
            ws.cell(row, c).fill = PatternFill("solid", fgColor="E8F5E9")
            ws.cell(row, c).font = Font(bold=True, color="1B5E20")

    # chart helper table (J:L), grouped and collapsed
    ws["J4"], ws["K4"], ws["L4"] = (t("wish.installed_backlog"), t("wish.with_data"),
                                    t("wish.estimated"))
    ws["J5"], ws["K5"], ws["L5"] = "=I15", "=I11", "=I13"
    chart = BarChart()
    chart.type = "col"
    chart.grouping = "stacked"
    chart.overlap = 100
    chart.title = t("wish.chart_title")
    chart.y_axis.title = t("axis.hours")
    chart.add_data(Reference(ws, min_col=10, max_col=12, min_row=4, max_row=5),
                   titles_from_data=True)
    chart.dataLabels = DataLabelList()
    chart.dataLabels.showVal = True
    chart.height, chart.width = 10, 17
    ws.add_chart(chart, "H22")

    for col, width in zip("ABCDEFGHI", [54, 11, 17, 14, 11, 13, 3, 54, 14]):
        ws.column_dimensions[col].width = width
    ws.column_dimensions.group("J", "L", hidden=True)

    rules = [
        (installed_label, PatternFill("solid", fgColor="FFE0B2"),
         Font(bold=True, color="7A4F01")),
        (no_data, None, Font(color="9AA3AF")),
        (press, None, Font(color="B7791F", italic=True)),
        (estimate, None, Font(color="C2410C", italic=True)),
        (duplicate, None, Font(color="9AA3AF", italic=True)),
        (played, None, Font(color="9AA3AF", italic=True)),
    ]
    for label, fill, font in rules:
        ws.conditional_formatting.add(
            "C5:C%d" % last,
            CellIsRule(operator="equal", formula=['"%s"' % label], fill=fill, font=font))
    ws.conditional_formatting.add(
        "B5:B%d" % last,
        DataBarRule(start_type="num", start_value=0, end_type="max", color="AD1457"))
    mc_format(ws, "D5:D%d" % last, "D5")
    dif_format(ws, "E5:F%d" % last)


def build_workbook(games, q1, q2, q3, wl=None, source="source not given",
                   mc_w=None, notes_w=None, st_w=None, dif_w=None):
    """Build the full workbook and return (wb, total_hours, history rows)."""
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    wb.properties.title = t("app.title")
    wb.properties.subject = t("app.subject")
    wb.properties.creator = "game-inventory"
    wb.properties.description = t("app.description")
    wb.properties.keywords = "games, backlog, GB per hour, Excel"
    ws = wb.active
    ws.title = sheet("games")
    ws["A1"] = t("title.games")
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = t("text.games_header", q1=q1, q2=q2, q3=q3)
    ws["A2"].font = Font(italic=True, size=9)

    for i, name in enumerate([t("col.game"), t("col.gb"), t("col.hours"),
                              t("col.gb_hour"), t("col.unit"), t("col.verdict"),
                              t("col.days"), t("col.metacritic"), t("col.skill"),
                              t("col.complexity"), t("col.path")], 1):
        cell = ws.cell(4, i, name)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="333333")
        cell.alignment = Alignment(horizontal="center")

    for row, j in enumerate(games, 5):
        text_cell(ws, row, 1, j["name"])
        ws.cell(row, 2, j["gb"])
        ws.cell(row, 3, t("row.endless") if j["hours"] is None else j["hours"])
        if str(j.get("note", "")).upper().startswith("ESTIMACION"):
            ws.cell(row, 3).comment = note_comment(j["note"])
            ws.cell(row, 3).font = Font(italic=True, color="C2410C")
        ws.cell(row, 4, j["ratio"] if j["ratio"] > 0 else "")
        ws.cell(row, 5, j["unit"])
        ws.cell(row, 6, t("verdict." + j["verdict"]))
        ws.cell(row, 7, j["days"])
        value, comment = mc_cell(j.get("mc"), j.get("steam"))
        cell = ws.cell(row, 8, value)
        if isinstance(value, PctSteam):
            cell.number_format = value.fmt
        if comment:
            cell.comment = mc_comment(comment)
        dif_write(ws, row, 9, j.get("dif"))
        text_cell(ws, row, 11, j["path"])

    for i, width in enumerate([44, 11, 11, 12, 12, 30, 17, 14, 11, 13, 58], 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.freeze_panes = "A5"
    ws.auto_filter.ref = "A4:K%d" % (len(games) + 4)

    space = wb.create_sheet(sheet("space"))
    space["A1"] = t("title.space")
    space["A1"].font = Font(bold=True, size=13)
    space.append([])
    space.append([t("col.unit"), t("col.free_gb"), t("col.total_gb"),
                  t("col.percent_free"), t("col.games_gb")])
    totals = {}
    for j in games:
        totals[j["unit"]] = totals.get(j["unit"], 0) + j["gb"]
    for unit in ["C:", "D:", "E:", "F:"]:
        try:
            total, used, free = shutil.disk_usage(unit + "\\")
            space.append([unit, round(free / 1024**3, 1), round(total / 1024**3, 1),
                          round(free / total * 100, 1) if total else 0,
                          round(totals.get(unit, 0), 2)])
        except Exception:
            pass
    for i, width in enumerate([10, 12, 12, 10, 12], 1):
        space.column_dimensions[get_column_letter(i)].width = width

    total_hours = extra_sheets(wb, games)
    history_rows = append_history(games, total_hours)
    history_sheet(wb, history_rows)
    if wl:
        wishlist_sheet(wb, games, wl, source, mc_w, notes_w, st_w, dif_w)
    style_workbook(wb, games)
    polish_workbook(wb, games)
    return wb, total_hours, history_rows
