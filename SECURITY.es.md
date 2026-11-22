# Seguridad

## Versiones con soporte

La línea 1.x recibe correcciones.

## Diseño

- La herramienta se ejecuta en local. No levanta un servidor, no escucha en un puerto ni acepta peticiones remotas.
- No guarda credenciales, tokens ni contraseñas.
- Los datos personales viven en `data/`, que está ignorado por git y no se incluye en el paquete.

## Red

Las peticiones son GET de solo lectura a:

- `dekudeals.com`
- `twoaveragegamers.com`
- `store.steampowered.com`
- `steamcommunity.com`
- `metacritic.com`

Hay un presupuesto de peticiones y un límite por servidor. `--offline` no hace ninguna petición.

## Seguridad del Excel

- El texto que empieza por `=` se guarda como texto, así que una carpeta de juego o un título de la wishlist no puede convertirse en fórmula.
- Los caracteres de control que Excel rechaza se eliminan de celdas y comentarios.

## Informar

Abre una incidencia en https://github.com/IkerAbad/game-inventory/issues. No adjuntes ficheros personales de `data/`. Si el informe contiene detalles sensibles, usa el aviso privado de seguridad del repositorio.
