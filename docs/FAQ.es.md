# Preguntas frecuentes

## ¿Sube mis datos a algún sitio?

No. Solo hace peticiones GET de lectura a las fuentes de [SECURITY.es.md](../SECURITY.es.md), y solo con la red activada. `--offline` no hace ninguna petición. Todo lo personal vive en `data/`, que está ignorado por git.

## ¿Por qué el inglés es el idioma por defecto?

El proyecto es público. Usa `--lang es`, o fija `GAME_INVENTORY_LANG=es` una vez, para tener la consola y el libro en español.

## ¿Dónde están mis ficheros?

`data/` contiene los JSON, el histórico y tus notas, además de un `config.json` opcional. El libro va a la ruta que se muestra al final de la ejecución. Ver [DATA.es.md](DATA.es.md).

## ¿Cómo se calculan las horas?

Las horas de historia principal salen de Deku Deals, twoaveragegamers o una estimación con reseñas de Steam. `null` significa que el juego no tiene final; `"?"` que todavía no hay dato. Las notas `PRENSA` y `ESTIMACION` indican de dónde sale cada cifra.

## Un juego sale SIN DATOS. ¿Qué hago?

Ejecuta `game-inventory --check-data`. Si la clave existe pero está a `?`, añade las horas en `hours.json`. Si falta la clave, el nombre de la carpeta y la clave del JSON no coinciden tras normalizar.

## ¿Cómo añado otra biblioteca?

Añade su carpeta a `libraries` o `loose_paths` en `data/config.json`. Una carpeta de `libraries` contiene una subcarpeta por juego; una entrada de `loose_paths` es un solo juego. `~` se expande.

## ¿Por qué no escribe el libro?

El Excel está abierto en otro programa, la ruta está dentro de `data/` o hay otra ejecución con el bloqueo. Cierra el libro y espera a la otra ejecución.

## ¿Se puede instalar sin tocar el Python global?

Sí, con `pipx install .` desde el checkout. Ver la sección de instalación del README.

## ¿Cómo saco un resumen de texto?

Ejecuta con `--report informe.md`. Escribe un resumen Markdown con los totales, las mejores elecciones, los completados, los juegos en curso, el delta del histórico y los contadores de la wishlist. El número de elecciones sigue a `--top`, o cinco por defecto. `--dry-run` no escribe informe.
