# La Mesa

Aplicación web en español para publicar y descubrir recetas por ingrediente.

## Requisitos

- Python 3.10 o posterior
- Flask (`pip install -r requirements.txt`)

## Ejecutar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY = "reemplaza-por-una-clave-aleatoria"
python app.py
```

Abre http://127.0.0.1:5000. La base de datos SQLite `recetas.db` se crea automáticamente en la carpeta del proyecto.

Si se omite `SECRET_KEY`, se genera una clave aleatoria al iniciar la app y las sesiones activas dejarán de funcionar al reiniciarla. En cualquier entorno desplegado se debe configurar una clave secreta persistente y mantener `FLASK_DEBUG` desactivado.

## Funcionalidades

- Registro e inicio/cierre de sesión.
- Publicación de recetas con descripción, ingredientes y preparación.
- Búsqueda de recetas por ingrediente.
- Contraseñas con hash, consultas parametrizadas y protección CSRF en formularios POST.

## Pruebas

```powershell
python -m pytest
```
