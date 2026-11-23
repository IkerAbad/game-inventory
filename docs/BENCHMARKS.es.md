# Rendimiento

Medido el 2026-11-23 en el equipo de desarrollo:

- AMD Ryzen 9 5900X, 12 núcleos / 24 hilos.
- 31,9 GiB de RAM (32 GB DDR4-3600 CL16).
- Windows 11 Pro 10.0.26300.
- Python 3.14.5.
- Disco C: local. Red desactivada con `--offline`.

## Método

- Bibliotecas sintéticas en `%TEMP%`: una carpeta por juego y un fichero de 1 KB por carpeta.
- Tres ejecuciones por tamaño; se muestra la mediana.
- `Escaneo` es `inventory.scan.scan_games`.
- `Construcción` es `inventory.excel.build_workbook` con las seis hojas y los gráficos.
- `Guardado` es la escritura del `.xlsx` con `openpyxl`.
- `Construcción + guardado` es el tiempo de publicación del libro.
- `CLI completa` es `python -m inventory --offline --keep --output`, con escaneo, análisis, libro e histórico.

## Bibliotecas sintéticas

| Juegos | Escaneo (s) | Construcción (s) | Guardado (s) | Construcción + guardado (s) | CLI completa (s) |
|---:|---:|---:|---:|---:|---:|
| 100 | 0,018 | 0,426 | 0,108 | 0,534 | 1,125 |
| 500 | 0,085 | 1,956 | 0,180 | 2,136 | 1,450 |
| 1000 | 0,105 | 1,881 | 0,219 | 2,100 | 2,639 |

El escaneo sintético es un límite inferior: cada juego tiene un solo fichero, mientras que una carpeta real contiene cientos o miles. El escaneo solo lee metadatos, no el contenido.

## Biblioteca real

136 juegos instalados, 1.323,49 GB, con las bibliotecas configuradas en C:, D:, E: y F:.

| Medición | Tiempo |
|---|---:|
| Escaneo y análisis (`--dry-run`, en caliente) | 6,278 s |
| CLI completa (`--offline --keep`, en caliente) | 8,457 s |
| Publicación del libro (completa menos dry run) | unos 2,18 s |
| Primer `--dry-run` en frío | 23,167 s |

La primera ejecución pagó los metadatos fríos y el antivirus. Las ejecuciones en caliente son las comparables con la tabla sintética.

## Límites

- El número de ficheros, la velocidad del disco, el antivirus y el sistema de ficheros cambian el escaneo.
- El tiempo del libro depende del número de filas, de los gráficos y de la versión de la librería de Excel.
- Son tiempos de guardado local. Imprimir, subir o abrir el libro no se mide.
- Son medianas de ejecuciones reales, no una garantía para otro equipo.
