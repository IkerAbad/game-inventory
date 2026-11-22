# -*- coding: utf-8 -*-
"""Paths and settings. The only place to change the drives and the output file."""

import os

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
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Personal data lives in data/ and is not versioned (see .gitignore).
DATA_DIR = os.path.join(BASE_DIR, "data")
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
OUTPUT = os.path.join(_desktop(), "Juegos", "Inventario juegos GB por hora.xlsx")

# Network autocomplete.
USER_AGENT = "GameInventory/1.0 (personal use; no bulk automation)"
MAX_REQUESTS = 600
RETRY_DAYS = 30
