# Registro de cambios

Cambios destacados del proyecto. El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa versionado semántico.

## [1.0.0] - 2026-11-23

### Añadido

- Escaneo de todas las bibliotecas configuradas, con tamaño en GB y días instalado.
- Horas de Deku Deals, twoaveragegamers, estimación con reseñas de Steam, Metascore y porcentaje de reseñas de Steam.
- Excel con las hojas Games, Space, Summary, Plan, History y Wishlist.
- Salida en inglés y español con `--lang en|es`.
- Escritura atómica de JSON, histórico y libro.
- Bloqueo exclusivo para que no se solapen dos ejecuciones.
- Copia antes de purgar y copia `.corrupto` del histórico roto.
- Freno de purga que se niega a borrar más de la mitad de las claves sin `--force-purge`.
- Paquete instalable con el comando `game-inventory`.
- Suite completa de pruebas, umbral de cobertura y lint en CI.
- `--dry-run` / `--simular`: escanea y muestra el resumen sin escribir el libro, el histórico, los JSON ni purgar.
- `--check-data` / `--validar`: valida los ficheros JSON, `config.json`, las claves de metadatos huérfanas, los valores de metadatos inválidos, los títulos repetidos de la wishlist y el histórico, y sale sin escanear ni escribir.
- `--strict` / `--estricto`: con `--check-data`, sale con código 1 si hay avisos.
- La comprobación de datos nombra las claves huérfanas e informa de claves desconocidas en la configuración, claves sin normalizar en `hours.json`, choques al normalizar, títulos de completados/jugando que no están en `hours.json` y juegos marcados como completados y jugando a la vez.
- La comprobación de datos también informa de bibliotecas accesibles, una salida dentro de `data/` y fechas del histórico repetidas o futuras.
- La comprobación de datos informa de bloques de metadatos que no son objetos, títulos que no son texto en `completed.json` o `playing.json` y filas del histórico sin ordenar, y muestra el total de avisos.
- La comprobación de datos informa de claves de configuración con tipo incorrecto.
- La comprobación de datos informa de claves JSON repetidas y de claves que quedan vacías al normalizar.
- La comprobación de datos informa de una misma ruta de biblioteca configurada dos veces.
- La comprobación de datos nombra las carpetas de biblioteca que no existen y valida las fechas de origen dentro de los metadatos.
- La comprobación de datos informa de campos que no son texto dentro de los metadatos y de una fecha `_actualizado` mal formada.
- El user agent de red usa la versión instalada del paquete.
- `--open` / `--abrir`: abre el libro con la aplicación predeterminada al guardarlo.
- Ayuda con ejemplos de uso.
- `--top N`: muestra los mejores GB/h que no estén completados ni en curso.
- `--report` / `--informe`: escribe un resumen Markdown de la ejecución. El número de elecciones sigue a `--top`. El informe no puede estar dentro de `data/` ni sobrescribir el libro.
- Los totales del informe incluyen los GB completados, los juegos en curso y los que no tienen datos.
- La ruta del informe se rechaza antes de escanear si es una carpeta.
- `GAME_INVENTORY_LANG` fija el idioma por defecto; `--lang` tiene prioridad.
- Ctrl+C se captura: el comando muestra `Cancelado.` y sale con código 130.
- Metadatos del libro (título, autor, asunto, descripción y palabras clave) y configuración de impresión horizontal ajustada al ancho.
- El libro marca `game-inventory` también como último modificador.
- `tools/check_release.py`: el flujo de release comprueba la etiqueta, la versión y los dos changelogs.
- La hoja Plan mantiene la cabecera visible al desplazarse.
- La hoja Plan tiene filtro automático en la cabecera.
- `--report` crea las carpetas necesarias para la ruta del informe.
- La hoja Historico tiene filtro automático en la cabecera.
- La normalización de nombres vive en `inventory/text.py` y la comparten `data.py` y `config.py`.
- La hoja Resumen muestra la fecha de generación.
- `--top` rechaza valores negativos.
- `data/config.json` puede sustituir bibliotecas, rutas sueltas, exclusiones y ruta de salida. `~` se expande en todas las rutas.
- Avisos de progreso para el escaneo de carpetas y el paso de red.
- `tools/check_i18n.py`: falla si las claves o los marcadores de inglés y español difieren, o si una clave de traducción está repetida.
- Textos de ayuda traducidos, así que `--help` sigue a `--lang`.
- `docs/DATA.es.md`, `docs/ARCHITECTURE.es.md` y `SECURITY.es.md`.
- `docs/EXAMPLES.es.md`: ejemplos de consola, libro y carpeta de datos.
- `docs/FAQ.es.md`: dudas sobre privacidad, horas, bibliotecas y errores.
- `docs/BENCHMARKS.es.md`: tiempos de escaneo y libro para 100, 500 y 1000 juegos, y la biblioteca real.
- `docs/PUBLISHING.es.md`: construcción, PyPI Trusted Publishing y la alternativa con token.
- `tests/test_offline.py`: bloquea `socket.socket` y `socket.create_connection` y demuestra que `--offline` no abre ningún socket.
- Plantillas de incidencia y de pull request, y EditorConfig.
- Análisis CodeQL en cada push, en cada pull request y semanal.
- Flujo de release: una etiqueta `v*` construye el wheel y el sdist, los revisa y publica una release de GitHub.
- `tools/check_links.py`: falla si un enlace relativo de la documentación está roto.
- `tools/check_all.py`: ejecuta pyflakes, la comprobación de enlaces y la de traducciones en un solo comando.
- Dependabot agrupa las actualizaciones menores y de parche en un pull request por ecosistema.
- CodeQL también se puede iniciar a mano.
- Instrucciones de instalación con pipx.
- Actualizaciones de Dependabot para pip y GitHub Actions.
- Guía de contribución en inglés y español.
- Palabras clave y clasificadores del paquete.

### Cambiado

- El CI cachea las descargas de pip, cancela ejecuciones sustituidas, usa permisos de solo lectura y un límite de 15 minutos.
- El CI construye el wheel y el sdist, comprueba que no llevan `data/`, instala el wheel y lo ejecuta.
- La comprobación del paquete rechaza las herramientas de desarrollo en el wheel y las exige en el sdist.
- El CI también instala el sdist y ejecuta el comando instalado.
- Umbral de cobertura subido del 97% al 98%; Windows y Ubuntu dan ahora un 99%.
- La fuente de cobertura y el umbral del 98% viven en `pyproject.toml`.
- El comando instalado `game-inventory` lee `data/` del checkout o de la carpeta actual. `GAME_INVENTORY_DATA` lo cambia.
- README: limitaciones, preparación de pruebas y enlaces a benchmarks.

### Seguridad

- El texto de JSON y del libro se mantiene como texto, así que un nombre que empieza por `=` no se trata como fórmula.
- Los caracteres de control se eliminan de celdas y comentarios de Excel.
