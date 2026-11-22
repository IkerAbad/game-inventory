# Registro de cambios

Cambios destacados del proyecto. El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa versionado semántico.

## [Sin publicar]

### Añadido

- `--dry-run` / `--simular`: escanea y muestra el resumen sin escribir el libro, el histórico, los JSON ni purgar.
- `--check-data` / `--validar`: valida los ficheros JSON y sale sin escanear ni escribir.
- Textos de ayuda traducidos, así que `--help` sigue a `--lang`.
- `docs/DATA.es.md`, `docs/ARCHITECTURE.es.md` y `SECURITY.es.md`.
- Plantillas de incidencia y de pull request, y EditorConfig.
- Actualizaciones de Dependabot para pip y GitHub Actions.
- Guía de contribución en inglés y español.
- Palabras clave y clasificadores del paquete.

### Cambiado

- El CI cachea las descargas de pip, cancela ejecuciones sustituidas, usa permisos de solo lectura y un límite de 15 minutos.
- El CI construye el wheel y el sdist, comprueba que no llevan `data/`, instala el wheel y lo ejecuta.
- El comando instalado `game-inventory` lee `data/` del checkout o de la carpeta actual. `GAME_INVENTORY_DATA` lo cambia.

## [1.0.0] - 2026-11-22

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
- 154 pruebas, umbral de cobertura y lint en CI.

### Seguridad

- El texto de JSON y del libro se mantiene como texto, así que un nombre que empieza por `=` no se trata como fórmula.
- Los caracteres de control se eliminan de celdas y comentarios de Excel.
