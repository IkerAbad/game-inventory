# -*- coding: utf-8 -*-
"""Cell formatting: Metacritic, Steam and difficulty."""

import math
import re

from .i18n import fmt_int, t

# Cell prefix when the score is the share of positive Steam reviews.
MC_FMT_STEAM = '"S "0"%"'
_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean_text(value, limit=32767):
    """Remove control characters Excel rejects and cap the cell length."""
    return _ILLEGAL.sub("", str(value))[:limit]


class PctSteam(int):
    """Fallback score (0-100 positive Steam reviews): stored as a number so it sorts
    with Metascores. fmt = cell number format (S prefix by default)."""
    fmt = MC_FMT_STEAM


def _reviews(n):
    return t("comment.reviews", n=n) if isinstance(n, int) else ""


def mc_cell(e, st=None):
    """_metacritic entry ({s, p, n, nota}) -> (cell value, comment or None).
    s: number = Metascore; "s/n" = Metacritic does not publish a Metascore; null = no data.
    st: _steam entry ({id, name, n, pct, desc}); only used when there is no numeric Metascore:
    the cell holds 92 (PctSteam) with format 'S 92%' (positive Steam reviews, another scale)."""
    pct = st.get("pct") if isinstance(st, dict) else None
    if (isinstance(pct, int) and not isinstance(pct, bool) and 0 <= pct <= 100
            and not (isinstance(e, dict) and isinstance(e.get("s"), (int, float)))):
        note = str(e.get("nota") or "").strip() if isinstance(e, dict) else ""
        note = (" (" + note + ")") if note else ""
        n_st = st.get("n")
        if isinstance(n_st, bool) or not isinstance(n_st, int):
            n_st = 0
        txt = (t("comment.no_metascore", note=note) + "\n"
               + t("comment.steam", pct=pct, n=fmt_int(n_st), desc=st.get("desc") or "?",
                   name=st.get("name") or "?", id=st.get("id")))
        value = PctSteam(pct)
        if st.get("pref"):
            value.fmt = '"%s "0' % st["pref"] if st["pref"] != "S" else MC_FMT_STEAM
        if st.get("txt"):
            txt = t("comment.no_metascore", note=note) + "\n" + str(st["txt"])
        return value, txt
    if not isinstance(e, dict):
        return None, None
    s, n = e.get("s"), e.get("n")
    p = str(e.get("p") or "").strip()
    note = str(e.get("nota") or "").strip()
    lines = []
    if p and p != "?":
        lines.append(t("comment.platform_reviews", platform=p, n=n)
                     if isinstance(n, int) else t("comment.platform", platform=p))
    elif isinstance(n, int):
        lines.append(t("comment.reviews", n=n))
    if s is None and not note:
        note = t("comment.no_data")
    if note:
        lines.append(note)
    comment = "\n".join(lines) if lines and (p not in ("PC", "") or note) else None
    if isinstance(s, str):
        # 's/n' (no Metascore and no Steam page): leave the cell empty so sorting
        # does not put a text first; the reason goes in the comment.
        extra = (" (" + _reviews(n) + ")") if isinstance(n, int) else ""
        lines2 = [t("comment.no_metascore_steam", note=extra)]
        if note:
            lines2.append(note)
        return None, "\n".join(lines2)
    if isinstance(s, (int, float)) and not isinstance(s, bool) and math.isfinite(s):
        return s, comment
    return None, comment


def mc_comment(txt):
    from openpyxl.comments import Comment
    txt = clean_text(txt)
    c = Comment(t("comment.metacritic") + "\n" + txt, t("comment.author"))
    c.width = 270
    c.height = 60 + 15 * (txt.count("\n") + len(txt) // 38)
    return c


def note_comment(txt):
    from openpyxl.comments import Comment
    txt = clean_text(txt)
    c = Comment(t("comment.hours") + "\n" + txt, t("comment.author"))
    c.width = 330
    c.height = 70 + 15 * (txt.count("\n") + len(txt) // 48)
    return c


def mc_format(ws, cell_range, first_cell):
    """Score colour: >=75 green, 50-74 yellow, <50 red (Metascore and Steam % alike). Text is ignored."""
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.styles import PatternFill, Font
    for cond, bg, fg in (("AND(ISNUMBER({c}),{c}>=75)", "C8E6C9", "1B5E20"),
                         ("AND(ISNUMBER({c}),{c}>=50,{c}<75)", "FFF9C4", "7A4F01"),
                         ("AND(ISNUMBER({c}),{c}<50)", "FFCDD2", "B71C1C")):
        ws.conditional_formatting.add(
            cell_range,
            FormulaRule(formula=[cond.format(c=first_cell)],
                        fill=PatternFill("solid", start_color=bg, end_color=bg),
                        font=Font(bold=True, color=fg)))


DIF_CERTAINTY = {
    "source": "comment.backed",
    "fuente": "comment.backed",
    "consenso": "comment.consensus",
    "inferencia": "comment.inference",
}


def dif_cells(e):
    """_dificultad entry ({h, c, ct, src, nota}) -> (skill, complexity, comment or None, is_inference).
    h = Skill 0-10 (reflexes, punishment, execution); c = Complexity 0-10 (rules, systems, learning
    curve); ct = certainty: source | consenso | inferencia. A null axis is left empty."""
    if not isinstance(e, dict):
        return None, None, None, False
    num = lambda v: (v if isinstance(v, (int, float)) and not isinstance(v, bool)
                     and math.isfinite(v) else None)
    h, c = num(e.get("h")), num(e.get("c"))
    if h is None and c is None:
        return None, None, None, False
    ct = e.get("ct") or "inferencia"
    fmt = lambda v: "-" if v is None else ("%g" % v)
    key = DIF_CERTAINTY.get(ct) if isinstance(ct, str) else None
    cert = t(key) if key else str(ct)
    if ct == "inferencia" and e.get("src"):
        cert = t("comment.inference_source")
    lines = [t("comment.skill", h=fmt(h), c=fmt(c)),
             t("comment.certainty", cert=cert)]
    if e.get("src"):
        lines.append(t("comment.source", src=e["src"]))
    if e.get("nota"):
        lines.append(str(e["nota"]))
    return h, c, "\n".join(lines), ct == "inferencia"


def dif_comment(txt):
    from openpyxl.comments import Comment
    txt = clean_text(txt)
    c = Comment(t("comment.difficulty") + "\n" + txt, t("comment.author"))
    c.width = 330
    c.height = 70 + 15 * (txt.count("\n") + len(txt) // 48)
    return c


def dif_write(ws, row, first_col, e):
    """Skill in column first_col and Complexity in first_col+1; orange italics for inferences;
    the comment carries certainty and source."""
    from openpyxl.styles import Font
    h, c, txt, inference = dif_cells(e)
    for col, value in ((first_col, h), (first_col + 1, c)):
        cell = ws.cell(row, col, value)
        if txt:
            cell.comment = dif_comment(txt)
        if inference and value is not None:
            cell.font = Font(italic=True, color="C2410C")


def dif_format(ws, cell_range):
    """0-10 colour scale: green (easy) -> yellow -> red (hard). Informative."""
    from openpyxl.formatting.rule import ColorScaleRule
    ws.conditional_formatting.add(
        cell_range,
        ColorScaleRule(start_type="num", start_value=0, start_color="C8E6C9",
                       mid_type="num", mid_value=5, mid_color="FFF9C4",
                       end_type="num", end_value=10, end_color="FFCDD2"))
