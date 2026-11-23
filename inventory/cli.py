# -*- coding: utf-8 -*-
"""Entry point: options, orchestration and console summary."""

import argparse
import datetime
import math
import os
import shutil
import statistics
import subprocess
import sys

from .cell_format import dif_cells
from .config import (COMPLETED_JSON, CONFIG_JSON, DATA_DIR, HOURS_JSON, LIBRARIES,
                     LOOSE_PATHS, OUTPUT, PLAYING_JSON, WISHLIST_JSON)
from . import __version__
from .data import (acquire_lock, clean_hours, clean_temp_files, is_valid_hours,
                   normalize, purge_hours, read_json, read_keys)
from .excel import build_workbook, read_history
from .i18n import set_lang, t
from .network import autocomplete
from .scan import excel_locked, scan_games


def inside_data(path):
    """True when path is inside the data folder (a JSON must not be overwritten)."""
    try:
        data = os.path.normcase(os.path.abspath(DATA_DIR))
        target = os.path.normcase(os.path.abspath(path))
        return os.path.commonpath([target, data]) == data
    except ValueError:
        return False


def _default_lang():
    """Default language: GAME_INVENTORY_LANG when it is en or es, else English."""
    value = os.environ.get("GAME_INVENTORY_LANG", "")
    return value if value in ("en", "es") else "en"


def _preselect_lang(argv):
    args = argv if argv is not None else sys.argv[1:]
    for i, value in enumerate(args):
        if value == "--lang" and i + 1 < len(args):
            return args[i + 1]
        if value.startswith("--lang="):
            return value.split("=", 1)[1]
    return _default_lang()


def open_file(path):
    """Open the workbook with the default application. Return an error or None."""
    try:
        if hasattr(os, "startfile"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except OSError as e:
        return e
    return None


def top_picks(games, limit):
    """Best GB per hour among games that are not completed, playing or duplicated."""
    picks = [j for j in games if j["verdict"] == "great"
             and not j["completed"] and not j["playing"] and not j["duplicate"]]
    picks.sort(key=lambda j: (-j["ratio"], -j["gb"]))
    return picks[:limit]


def print_top(games, limit):
    picks = top_picks(games, limit)
    if not picks:
        return
    print("\n" + t("cli.top"))
    for i, j in enumerate(picks, 1):
        print(t("cli.top_line", i=i, name=j["name"], ratio=j["ratio"],
                hours=j["hours"], gb=j["gb"]))


def check_data(strict=False):
    """Validate the JSON data files without scanning or writing. Return 0 or 1."""
    print(t("check.title"))
    warnings = 0
    try:
        config = read_json(CONFIG_JSON, {})
        if not isinstance(config, dict):
            raise ValueError("%s must be a JSON object" % CONFIG_JSON)
        known_config = {"libraries", "loose_paths", "exclude", "output"}
        print(t("check.config", n=sum(1 for key in known_config if key in config)))
        unknown_config = sorted(set(config) - known_config)
        if unknown_config:
            warnings += len(unknown_config)
            print(t("check.config_unknown", n=len(unknown_config),
                    names=_names(unknown_config)))
        libraries = _path_list(config, "libraries", LIBRARIES)
        loose = _path_list(config, "loose_paths", LOOSE_PATHS)
        paths = libraries + loose
        print(t("check.libraries",
                n=sum(1 for path in paths if os.path.isdir(path)), total=len(paths)))
        output = config.get("output")
        if (isinstance(output, str) and output.strip()
                and inside_data(os.path.expanduser(output))):
            warnings += 1
            print(t("check.output_in_data"))
        hours = read_json(HOURS_JSON, {})
        if not isinstance(hours, dict):
            raise ValueError("%s must be a JSON object" % HOURS_JSON)
        _, hour_warnings = clean_hours(hours)
        warnings += len(hour_warnings)
        print(t("check.hours",
                n=sum(1 for key in hours if not key.startswith("_")),
                warnings=len(hour_warnings)))
        for warning in hour_warnings[:10]:
            print("   " + warning)
        bad_blocks = _bad_blocks(hours)
        if bad_blocks:
            warnings += len(bad_blocks)
            print(t("check.blocks", n=len(bad_blocks), names=_names(bad_blocks)))
        completed = read_keys(COMPLETED_JSON)
        playing = read_keys(PLAYING_JSON)
        print(t("check.keys", completed=len(completed), playing=len(playing)))
        both = sorted(completed & playing)
        if both:
            warnings += len(both)
            print(t("check.overlap", n=len(both), names=_names(both)))
        meta = read_json(WISHLIST_JSON, {})
        if not isinstance(meta, dict):
            raise ValueError("%s must be a JSON object" % WISHLIST_JSON)
        wishlist = meta.get("juegos", {})
        if not isinstance(wishlist, dict):
            raise ValueError("%s: 'juegos' must be a JSON object" % WISHLIST_JSON)
        bad = sum(1 for value in wishlist.values()
                  if not (value is None or value == "?" or is_valid_hours(value)))
        warnings += bad
        print(t("check.wishlist", n=len(wishlist), warnings=bad))
        bad_wish_blocks = _bad_blocks(meta)
        if bad_wish_blocks:
            warnings += len(bad_wish_blocks)
            print(t("check.blocks", n=len(bad_wish_blocks),
                    names=_names(bad_wish_blocks)))
        stale_hours = _stale_keys(hours, hours)
        stale_wish = _stale_keys(meta, wishlist)
        warnings += len(stale_hours) + len(stale_wish)
        print(t("check.stale", hours=len(stale_hours), wishlist=len(stale_wish)))
        if stale_hours or stale_wish:
            print(t("check.stale_names", hours=_names(stale_hours),
                    wishlist=_names(stale_wish)))
        mc_bad, steam_bad, dif_bad = _bad_metadata(hours)
        mc_w, steam_w, dif_w = _bad_metadata(meta)
        metadata_bad = mc_bad + mc_w + steam_bad + steam_w + dif_bad + dif_w
        warnings += metadata_bad
        print(t("check.metadata",
                metacritic=mc_bad + mc_w,
                steam=steam_bad + steam_w,
                difficulty=dif_bad + dif_w))
        groups = {}
        for title in wishlist:
            groups.setdefault(normalize(title), []).append(title)
        repeated = sum(len(titles) - 1 for titles in groups.values()
                       if len(titles) > 1)
        warnings += repeated
        print(t("check.duplicates", n=repeated))
        unnormalized, collisions = _hours_key_problems(hours)
        warnings += len(unnormalized) + len(collisions)
        if unnormalized:
            print(t("check.unnormalized", n=len(unnormalized),
                    names=_names(unnormalized)))
        if collisions:
            print(t("check.collisions", n=len(collisions),
                    names=_names(collisions)))
        missing_completed = sorted(completed - _game_keys(hours))
        missing_playing = sorted(playing - _game_keys(hours))
        if missing_completed or missing_playing:
            warnings += len(missing_completed) + len(missing_playing)
            print(t("check.missing", completed=_names(missing_completed),
                    playing=_names(missing_playing)))
        rows, problems = read_history()
        warnings += len(problems)
        if rows:
            dates = [row[0] for row in rows]
            repeated = len(dates) - len(set(dates))
            future = sum(1 for date in dates
                         if date > datetime.date.today().isoformat())
            if repeated or future:
                warnings += repeated + future
                print(t("check.history_dates", repeated=repeated, future=future))
            if dates != sorted(dates):
                warnings += 1
                print(t("check.history_order"))
            print(t("check.history", n=len(rows), last=max(r[0] for r in rows),
                    warnings=len(problems)))
        else:
            print(t("check.history_empty", warnings=len(problems)))
        print(t("check.warnings", n=warnings))
        if strict and warnings:
            print(t("check.strict", n=warnings))
            return 1
        return 0
    except ValueError as e:
        print(t("cli.abort", error=e))
        return 1


def _names(items, limit=5):
    items = list(items)
    if not items:
        return "-"
    text = ", ".join(str(item) for item in items[:limit])
    if len(items) > limit:
        text += " (+%d)" % (len(items) - limit)
    return text


def _game_keys(data):
    return {str(key) for key in data if not str(key).startswith("_")}


def _bad_blocks(data):
    """Metadata blocks that exist but are not JSON objects."""
    if not isinstance(data, dict):
        return []
    blocks = ("_metacritic", "_steam", "_dificultad", "_notas")
    return [block for block in blocks
            if block in data and not isinstance(data[block], dict)]


def _path_list(config, key, default):
    """Path list from config.json, expanding ~, or the default when it is invalid."""
    value = config.get(key)
    if (isinstance(value, list)
            and all(isinstance(item, str) and item.strip() for item in value)):
        return [os.path.expanduser(item) for item in value]
    return list(default)


def _hours_key_problems(hours):
    """Return (unnormalized keys, keys that collide after normalization)."""
    if not isinstance(hours, dict):
        return [], []
    keys = sorted(_game_keys(hours))
    unnormalized = [key for key in keys if normalize(key) != key]
    seen, collisions = {}, set()
    for key in keys:
        normalized = normalize(key)
        if normalized in seen:
            collisions.add(seen[normalized])
            collisions.add(key)
        else:
            seen[normalized] = key
    return unnormalized, sorted(collisions)


def _stale_keys(container, games):
    """Metadata keys that do not match any game key in the same file."""
    if not isinstance(container, dict) or not isinstance(games, dict):
        return []
    known = _game_keys(games)
    stale = set()
    for block in ("_metacritic", "_steam", "_dificultad", "_notas"):
        value = container.get(block)
        if isinstance(value, dict):
            stale.update(str(key) for key in value if key not in known)
    return sorted(stale)


def _number_in(value, low, high):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and low <= value <= high)


def _count_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _bad_metadata(data):
    """Count invalid entries in _metacritic, _steam and _dificultad."""
    if not isinstance(data, dict):
        return 0, 0, 0
    bad_mc = bad_steam = bad_dif = 0
    mc = data.get("_metacritic")
    if isinstance(mc, dict):
        for value in mc.values():
            if not isinstance(value, dict):
                bad_mc += 1
            elif not (value.get("s") is None or value.get("s") == "s/n"
                      or _number_in(value.get("s"), 0, 100)):
                bad_mc += 1
            elif not (value.get("n") is None or _count_int(value.get("n"))):
                bad_mc += 1
    steam = data.get("_steam")
    if isinstance(steam, dict):
        for value in steam.values():
            if not isinstance(value, dict):
                bad_steam += 1
            elif not (value.get("pct") is None or _count_int(value.get("pct"))
                      and value.get("pct") <= 100):
                bad_steam += 1
            elif not (value.get("n") is None or _count_int(value.get("n"))):
                bad_steam += 1
    dif = data.get("_dificultad")
    if isinstance(dif, dict):
        for value in dif.values():
            if not isinstance(value, dict):
                bad_dif += 1
                continue
            axes = [value.get(axis) for axis in ("h", "c")]
            if any(axis is not None and not _number_in(axis, 0, 10) for axis in axes):
                bad_dif += 1
            elif value.get("ct") is not None and value.get("ct") not in (
                    "source", "fuente", "consenso", "inferencia"):
                bad_dif += 1
    return bad_mc, bad_steam, bad_dif


def main(argv=None):
    lang = _preselect_lang(argv)
    if lang in ("en", "es"):
        set_lang(lang)
    parser = argparse.ArgumentParser(
        prog="game-inventory",
        description=t("help.description"),
        epilog=t("help.examples"),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lang", choices=["en", "es"], default=_default_lang(),
                        help=t("help.lang"))
    parser.add_argument("--version", action="version",
                        version="game-inventory " + __version__,
                        help=t("help.version"))
    parser.add_argument("--offline", "--sin-red", dest="offline", action="store_true",
                        help=t("help.offline"))
    parser.add_argument("--keep", "--conservar", dest="keep", action="store_true",
                        help=t("help.keep"))
    parser.add_argument("--force-purge", "--forzar-purga", dest="force_purge",
                        action="store_true", help=t("help.force_purge"))
    parser.add_argument("--dry-run", "--simular", dest="dry_run",
                        action="store_true", help=t("help.dry_run"))
    parser.add_argument("--top", dest="top", type=int, default=0, metavar="N",
                        help=t("help.top"))
    parser.add_argument("--open", "--abrir", dest="open_file", action="store_true",
                        help=t("help.open"))
    parser.add_argument("--check-data", "--validar", dest="check_data",
                        action="store_true", help=t("help.check_data"))
    parser.add_argument("--strict", "--estricto", dest="strict",
                        action="store_true", help=t("help.strict"))
    parser.add_argument("--output", "--salida", dest="output", default=None,
                        help=t("help.output"))
    args = parser.parse_args(argv)
    if args.top < 0:
        parser.error(t("cli.top_negative"))
    set_lang(args.lang)
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    if args.check_data:
        return check_data(args.strict)
    output = os.path.expanduser(args.output) if args.output else OUTPUT
    if os.path.isdir(output):
        print(t("cli.output_is_dir"))
        print("   " + output)
        return 1
    if inside_data(output):
        print(t("cli.output_in_data"))
        print("   " + output)
        return 1
    if excel_locked(output):
        print(t("cli.excel_open"))
        print("   " + output)
        print(t("cli.close_excel"))
        return 1
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except OSError as e:
        print(t("cli.data_dir_error", error=e))
        return 1
    try:
        lock = acquire_lock(DATA_DIR)
    except OSError as e:
        print(t("cli.lock_error", error=e))
        return 1
    if lock is None:
        print(t("cli.already_running"))
        print(t("cli.wait"))
        return 1
    clean_temp_files(DATA_DIR)
    if not os.path.exists(HOURS_JSON):
        print(t("cli.no_hours"))
    try:
        hours = read_json(HOURS_JSON, {})
        if not isinstance(hours, dict):
            raise ValueError("%s must be a JSON object" % HOURS_JSON)
        completed = read_keys(COMPLETED_JSON)
        playing = read_keys(PLAYING_JSON)
        wl_meta = read_json(WISHLIST_JSON, {})
        if not isinstance(wl_meta, dict):
            raise ValueError("%s must be a JSON object" % WISHLIST_JSON)
        wishlist = wl_meta.get("juegos", {})
        if not isinstance(wishlist, dict):
            raise ValueError("%s: 'juegos' must be a JSON object" % WISHLIST_JSON)
    except ValueError as e:
        print(t("cli.abort", error=e))
        print(t("cli.check_file"))
        lock.close()
        return 1
    valid_hours, hour_warnings = clean_hours(hours)
    if hour_warnings:
        print(t("cli.invalid_hours", n=len(hour_warnings)))
        for warning in hour_warnings[:10]:
            print("   " + warning)
        if len(hour_warnings) > 10:
            print(t("cli.more", n=len(hour_warnings) - 10))
    print(t("cli.scanning"))
    games, failed_bases = scan_games()
    if not args.offline and not args.dry_run:
        print(t("cli.fetching"))
        try:
            autocomplete(games, hours, wl_meta)
        except Exception as e:
            print(t("cli.autocomplete_error", error="%s: %s" % (type(e).__name__, e)))
        wishlist = wl_meta.get("juegos", {})
    wishlist_hours = {normalize(title): value for title, value in wishlist.items()
                      if is_valid_hours(value)}
    mc_hours = hours.get("_metacritic") if isinstance(hours.get("_metacritic"), dict) else {}
    mc_wish = wl_meta.get("_metacritic") if isinstance(wl_meta.get("_metacritic"), dict) else {}
    steam_hours = hours.get("_steam") if isinstance(hours.get("_steam"), dict) else {}
    steam_wish = wl_meta.get("_steam") if isinstance(wl_meta.get("_steam"), dict) else {}
    dif_hours = hours.get("_dificultad") if isinstance(hours.get("_dificultad"), dict) else {}
    dif_wish = wl_meta.get("_dificultad") if isinstance(wl_meta.get("_dificultad"), dict) else {}
    from_wishlist = []
    no_data = []
    for j in games:
        key = normalize(j["name"])
        j["hours"] = valid_hours.get(key, "?")
        j["mc"] = mc_hours.get(key)
        j["steam"] = steam_hours.get(key)
        j["dif"] = dif_hours.get(key)
        notes = hours.get("_notas") if isinstance(hours.get("_notas"), dict) else {}
        j["note"] = str(notes.get(key) or "")
        if j["hours"] == "?" and key in wishlist_hours:
            j["hours"] = wishlist_hours[key]
            from_wishlist.append((j["name"], wishlist_hours[key]))
        j["completed"] = key in completed
        j["playing"] = key in playing and not j["completed"]
        if j["completed"]:
            j["ratio"] = -0.5
            j["verdict"] = "completed"
        elif j["hours"] == "?":
            j["ratio"] = -1
            j["verdict"] = "no_data"
            no_data.append(j["name"])
        elif j["hours"] is None:
            j["ratio"] = 0.0
            j["verdict"] = "no_end"
        else:
            j["ratio"] = round(j["gb"] / j["hours"], 2)
            j["verdict"] = "__RATIO__"
        if j["duplicate"]:
            j["verdict"] = "duplicate"
        if j["playing"]:
            j["verdict"] = "playing"

    ratios = sorted(j["ratio"] for j in games
                    if j["verdict"] == "__RATIO__" and j["ratio"] > 0)
    q1, q2, q3 = statistics.quantiles(ratios, n=4) if len(ratios) >= 4 else (1.0, 2.0, 4.0)
    for j in games:
        if j["verdict"] == "__RATIO__":
            ratio = j["ratio"]
            j["verdict"] = ("great" if ratio >= q3 else
                            "good" if ratio >= q2 else
                            "medium" if ratio >= q1 else
                            "bad")

    games.sort(key=lambda x: (not x["playing"], -x["ratio"], -x["gb"]))

    if args.dry_run:
        dry_hours = sum(j["hours"] for j in games
                        if isinstance(j["hours"], (int, float))
                        and not j["completed"])
        print(t("cli.found", n=len(games), gb=sum(j["gb"] for j in games)))
        print(t("cli.pending", hours=dry_hours, days=round(dry_hours / 4),
                years=dry_hours / 4 / 365.25))
        print(t("cli.quartiles", q1=q1, q2=q2, q3=q3))
        if args.top > 0:
            print_top(games, args.top)
        print(t("cli.dry_run"))
        lock.close()
        return 0

    wb, total_hours, history_rows = build_workbook(
        games, q1, q2, q3, wl=wishlist,
        source=wl_meta.get("_fuente_horas", "source not given"),
        mc_w=mc_wish,
        notes_w=wl_meta.get("_notas") if isinstance(wl_meta.get("_notas"), dict) else None,
        st_w=steam_wish, dif_w=dif_wish)

    output_dir = os.path.dirname(os.path.abspath(output))
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        print(t("cli.output_dir_error", error=e))
        lock.close()
        return 1
    if os.path.exists(output):
        base, ext = os.path.splitext(output)
        try:
            shutil.copy2(output, base + ".bak" + (ext or ".xlsx"))
        except Exception as e:
            print(t("cli.backup_failed", error=e))
    tmp = output + ".tmp"
    try:
        wb.save(tmp)
        os.replace(tmp, output)
    except Exception as e:
        try:
            os.remove(tmp)
        except OSError:
            pass
        print(t("cli.save_error", error=e))
        lock.close()
        return 1
    print(t("cli.found", n=len(games), gb=sum(j["gb"] for j in games)))
    print(t("cli.pending", hours=total_hours, days=round(total_hours / 4),
            years=total_hours / 4 / 365.25))
    print(t("cli.quartiles", q1=q1, q2=q2, q3=q3))
    if args.top > 0:
        print_top(games, args.top)
    completed_games = [j for j in games if j["completed"]]
    if completed_games:
        print("\n" + t("cli.completed", n=len(completed_games),
                       gb=sum(j["gb"] for j in completed_games)))
        for j in sorted(completed_games, key=lambda x: -x["gb"]):
            print("   %-42s %6.2f GB  %s" % (j["name"], j["gb"], j["unit"]))
    playing_games = [j for j in games if j["playing"]]
    if playing_games:
        print("\n" + t("cli.playing", n=len(playing_games),
                       names=", ".join(j["name"] for j in playing_games)))
    if len(history_rows) > 1:
        a, b = history_rows[-2], history_rows[-1]
        print("\n" + t("cli.since", date=a[0],
                       gb=float(b[2]) - float(a[2]),
                       hours=float(b[3]) - float(a[3]),
                       games=int(b[1]) - int(a[1])))
    installed_keys = {normalize(j["name"]) for j in games}
    completed_orphans = completed - installed_keys
    if completed_orphans:
        print("\n" + t("cli.completed_orphans",
                       names=", ".join(sorted(completed_orphans))))
    playing_orphans = playing - installed_keys
    if playing_orphans:
        print("\n" + t("cli.playing_orphans", names=", ".join(sorted(playing_orphans))))
    orphan_keys = sorted(({k for k in hours if not k.startswith("_")}
                          | {k for block in ("_notas", "_metacritic", "_steam", "_dificultad")
                             if isinstance(hours.get(block), dict)
                             for k in hours[block]}) - installed_keys)
    if not args.keep:
        purged = purge_hours(hours, installed_keys, failed_bases, force=args.force_purge)
        if purged:
            print("\n" + t("cli.cleanup", n=purged, names=", ".join(orphan_keys)))
    elif orphan_keys:
        print("\n" + t("cli.orphans", n=len(orphan_keys), names=", ".join(orphan_keys)))
        print(t("cli.kept"))
    if from_wishlist:
        print("\n" + t("cli.from_wishlist"))
        for name, value in from_wishlist:
            print("   %-40s %s h" % (name, value))
    if wishlist:
        with_hours = sum(1 for value in wishlist.values() if is_valid_hours(value))
        without_data = sum(1 for value in wishlist.values() if value == "?")
        notes = wl_meta.get("_notas") if isinstance(wl_meta.get("_notas"), dict) else {}
        press = sum(1 for title, value in wishlist.items() if is_valid_hours(value)
                    and str(notes.get(title, "")).upper().startswith("PRENSA"))
        duplicates = sum(1 for title in wishlist
                         if str(notes.get(title, "")).upper().startswith("EDICION DUPLICADA"))
        played = sum(1 for title in wishlist
                     if str(notes.get(title, "")).upper().startswith("YA JUGADO"))
        estimates = sum(1 for title in wishlist
                        if str(notes.get(title, "")).upper().startswith("ESTIMACION"))
        print("\n" + t("cli.wishlist", n=len(wishlist), hours=with_hours, press=press,
                       estimates=estimates, dups=duplicates, played=played,
                       no_data=without_data,
                       no_end=len(wishlist) - with_hours - without_data))
    if no_data:
        print("\n" + t("cli.no_hours_list", n=len(no_data)))
        for name in no_data:
            print("   " + name)
    no_difficulty = [j["name"] for j in games if not j["duplicate"]
                     and dif_cells(j.get("dif"))[0] is None
                     and dif_cells(j.get("dif"))[1] is None]
    if no_difficulty:
        print("\n" + t("cli.no_difficulty", n=len(no_difficulty)))
        for name in no_difficulty:
            print("   " + name)
    if wishlist:
        known_dif = {normalize(key) for key in dif_wish}
        missing_dif = [title for title in wishlist
                       if title not in dif_wish and normalize(title) not in known_dif]
        if missing_dif:
            print("\n" + t("cli.no_difficulty_wishlist", n=len(missing_dif),
                           total=len(wishlist), names=", ".join(missing_dif[:5])))
    duplicates = [j["name"] for j in games if j["duplicate"]]
    if duplicates:
        print("\n" + t("cli.duplicates", names=", ".join(duplicates)))
    print("\n" + t("cli.ok", path=output))
    lock.close()
    if args.open_file:
        error = open_file(output)
        if error is None:
            print(t("cli.opened", path=output))
        else:
            print(t("cli.open_failed", error=error))
    return 0


def run(argv=None):
    """Console entry point: turn Ctrl+C into a message and exit code 130."""
    try:
        return main(argv)
    except KeyboardInterrupt:
        print()
        print(t("cli.cancelled"))
        return 130
