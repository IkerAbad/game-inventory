# -*- coding: utf-8 -*-
"""Autocompletado por red: horas, Metacritic y Steam."""

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

_RED = {"ult": {}, "fallos": {}, "seguidos": 0, "n": 0, "caida": False}


def http_get(url, cookie=None, timeout=25):
    """(status, texto) o None si la red no responde o se agoto el presupuesto. 1 peticion/s por servidor."""
    host = urllib.parse.urlparse(url).netloc
    if _RED["caida"] or _RED["n"] >= MAX_REQUESTS or _RED["fallos"].get(host, 0) >= 4:
        return None
    espera = 1.0 - (time.time() - _RED["ult"].get(host, 0))
    if espera > 0:
        time.sleep(espera)
    cab = {"User-Agent": USER_AGENT, "Accept-Language": "en"}
    if cookie:
        cab["Cookie"] = cookie
    _RED["n"] += 1
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=timeout) as r:
            txt = r.read().decode("utf-8", "replace")
            _RED["seguidos"] = 0
            _RED["fallos"][host] = 0
            return r.status, txt
    except urllib.error.HTTPError as e:
        _RED["seguidos"] = 0
        if e.code != 404:
            _RED["fallos"][host] = _RED["fallos"].get(host, 0) + 1
        return e.code, ""
    except Exception:
        _RED["fallos"][host] = _RED["fallos"].get(host, 0) + 1
        _RED["seguidos"] += 1
        if _RED["seguidos"] >= 3:
            _RED["caida"] = True
        return None
    finally:
        _RED["ult"][host] = time.time()


def _json_get(url):
    r = http_get(url)
    if not r or r[0] != 200:
        return None
    try:
        return json.loads(r[1])
    except Exception:
        return None


def steam_manifests():
    """installdir normalizado -> (appid, nombre), leyendo appmanifest_*.acf de todas las bibliotecas de Steam."""
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


def match_title(nombres, cands):
    """nombres: nombres a probar (carpeta, ficha de Steam). cands: [(ref, titulo)].
    Devuelve (ref, titulo) si hay una coincidencia clara, "ambiguo" si hay varias, None si ninguna."""
    vistos, cu = set(), []
    for c in cands:
        if c[0] not in vistos:
            vistos.add(c[0])
            cu.append(c)
    for nom in nombres:
        k = _tokens(nom)
        ex = [c for c in cu if _tokens(c[1]) == k]
        if len(ex) == 1:
            return ex[0]
    pre = []
    for nom in nombres:
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


def _slugs(nombre):
    b = nombre.lower().replace("&", " and ")
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


def _slugs_for(nombres):
    return list(dict.fromkeys(s for n in nombres for s in _slugs(n) if s))


# --- horas: Deku Deals (cita HowLongToBeat) -------------------------------
def deku_search(nombre):
    r = http_get("https://www.dekudeals.com/search?q=" + urllib.parse.quote_plus(nombre))
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


def deku_item(ruta):
    r = http_get("https://www.dekudeals.com" + ruta)
    if not r or r[0] != 200:
        return None
    m = re.search(r"Main Story:</strong>\s*([^<]+)<", r[1])
    return _hours_text(m.group(1)) if m else None


# --- horas: twoaveragegamers.com (prensa, espejo sin fuente declarada) -----
def tag_hours(nombres):
    for sl in _slugs_for(nombres):
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
        if not isinstance(match_title(nombres, [(sl, t.group(1))]), tuple):
            continue
        return float(h.group(1)), t.group(1), t.group(2)
    return None


# --- Steam -----------------------------------------------------------------
def steam_search(nombres):
    """(appid, nombre) por busqueda en la tienda, solo con coincidencia de titulo clara."""
    for nom in dict.fromkeys(nombres):
        # la busqueda de Steam falla con " - " en el termino: se prueba tambien el nombre solo con letras y numeros
        for term in dict.fromkeys([nom, normalize(nom)]):
            d = _json_get("https://store.steampowered.com/api/storesearch/?term=%s&cc=es&l=en"
                          % urllib.parse.quote_plus(term))
            items = d.get("items") if isinstance(d, dict) else None
            if not isinstance(items, list):
                items = []
            its = [(i["id"], i["name"]) for i in items
                   if isinstance(i, dict) and i.get("type") == "app"
                   and i.get("id") is not None and i.get("name")]
            c = match_title(nombres, its)
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
    """Mediana de las horas totales jugadas por autores de resenas (10 mas utiles + 10 recientes) o None."""
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
def mc_search(nombres):
    """Entrada para _metacritic ({s, p, n, f[, nota]}) o None si no hay ficha.
    PC primero; si PC no tiene Metascore, la primera plataforma que lo tenga (queda en 'p' y en 'nota')."""
    hoy = datetime.date.today().isoformat()
    for sl in _slugs_for(nombres):
        r = http_get("https://www.metacritic.com/game/%s/" % sl)
        if not r or r[0] != 200:
            continue
        t = re.search(r"<title>([^<]+?) Reviews - Metacritic</title>", r[1])
        if not t or not isinstance(match_title(nombres, [(sl, _html.unescape(t.group(1)))]), tuple):
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


# --- resolucion de horas ----------------------------------------------------
def _fmt_h(v):
    return "%g" % v


def resolve_hours(nombres, get_appid, hoy_es, es_wl):
    """{valor, nota, fuente, amb}. valor None = ninguna fuente utilizable (amb = fichas ambiguas de Deku)."""
    cands, sel = [], None
    for nom in dict.fromkeys(nombres):
        cands += deku_search(nom)
        sel = match_title(nombres, cands)
        if isinstance(sel, tuple):
            break
    if sel == "ambiguo":
        # varias fichas con el mismo comienzo (p. ej. juego base y secuela independiente): se desempata con el
        # nombre oficial de la ficha de Steam
        ap = get_appid()
        nm = steam_store_name(ap[0]) if ap and ap[0] else None
        if nm:
            sel = match_title(list(nombres) + [nm], cands)
    if isinstance(sel, tuple):
        v = deku_item(sel[0])
        if v:
            return {"valor": v, "fuente": "Deku/HLTB", "amb": None,
                    "nota": "%s Main Story %s h (Deku Deals, %s). Ficha: %s."
                            % ("Deku/HLTB" if es_wl else "HLTB", _fmt_h(v), hoy_es, sel[1])}
    amb = [c[1] for c in cands][:4] if sel == "ambiguo" else None
    t = tag_hours(nombres)
    if t:
        return {"valor": t[0], "fuente": "twoaveragegamers (prensa)", "amb": None,
                "nota": "PRENSA (twoaveragegamers.com, %s): %s h; ficha %s (%s). Espejo sin fuente declarada: "
                        "certeza media-baja." % (hoy_es, _fmt_h(t[0]), t[1], t[2])}
    ap = get_appid()
    if ap and ap[0]:
        e = steam_estimate(ap[0])
        if e:
            return {"valor": e[0], "fuente": "ESTIMACION con resenas de Steam", "amb": None,
                    "nota": "ESTIMACION (%s): mediana de %d resenas de Steam (%d mas utiles + %d recientes), tiempo "
                            "total jugado por sus autores. No hay duracion de campana publicada; incluye jugadores que "
                            "no terminaron y rejugadores. Certeza muy baja."
                            % (hoy_es, e[1], e[2][0] if e[2] else 0, e[2][1] if len(e[2]) > 1 else 0)}
    return {"valor": None, "nota": None, "fuente": None, "amb": amb}


def _should_retry(e, hoy):
    """Entradas automaticas sin Metascore (con fecha 'f') se vuelven a mirar a los RETRY_DAYS dias."""
    if not (isinstance(e, dict) and e.get("f") and e.get("s") in (None, "s/n")):
        return False
    try:
        return (hoy - datetime.date.fromisoformat(e["f"])).days >= RETRY_DAYS
    except Exception:
        return False


def autocomplete(juegos, horas, wl_meta):
    hoy = datetime.date.today()
    hoy_es, hoy_iso = hoy.strftime("%d/%m/%Y"), hoy.isoformat()
    nts, mc, st = _dict_block(horas, "_notas"), _dict_block(horas, "_metacritic"), _dict_block(horas, "_steam")
    wj = wl_meta.get("juegos") if isinstance(wl_meta.get("juegos"), dict) else {}
    wl_num = {normalize(t): v for t, v in wj.items() if is_valid_hours(v)}
    pend = []
    for j in juegos:
        if j["duplicado"]:
            continue
        k = normalize(j["nombre"])
        falta_h = horas.get(k, "?") == "?" and k not in wl_num
        falta_n = (k not in mc) or _should_retry(mc.get(k), hoy)
        if falta_h or falta_n:
            pend.append((j, k, falta_h, falta_n))
    wpend = []
    if wj:
        wmc, wst, wnt = _dict_block(wl_meta, "_metacritic"), _dict_block(wl_meta, "_steam"), _dict_block(wl_meta, "_notas")
        for title, value in wj.items():
            falta_h = isinstance(value, str) and value == "?"
            falta_n = (title not in wmc) or _should_retry(wmc.get(title), hoy)
            if falta_h or falta_n:
                wpend.append((title, falta_h, falta_n))
    if not pend and not wpend:
        print("\n" + t("net.nothing"))
        return
    print("\n" + t("net.start", installed=len(pend), wishlist=len(wpend)))
    sys.stdout.flush()
    log, sin = [], []
    cambio_h = cambio_w = False
    cache_app = {}

    def appid_de(clave, nombres, app_m):
        if clave not in cache_app:
            cache_app[clave] = app_m if app_m else (steam_search(nombres) or (None, None))
        return cache_app[clave]

    def procesar(clave, vis, nombres, app_m, falta_h, falta_n, poner_h, mcd, std):
        cambio = False
        print("   %s" % vis)
        sys.stdout.flush()
        if falta_h:
            r = resolve_hours(nombres, lambda: appid_de(clave, nombres, app_m), hoy_es, mcd is not mc)
            if r["valor"] is not None:
                poner_h(r["valor"], r["nota"])
                cambio = True
                log.append(t("net.hours_log", name=vis, hours=_fmt_h(r["valor"]),
                             source=r["fuente"]))
            else:
                extra = t("net.ambiguous", names=" | ".join(r["amb"])) if r["amb"] else ""
                sin.append("%s%s" % (vis, extra))
        if falta_n:
            e = mc_search(nombres)
            if e is None:
                e = {"s": None, "nota": "sin ficha en Metacritic (%s)" % hoy_es, "f": hoy_iso}
            mcd[clave] = e
            cambio = True
            reviews = t("net.reviews", n=e["n"]) if e.get("n") else ""
            d = (t("net.metascore", score=e["s"], platform=e.get("p", "?"), reviews=reviews)
                 if isinstance(e.get("s"), int) else t("net.no_metascore"))
            if not isinstance(e.get("s"), int):
                ap = appid_de(clave, nombres, app_m)
                rs = steam_reviews(ap[0]) if ap and ap[0] else None
                if rs and rs[1] is not None:
                    std[clave] = {"id": ap[0], "name": ap[1] or nombres[0], "n": rs[0],
                                  "desc": "histograma de Steam, todos los idiomas", "pct": rs[1]}
                    d += t("net.steam_suffix", pct=rs[1], n=rs[0])
                else:
                    d += t("net.no_steam")
            log.append(t("net.note_log", name=vis, desc=d))
        return cambio

    try:
        if pend:
            man = steam_manifests()
            for j, k, falta_h, falta_n in pend:
                app_m = man.get(k)
                nombres = [j["nombre"]] + ([app_m[1]] if app_m and app_m[1] else [])
                sin_camel = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", j["nombre"])      # CatherineClassic -> Catherine Classic
                if sin_camel != j["nombre"]:
                    nombres.append(sin_camel)

                def poner(v, nota, k=k):
                    horas[k] = v
                    nts[k] = nota
                if procesar(k, j["nombre"], nombres, app_m, falta_h, falta_n, poner, mc, st):
                    cambio_h = True
        for title, falta_h, falta_n in wpend:
            def poner_w(v, nota, title=title):
                wj[title] = v
                wnt[title] = nota
            if procesar(title, title, [title], None, falta_h, falta_n, poner_w, wmc, wst):
                cambio_w = True
    finally:
        if cambio_h:
            _save_json(HOURS_JSON, write_hours, horas)
        if cambio_w:
            wl_meta["_actualizado"] = hoy_iso
            _save_json(WISHLIST_JSON, write_wishlist, wl_meta)
        print("\n" + t("net.done", n=_RED["n"],
                       offline=t("net.offline") if _RED["caida"] else ""))
        for line in log:
            print(line)
        if sin:
            print(t("net.no_source", n=len(sin)))
            for item in sin:
                print("      " + item)
        sys.stdout.flush()
