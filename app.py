import os
import secrets
import sqlite3
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=str(BASE_DIR / "recetas.db"),
    )
    if test_config:
        app.config.update(test_config)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def initialize_database():
        db = get_db()
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                instructions TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
                name TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ingredients_name_idx ON ingredients(name);
            """
        )
        db.commit()

    with app.app_context():
        initialize_database()

    @app.before_request
    def protect_post_requests():
        if request.method == "POST":
            submitted_token = request.form.get("csrf_token", "")
            session_token = session.get("csrf_token", "")
            if not session_token or not secrets.compare_digest(
                submitted_token, session_token
            ):
                abort(400, description="Token de seguridad no válido.")

    @app.context_processor
    def inject_template_values():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return {"csrf_token": session["csrf_token"]}

    def login_required(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if "user_id" not in session:
                flash("Inicia sesión para publicar una receta.", "info")
                return redirect(url_for("login", next=request.path))
            return view(**kwargs)

        return wrapped_view

    @app.get("/")
    def index():
        ingredient = request.args.get("ingrediente", "").strip()
        db = get_db()
        if ingredient:
            recipes = db.execute(
                """
                SELECT DISTINCT recipes.*, users.username
                FROM recipes
                JOIN users ON users.id = recipes.user_id
                JOIN ingredients ON ingredients.recipe_id = recipes.id
                WHERE ingredients.name LIKE ? ESCAPE '\\'
                ORDER BY recipes.created_at DESC
                """,
                (f"%{escape_like(ingredient)}%",),
            ).fetchall()
        else:
            recipes = db.execute(
                """
                SELECT recipes.*, users.username
                FROM recipes
                JOIN users ON users.id = recipes.user_id
                ORDER BY recipes.created_at DESC
                """
            ).fetchall()
        return render_template("index.html", recipes=recipes, ingredient=ingredient)

    @app.route("/registro", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if len(username) < 3 or len(username) > 40:
                flash("El usuario debe tener entre 3 y 40 caracteres.", "error")
            elif len(password) < 8:
                flash("La contraseña debe tener al menos 8 caracteres.", "error")
            else:
                db = get_db()
                try:
                    cursor = db.execute(
                        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        (username, generate_password_hash(password)),
                    )
                    db.commit()
                except sqlite3.IntegrityError:
                    flash("Ese nombre de usuario ya está en uso.", "error")
                else:
                    session.clear()
                    session["user_id"] = cursor.lastrowid
                    session["username"] = username
                    flash("¡Cuenta creada! Ya puedes compartir tus recetas.", "success")
                    return redirect(url_for("index"))
        return render_template("register.html")

    @app.route("/iniciar-sesion", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = get_db().execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Usuario o contraseña incorrectos.", "error")
            else:
                session.clear()
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                flash("Has iniciado sesión.", "success")
                destination = request.args.get("next", "")
                if destination.startswith("/") and not destination.startswith("//"):
                    return redirect(destination)
                return redirect(url_for("index"))
        return render_template("login.html")

    @app.post("/cerrar-sesion")
    def logout():
        session.clear()
        flash("Has cerrado sesión.", "info")
        return redirect(url_for("index"))

    @app.route("/recetas/nueva", methods=["GET", "POST"])
    @login_required
    def new_recipe():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            instructions = request.form.get("instructions", "").strip()
            ingredients = [
                line.strip()
                for line in request.form.get("ingredients", "").splitlines()
                if line.strip()
            ]
            if not title or not description or not instructions or not ingredients:
                flash("Completa todos los campos e incluye al menos un ingrediente.", "error")
            else:
                db = get_db()
                cursor = db.execute(
                    """
                    INSERT INTO recipes (user_id, title, description, instructions)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session["user_id"], title, description, instructions),
                )
                db.executemany(
                    "INSERT INTO ingredients (recipe_id, name) VALUES (?, ?)",
                    [(cursor.lastrowid, name) for name in ingredients],
                )
                db.commit()
                flash("Tu receta ya está publicada.", "success")
                return redirect(url_for("recipe_detail", recipe_id=cursor.lastrowid))
        return render_template("recipe_form.html")

    @app.get("/recetas/<int:recipe_id>")
    def recipe_detail(recipe_id):
        recipe = get_db().execute(
            """
            SELECT recipes.*, users.username
            FROM recipes JOIN users ON users.id = recipes.user_id
            WHERE recipes.id = ?
            """,
            (recipe_id,),
        ).fetchone()
        if recipe is None:
            abort(404)
        ingredients = get_db().execute(
            "SELECT name FROM ingredients WHERE recipe_id = ? ORDER BY id",
            (recipe_id,),
        ).fetchall()
        return render_template(
            "recipe_detail.html", recipe=recipe, ingredients=ingredients
        )

    return app


def escape_like(value):
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
