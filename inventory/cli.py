# -*- coding: utf-8 -*-
"""Entry point: options, orchestration and console summary."""

import argparse
import os
import shutil
import statistics
import sys

from .cell_format import dif_cells
from .config import COMPLETED_JSON, DATA_DIR, HOURS_JSON, OUTPUT, PLAYING_JSON, WISHLIST_JSON
from . import __version__
from .data import (acquire_lock, clean_hours, clean_temp_files, is_valid_hours,
                   normalize, purge_hours, read_json, read_keys)
from .excel import build_workbook
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


def _preselect_lang(argv):
    args = argv if argv is not None else sys.argv[1:]
    for i, value in enumerate(args):
        if value == "--lang" and i + 1 < len(args):
            return args[i + 1]
        if value.startswith("--lang="):
            return value.split("=", 1)[1]
    return "en"


def main(argv=None):
    lang = _preselect_lang(argv)
    if lang in ("en", "es"):
        set_lang(lang)
    parser = argparse.ArgumentParser(
        prog="game-inventory",
        description="Scan installed games, fill missing data from the network and build the Excel workbook.")
    parser.add_argument("--lang", choices=["en", "es"], default="en",
                        help="output language (default: en)")
    parser.add_argument("--version", action="version",
                        version="game-inventory " + __version__)
    parser.add_argument("--offline", "--sin-red", dest="offline", action="store_true",
                        help="do not use the network")
    parser.add_argument("--keep", "--conservar", dest="keep", action="store_true",
                        help="do not purge uninstalled game keys")
    parser.add_argument("--force-purge", "--forzar-purga", dest="force_purge",
                        action="store_true",
                        help="allow purging more than half of the keys at once")
    parser.add_argument("--dry-run", "--simular", dest="dry_run",
                        action="store_true",
                        help="scan and show the summary without writing anything")
    parser.add_argument("--output", "--salida", dest="output", default=None,
                        help="Excel path (default: config.py)")
    args = parser.parse_args(argv)
    set_lang(args.lang)
    output = os.path.expanduser(args.output) if args.output else OUTPUT
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
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
    games, failed_bases = scan_games()
    if not args.offline and not args.dry_run:
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
    return 0
