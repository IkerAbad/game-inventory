# Arquitectura

La herramienta es un programa local de consola. Lee los juegos instalados, completa horas y notas, calcula los veredictos del backlog y escribe un único Excel.

## Flujo

1. `cli.main` lee las opciones, fija el idioma y toma el bloqueo de datos.
2. `data` carga `hours.json`, `wishlist.json`, `completed.json` y `playing.json`.
3. `scan` recorre las bibliotecas configuradas y mide cada carpeta de juego.
4. `network.autocomplete` rellena horas y notas si la red está activada.
5. `cli` cruza ambos lados y calcula GB/hora, cuartiles y veredictos.
6. `excel` construye el libro, actualiza `history.csv` y guarda de forma atómica.
7. `data.purge_hours` quita claves sin carpeta, salvo `--keep` o que el freno lo impida.
8. `cli` escribe opcionalmente un resumen Markdown con `--report`.

## Módulos

| Módulo | Responsabilidad |
|---|---|
| `config.py` | Bibliotecas, carpeta de datos, ruta de salida y límites de red. `data/config.json` los sustituye. |
| `text.py` | Normalización de nombres compartida. |
| `data.py` | Lectura y escritura de JSON, escritura atómica, bloqueo, purga y copias. |
| `scan.py` | Tamaño de carpeta, días instalado, duplicados y comprobación del Excel. |
| `network.py` | Peticiones y casado de Deku Deals, twoaveragegamers, Steam y Metacritic. |
| `cell_format.py` | Celdas y comentarios de Metacritic, Steam y dificultad. |
| `excel.py` | Hojas, estilos, gráficos, histórico y comparativa de wishlist. |
| `i18n.py` | Textos en inglés y español. |
| `cli.py` | Opciones, orquestación, resumen por consola y simulación. |

## Puntos de entrada

- `generate_inventory.py`: script directo.
- `py -m inventory`: módulo.
- `game-inventory`: comando instalado.
- `start.cmd`: lanzador de Windows con registro en `data/last_run.log`.

## Garantías

- Una sola ejecución a la vez, con bloqueo del sistema.
- Escrituras atómicas de JSON, histórico y libro.
- Un JSON roto aborta antes de escribir.
- La purga se niega si falta una unidad, no se puede leer o borraría más de la mitad.
- El texto del Excel se escribe como texto, nunca como fórmula.
- Ctrl+C sale con código 130 y el libro es el anterior o el nuevo, nunca uno a medias.
- Los datos personales viven en `data/` y no se versionan.

## Pruebas

`tests/` cubre los módulos con pruebas unitarias, respuestas HTTP simuladas, un `main` de extremo a extremo con datos falsos y los caminos de aborto. El CI instala el paquete, ejecuta el comando de consola, prueba el lanzador en Windows, pasa pyflakes y exige al menos un 98% de cobertura. Ver `CHANGELOG.es.md` y `CONTRIBUTING.es.md`.
