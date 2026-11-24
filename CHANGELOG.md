# Changelog

All notable changes to this project. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses semantic versioning.

## [1.0.1] - 2026-11-24

### Changed

- Distribution name changed to `gamesize`. PyPI rejected `game-inventory` as too similar to an existing project. The command is still `game-inventory` and the import package is still `inventory`.

## [1.0.0] - 2026-11-23

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
- Full test suite, coverage gate and lint in CI.
- `--dry-run` / `--simular`: scan and print the summary without writing the workbook, history, JSON or purging.
- `--check-data` / `--validar`: validate the JSON data files, `config.json`, stale metadata keys, invalid metadata values, repeated wishlist titles and the history, then exit without scanning or writing.
- `--strict` / `--estricto`: with `--check-data`, exit with code 1 when there are warnings.
- The data check names the stale keys and reports unknown config keys, unnormalized `hours.json` keys, normalization collisions, completed/playing titles missing from `hours.json` and games marked as completed and playing at the same time.
- The data check also reports reachable libraries, an output path inside `data/`, and repeated or future history dates.
- The data check reports metadata blocks that are not objects, non-string titles in `completed.json` or `playing.json`, and unsorted history rows, and prints the total warnings.
- The data check reports config keys with a wrong value type.
- The data check reports duplicate JSON keys and keys that normalize to an empty name.
- The data check reports the same library path configured twice.
- The data check names the library folders that do not exist and validates the source dates inside metadata entries.
- The data check reports non-text fields inside metadata entries and a malformed `_actualizado` date.
- The network user agent uses the installed package version.
- `--open` / `--abrir`: open the workbook with the default application after saving it.
- Workbook metadata (title, creator, subject, description, keywords) and landscape print setup with fit-to-width.
- The workbook marks `game-inventory` as the last modifier too.
- `tools/check_release.py`: the release workflow checks the tag, the version and both changelogs.
- The Plan sheet keeps its header visible when scrolling.
- `--report` creates the parent folders of the report path.
- The Plan sheet has an auto-filter on its header.
- The History sheet has an auto-filter on its header.
- Name normalization lives in `inventory/text.py` and is shared by `data.py` and `config.py`.
- The Summary sheet shows the generation date.
- `--top` rejects negative values.
- Help output with usage examples.
- `--top N`: print the best GB/h picks that are not completed or playing.
- `--report` / `--informe`: write a Markdown summary of the run. The number of picks follows `--top`. The report cannot be inside `data/` or overwrite the workbook.
- The report totals include completed GB, playing and games without data.
- The report path is rejected before scanning when it is a folder.
- `GAME_INVENTORY_LANG` sets the default language; `--lang` overrides it.
- Ctrl+C is caught: the command prints `Cancelled.` and exits with code 130.
- `data/config.json` can override the libraries, loose paths, exclusions and output path. `~` is expanded in every path.
- Progress lines for the folder scan and the network step.
- `tools/check_i18n.py`: fails when the English and Spanish keys or placeholders differ, or when a translation key is repeated.
- Help texts translated, so `--help` follows `--lang`.
- `docs/DATA.md` and `docs/ARCHITECTURE.md`, and `SECURITY.md`.
- `docs/EXAMPLES.md`: console, workbook and data folder examples.
- `docs/FAQ.md`: common questions about privacy, hours, libraries and errors.
- `docs/BENCHMARKS.md`: scan and workbook times for 100, 500 and 1000 games, plus the real library.
- `docs/PUBLISHING.md`: build, PyPI Trusted Publishing and the token alternative.
- `docs/PUBLISHING.md` records the PyPI name conflict with `gameinventory`.
- `tests/test_offline.py`: blocks `socket.socket` and `socket.create_connection` and proves that `--offline` never opens a socket.
- Issue forms, pull request template and EditorConfig.
- CodeQL analysis on every push and pull request, and weekly.
- Release workflow: a `v*` tag builds the wheel and sdist, checks them and publishes a GitHub release.
- `tools/check_links.py`: fails when a relative documentation link is broken.
- `tools/check_all.py`: runs pyflakes, the link check and the translation check in one command.
- Dependabot groups minor and patch updates into one pull request per ecosystem.
- CodeQL can also be started manually.
- pipx install instructions.
- Dependabot updates for pip and GitHub Actions.
- Contributing guide in English and Spanish.
- Package keywords and classifiers.

### Changed

- CI caches pip downloads, cancels superseded runs, uses read-only permissions and a 15-minute timeout.
- CI builds the wheel and sdist, checks that `data/` is not inside, installs the wheel and runs it.
- The package check rejects development tools in the wheel and requires them in the sdist.
- CI also installs the sdist and runs the installed command.
- Coverage gate raised from 97% to 98%; Windows and Ubuntu currently report 99%.
- Coverage source and the 98% gate live in `pyproject.toml`.
- The installed `game-inventory` command reads `data/` from the source checkout or the current folder. `GAME_INVENTORY_DATA` overrides it.
- README: limitations, test setup and benchmark links.
- README: example workbook screenshot with fictional games and no personal paths.

### Security

- JSON and workbook text is kept as text, so a name starting with `=` is not treated as a formula.
- Control characters are removed from Excel cells and comments.
