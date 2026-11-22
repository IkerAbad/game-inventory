# Architecture

The tool is a local command-line program. It reads the installed games, enriches the hours and scores, computes the backlog verdicts and writes one Excel workbook.

## Flow

1. `cli.main` parses the options, sets the language and takes the data lock.
2. `data` loads `hours.json`, `wishlist.json`, `completed.json` and `playing.json`.
3. `scan` walks the configured libraries and measures every game folder.
4. `network.autocomplete` fills missing hours and notes when the network is enabled.
5. `cli` joins both sides, computes GB/hour, quartiles and verdicts.
6. `excel` builds the workbook, updates `history.csv` and saves the file atomically.
7. `data.purge_hours` removes keys without a folder, unless `--keep` is used or the guard refuses.

## Modules

| Module | Responsibility |
|---|---|
| `config.py` | Libraries, data folder, output path and network limits. `data/config.json` overrides them. |
| `data.py` | JSON reading and writing, atomic writes, lock, purge and backups. |
| `scan.py` | Folder size, days installed, duplicate detection and Excel lock check. |
| `network.py` | Deku Deals, twoaveragegamers, Steam and Metacritic requests and matching. |
| `cell_format.py` | Metacritic, Steam and difficulty cells and comments. |
| `excel.py` | Workbook sheets, styles, charts, history and wishlist comparison. |
| `i18n.py` | English and Spanish strings. |
| `cli.py` | Options, orchestration, console summary and dry run. |

## Entry points

- `generate_inventory.py`: direct script.
- `py -m inventory`: module.
- `game-inventory`: installed console script.
- `start.cmd`: Windows launcher with a log in `data/last_run.log`.

## Guarantees

- Only one run at a time, through an OS lock.
- JSON, history and workbook writes are atomic.
- A broken JSON aborts before any write.
- The purge refuses to run when a drive is missing or unreadable, or when it would remove more than half of the keys.
- Excel text is written as text, never as a formula.
- Ctrl+C exits with code 130 and the workbook is either the old one or the new one, never half written.
- Personal data stays in `data/` and is not versioned.

## Tests

`tests/` covers the modules with unit tests, mocked HTTP responses, an end-to-end `main` with fake data and the abort paths. CI installs the package, runs the console script, checks the launcher on Windows, runs pyflakes and enforces at least 98% coverage. See `CHANGELOG.md` and `CONTRIBUTING.md`.
