# Inventario de juegos

[![CI](https://github.com/IkerAbad/inventario-juegos/actions/workflows/ci.yml/badge.svg)](https://github.com/IkerAbad/inventario-juegos/actions/workflows/ci.yml)
[![Licencia MIT](https://img.shields.io/badge/licencia-MIT-blue.svg)](LICENSE)

Escanea las carpetas donde tienes juegos instalados, cruza el tamaño en disco con las horas de la historia principal y genera un Excel con el ratio GB por hora, un plan de borrado, el histórico y la wishlist.

## Qué hace

- Escanea las unidades y carpetas configuradas en `inventario/config.py` y mide cada juego en disco.
- Completa por red las horas que falten (Deku Deals, twoaveragegamers y una estimación con reseñas de Steam), el Metascore y, si no hay Metascore, el porcentaje de reseñas positivas de Steam.
- Purga de `horas.json` las claves de juegos que ya no están instalados, solo si están todas las unidades.
- Genera el Excel con las hojas Juegos, Espacio, Resumen, Plan, Historico y, si hay wishlist, Wishlist.

## Requisitos

- Python 3.12 o superior.
- `openpyxl` (está en `requirements.txt`).

## Uso

```
cd C:\Dev\inventario-juegos
py -m pip install -r requirements.txt
py generar_inventario.py
```

También funciona como módulo, desde la misma carpeta:

```
py -m inventario
```

Opciones:

| Opción | Qué hace |
|---|---|
| `--sin-red` | No consulta internet. |
| `--conservar` | No purga las claves de juegos desinstalados. |
| `--forzar-purga` | Permite purgar más de la mitad de las claves de una vez. |
| `--salida RUTA` | Escribe el Excel en otra ruta. |

El Excel sale por defecto a `%USERPROFILE%\Desktop\Juegos\Inventario juegos GB por hora.xlsx` y deja una copia `.bak.xlsx` de la ejecución anterior. Ciérralo antes de ejecutar: si está abierto, el script aborta sin escanear nada.

## Datos

Todo lo personal vive en `datos/`, que no se versiona. El script crea la carpeta si no existe y lee de ahí.

| Fichero | Contenido |
|---|---|
| `datos/horas.json` | Horas de historia principal por clave normalizada. `null` = sin final. Sus bloques `_metacritic`, `_steam`, `_dificultad` y `_notas` guardan las notas. |
| `datos/wishlist.json` | Títulos de la wishlist con horas, notas, Metacritic, Steam y dificultad. |
| `datos/jugando.json` | Claves de lo que estás jugando ahora. |
| `datos/completados.json` | Claves de lo que ya has terminado y sigue instalado. |
| `datos/historico.csv` | Una fila por día de ejecución. Alimenta la hoja Historico. |

## Robustez

- Si un JSON tiene un error de sintaxis, el script aborta, indica la línea y la columna, y no escribe nada.
- Los valores de horas que no sean números positivos, `null` o `"?"` se tratan como sin datos y se avisan.
- Antes de purgar, `horas.json` se copia a `horas.json.bak`.
- La purga se niega si borraría más de la mitad de las claves. Para hacerlo igual, `--forzar-purga`.
- Si el histórico no se puede leer o tiene filas rotas, el original se guarda como `historico.csv.corrupto`.
- Los JSON, el histórico y el Excel se escriben en un temporal y se renombran: un fallo a mitad no deja ficheros corruptos.
- Si el Excel está abierto, aborta antes de escanear.
- Solo puede haber una ejecución a la vez: un bloqueo en `datos/` impide dos procesos simultáneos.
- Acepta JSON con BOM y descarta filas corruptas del histórico con un aviso.

## Estructura

```
generar_inventario.py      punto de entrada
inventario/
  config.py                unidades, rutas y ajustes de red
  datos.py                 JSON: carga, formato y escritura segura
  escaneo.py               tamaño, días instalado y bloqueo del Excel
  formato.py               celdas: Metacritic, Steam y dificultad
  excel.py                 hojas, estilos, gráficos y comparativas
  red.py                   autocompletado por red
  cli.py                   opciones, orquestación y resumen por consola
pruebas/                   pruebas unitarias
datos/                     JSON, CSV y LEEME (no versionado)
```

## Pruebas

```
py -m unittest discover -s pruebas -v
```

## Documentación

El `LEEME.md` de la carpeta `datos/` explica el método, las fuentes, los valores dudosos y el historial de decisiones. No se versiona.

## Licencia

MIT. Ver `LICENSE`.
