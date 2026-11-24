# AGENTS.md

## Proyecto
La Mesa permite publicar, descubrir y buscar recetas por ingredientes.
Incluye registro, inicio de sesión y gestión básica de recetas.

## Stack
- Framework: Python con Flask y Jinja2.
- Base de datos: SQLite mediante sqlite3.
- Librerías: Werkzeug, pytest y Ruff.

## Comandos
- Instalar: `python -m venv .venv` y `pip install -r requirements.txt`
- Ejecutar: `python app.py`
- Pruebas: `python -m pytest -v`
- Estilo: `ruff check .`

## Estructura
- `app.py`: aplicación Flask, rutas, seguridad, datos y arranque.
- `requirements.txt`: dependencia principal del proyecto.
- `recetas.db`: base de datos SQLite de la aplicación.
- `static/`: contiene `style.css`, recursos visuales estáticos.
- `templates/`: plantillas Jinja que forman todas las páginas.
- `templates/base.html`: diseño común y navegación.
- `templates/index.html`: portada, búsqueda y listado de recetas.
- `templates/login.html`: formulario de inicio de sesión.
- `templates/register.html`: formulario de registro.
- `templates/recipe_detail.html`: detalle de una receta.
- `templates/recipe_form.html`: publicación de recetas.
- `tests/test_app.py`: pruebas de registro, búsqueda y publicación.
- `README.md`: documentación de instalación y ejecución.
- `.gitignore`: exclusiones de entornos, cachés y bases locales.
- `.venv/`: entorno virtual local de Python.
- `.pytest_cache/`: caché generada por pytest.

## Qué no hacer
- No modificar las pruebas para hacerlas pasar.
- No escribir claves o secretos directamente en el código.
- No instalar dependencias sin explicar para qué.
- No hacer commit ni push.

## Lecciones aprendidas
