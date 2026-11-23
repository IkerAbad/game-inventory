# -*- coding: utf-8 -*-
"""Loading, formatting and writing the JSON data files."""

import json
import math
import os
import re
import shutil
import tempfile

from .config import HOURS_JSON, LIBRARIES, WISHLIST_JSON
from .i18n import t


def normalize(name):
    name = re.sub(r"[^a-z0-9]+", " ", str(name).lower().strip())
    return re.sub(r"\s+", " ", name).strip()


def is_valid_hours(value):
    """True for a usable duration: finite number between 0 and 1,000,000 hours (bool excluded)."""
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and 0 < value <= 1000000)


def read_json(path, default):
    """Read a UTF-8 JSON file, with or without BOM. Return default when it does not exist.
    Raise ValueError with the path and position when the file is corrupt."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError("%s is not valid JSON (line %d, column %d): %s"
                         % (path, e.lineno, e.colno, e.msg)) from e
    except UnicodeDecodeError as e:
        raise ValueError("%s is not UTF-8: %s" % (path, e)) from e
    except OSError as e:
        raise ValueError("cannot read %s: %s" % (path, e)) from e


def read_keys(path):
    """Keys from a JSON file that must be a list of titles (completed, playing)."""
    data = read_json(path, [])
    if not isinstance(data, list):
        raise ValueError("%s must be a list of titles" % path)
    for item in data:
        if not isinstance(item, str) and not str(item).startswith("_"):
            raise ValueError("%s must be a list of titles" % path)
    return {normalize(item) for item in data if not str(item).startswith("_")}


def clean_hours(hours):
    """Return (clean hours, warnings). A value that is not a positive number, null or '?'
    becomes '?' so it cannot break the calculations. The file is not modified."""
    clean, warnings = {}, []
    for key, value in hours.items():
        if key.startswith("_"):
            clean[key] = value
        elif value is None or value == "?":
            clean[key] = value
        elif is_valid_hours(value):
            clean[key] = value
        else:
            clean[key] = "?"
            warnings.append("%s = %r" % (key, value))
    return clean, warnings


def acquire_lock(folder):
    """Non-blocking exclusive lock that prevents two runs at once.
    Return the open file (keep it alive) or None when it is already taken."""
    handle = open(os.path.join(folder, ".lock"), "a+b")
    try:
        if os.name == "nt":
            import msvcrt
            if os.fstat(handle.fileno()).st_size == 0:
                handle.write(b"x")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def clean_temp_files(folder):
    """Remove .tmp_* leftovers from interrupted writes. Call only while holding the lock."""
    try:
        names = os.listdir(folder)
    except OSError:
        return
    for name in names:
        if name.startswith(".tmp_"):
            try:
                os.remove(os.path.join(folder, name))
            except OSError:
                pass


def write_atomic(path, text):
    """Write to a temporary file in the same folder and rename it. A mid-write failure
    leaves the original file intact."""
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".tmp_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_hours(hours):
    """Rewrite hours.json with the usual format (_comentario, keys, _notas)."""
    notes = hours.get("_notas") if isinstance(hours.get("_notas"), dict) else {}
    hours["_notas"] = notes    # the object must match what is written (see _save_json)
    lines = ["{"]
    if "_comentario" in hours:
        lines.append('  "_comentario": %s,' % json.dumps(hours["_comentario"], ensure_ascii=False))
        lines.append("")
    for key, value in hours.items():
        if not key.startswith("_"):
            lines.append("  %s: %s," % (json.dumps(key, ensure_ascii=False), json.dumps(value)))
    lines.append("")
    metacritic = hours.get("_metacritic") if isinstance(hours.get("_metacritic"), dict) else {}
    if metacritic:
        lines.append('  "_metacritic": {')
        items = list(metacritic.items())
        for i, (key, value) in enumerate(items):
            lines.append("    %s: %s%s" % (json.dumps(key, ensure_ascii=False),
                                           json.dumps(value, ensure_ascii=False),
                                           "," if i < len(items) - 1 else ""))
        lines.append("  },")
        lines.append("")
    steam = hours.get("_steam") if isinstance(hours.get("_steam"), dict) else {}
    if steam:
        lines.append('  "_steam": {')
        items = list(steam.items())
        for i, (key, value) in enumerate(items):
            lines.append("    %s: %s%s" % (json.dumps(key, ensure_ascii=False),
                                           json.dumps(value, ensure_ascii=False),
                                           "," if i < len(items) - 1 else ""))
        lines.append("  },")
        lines.append("")
    difficulty = hours.get("_dificultad") if isinstance(hours.get("_dificultad"), dict) else {}
    if difficulty:
        lines.append('  "_dificultad": {')
        items = list(difficulty.items())
        for i, (key, value) in enumerate(items):
            lines.append("    %s: %s%s" % (json.dumps(key, ensure_ascii=False),
                                           json.dumps(value, ensure_ascii=False),
                                           "," if i < len(items) - 1 else ""))
        lines.append("  },")
        lines.append("")
    known = {"_comentario", "_metacritic", "_steam", "_dificultad", "_notas"}
    for key, value in hours.items():
        if key.startswith("_") and key not in known:
            lines.append("  %s: %s," % (json.dumps(key, ensure_ascii=False),
                                        json.dumps(value, ensure_ascii=False)))
            lines.append("")
    lines.append('  "_notas": {')
    items = list(notes.items())
    for i, (key, note) in enumerate(items):
        lines.append("    %s: %s%s" % (json.dumps(key, ensure_ascii=False),
                                       json.dumps(note, ensure_ascii=False),
                                       "," if i < len(items) - 1 else ""))
    lines.append("  }")
    lines.append("}")
    write_atomic(HOURS_JSON, "\n".join(lines) + "\n")


def purge_hours(hours, installed_keys, failed_bases=(), force=False):
    """Remove keys without a folder from hours.json. Refuse when a drive is missing,
    unreadable, or when more than half of the keys would be removed at once."""
    problems = []
    missing = [base for base in LIBRARIES
               if isinstance(base, str) and base and not os.path.isdir(base)]
    if missing:
        problems.append(t("data.not_found", paths=", ".join(missing)))
    if failed_bases:
        problems.append(t("data.unreadable", paths=", ".join(failed_bases)))
    if problems:
        print("\n" + t("data.no_purge", problems="; ".join(problems)))
        return 0
    total = sum(1 for key in hours if not key.startswith("_"))
    orphans = [key for key in hours
               if not key.startswith("_") and key not in installed_keys]
    if not force and total >= 10 and len(orphans) > total // 2:
        print("\n" + t("data.no_purge_many", n=len(orphans), total=total))
        return 0
    for key in orphans:
        del hours[key]
    removed = set(orphans)
    for block in ("_notas", "_metacritic", "_steam", "_dificultad"):
        if isinstance(hours.get(block), dict):
            for key in [x for x in hours[block] if x not in installed_keys]:
                hours[block].pop(key, None)
                removed.add(key)
    if removed:
        try:
            shutil.copy2(HOURS_JSON, HOURS_JSON + ".bak")
        except OSError:
            pass
        try:
            _save_json(HOURS_JSON, write_hours, hours)
        except OSError as e:
            print(t("data.write_error", error=e))
    return len(removed)


def write_wishlist(meta):
    """Rewrite wishlist.json with the usual format (one entry per line)."""
    lines = ["{"]
    items = list(meta.items())
    for i, (key, value) in enumerate(items):
        comma = "," if i < len(items) - 1 else ""
        if isinstance(value, dict):
            lines.append("  %s: {" % json.dumps(key, ensure_ascii=False))
            subitems = list(value.items())
            for j, (subkey, subvalue) in enumerate(subitems):
                lines.append("    %s: %s%s" % (json.dumps(subkey, ensure_ascii=False),
                                               json.dumps(subvalue, ensure_ascii=False),
                                               "," if j < len(subitems) - 1 else ""))
            lines.append("  }" + comma)
        else:
            lines.append("  %s: %s%s" % (json.dumps(key, ensure_ascii=False),
                                         json.dumps(value, ensure_ascii=False), comma))
    lines.append("}")
    write_atomic(WISHLIST_JSON, "\n".join(lines) + "\n")


def _same(a, b):
    """JSON data equality that tolerates NaN (nan != nan in Python)."""
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b


def _save_json(path, writer, obj):
    """Write with 'writer' and check that the file read back equals the object; otherwise
    restore the previous copy (kept in the temporary folder)."""
    previous = os.path.join(tempfile.gettempdir(), "inventory_prev_" + os.path.basename(path))
    try:
        shutil.copy2(path, previous)
    except Exception:
        previous = None
    writer(obj)
    try:
        ok = _same(read_json(path, None), obj)
    except ValueError:
        ok = False
    if not ok:
        print(t("data.rewrite_failed", name=os.path.basename(path)))
        if previous:
            shutil.copy2(previous, path)
    return ok


def _dict_block(d, key):
    if not isinstance(d.get(key), dict):
        d[key] = {}
    return d[key]
