import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash


def initialize_database(db):
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


def get_recipes(db, ingredient):
    if ingredient:
        return db.execute(
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
    return db.execute(
        """
        SELECT recipes.*, users.username
        FROM recipes
        JOIN users ON users.id = recipes.user_id
        ORDER BY recipes.created_at DESC
        """
    ).fetchall()


def validate_user_form(username, password):
    username = username.strip()
    if len(username) < 3 or len(username) > 40:
        error = "El usuario debe tener entre 3 y 40 caracteres."
    elif len(password) < 8:
        error = "La contraseña debe tener al menos 8 caracteres."
    elif len(password) > 128:
        error = "La contraseña no puede tener más de 128 caracteres."
    else:
        error = None
    return username, error


def create_user(db, username, password):
    try:
        cursor = db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return None
    return cursor.lastrowid


def authenticate_user(db, username, password):
    user = db.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return None
    return user


def validate_recipe_form(title, description, instructions, ingredients):
    title = title.strip()
    description = description.strip()
    instructions = instructions.strip()
    ingredients = [
        line.strip() for line in ingredients.splitlines() if line.strip()
    ]
    if (
        not title
        or len(title) > 500
        or not description
        or not instructions
        or not ingredients
    ):
        error = "Completa todos los campos e incluye al menos un ingrediente."
    else:
        error = None
    return title, description, instructions, ingredients, error


def create_recipe(db, user_id, title, description, instructions, ingredients):
    cursor = db.execute(
        """
        INSERT INTO recipes (user_id, title, description, instructions)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, title, description, instructions),
    )
    recipe_id = cursor.lastrowid
    db.executemany(
        "INSERT INTO ingredients (recipe_id, name) VALUES (?, ?)",
        [(recipe_id, name) for name in ingredients],
    )
    db.commit()
    return recipe_id


def get_recipe(db, recipe_id):
    return db.execute(
        """
        SELECT recipes.*, users.username
        FROM recipes JOIN users ON users.id = recipes.user_id
        WHERE recipes.id = ?
        """,
        (recipe_id,),
    ).fetchone()


def get_recipe_ingredients(db, recipe_id):
    return db.execute(
        "SELECT name FROM ingredients WHERE recipe_id = ? ORDER BY id",
        (recipe_id,),
    ).fetchall()


def escape_like(value):
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
