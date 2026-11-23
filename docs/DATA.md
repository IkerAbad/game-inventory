# Data files

Everything personal lives in `data/`, which is not versioned. The script creates the folder when it does not exist. The installed command reads `data/` from the source checkout or the current folder. `GAME_INVENTORY_DATA` points to another folder.

## hours.json

One entry per installed game. The key is the normalized folder name.

```json
{
  "_comentario": "optional note",
  "hades": 21.0,
  "a short hike": 1.5,
  "factorio": null,
  "_metacritic": {"hades": {"s": 93, "p": "PC", "n": 45}},
  "_steam": {"hades": {"id": 1145360, "name": "Hades", "n": 250000, "pct": 98, "desc": "Overwhelmingly Positive"}},
  "_dificultad": {"hades": {"h": 6, "c": 5, "ct": "consenso", "src": "Steam tags"}},
  "_notas": {"hades": "HLTB Main Story 21 h (Deku Deals, 22/11/2026)."}
}
```

- Number: main-story hours. `null`: no end (sandbox, service, roguelike). `"?"`: no data yet.
- `_comentario`: optional text.
- `_metacritic`: `s` is the Metascore, `"s/n"` when Metacritic publishes none, `null` when unknown. `p` is the platform, `n` the review count.
- `_steam`: fallback score when there is no numeric Metascore. `pct` is the share of positive reviews.
- `_dificultad`: `h` skill and `c` complexity, both 0-10. `ct` is `source` (or `fuente`), `consenso` or `inferencia`.
- `_notas`: source and decision notes. Unknown `_` blocks are preserved.

## wishlist.json

```json
{
  "_usuario": "Backloggd user",
  "_fuente_horas": "source description",
  "_actualizado": "2026-11-22",
  "juegos": {
    "Hades II": 25.0,
    "Signalis": "?",
    "Factorio": null
  },
  "_notas": {"Signalis": "SIN DATO"},
  "_metacritic": {},
  "_steam": {},
  "_dificultad": {}
}
```

- `juegos`: title to hours. Same number, `null` and `"?"` rules as `hours.json`.
- `_notas` prefixes used by the code: `PRENSA`, `ESTIMACION`, `EDICION DUPLICADA`, `YA JUGADO`, `SIN DATO`, `DECISION`.

## completed.json and playing.json

JSON lists of titles:

```json
["Hades", "A Short Hike"]
```

Entries starting with `_` are ignored. A game in both lists is treated as completed. Any entry that is not text is rejected.

## history.csv

One row per run day:

```csv
date,games,gb,hours
2026-11-16,132,1243.47,1745.3
```

The old header `fecha,juegos,gb,horas` is still accepted. Broken rows are skipped with a warning and the original file is kept as `history.csv.corrupto`.

## config.json

Optional. It overrides the defaults written in `inventory/config.py`:

```json
{
  "libraries": ["D:/Games", "E:/SteamLibrary/steamapps/common"],
  "loose_paths": ["C:/Program Files/Game"],
  "exclude": ["steamworks shared", "emuladores"],
  "output": "C:/Users/me/Desktop/Games.xlsx"
}
```

- `libraries`: folders whose subfolders are games.
- `loose_paths`: one game per folder.
- `exclude`: folder names to skip. Case and punctuation are ignored.
- `output`: workbook path; `~` is expanded.

A missing or invalid key keeps the default. `~` is expanded in every path. The file lives in `data/` and is not versioned.

## Writes and backups

- JSON, history and the workbook are written to a temporary file and renamed.
- A purge keeps `hours.json.bak`.
- A broken history keeps `history.csv.corrupto`.
- `data/` is ignored by git. Do not commit it.

## Language

Source notes keep the language they were written in. Interface strings come from `inventory/i18n.py` and change with `--lang`.
