# Ficheros de datos

Todo lo personal vive en `data/`, que no se versiona. El script crea la carpeta si no existe. El comando instalado lee `data/` del checkout o de la carpeta actual. `GAME_INVENTORY_DATA` apunta a otra carpeta.

## hours.json

Una entrada por juego instalado. La clave es el nombre de carpeta normalizado.

```json
{
  "_comentario": "nota opcional",
  "hades": 21.0,
  "a short hike": 1.5,
  "factorio": null,
  "_metacritic": {"hades": {"s": 93, "p": "PC", "n": 45}},
  "_steam": {"hades": {"id": 1145360, "name": "Hades", "n": 250000, "pct": 98, "desc": "Overwhelmingly Positive"}},
  "_dificultad": {"hades": {"h": 6, "c": 5, "ct": "consenso", "src": "Steam tags"}},
  "_notas": {"hades": "HLTB Main Story 21 h (Deku Deals, 22/11/2026)."}
}
```

- Número: horas de historia principal. `null`: sin final (sandbox, servicio, roguelike). `"?"`: sin dato todavía.
- `_comentario`: texto opcional.
- `_metacritic`: `s` es el Metascore, `"s/n"` cuando Metacritic no publica ninguno, `null` cuando se desconoce. `p` es la plataforma, `n` el número de reseñas y `f` la fecha de consulta (`YYYY-MM-DD`).
- `_steam`: nota de respaldo cuando no hay Metascore numérico. `pct` es el porcentaje de reseñas positivas y `f` la fecha de consulta (`YYYY-MM-DD`).
- `_dificultad`: `h` habilidad y `c` complejidad, de 0 a 10. `ct` es `source` (o `fuente`), `consenso` o `inferencia`.
- `_notas`: fuentes y decisiones. Los bloques `_` desconocidos se conservan.

## wishlist.json

```json
{
  "_usuario": "usuario de Backloggd",
  "_fuente_horas": "descripción de la fuente",
  "_actualizado": "2026-11-22",
  "juegos": {
    "Hades II": 25.0,
    "Signalis": "?",
    "Factorio": null
  },
  "_notas": {"Signalis": "SIN DATO"},
  "_metacritic": {},
  "_steam": {},
  "_dificultad": {}
}
```

- `juegos`: título a horas. Las mismas reglas de número, `null` y `"?"` que en `hours.json`.
- `_actualizado`: fecha en `YYYY-MM-DD`. La comprobación de datos rechaza otros formatos.
- Prefijos de `_notas` que usa el código: `PRENSA`, `ESTIMACION`, `EDICION DUPLICADA`, `YA JUGADO`, `SIN DATO`, `DECISION`.

## completed.json y playing.json

Listas JSON de títulos:

```json
["Hades", "A Short Hike"]
```

Las entradas que empiezan por `_` se ignoran. Un juego en las dos listas se trata como completado. Cualquier entrada que no sea texto se rechaza.

## history.csv

Una fila por día de ejecución:

```csv
date,games,gb,hours
2026-11-16,132,1243.47,1745.3
```

La cabecera antigua `fecha,juegos,gb,horas` sigue aceptándose. Las filas rotas se descartan con un aviso y el original se guarda como `history.csv.corrupto`.

## config.json

Opcional. Sustituye los valores por defecto de `inventory/config.py`:

```json
{
  "libraries": ["D:/Games", "E:/SteamLibrary/steamapps/common"],
  "loose_paths": ["C:/Program Files/Game"],
  "exclude": ["steamworks shared", "emuladores"],
  "output": "C:/Users/me/Desktop/Games.xlsx"
}
```

- `libraries`: carpetas cuyas subcarpetas son juegos. Una ruta repetida se avisa con `--check-data`.
- `loose_paths`: un juego por carpeta.
- `exclude`: nombres de carpeta que se saltan. No distingue mayúsculas ni puntuación.
- `output`: ruta del libro; `~` se expande.

Una clave ausente o inválida mantiene el valor por defecto. `~` se expande en todas las rutas. El fichero vive en `data/` y no se versiona.

## Escrituras y copias

- JSON, histórico y libro se escriben en un temporal y se renombran.
- Una purga guarda `hours.json.bak`.
- Un histórico roto guarda `history.csv.corrupto`.
- `data/` está ignorado por git. No lo subas.

`--check-data` informa de claves repetidas dentro del mismo objeto JSON, porque al leer el fichero gana la última. También informa de claves que quedan vacías al normalizar.

## Idioma

Las notas de fuentes conservan el idioma en que se escribieron. Los textos de interfaz salen de `inventory/i18n.py` y cambian con `--lang`.
