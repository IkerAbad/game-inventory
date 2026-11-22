# Changelog

All notable changes to this project. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses semantic versioning.

## [Unreleased]

### Added

- `--dry-run` / `--simular`: scan and print the summary without writing the workbook, history, JSON or purging.
- `--check-data` / `--validar`: validate the JSON data files, `config.json`, stale metadata keys, invalid metadata values, repeated wishlist titles and the history, then exit without scanning or writing.
- `--open` / `--abrir`: open the workbook with the default application after saving it.
- Help output with usage examples.
- Ctrl+C is caught: the command prints `Cancelled.` and exits with code 130.
- `data/config.json` can override the libraries, loose paths, exclusions and output path. `~` is expanded in every path.
- Progress lines for the folder scan and the network step.
- `tools/check_i18n.py`: fails when the English and Spanish keys or placeholders differ, or when a translation key is repeated.
- Help texts translated, so `--help` follows `--lang`.
- `docs/DATA.md` and `docs/ARCHITECTURE.md`, and `SECURITY.md`.
- Issue forms, pull request template and EditorConfig.
- CodeQL analysis on every push and pull request, and weekly.
- Release workflow: a `v*` tag builds the wheel and sdist, checks them and publishes a GitHub release.
- `tools/check_links.py`: fails when a relative documentation link is broken.
- pipx install instructions.
- Dependabot updates for pip and GitHub Actions.
- Contributing guide in English and Spanish.
- Package keywords and classifiers.

### Changed

- CI caches pip downloads, cancels superseded runs, uses read-only permissions and a 15-minute timeout.
- CI builds the wheel and sdist, checks that `data/` is not inside, installs the wheel and runs it.
- CI also installs the sdist and runs the installed command.
- Coverage gate raised from 97% to 98%; Windows and Ubuntu currently report 99%.
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
