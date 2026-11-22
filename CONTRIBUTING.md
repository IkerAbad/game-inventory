# Contributing

English | [Español](CONTRIBUTING.es.md)

## Setup

```
git clone https://github.com/IkerAbad/game-inventory.git
cd game-inventory
py -m venv .venv
.venv\Scripts\activate
py -m pip install -e ".[dev]"
```

`requirements-dev.txt` holds the same tools for the CI.

## Checks

```
py tools/check_all.py
py -m coverage run --source=inventory -m unittest discover -s tests -v
py -m coverage report -m
```

`check_all.py` runs pyflakes, the documentation link check and the translation check.

The CI fails below 98% coverage.

## Code

- Python 3.12 or newer.
- Identifiers, comments and docstrings in English.
- User-facing strings go in `inventory/i18n.py` with both English and Spanish versions.
- Add or update tests for every behaviour change.
- Do not commit anything from `data/`. It holds personal data and is ignored.

## Docs

- `README.md` and `README.es.md` must stay in sync.
- `CHANGELOG.md` and `CHANGELOG.es.md` must stay in sync.
- New options need a row in both README tables.

## Pull requests

Run the checks above and keep the change focused. Mention behaviour changes, new options and data format changes in the changelog.

## Release

1. Set the new version in `inventory/__init__.py` and move the changelog entries from `Unreleased` to that version, in both languages.
2. Commit, then create and push the tag: `git tag v1.0.1` and `git push --tags`.
3. The Release workflow checks that the tag matches the version, builds the wheel and the sdist, checks them and opens a GitHub release with the notes.

CodeQL runs on every push and pull request, and once a week.
