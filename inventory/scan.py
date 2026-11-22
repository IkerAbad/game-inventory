# -*- coding: utf-8 -*-
"""Scan of the installed game folders."""

import os

from .config import EXCLUDE, LIBRARIES, LOOSE_PATHS
from .data import normalize
from .i18n import t


def size_gb(path):
    total = 0
    for root, dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except Exception:
                pass
    return total / 1024 ** 3


def days_installed(path):
    """Days since the folder exists. Uses the oldest available timestamp."""
    import time
    try:
        st = os.stat(path)
        changed = min(st.st_ctime, st.st_mtime)
        return int((time.time() - changed) / 86400)
    except Exception:
        return ""


def scan_games():
    games, seen, failed = [], set(), []
    for base in LIBRARIES:
        if not isinstance(base, str) or not base or not os.path.isdir(base):
            continue
        drive = base[0]
        try:
            names = sorted(os.listdir(base))
        except OSError as e:
            print(t("scan.read_error", path=base, error=e))
            failed.append(base)
            continue
        for name in names:
            path = os.path.join(base, name)
            if not os.path.isdir(path) or normalize(name) in EXCLUDE:
                continue
            key = normalize(name)
            duplicate = key in seen
            seen.add(key)
            games.append({"nombre": name, "gb": round(size_gb(path), 2),
                          "dias": days_installed(path), "unidad": drive + ":",
                          "ruta": path, "duplicado": duplicate})
    for path in LOOSE_PATHS:
        if isinstance(path, str) and path and os.path.isdir(path):
            games.append({"nombre": os.path.basename(path), "gb": round(size_gb(path), 2),
                          "dias": days_installed(path), "unidad": path[0] + ":",
                          "ruta": path, "duplicado": False})
    return games, failed


def excel_locked(path):
    """True when the Excel file is open: ~$ lock file or an exclusive handle."""
    if not os.path.exists(path):
        return False
    lock = os.path.join(os.path.dirname(path), "~$" + os.path.basename(path))
    if os.path.exists(lock):
        return True
    try:
        os.rename(path, path)
        return False
    except (IOError, OSError, PermissionError):
        return True
