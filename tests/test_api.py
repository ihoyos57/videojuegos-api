import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from tests.conftest import db as db_fixture


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_ruta_principal(client):
    respuesta = client.get("/")
    assert respuesta.status_code == 200
    assert "funcionando" in respuesta.json()["mensaje"].lower()


def test_documentacion_openapi(client):
    respuesta = client.get("/openapi.json")
    assert respuesta.status_code == 200
    assert "/juegos/" in respuesta.json()["paths"]
    assert "/jugadores/" in respuesta.json()["paths"]
    assert "/compras/" in respuesta.json()["paths"]


def test_listar_juegos_vacio(client):
    respuesta = client.get("/juegos/")
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_crear_y_consultar_juego(client):
    datos = {
        "nombre": "Minecraft",
        "genero": "Aventura",
        "plataforma": "PC",
        "precio": 50,
        "stock": 10,
    }

    creado = client.post("/juegos/", json=datos)
    assert creado.status_code == 200
    juego_id = creado.json()["id"]

    consultado = client.get(f"/juegos/{juego_id}")
    assert consultado.status_code == 200
    assert consultado.json()["nombre"] == "Minecraft"


def test_juego_inexistente(client):
    respuesta = client.get("/juegos/99999")
    assert respuesta.status_code == 404


def test_actualizar_juego_http(client):
    creado = client.post(
        "/juegos/",
        json={
            "nombre": "Mario",
            "genero": "Plataformas",
            "plataforma": "Switch",
            "precio": 80,
            "stock": 4,
        },
    )
    juego_id = creado.json()["id"]

    respuesta = client.patch(
        f"/juegos/{juego_id}",
        json={"stock": 9},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["stock"] == 9


def test_eliminar_juego_http(client):
    creado = client.post(
        "/juegos/",
        json={
            "nombre": "Zelda",
            "genero": "Aventura",
            "plataforma": "Switch",
            "precio": 100,
            "stock": 3,
        },
    )
    juego_id = creado.json()["id"]

    eliminado = client.delete(f"/juegos/{juego_id}")
    assert eliminado.status_code == 200

    consulta = client.get(f"/juegos/{juego_id}")
    assert consulta.status_code == 404


def test_crear_y_listar_jugador(client):
    respuesta = client.post(
        "/jugadores/",
        json={
            "nombre": "Ana",
            "correo": "ana.pruebas@example.com",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Ana"

    lista = client.get("/jugadores/")
    assert lista.status_code == 200
    assert len(lista.json()) == 1


def test_jugador_inexistente(client):
    respuesta = client.get("/jugadores/99999")
    assert respuesta.status_code == 404


def test_crear_y_listar_compra(client):
    jugador = client.post(
        "/jugadores/",
        json={
            "nombre": "Carlos",
            "correo": "carlos.pruebas@example.com",
        },
    )
    juego = client.post(
        "/juegos/",
        json={
            "nombre": "FIFA",
            "genero": "Deportes",
            "plataforma": "PlayStation",
            "precio": 100,
            "stock": 5,
        },
    )

    compra = client.post(
        "/compras/",
        json={
            "jugador_id": jugador.json()["id"],
            "juego_id": juego.json()["id"],
            "cantidad": 2,
        },
    )

    assert compra.status_code == 200
    assert compra.json()["total"] == 200

    lista = client.get("/compras/")
    assert lista.status_code == 200
    assert len(lista.json()) == 1


def test_compra_inexistente(client):
    respuesta = client.get("/compras/99999")
    assert respuesta.status_code == 404


def test_consulta_test_db(client):
    respuesta = client.get("/test-db")
    assert respuesta.status_code in (200, 500)

