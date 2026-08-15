import pytest
from app import crud, models, schemas


def test_crear_juego(db_mock):
    datos = schemas.JuegoCreate(
        nombre="Elden Ring", genero="RPG", plataforma="PC", precio=59.99, stock=10
    )

    resultado = crud.crear_juego(db_mock, datos)

    db_mock.add.assert_called_once()
    db_mock.commit.assert_called_once()
    assert resultado.nombre == "Elden Ring"
    assert resultado.stock == 10


def test_obtener_juego_existente(db_mock):
    juego_falso = models.Juego(id=1, nombre="Elden Ring", genero="RPG", plataforma="PC", precio=59.99, stock=10)
    db_mock.query.return_value.filter.return_value.first.return_value = juego_falso

    resultado = crud.obtener_juego(db_mock, 1)

    assert resultado.nombre == "Elden Ring"


def test_obtener_juego_inexistente(db_mock):
    db_mock.query.return_value.filter.return_value.first.return_value = None

    resultado = crud.obtener_juego(db_mock, 999)

    assert resultado is None


def test_obtener_juegos_lista(db_mock):
    juegos_falsos = [
        models.Juego(id=1, nombre="Elden Ring", genero="RPG", plataforma="PC", precio=59.99, stock=10),
        models.Juego(id=2, nombre="FIFA 24", genero="Deportes", plataforma="PS5", precio=39.99, stock=5),
    ]
    db_mock.query.return_value.all.return_value = juegos_falsos

    resultado = crud.obtener_juegos(db_mock)

    assert len(resultado) == 2


def test_actualizar_juego_existente(db_mock):
    juego_falso = models.Juego(id=1, nombre="Elden Ring", genero="RPG", plataforma="PC", precio=59.99, stock=10)
    db_mock.query.return_value.filter.return_value.first.return_value = juego_falso

    datos = schemas.JuegoUpdate(precio=49.99)
    resultado = crud.actualizar_juego(db_mock, 1, datos)

    assert resultado.precio == 49.99
    db_mock.commit.assert_called_once()


def test_actualizar_juego_inexistente(db_mock):
    db_mock.query.return_value.filter.return_value.first.return_value = None

    datos = schemas.JuegoUpdate(precio=49.99)
    resultado = crud.actualizar_juego(db_mock, 999, datos)

    assert resultado is None


def test_eliminar_juego_existente(db_mock):
    juego_falso = models.Juego(id=1, nombre="Elden Ring", genero="RPG", plataforma="PC", precio=59.99, stock=10)
    db_mock.query.return_value.filter.return_value.first.return_value = juego_falso

    resultado = crud.eliminar_juego(db_mock, 1)

    assert resultado == juego_falso
    db_mock.delete.assert_called_once_with(juego_falso)


def test_eliminar_juego_inexistente(db_mock):
    db_mock.query.return_value.filter.return_value.first.return_value = None

    resultado = crud.eliminar_juego(db_mock, 999)

    assert resultado is None


def test_filtrar_juegos_por_genero(db_mock):
    juegos_falsos = [models.Juego(id=1, nombre="Elden Ring", genero="RPG", plataforma="PC", precio=59.99, stock=10)]
    query_mock = db_mock.query.return_value
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = juegos_falsos

    resultado = crud.filtrar_juegos(db_mock, genero="RPG")

    assert len(resultado) == 1
    assert resultado[0].genero == "RPG"


def test_filtrar_juegos_disponibles(db_mock):
    juegos_falsos = [models.Juego(id=1, nombre="Elden Ring", genero="RPG", plataforma="PC", precio=59.99, stock=10)]
    query_mock = db_mock.query.return_value
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = juegos_falsos

    resultado = crud.filtrar_juegos(db_mock, disponible=True)

    assert len(resultado) == 1


def test_juego_precio_invalido():
    with pytest.raises(ValueError):
        schemas.JuegoCreate(nombre="Juego X", genero="Acción", plataforma="PC", precio="no-es-numero", stock=5)