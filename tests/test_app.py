import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": str(tmp_path / "test.db"),
        }
    )
    return app.test_client()


def post_form(client, url, data):
    with client.session_transaction() as session:
        has_token = "csrf_token" in session
    if not has_token:
        client.get("/")
    with client.session_transaction() as session:
        data["csrf_token"] = session["csrf_token"]
    return client.post(url, data=data, follow_redirects=True)


def test_registration_login_and_recipe_publication(client):
    response = post_form(
        client,
        "/registro",
        {"username": "cocinera", "password": "contraseña-segura"},
    )
    assert response.status_code == 200
    assert "Cuenta creada".encode() in response.data

    response = post_form(
        client,
        "/recetas/nueva",
        {
            "title": "Tostadas frescas",
            "description": "Un desayuno sencillo",
            "ingredients": "Pan\nTomate\nAceite de oliva",
            "instructions": "Tuesta el pan y añade el tomate.",
        },
    )
    assert response.status_code == 200
    assert "Tostadas frescas".encode() in response.data
    assert "Aceite de oliva".encode() in response.data

    response = post_form(client, "/cerrar-sesion", {})
    assert response.status_code == 200
    response = post_form(
        client,
        "/iniciar-sesion",
        {"username": "cocinera", "password": "contraseña-segura"},
    )
    assert "Has iniciado sesión".encode() in response.data


def test_search_matches_ingredient_case_insensitively(client):
    post_form(
        client,
        "/registro",
        {"username": "cocinera", "password": "contraseña-segura"},
    )
    post_form(
        client,
        "/recetas/nueva",
        {
            "title": "Pasta al limón",
            "description": "Fresca y fácil",
            "ingredients": "200 g de pasta\nLimón\nAceite",
            "instructions": "Cocina y mezcla.",
        },
    )

    response = client.get("/?ingrediente=lim%C3%B3n")
    assert response.status_code == 200
    assert "Pasta al limón".encode() in response.data

    response = client.get("/?ingrediente=chocolate")
    assert "Todavía no hay recetas".encode() in response.data


def test_post_without_csrf_token_is_rejected(client):
    response = client.post(
        "/registro",
        data={"username": "cocinera", "password": "contraseña-segura"},
    )
    assert response.status_code == 400


def test_recipe_publication_requires_login(client):
    response = client.get("/recetas/nueva", follow_redirects=True)
    assert "Iniciar sesión".encode() in response.data
    assert "Inicia sesión para publicar".encode() in response.data
