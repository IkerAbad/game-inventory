# Examples

Names, paths and numbers below are illustrative.

## Console run

```
$ game-inventory --offline --top 3
Scanning game folders...
Games found: 42  |  Total: 380.12 GB
Pending hours: 512.4  |  At 4 h/day: 128 days (0.35 years)
GB/h quartiles: Bad < 0.25 | Medium < 0.60 | Good < 1.40 | PLAY NOW >= 1.40

TOP PICKS (best GB per hour):
   1. Example Game  |  2.10 GB/h  |  12 h  |  25.2 GB
   2. Another Game  |  1.80 GB/h  |  8 h  |  14.4 GB
   3. Third Game  |  1.55 GB/h  |  20 h  |  31.0 GB

OK: C:\Users\me\Desktop\Juegos\Inventario juegos GB por hora.xlsx
```

`--offline` skips every network request. Without it, the tool fills the missing hours and scores first.

## Data check

```
$ game-inventory --check-data
DATA CHECK
Config: 0 overrides in config.json
Hours: 42 games (0 warnings)
Completed: 3 | Playing: 1
Wishlist: 120 titles (0 warnings)
Metadata keys without a game: hours 0 | wishlist 0
Invalid metadata entries: metacritic 0 | steam 0 | difficulty 0
Wishlist titles repeated after normalization: 0
History: 8 days, last 2026-11-22 (0 bad rows)
```

Add `--strict` to return exit code 1 when any of those warning counters is not zero.

## Workbook

| Sheet | Content |
|---|---|
| Games | One row per installed game: size, hours, GB per hour, verdict, days installed, scores, difficulty and path. |
| Space | Free and used space per drive, plus the space taken by games. |
| Summary | Totals, completed games and the days needed at 1, 2, 3, 4, 6 and 8 hours per day. |
| Plan | Pending games ordered by GB per hour, with the date each one would be finished. |
| History | One row per run day and the chart of the evolution. |
| Wishlist | Wishlist titles, hours, status, scores and the comparison with the installed backlog. |

The workbook is English by default. `--lang es` switches the console and the workbook, including the sheet names.

## Data folder

```
data/
  config.json       optional: libraries, loose paths, exclusions and output path
  hours.json        hours, Metacritic, Steam, difficulty and notes per game
  wishlist.json     wishlist titles with hours and notes
  completed.json    finished games that are still installed
  playing.json      games you are playing now
  history.csv       one row per run day
  NOTES.md          personal notes and sources
```

Everything in `data/` is personal and is ignored by git. See [DATA.md](DATA.md) for the exact format.
