# Publicación

## Construir y comprobar

```
py -m build
py tools/check_dist.py
py -m twine check dist/*
```

La construcción genera `dist/game_inventory-1.0.0-py3-none-any.whl` y `dist/game_inventory-1.0.0.tar.gz`. La comprobación del paquete rechaza `data/` y las herramientas de desarrollo en el wheel.

## PyPI con Trusted Publishing

`.github/workflows/pypi.yml` publica con OIDC, así que no hay ningún token guardado en el repositorio. Antes de la primera subida, añade un publicador pendiente en <https://pypi.org/manage/account/publishing/> con estos valores exactos:

- Nombre del proyecto en PyPI: `game-inventory`
- Propietario: `IkerAbad`
- Repositorio: `game-inventory`
- Nombre del workflow: `pypi.yml`
- Entorno: `pypi`

Después publica una release de GitHub o lanza el workflow a mano. Sin el publicador pendiente, la acción falla con `invalid-publisher`; no usa un token como respaldo.

## Alternativa con token

Twine también funciona con un token de API de PyPI:

```
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-..."
py -m twine upload dist/*
```

No hagas commit del token. En Linux o macOS usa `export` en vez de `$env:`.

## Ficheros de la release

El flujo de Release adjunta el wheel y el sdist a la release de GitHub. Son los mismos ficheros que se suben a PyPI.
