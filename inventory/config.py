# -*- coding: utf-8 -*-
"""Paths and settings. The defaults are here; data/config.json can override them."""

import json
import os
import re

# Folders scanned for games (one entry per game library).
LIBRARIES = [
    r"C:\Matrix Games",
    r"C:\Program Files (x86)\Steam\steamapps\common",
    r"D:\Games",
    r"E:\Games",
    r"E:\SteamLibrary\steamapps\common",
    r"F:\Games",
]
# Loose installs outside the folders above.
LOOSE_PATHS = [
    r"C:\Program Files\PRAGMATA",
    r"C:\Program Files\Stellar Blade",
    r"C:\Program Files (x86)\Diablo II Resurrected",
    r"C:\Battlestate Games",
]
EXCLUDE = {"steamworks shared", "steam controller configs", "emuladores"}

# Repository root (the package lives in <root>/inventory).
PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root(package_root, cwd):
    """Use the source checkout when running from it; otherwise the current folder."""
    if (os.path.isdir(os.path.join(package_root, "data"))
            or os.path.isdir(os.path.join(package_root, ".git"))):
        return package_root
    return cwd


BASE_DIR = _data_root(PACKAGE_ROOT, os.getcwd())
# Personal data lives in data/ and is not versioned (see .gitignore).
# GAME_INVENTORY_DATA points to another data folder when needed.
DATA_DIR = os.environ.get("GAME_INVENTORY_DATA") or os.path.join(BASE_DIR, "data")
HOURS_JSON = os.path.join(DATA_DIR, "hours.json")
COMPLETED_JSON = os.path.join(DATA_DIR, "completed.json")
PLAYING_JSON = os.path.join(DATA_DIR, "playing.json")
HISTORY_CSV = os.path.join(DATA_DIR, "history.csv")
WISHLIST_JSON = os.path.join(DATA_DIR, "wishlist.json")


def _desktop():
    """User desktop, following the OneDrive redirect when it exists."""
    home = os.path.expanduser("~")
    for folder in (os.path.join(home, "Desktop"), os.path.join(home, "OneDrive", "Desktop")):
        if os.path.isdir(folder):
            return folder
    return os.path.join(home, "Desktop")


# Kept under the original Spanish name so the existing workbook is updated in place.
OUTPUT = os.path.join(_desktop(), "Juegos", "Inventario games GB por hora.xlsx")

# Optional overrides: data/config.json with "libraries", "loose_paths",
# "exclude" and "output". Missing or invalid values keep the defaults below.
CONFIG_JSON = os.path.join(DATA_DIR, "config.json")


def _read_config(path):
    """Read the optional config.json. Return {} when it is missing or invalid."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _string_list(value):
    return (isinstance(value, list)
            and all(isinstance(item, str) and item.strip() for item in value))


def _normalize_exclude(name):
    """Same normalization as data.normalize, without importing it (cycle)."""
    name = re.sub(r"[^a-z0-9]+", " ", str(name).lower().strip())
    return re.sub(r"\s+", " ", name).strip()


def _apply_config(config):
    """Return (libraries, loose, exclude, output) with the valid overrides applied."""
    libraries, loose, exclude, output = LIBRARIES, LOOSE_PATHS, EXCLUDE, OUTPUT
    if not isinstance(config, dict):
        return libraries, loose, exclude, output
    if _string_list(config.get("libraries")):
        libraries = [os.path.expanduser(item) for item in config["libraries"]]
    if _string_list(config.get("loose_paths")):
        loose = [os.path.expanduser(item) for item in config["loose_paths"]]
    if _string_list(config.get("exclude")):
        exclude = {_normalize_exclude(item) for item in config["exclude"]}
    if isinstance(config.get("output"), str) and config["output"].strip():
        output = os.path.expanduser(config["output"])
    return libraries, loose, exclude, output


LIBRARIES, LOOSE_PATHS, EXCLUDE, OUTPUT = _apply_config(_read_config(CONFIG_JSON))

# Network autocomplete.
USER_AGENT = "GameInventory/1.0 (personal use; no bulk automation)"
MAX_REQUESTS = 600
RETRY_DAYS = 30
