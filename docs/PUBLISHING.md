# Publishing

## Project name

`game-inventory` is not accepted by PyPI: the upload returns `400 The name 'game-inventory' is too similar to an existing project`. The existing project is `gameinventory` (0.1.1). A different distribution name is required before the first upload. The import package (`inventory`) and the console command (`game-inventory`) can stay the same.

## Build and check

```
py -m build
py tools/check_dist.py
py -m twine check dist/*
```

The build produces `dist/game_inventory-1.0.0-py3-none-any.whl` and `dist/game_inventory-1.0.0.tar.gz`. The package check rejects `data/` and development tools in the wheel.

## PyPI with Trusted Publishing

`.github/workflows/pypi.yml` publishes with OIDC, so no token is stored in the repository. Before the first upload, add a pending publisher at <https://pypi.org/manage/account/publishing/> with these exact values:

- PyPI project name: `game-inventory`
- Owner: `IkerAbad`
- Repository: `game-inventory`
- Workflow name: `pypi.yml`
- Environment: `pypi`

Then run the `PyPI` workflow manually from the Actions tab after the pending publisher is saved. Without the pending publisher the action fails with `invalid-publisher`; it does not fall back to a token.

## Token alternative

Twine also works with a PyPI API token:

```
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-..."
py -m twine upload dist/*
```

Do not commit the token. On Linux or macOS use `export` instead of `$env:`.

## Release assets

The Release workflow attaches the wheel and the sdist to the GitHub release. They are the same files that are uploaded to PyPI.
