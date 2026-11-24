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

from servicios import (
    authenticate_user,
    create_recipe,
    create_user,
    get_recipe,
    get_recipe_ingredients,
    get_recipes,
    initialize_database,
    validate_recipe_form,
    validate_user_form,
)

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

    with app.app_context():
        initialize_database(get_db())

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
        recipes = get_recipes(get_db(), ingredient)
        return render_template("index.html", recipes=recipes, ingredient=ingredient)

    @app.route("/registro", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username, validation_error = validate_user_form(
                request.form.get("username", ""),
                request.form.get("password", ""),
            )
            password = request.form.get("password", "")
            if validation_error:
                flash(validation_error, "error")
            else:
                user_id = create_user(get_db(), username, password)
                if user_id is None:
                    flash("Ese nombre de usuario ya está en uso.", "error")
                else:
                    session.clear()
                    session["user_id"] = user_id
                    session["username"] = username
                    flash("¡Cuenta creada! Ya puedes compartir tus recetas.", "success")
                    return redirect(url_for("index"))
        return render_template("register.html")

    @app.route("/iniciar-sesion", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = authenticate_user(get_db(), username, password)
            if user is None:
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
            title, description, instructions, ingredients, validation_error = (
                validate_recipe_form(
                    request.form.get("title", ""),
                    request.form.get("description", ""),
                    request.form.get("instructions", ""),
                    request.form.get("ingredients", ""),
                )
            )
            if validation_error:
                flash(validation_error, "error")
            else:
                recipe_id = create_recipe(
                    get_db(),
                    session["user_id"],
                    title,
                    description,
                    instructions,
                    ingredients,
                )
                flash("Tu receta ya está publicada.", "success")
                return redirect(url_for("recipe_detail", recipe_id=recipe_id))
        return render_template("recipe_form.html")

    @app.get("/recetas/<int:recipe_id>")
    def recipe_detail(recipe_id):
        db = get_db()
        recipe = get_recipe(db, recipe_id)
        if recipe is None:
            abort(404)
        ingredients = get_recipe_ingredients(db, recipe_id)
        return render_template(
            "recipe_detail.html", recipe=recipe, ingredients=ingredients
        )

    return app

app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
