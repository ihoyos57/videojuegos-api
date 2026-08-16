from app import models


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"mensaje": "API de Videojuegos funcionando"}


def test_crear_jugador_endpoint(client):
    body = {"nombre": "Carlos Ruiz", "correo": "carlos@correo.com"}

    response = client.post("/jugadores/", json=body)

    assert response.status_code == 200
    data = response.json()
    assert data["nombre"] == "Carlos Ruiz"
    assert data["correo"] == "carlos@correo.com"


def test_crear_jugador_correo_invalido_endpoint(client):
    body = {"nombre": "Carlos Ruiz", "correo": "no-es-un-correo"}

    response = client.post("/jugadores/", json=body)

    assert response.status_code == 422  # error de validación de FastAPI/Pydantic


def test_listar_jugadores_endpoint(client, db_mock):
    from datetime import datetime
    jugadores_falsos = [
        models.Jugador(id=1, nombre="Ana", correo="ana@correo.com", fecha_registro=datetime.utcnow())
    ]
    db_mock.query.return_value.all.return_value = jugadores_falsos

    response = client.get("/jugadores/")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_obtener_jugador_no_encontrado_endpoint(client, db_mock):
    db_mock.query.return_value.filter.return_value.first.return_value = None

    response = client.get("/jugadores/999")

    assert response.status_code == 404


def test_crear_juego_endpoint(client):
    body = {"nombre": "Hades", "genero": "Roguelike", "plataforma": "PC", "precio": 24.99, "stock": 20}

    response = client.post("/juegos/", json=body)

    assert response.status_code == 200
    assert response.json()["nombre"] == "Hades"


def test_listar_juegos_endpoint(client, db_mock):
    juegos_falsos = [models.Juego(id=1, nombre="Hades", genero="Roguelike", plataforma="PC", precio=24.99, stock=20)]
    db_mock.query.return_value.all.return_value = juegos_falsos

    response = client.get("/juegos/")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_query_juegos_endpoint(client, db_mock):
    juegos_falsos = [models.Juego(id=1, nombre="Hades", genero="Roguelike", plataforma="PC", precio=24.99, stock=20)]
    query_mock = db_mock.query.return_value
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = juegos_falsos

    response = client.request("QUERY", "/juegos/", json={"genero": "Roguelike"})

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_crear_compra_endpoint(client, db_mock):
    jugador_falso = models.Jugador(id=1, nombre="Ana", correo="ana@correo.com")
    juego_falso = models.Juego(id=1, nombre="Hades", genero="Roguelike", plataforma="PC", precio=25.0, stock=10)
    db_mock.query.return_value.filter.return_value.first.side_effect = [jugador_falso, juego_falso]

    body = {"jugador_id": 1, "juego_id": 1, "cantidad": 2}
    response = client.post("/compras/", json=body)

    assert response.status_code == 200
    assert response.json()["total"] == 50.0


def test_crear_compra_stock_insuficiente_endpoint(client, db_mock):
    jugador_falso = models.Jugador(id=1, nombre="Ana", correo="ana@correo.com")
    juego_falso = models.Juego(id=1, nombre="Hades", genero="Roguelike", plataforma="PC", precio=25.0, stock=1)
    db_mock.query.return_value.filter.return_value.first.side_effect = [jugador_falso, juego_falso]

    body = {"jugador_id": 1, "juego_id": 1, "cantidad": 99}
    response = client.post("/compras/", json=body)

    assert response.status_code == 400