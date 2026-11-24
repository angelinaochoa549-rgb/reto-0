import secrets
import sqlite3

from app import create_app


def test_new_recipe_title_over_500_characters_is_not_published(tmp_path):
    database = tmp_path / "test.db"
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": str(database),
        }
    )
    client = app.test_client()
    username = f"prueba{secrets.randbelow(1_000_000)}"

    client.get("/")
    with client.session_transaction() as session:
        csrf_token = session["csrf_token"]

    response = client.post(
        "/registro",
        data={
            "username": username,
            "password": "contraseña-segura",
            "csrf_token": csrf_token,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with client.session_transaction() as session:
        csrf_token = session["csrf_token"]

    with sqlite3.connect(database) as connection:
        recipes_before = connection.execute(
            "SELECT COUNT(*) FROM recipes"
        ).fetchone()[0]

    response = client.post(
        "/recetas/nueva",
        data={
            "title": f"Receta {secrets.randbelow(1_000_000)} " + "x" * 501,
            "description": "Descripción ficticia",
            "ingredients": "Ingrediente ficticio",
            "instructions": "Instrucciones ficticias",
            "csrf_token": csrf_token,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with sqlite3.connect(database) as connection:
        recipes_after = connection.execute(
            "SELECT COUNT(*) FROM recipes"
        ).fetchone()[0]

    assert recipes_after == recipes_before
