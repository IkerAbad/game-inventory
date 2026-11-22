# Contributing

English | [Español](CONTRIBUTING.es.md)

## Setup

```
git clone https://github.com/IkerAbad/game-inventory.git
cd game-inventory
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements-dev.txt
py -m pip install -e .
```

## Checks

```
py -m pyflakes inventory generate_inventory.py tests
py -m coverage run --source=inventory -m unittest discover -s tests -v
py -m coverage report -m
```

The CI fails below 97% coverage.

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
