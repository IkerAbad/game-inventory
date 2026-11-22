# Changelog

All notable changes to this project. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses semantic versioning.

## [Unreleased]

### Added

- `--dry-run` / `--simular`: scan and print the summary without writing the workbook, history, JSON or purging.
- Dependabot updates for pip and GitHub Actions.
- Contributing guide in English and Spanish.
- Package keywords and classifiers.

### Changed

- CI caches pip downloads, cancels superseded runs, uses read-only permissions and a 15-minute timeout.
- The installed `game-inventory` command reads `data/` from the source checkout or the current folder. `GAME_INVENTORY_DATA` overrides it.

## [1.0.0] - 2026-11-22

### Added

- Scan of every configured game library, with size in GB and days installed.
- Hours from Deku Deals, twoaveragegamers, Steam review estimates, Metascore and Steam review percentage.
- Excel workbook with Games, Space, Summary, Plan, History and Wishlist sheets.
- English and Spanish output with `--lang en|es`.
- Atomic writes for JSON, history and the workbook.
- Exclusive lock so two runs cannot overlap.
- Backup before purging and `.corrupto` copy of a broken history.
- Purge guard that refuses to remove more than half of the keys without `--force-purge`.
- Installable package with the `game-inventory` console script.
- 154 tests, coverage gate and lint in CI.

### Security

- JSON and workbook text is kept as text, so a name starting with `=` is not treated as a formula.
- Control characters are removed from Excel cells and comments.
