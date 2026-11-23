# Contribuir

[English](CONTRIBUTING.md) | Español

## Preparación

```
git clone https://github.com/IkerAbad/game-inventory.git
cd game-inventory
py -m venv .venv
.venv\Scripts\activate
py -m pip install -e ".[dev]"
```

`requirements-dev.txt` contiene las mismas herramientas para el CI.

## Comprobaciones

```
py tools/check_all.py
py -m coverage run -m unittest discover -s tests -v
py -m coverage report
```

`check_all.py` ejecuta pyflakes, la comprobación de enlaces de la documentación y la de traducciones.

El CI falla por debajo del 98% de cobertura.

## Código

- Python 3.12 o superior.
- Identificadores, comentarios y docstrings en inglés.
- Los textos de interfaz van en `inventory/i18n.py`, con inglés y español.
- Añade o actualiza pruebas con cada cambio de comportamiento.
- No subas nada de `data/`. Contiene datos personales y está ignorado.

## Documentación

- `README.md` y `README.es.md` deben ir en paralelo.
- `CHANGELOG.md` y `CHANGELOG.es.md` deben ir en paralelo.
- Cada opción nueva necesita una fila en las dos tablas del README.

## Pull requests

Ejecuta las comprobaciones y mantén el cambio acotado. Indica en el changelog los cambios de comportamiento, las opciones nuevas y los cambios de formato de datos.

## Publicación

1. Fija la versión nueva en `inventory/__init__.py` y mueve las entradas del changelog de `Sin publicar` a esa versión, en los dos idiomas.
2. Haz commit, crea la etiqueta y súbela: `git tag v1.0.1` y `git push --tags`.
3. El flujo de Release comprueba que la etiqueta coincide con la versión y que los dos changelogs tienen una sección para ella, construye el wheel y el sdist, los revisa y abre una release de GitHub con las notas. PyPI usa Trusted Publishing y se publica desde el workflow `PyPI` cuando el publicador pendiente está configurado; ver [docs/PUBLISHING.es.md](docs/PUBLISHING.es.md).

CodeQL se ejecuta en cada push, en cada pull request y una vez a la semana.
