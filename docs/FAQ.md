# FAQ

## Does it upload my data?

No. It only makes read-only GET requests to the sources listed in [SECURITY.md](../SECURITY.md), and only when the network is enabled. `--offline` makes no requests at all. Everything personal stays in `data/`, which is ignored by git.

## Why is English the default?

The project is public. Use `--lang es`, or set `GAME_INVENTORY_LANG=es` once, to get the console and the workbook in Spanish.

## Where are my files?

`data/` holds the JSON files, the history and your notes, plus an optional `config.json`. The workbook goes to the path shown at the end of the run. See [DATA.md](DATA.md).

## How are the hours calculated?

The main-story hours come from Deku Deals, twoaveragegamers or an estimate from Steam reviews. `null` means the game has no end; `"?"` means there is no data yet. The `PRENSA` and `ESTIMACION` notes record where a number comes from.

## A game shows NO DATA. What now?

Run `game-inventory --check-data`. If the key exists but is marked `?`, add the hours to `hours.json`. If the key is missing, the folder name and the JSON key do not match after normalization.

## How do I add another library?

Add its folder to `libraries` or `loose_paths` in `data/config.json`. A `libraries` folder contains one subfolder per game; a `loose_paths` entry is a single game. `~` is expanded.

## Why does it refuse to write the workbook?

The Excel file is open in another program, the path is inside `data/`, or another run holds the lock. Close the workbook and wait for the other run.

## Can I install it without touching the global Python?

Yes, with `pipx install .` from the checkout. See the install section of the README.
