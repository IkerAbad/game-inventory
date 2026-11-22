# Contribuir

[English](CONTRIBUTING.md) | Español

## Preparación

```
git clone https://github.com/IkerAbad/game-inventory.git
cd game-inventory
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements-dev.txt
py -m pip install -e .
```

## Comprobaciones

```
py -m pyflakes inventory generate_inventory.py tests
py -m coverage run --source=inventory -m unittest discover -s tests -v
py -m coverage report -m
```

El CI falla por debajo del 97% de cobertura.

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
