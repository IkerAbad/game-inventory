# Inventario de juegos

[![CI](https://github.com/IkerAbad/game-inventory/actions/workflows/ci.yml/badge.svg)](https://github.com/IkerAbad/game-inventory/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://github.com/IkerAbad/game-inventory/blob/main/pyproject.toml)
[![Licencia MIT](https://img.shields.io/badge/licencia-MIT-blue.svg)](LICENSE)

[English](README.md) | Español

Escanea las carpetas donde tienes juegos instalados, cruza el tamaño en disco con las horas de la historia principal y genera un Excel con el ratio GB por hora, un plan de borrado, el histórico y la wishlist. La consola y el libro están disponibles en inglés y en español.

## Qué hace

- Escanea las unidades y carpetas configuradas en `inventory/config.py` y mide cada juego en disco.
- Completa por red las horas que falten (Deku Deals, twoaveragegamers y una estimación con reseñas de Steam), el Metascore y, si no hay Metascore, el porcentaje de reseñas positivas de Steam.
- Purga de `hours.json` las claves de juegos que ya no están instalados, solo si están todas las unidades.
- Genera el Excel con hasta seis hojas: Juegos, Espacio, Resumen, Plan, Historico y Wishlist.

## Requisitos

- Python 3.12 o superior.
- `openpyxl` (está en `requirements.txt`).

## Instalar como paquete

```
py -m pip install .
game-inventory --lang es
```

Los comandos directos de abajo también funcionan sin instalar. Instalado, `data/` se lee de la carpeta actual salvo que `GAME_INVENTORY_DATA` apunte a otra.

O como comando aislado con [pipx](https://pipx.pypa.io):

```
pipx install .
game-inventory --version
```

## Uso

```
cd C:\Dev\game-inventory
py -m pip install -r requirements.txt
py generate_inventory.py
```

También funciona como módulo, desde la misma carpeta:

```
py -m inventory
```

O con doble clic en `start.cmd`. Guarda la salida en `data/last_run.log` y deja la ventana abierta si hay un error.

Opciones:

| Opción | Qué hace |
|---|---|
| `--lang en\|es` | Idioma de la consola y del libro. Por defecto: `en`. |
| `--offline`, `--sin-red` | No consulta internet. |
| `--keep`, `--conservar` | No purga las claves de juegos desinstalados. |
| `--force-purge`, `--forzar-purga` | Permite purgar más de la mitad de las claves de una vez. |
| `--dry-run`, `--simular` | Escanea y muestra el resumen sin escribir nada. |
| `--open` | Abre el libro guardado con la aplicación predeterminada. |
| `--check-data`, `--validar` | Valida los ficheros JSON, las claves de metadatos huérfanas, los valores de metadatos inválidos, los títulos repetidos de la wishlist y el histórico, y sale. |
| `--output RUTA`, `--salida RUTA` | Escribe el Excel en otra ruta. |
| `--version` | Muestra la versión instalada. |

El Excel sale por defecto a `%USERPROFILE%\Desktop\Juegos\Inventario juegos GB por hora.xlsx` y deja una copia `.bak.xlsx` de la ejecución anterior. Se mantiene el nombre español para actualizar el libro que ya existe. Ciérralo antes de ejecutar, si está abierto el script aborta sin escanear nada.

## Datos

Todo lo personal vive en `data/`, que no se versiona. El script crea la carpeta si no existe.

| Fichero | Contenido |
|---|---|
| `data/hours.json` | Horas de historia principal por clave normalizada. `null` = sin final. Sus bloques `_metacritic`, `_steam`, `_dificultad` y `_notas` guardan las notas. |
| `data/wishlist.json` | Títulos de la wishlist con horas, notas, Metacritic, Steam y dificultad. |
| `data/playing.json` | Claves de lo que estás jugando ahora. |
| `data/completed.json` | Claves de lo que ya has terminado y sigue instalado. |
| `data/history.csv` | Una fila por día de ejecución. Alimenta la hoja History. |
| `data/config.json` | Opcional. Sustituye bibliotecas, rutas sueltas, exclusiones y ruta de salida. |

Las notas de fuentes dentro de los JSON conservan el idioma en que se escribieron.

## Robustez

- Un error de sintaxis en un JSON aborta, indica la línea y la columna, y no escribe nada.
- Las horas que no sean números positivos, `null` o `"?"` se tratan como sin datos y se avisan.
- Los JSON, el histórico y el Excel se escriben en un temporal y se renombran, así un fallo a mitad no deja ficheros corruptos.
- La purga guarda `hours.json.bak` y se niega a borrar más de la mitad de las claves sin `--force-purge`.
- Si el histórico no se puede leer o tiene filas rotas, el original se guarda como `history.csv.corrupto`.
- Si el Excel está abierto, aborta antes de escanear.
- Solo puede haber una ejecución a la vez, con un bloqueo en `data/`.
- Acepta JSON con BOM y descarta filas corruptas del histórico con un aviso.

- `--dry-run` escanea y muestra el resumen, pero no escribe libro, histórico ni JSON.

## Problemas frecuentes

| Síntoma | Qué hacer |
|---|---|
| `ABORTADO: el Excel está abierto` | Cierra el libro y vuelve a ejecutar. No se ha escaneado nada. |
| `ABORTADO: hay otra ejecución en curso` | Espera a la otra ejecución. El bloqueo vive en `data/`. |
| `no es JSON válido (línea ..., columna ...)` | Corrige esa línea o restaura una copia del fichero. |
| `Aviso: no se puede leer history.csv` | El original queda como `history.csv.corrupto` y la ejecución escribe uno limpio. |
| Falta un juego | Añade su carpeta a `libraries` o `loose_paths` en `data/config.json`. |
| Todos los juegos salen SIN DATOS | Falta `hours.json` o sus claves no coinciden con las carpetas. Ejecuta `--check-data`. |

## Estructura

```
generate_inventory.py      punto de entrada
pyproject.toml             metadatos del paquete y comando de consola
CHANGELOG.es.md            registro de cambios en español
CONTRIBUTING.es.md         guía de contribución en español
SECURITY.es.md             política de seguridad en español
docs/
  DATA.es.md               formatos de datos y copias
  ARCHITECTURE.es.md       flujo, módulos y garantías
tools/
  check_dist.py            comprueba el contenido del wheel y del sdist
  check_links.py           comprueba los enlaces relativos de la documentación
inventory/
  config.py                unidades, rutas y ajustes de red
  data.py                  JSON: carga, formato y escritura segura
  scan.py                  tamaño, días instalado y bloqueo del Excel
  cell_format.py           celdas: Metacritic, Steam y dificultad
  excel.py                 hojas, estilos, gráficos y comparativas
  network.py               autocompletado por red
  i18n.py                  textos en inglés y español
  cli.py                   opciones, orquestación y resumen por consola
tests/                     pruebas unitarias y de extremo a extremo
start.cmd                  lanzador de Windows
```

## Pruebas

```
py -m pip install -r requirements-dev.txt
py -m coverage run --source=inventory -m unittest discover -s tests -v
py -m coverage report -m
py -m pyflakes inventory generate_inventory.py tests
```

El CI falla por debajo del 97% de cobertura.

## Documentación

`README.md` es la versión inglesa. Las notas personales con fuentes y decisiones viven en `data/NOTES.md`, que no se versiona.

- [Changelog](CHANGELOG.md) / [Registro de cambios](CHANGELOG.es.md)
- [Contributing](CONTRIBUTING.md) / [Contribuir](CONTRIBUTING.es.md)
- [Data formats](docs/DATA.md) / [Formatos de datos](docs/DATA.es.md)
- [Architecture](docs/ARCHITECTURE.md) / [Arquitectura](docs/ARCHITECTURE.es.md)
- [Security](SECURITY.md) / [Seguridad](SECURITY.es.md)

## Licencia

MIT. Ver `LICENSE`.
