# -*- coding: utf-8 -*-
"""Autocompletado por red: hours, Metacritic y Steam."""

import datetime
import glob
import html as _html
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from .config import (LIBRARIES, HOURS_JSON, MAX_REQUESTS, RETRY_DAYS, USER_AGENT,
                     WISHLIST_JSON)
from .data import (_dict_block, _save_json, write_hours, write_wishlist,
                    is_valid_hours, normalize)
from .i18n import t

_NET = {"ult": {}, "failures": {}, "streak": 0, "n": 0, "down": False}


def http_get(url, cookie=None, timeout=25):
    """(status, texto) o None si la red no responde o se agoto el presupuesto. 1 peticion/s por servidor."""
    host = urllib.parse.urlparse(url).netloc
    if _NET["down"] or _NET["n"] >= MAX_REQUESTS or _NET["failures"].get(host, 0) >= 4:
        return None
    espera = 1.0 - (time.time() - _NET["ult"].get(host, 0))
    if espera > 0:
        time.sleep(espera)
    cab = {"User-Agent": USER_AGENT, "Accept-Language": "en"}
    if cookie:
        cab["Cookie"] = cookie
    _NET["n"] += 1
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=timeout) as r:
            txt = r.read().decode("utf-8", "replace")
            _NET["streak"] = 0
            _NET["failures"][host] = 0
            return r.status, txt
    except urllib.error.HTTPError as e:
        _NET["streak"] = 0
        if e.code != 404:
            _NET["failures"][host] = _NET["failures"].get(host, 0) + 1
        return e.code, ""
    except Exception:
        _NET["failures"][host] = _NET["failures"].get(host, 0) + 1
        _NET["streak"] += 1
        if _NET["streak"] >= 3:
            _NET["down"] = True
        return None
    finally:
        _NET["ult"][host] = time.time()


def _json_get(url):
    r = http_get(url)
    if not r or r[0] != 200:
        return None
    try:
        return json.loads(r[1])
    except Exception:
        return None


def steam_manifests():
    """installdir normalizado -> (appid, name), leyendo appmanifest_*.acf de todas las bibliotecas de Steam."""
    dirs = {os.path.dirname(b) for b in LIBRARIES
            if isinstance(b, str) and b.lower().endswith("steamapps\\common")}
    vdf = r"C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf"
    try:
        for p in re.findall(r'"path"\s+"([^"]+)"', open(vdf, encoding="utf-8", errors="replace").read()):
            dirs.add(os.path.join(p.replace("\\\\", "\\"), "steamapps"))
    except Exception:
        pass
    out = {}
    for d in dirs:
        for f in glob.glob(os.path.join(d, "appmanifest_*.acf")):
            try:
                t = open(f, encoding="utf-8", errors="replace").read()
                a = re.search(r'"appid"\s+"(\d+)"', t)
                i = re.search(r'"installdir"\s+"([^"]+)"', t)
                n = re.search(r'"name"\s+"([^"]+)"', t)
                if a and i:
                    out[normalize(i.group(1))] = (int(a.group(1)), n.group(1) if n else None)
            except Exception:
                pass
    return out


_ROM = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}
_EDIC = {"remastered", "remaster", "definitive", "edition", "enhanced", "complete", "deluxe", "goty",
         "game", "of", "the", "year", "directors", "cut", "hd", "anniversary", "ultimate", "pirate",
         "legendary", "special", "gold", "premium", "classic"}
_NO = {"dlc", "expansion", "soundtrack", "pack", "demo", "bundle", "collection", "trilogy", "ost",
       "artbook", "season", "pass", "playtest", "upgrade", "voice", "mod"}


_ROM_DIG = {"ii": "2", "iii": "3", "iv": "4", "vi": "6", "vii": "7", "viii": "8", "ix": "9"}
_DIG_ROM = {v: k for k, v in _ROM_DIG.items()}


def _tokens(s):
    """Palabras normalizadas; los numeros romanos 2-4 y 6-9 se comparan como cifras (Alan Wake II = Alan Wake 2).
    V y X no se tocan: pueden ser letras (Mega Man X)."""
    t = [_ROM_DIG.get(w, w) for w in normalize(s).split()]
    return t[1:] if len(t) > 1 and t[0] == "the" else t      # "The Legend of Zelda" = "Legend of Zelda"


def _prefix_ok(corto, largo):
    """True si 'largo' = 'corto' + palabras que no cambian de juego (sin numero de secuela, DLC ni pack)."""
    if not corto or largo[:len(corto)] != corto or len(largo) == len(corto):
        return False
    extra = largo[len(corto):]
    if extra[0].isdigit() or extra[0] in _ROM or any(t in _NO for t in extra) or len(extra) > 6:
        return False
    return True


def match_title(names, cands):
    """names: names a probar (carpeta, ficha de Steam). cands: [(ref, titulo)].
    Devuelve (ref, titulo) si hay una coincidencia clara, "ambiguo" si hay varias, None si ninguna."""
    vistos, cu = set(), []
    for c in cands:
        if c[0] not in vistos:
            vistos.add(c[0])
            cu.append(c)
    for nom in names:
        k = _tokens(nom)
        ex = [c for c in cu if _tokens(c[1]) == k]
        if len(ex) == 1:
            return ex[0]
    pre = []
    for nom in names:
        k = _tokens(nom)
        for c in cu:
            ct = _tokens(c[1])
            ok = _prefix_ok(k, ct) or (ct and ct != k and ct == k[:len(ct)]
                                        and all(t in _EDIC for t in k[len(ct):]))
            if ok and c not in pre:
                pre.append(c)
    if len(pre) == 1:
        return pre[0]
    return "ambiguo" if pre else None


def _slugs(name):
    b = name.lower().replace("&", " and ")
    b = re.sub(r"['\u2019]", "", b)
    base = re.sub(r"[^a-z0-9]+", "-", b).strip("-")
    out = [base]
    partes = base.split("-")
    for i in range(len(partes) - 1, 0, -1):          # ultimo numero (o romano) del titulo: se prueba la otra grafia
        if partes[i] in _DIG_ROM:
            out.append("-".join(partes[:i] + [_DIG_ROM[partes[i]]] + partes[i + 1:]))
            break
        if partes[i] in _ROM_DIG:
            out.append("-".join(partes[:i] + [_ROM_DIG[partes[i]]] + partes[i + 1:]))
            break
    sin_ed = re.sub(r"-(classic|remastered|remaster|definitive-edition|enhanced-edition|game-of-the-year-edition|"
                    r"goty-edition|pirate-edition|deluxe-edition|complete-edition|directors-cut)$", "", base)
    if sin_ed != base:
        out.append(sin_ed)
    return out


def _slugs_for(names):
    return list(dict.fromkeys(s for n in names for s in _slugs(n) if s))


# --- hours: Deku Deals (cita HowLongToBeat) -------------------------------
def deku_search(name):
    r = http_get("https://www.dekudeals.com/search?q=" + urllib.parse.quote_plus(name))
    if not r or r[0] != 200:
        return []
    out = []
    for m in re.finditer(r"href='(/items/[^']+)'>\s*<h6[^>]*>(.*?)</h6>", r[1], re.S):
        out.append((m.group(1), _html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()))
    return out


def _hours_text(raw):
    raw = _html.unescape(raw)
    h = re.search(r"(\d+)?\s*(\u00bd)?\s*(?:hours?|hrs?)\b", raw)
    m = re.search(r"(\d+)\s*(?:minutes?|mins?)\b", raw)
    if not h and not m:
        return None
    v = 0.0
    if h:
        v += int(h.group(1) or 0) + (0.5 if h.group(2) else 0)
    if m:
        v += int(m.group(1)) / 60.0
    return round(v, 1) if v > 0 else None


def deku_item(path):
    r = http_get("https://www.dekudeals.com" + path)
    if not r or r[0] != 200:
        return None
    m = re.search(r"Main Story:</strong>\s*([^<]+)<", r[1])
    return _hours_text(m.group(1)) if m else None


# --- hours: twoaveragegamers.com (prensa, espejo sin source declarada) -----
def tag_hours(names):
    for sl in _slugs_for(names):
        r = http_get("https://www.twoaveragegamers.com/games/%s/" % sl)
        if not r or r[0] != 200:
            continue
        m = re.search(r'<meta name="description" content="([^"]+)"', r[1])
        if not m:
            continue
        d = _html.unescape(m.group(1))
        t = re.match(r"(.+?) \((\d{4})\)\.", d)
        h = re.search(r"About ([\d.]+) hours? to beat the main story", d)
        if not t or not h:
            continue
        if not isinstance(match_title(names, [(sl, t.group(1))]), tuple):
            continue
        return float(h.group(1)), t.group(1), t.group(2)
    return None


# --- Steam -----------------------------------------------------------------
def steam_search(names):
    """(appid, name) por busqueda en la tienda, solo con coincidencia de titulo clara."""
    for nom in dict.fromkeys(names):
        # la busqueda de Steam falla con " - " en el termino: se prueba tambien el name solo con letras y numeros
        for term in dict.fromkeys([nom, normalize(nom)]):
            d = _json_get("https://store.steampowered.com/api/storesearch/?term=%s&cc=es&l=en"
                          % urllib.parse.quote_plus(term))
            items = d.get("items") if isinstance(d, dict) else None
            if not isinstance(items, list):
                items = []
            its = [(i["id"], i["name"]) for i in items
                   if isinstance(i, dict) and i.get("type") == "app"
                   and i.get("id") is not None and i.get("name")]
            c = match_title(names, its)
            if isinstance(c, tuple):
                return c
    return None


def steam_store_name(appid):
    """Nombre oficial de la ficha de tienda (el del manifiesto puede ser mas corto)."""
    d = _json_get("https://store.steampowered.com/api/appdetails?appids=%d&filters=basic&l=english" % appid)
    try:
        return d[str(appid)]["data"]["name"]
    except Exception:
        return None


def steam_reviews(appid):
    """(total, % positivas) de todas las resenas y todos los idiomas, o None. % None si hay menos de 10."""
    d = _json_get("https://store.steampowered.com/appreviewhistogram/%d?l=english" % appid)
    try:
        ro = d["results"]["rollups"]
        up = sum(x["recommendations_up"] for x in ro)
        dn = sum(x["recommendations_down"] for x in ro)
    except Exception:
        return None
    n = up + dn
    return (n, int(round(100.0 * up / n))) if n >= 10 else (n, None)


def steam_estimate(appid):
    """Mediana de las hours totales jugadas por autores de resenas (10 mas utiles + 10 recientes) o None."""
    hs, partes = [], []
    for filtro in ("toprated", "mostrecent"):
        r = http_get("https://steamcommunity.com/app/%d/reviews/?browsefilter=%s&snr=1_5_100010_&filterLanguage=all"
                     % (appid, filtro))
        if not r or r[0] != 200:
            continue
        v = [float(x.replace(",", "")) for x in re.findall(r"([\d,]+(?:\.\d+)?) hrs on record", r[1])]
        hs += v
        partes.append(len(v))
    if len(hs) < 8:
        return None
    return round(statistics.median(hs), 1), len(hs), partes


# --- Metacritic ------------------------------------------------------------
def mc_search(names):
    """Entrada para _metacritic ({s, p, n, f[, nota]}) o None si no hay ficha.
    PC primero; si PC no tiene Metascore, la primera plataforma que lo tenga (queda en 'p' y en 'nota')."""
    hoy = datetime.date.today().isoformat()
    for sl in _slugs_for(names):
        r = http_get("https://www.metacritic.com/game/%s/" % sl)
        if not r or r[0] != 200:
            continue
        t = re.search(r"<title>([^<]+?) Reviews - Metacritic</title>", r[1])
        if not t or not isinstance(match_title(names, [(sl, _html.unescape(t.group(1)))]), tuple):
            continue
        pl = re.search(r'"gamePlatform":\[([^\]]*)\]', r[1])
        lista = re.findall(r'"([^"]+)"', pl.group(1)) if pl else []
        if len(lista) <= 1:
            m = re.search(r'"name":"Metascore"[^}]*?"ratingValue":(\d+),"reviewCount":(\d+)', r[1])
            p = lista[0] if lista else "?"
            if m:
                return {"s": int(m.group(1)), "p": p, "n": int(m.group(2)), "f": hoy}
            return {"s": "s/n", "p": p, "f": hoy}
        n_pc = None
        for p in sorted(lista, key=lambda x: x != "PC"):
            rp = http_get("https://www.metacritic.com/game/%s/critic-reviews/?platform=%s"
                          % (sl, re.sub(r"[^a-z0-9]+", "-", p.lower()).strip("-")))
            if not rp or rp[0] != 200:
                continue
            ms = re.search(r'title="Metascore (\d+) out of 100"', rp[1])
            nr = re.search(r"Showing (\d+) Critic Review", rp[1])
            if p == "PC" and nr:
                n_pc = int(nr.group(1))
            if ms:
                e = {"s": int(ms.group(1)), "p": p, "f": hoy}
                if nr:
                    e["n"] = int(nr.group(1))
                if p != "PC" and "PC" in lista:
                    e["nota"] = "PC sin Metascore; se usa la ficha de %s" % p
                return e
        e = {"s": "s/n", "p": "PC" if "PC" in lista else lista[0], "f": hoy}
        if n_pc is not None:
            e["n"] = n_pc
        return e
    return None


# --- resolucion de hours ----------------------------------------------------
def _fmt_h(v):
    return "%g" % v


def resolve_hours(names, get_appid, hoy_es, es_wl):
    """{value, nota, source, ambiguous}. value None = ninguna source utilizable (ambiguous = fichas ambiguas de Deku)."""
    cands, sel = [], None
    for nom in dict.fromkeys(names):
        cands += deku_search(nom)
        sel = match_title(names, cands)
        if isinstance(sel, tuple):
            break
    if sel == "ambiguo":
        # varias fichas con el mismo comienzo (p. ej. juego base y secuela independiente): se desempata con el
        # name oficial de la ficha de Steam
        ap = get_appid()
        nm = steam_store_name(ap[0]) if ap and ap[0] else None
        if nm:
            sel = match_title(list(names) + [nm], cands)
    if isinstance(sel, tuple):
        v = deku_item(sel[0])
        if v:
            return {"value": v, "source": "Deku/HLTB", "ambiguous": None,
                    "nota": "%s Main Story %s h (Deku Deals, %s). Ficha: %s."
                            % ("Deku/HLTB" if es_wl else "HLTB", _fmt_h(v), hoy_es, sel[1])}
    ambiguous = [c[1] for c in cands][:4] if sel == "ambiguo" else None
    t = tag_hours(names)
    if t:
        return {"value": t[0], "source": "twoaveragegamers (prensa)", "ambiguous": None,
                "nota": "PRENSA (twoaveragegamers.com, %s): %s h; ficha %s (%s). Espejo sin source declarada: "
                        "certeza media-baja." % (hoy_es, _fmt_h(t[0]), t[1], t[2])}
    ap = get_appid()
    if ap and ap[0]:
        e = steam_estimate(ap[0])
        if e:
            return {"value": e[0], "source": "ESTIMACION con resenas de Steam", "ambiguous": None,
                    "nota": "ESTIMACION (%s): mediana de %d resenas de Steam (%d mas utiles + %d recientes), tiempo "
                            "total jugado por sus autores. No hay duracion de campana publicada; incluye jugadores que "
                            "no terminaron y rejugadores. Certeza muy baja."
                            % (hoy_es, e[1], e[2][0] if e[2] else 0, e[2][1] if len(e[2]) > 1 else 0)}
    return {"value": None, "nota": None, "source": None, "ambiguous": ambiguous}


def _should_retry(e, hoy):
    """Entradas automaticas sin Metascore (con fecha 'f') se vuelven a mirar a los RETRY_DAYS days."""
    if not (isinstance(e, dict) and e.get("f") and e.get("s") in (None, "s/n")):
        return False
    try:
        return (hoy - datetime.date.fromisoformat(e["f"])).days >= RETRY_DAYS
    except Exception:
        return False


def autocomplete(games, hours, wl_meta):
    hoy = datetime.date.today()
    hoy_es, hoy_iso = hoy.strftime("%d/%m/%Y"), hoy.isoformat()
    nts, mc, st = _dict_block(hours, "_notas"), _dict_block(hours, "_metacritic"), _dict_block(hours, "_steam")
    wj = wl_meta.get("juegos") if isinstance(wl_meta.get("juegos"), dict) else {}
    wl_num = {normalize(t): v for t, v in wj.items() if is_valid_hours(v)}
    pending = []
    for j in games:
        if j["duplicate"]:
            continue
        k = normalize(j["name"])
        missing_hours = hours.get(k, "?") == "?" and k not in wl_num
        missing_note = (k not in mc) or _should_retry(mc.get(k), hoy)
        if missing_hours or missing_note:
            pending.append((j, k, missing_hours, missing_note))
    wishlist_pending = []
    if wj:
        wmc, wst, wnt = _dict_block(wl_meta, "_metacritic"), _dict_block(wl_meta, "_steam"), _dict_block(wl_meta, "_notas")
        for title, value in wj.items():
            missing_hours = isinstance(value, str) and value == "?"
            missing_note = (title not in wmc) or _should_retry(wmc.get(title), hoy)
            if missing_hours or missing_note:
                wishlist_pending.append((title, missing_hours, missing_note))
    if not pending and not wishlist_pending:
        print("\n" + t("net.nothing"))
        return
    print("\n" + t("net.start", installed=len(pending), wishlist=len(wishlist_pending)))
    sys.stdout.flush()
    log, sin = [], []
    changed_hours = changed_wishlist = False
    cache_app = {}

    def appid_for(key, names, app_m):
        if key not in cache_app:
            cache_app[key] = app_m if app_m else (steam_search(names) or (None, None))
        return cache_app[key]

    def process_item(key, display, names, app_m, missing_hours, missing_note, set_hours, mcd, std):
        cambio = False
        print("   %s" % display)
        sys.stdout.flush()
        if missing_hours:
            r = resolve_hours(names, lambda: appid_for(key, names, app_m), hoy_es, mcd is not mc)
            if r["value"] is not None:
                set_hours(r["value"], r["nota"])
                cambio = True
                log.append(t("net.hours_log", name=display, hours=_fmt_h(r["value"]),
                             source=r["source"]))
            else:
                extra = t("net.ambiguous", names=" | ".join(r["ambiguous"])) if r["ambiguous"] else ""
                sin.append("%s%s" % (display, extra))
        if missing_note:
            e = mc_search(names)
            if e is None:
                e = {"s": None, "nota": "sin ficha en Metacritic (%s)" % hoy_es, "f": hoy_iso}
            mcd[key] = e
            cambio = True
            reviews = t("net.reviews", n=e["n"]) if e.get("n") else ""
            d = (t("net.metascore", score=e["s"], platform=e.get("p", "?"), reviews=reviews)
                 if isinstance(e.get("s"), int) else t("net.no_metascore"))
            if not isinstance(e.get("s"), int):
                ap = appid_for(key, names, app_m)
                rs = steam_reviews(ap[0]) if ap and ap[0] else None
                if rs and rs[1] is not None:
                    std[key] = {"id": ap[0], "name": ap[1] or names[0], "n": rs[0],
                                  "desc": "histograma de Steam, todos los idiomas", "pct": rs[1]}
                    d += t("net.steam_suffix", pct=rs[1], n=rs[0])
                else:
                    d += t("net.no_steam")
            log.append(t("net.note_log", name=display, desc=d))
        return cambio

    try:
        if pending:
            manifests = steam_manifests()
            for j, k, missing_hours, missing_note in pending:
                app_m = manifests.get(k)
                names = [j["name"]] + ([app_m[1]] if app_m and app_m[1] else [])
                sin_camel = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", j["name"])      # CatherineClassic -> Catherine Classic
                if sin_camel != j["name"]:
                    names.append(sin_camel)

                def poner(v, nota, k=k):
                    hours[k] = v
                    nts[k] = nota
                if process_item(k, j["name"], names, app_m, missing_hours, missing_note, poner, mc, st):
                    changed_hours = True
        for title, missing_hours, missing_note in wishlist_pending:
            def set_wishlist(v, nota, title=title):
                wj[title] = v
                wnt[title] = nota
            if process_item(title, title, [title], None, missing_hours, missing_note, set_wishlist, wmc, wst):
                changed_wishlist = True
    finally:
        if changed_hours:
            _save_json(HOURS_JSON, write_hours, hours)
        if changed_wishlist:
            wl_meta["_actualizado"] = hoy_iso
            _save_json(WISHLIST_JSON, write_wishlist, wl_meta)
        print("\n" + t("net.done", n=_NET["n"],
                       offline=t("net.offline") if _NET["down"] else ""))
        for line in log:
            print(line)
        if sin:
            print(t("net.no_source", n=len(sin)))
            for item in sin:
                print("      " + item)
        sys.stdout.flush()
