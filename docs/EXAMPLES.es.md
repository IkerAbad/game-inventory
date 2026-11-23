# Ejemplos

Los nombres, rutas y cifras de abajo son ilustrativos.

## Ejecución por consola

```
$ game-inventory --offline --top 3
Buscando juegos en las carpetas...
Games found: 42  |  Total: 380.12 GB
Pending hours: 512.4  |  At 4 h/day: 128 days (0.35 years)
GB/h quartiles: Bad < 0.25 | Medium < 0.60 | Good < 1.40 | PLAY NOW >= 1.40

TOP PICKS (best GB per hour):
   1. Example Game  |  2.10 GB/h  |  12 h  |  25.2 GB
   2. Another Game  |  1.80 GB/h  |  8 h  |  14.4 GB
   3. Third Game  |  1.55 GB/h  |  20 h  |  31.0 GB

OK: C:\Users\me\Desktop\Juegos\Inventario juegos GB por hora.xlsx
```

`--offline` no hace ninguna petición de red. Sin él, la herramienta completa antes las horas y notas que faltan.

## Comprobación de datos

```
$ game-inventory --check-data
COMPROBACION DE DATOS
Config: 0 ajustes en config.json
Horas: 42 juegos (0 avisos)
Completados: 3 | Jugando: 1
Wishlist: 120 titulos (0 avisos)
Claves de metadatos sin juego: horas 0 | wishlist 0
Entradas de metadatos invalidas: metacritic 0 | steam 0 | dificultad 0
Titulos de wishlist repetidos tras normalizar: 0
Historico: 8 dias, ultimo 2026-11-22 (0 filas malas)
```

Añade `--strict` para que devuelva código 1 si alguno de esos contadores no es cero.

## Informe Markdown

`--report informe.md` escribe un resumen al terminar:

```
# Inventario de juegos - 2026-11-23

- Juegos: 42
- Instalado: 380.12 GB
- Horas pendientes: 512.4 (128 dias a 4 h/dia)
- Completados: 3 juegos, 45.20 GB recuperables
- Jugando: 1
- Sin datos: 2
- Cuartiles GB/h: Malo < 0.25 | Medio < 0.60 | Bueno < 1.40 | JUGAR YA >= 1.40

## Mejores elecciones

1. **Example Game** - 2.10 GB/h, 12 h, 25.2 GB

Libro: `C:\Users\me\Desktop\Juegos\Inventario juegos GB por hora.xlsx`
```

`--dry-run` no escribe informe, porque no escribe nada.

## Libro

| Hoja | Contenido |
|---|---|
| Juegos | Una fila por juego instalado: tamaño, horas, GB por hora, veredicto, días instalado, notas, dificultad y ruta. |
| Espacio | Espacio libre y usado por unidad, y lo que ocupan los juegos. |
| Resumen | Totales, juegos completados y los días necesarios a 1, 2, 3, 4, 6 y 8 horas al día. |
| Plan | Juegos pendientes ordenados por GB por hora, con la fecha en que terminaría cada uno. |
| Historico | Una fila por día de ejecución y el gráfico de la evolución. |
| Wishlist | Títulos de la wishlist, horas, estado, notas y la comparación con el backlog instalado. |

El libro sale en inglés por defecto. `--lang es` cambia la consola y el libro, incluidos los nombres de las hojas.

## Carpeta de datos

```
data/
  config.json       opcional: bibliotecas, rutas sueltas, exclusiones y ruta de salida
  hours.json        horas, Metacritic, Steam, dificultad y notas por juego
  wishlist.json     títulos de la wishlist con horas y notas
  completed.json    juegos terminados que siguen instalados
  playing.json      juegos que estás jugando ahora
  history.csv       una fila por día de ejecución
  NOTES.md          notas personales y fuentes
```

Todo lo de `data/` es personal y está ignorado por git. El formato exacto está en [DATA.es.md](DATA.es.md).
