# Game inventory

[![CI](https://github.com/IkerAbad/game-inventory/actions/workflows/ci.yml/badge.svg)](https://github.com/IkerAbad/game-inventory/actions/workflows/ci.yml)
[![MIT license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

English | [Español](README.es.md)

Scan the folders where your games are installed, cross the disk size with the main-story hours and build an Excel workbook with the GB per hour ratio, a deletion plan, the history and the wishlist. The console and the workbook are available in English and Spanish.

## What it does

- Scans the drives and folders configured in `inventory/config.py` and measures every game on disk.
- Fills missing hours from the network (Deku Deals, twoaveragegamers and an estimate from Steam reviews), the Metascore and, when there is no Metascore, the share of positive Steam reviews.
- Purges from `hours.json` the keys of games that are no longer installed, only when every drive is present.
- Builds the Excel workbook with up to six sheets: Games, Space, Summary, Plan, History and Wishlist.

## Requirements

- Python 3.12 or newer.
- `openpyxl` (see `requirements.txt`).

## Install as a package

```
py -m pip install .
game-inventory --lang es
```

The direct script and module commands below also work without installing.

## Usage

```
cd C:\Dev\game-inventory
py -m pip install -r requirements.txt
py generate_inventory.py
```

Or as a module, from the same folder:

```
py -m inventory
```

Or double-click `start.cmd`. It saves the output to `data/last_run.log` and keeps the window open when there is an error.

Options:

| Option | What it does |
|---|---|
| `--lang en\|es` | Output language for the console and the workbook. Default: `en`. |
| `--offline`, `--sin-red` | Do not use the network. |
| `--keep`, `--conservar` | Do not purge uninstalled game keys. |
| `--force-purge`, `--forzar-purga` | Allow purging more than half of the keys at once. |
| `--output PATH`, `--salida PATH` | Write the Excel workbook to another path. |
| `--version` | Show the installed version. |

The workbook is written by default to `%USERPROFILE%\Desktop\Juegos\Inventario juegos GB por hora.xlsx` and keeps a `.bak.xlsx` copy of the previous run. The Spanish file name is kept so the existing workbook is updated in place. Close the workbook before running, otherwise the script stops before scanning anything.

## Data

All personal data lives in `data/`, which is not versioned. The script creates the folder when it does not exist.

| File | Content |
|---|---|
| `data/hours.json` | Main-story hours by normalized key. `null` = no end. The `_metacritic`, `_steam`, `_dificultad` and `_notas` blocks keep the notes. |
| `data/wishlist.json` | Wishlist titles with hours, notes, Metacritic, Steam and difficulty. |
| `data/playing.json` | Keys of the games you are playing now. |
| `data/completed.json` | Keys of the games you finished but still have installed. |
| `data/history.csv` | One row per run day. It feeds the History sheet. |

The source notes inside the JSON files keep the language they were written in.

## Robustness

- A syntax error in a JSON file aborts the run, shows the line and column, and writes nothing.
- Hours that are not positive numbers, `null` or `"?"` are treated as no data and reported.
- JSON, history and the workbook are written to a temporary file and renamed, so a mid-write failure leaves no corrupt file.
- The purge keeps `hours.json.bak` and refuses to remove more than half of the keys without `--force-purge`.
- If the history cannot be read or has broken rows, the original is kept as `history.csv.corrupto`.
- If the workbook is open, the script stops before scanning.
- Only one run can be active at a time, enforced by a lock in `data/`.
- BOM-prefixed JSON is accepted and broken history rows are skipped with a warning.

## Structure

```
generate_inventory.py      entry point
pyproject.toml             package metadata and console script
inventory/
  config.py                drives, paths and network settings
  data.py                  JSON: loading, formatting and safe writing
  scan.py                  size, days installed and workbook lock
  cell_format.py           cells: Metacritic, Steam and difficulty
  excel.py                 sheets, styles, charts and comparisons
  network.py               network autocomplete
  i18n.py                  English and Spanish strings
  cli.py                   options, orchestration and console summary
tests/                     unit and end-to-end tests
start.cmd                  Windows launcher
```

## Tests

```
py -m pip install -r requirements-dev.txt
py -m coverage run --source=inventory -m unittest discover -s tests -v
py -m coverage report -m
py -m pyflakes inventory generate_inventory.py tests
```

The CI fails below 90% coverage.

## Documentation

`README.es.md` is the Spanish version. The personal notes with sources and decisions live in `data/NOTES.md`, which is not versioned.

## License

MIT. See `LICENSE`.
