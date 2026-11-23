# Publicación

## Nombre del proyecto

PyPI no acepta `game-inventory`: la subida devuelve `400 The name 'game-inventory' is too similar to an existing project`. El proyecto existente es `gameinventory` (0.1.1). Hace falta otro nombre de distribución antes de la primera subida. El paquete que se importa (`inventory`) y el comando de consola (`game-inventory`) pueden seguir igual.

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

Después lanza el workflow `PyPI` a mano desde la pestaña Actions cuando el publicador pendiente esté guardado. Sin el publicador pendiente, la acción falla con `invalid-publisher`; no usa un token como respaldo.

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
