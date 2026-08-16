import pytest
from unittest.mock import MagicMock
from app import crud, models, schemas


def test_crear_jugador(db_mock):
    datos = schemas.JugadorCreate(nombre="Ana Torres", correo="ana@correo.com")

    resultado = crud.crear_jugador(db_mock, datos)

    db_mock.add.assert_called_once()
    db_mock.commit.assert_called_once()
    db_mock.refresh.assert_called_once()
    assert resultado.nombre == "Ana Torres"
    assert resultado.correo == "ana@correo.com"


def test_obtener_jugador_existente(db_mock):
    jugador_falso = models.Jugador(id=1, nombre="Ana Torres", correo="ana@correo.com")
    db_mock.query.return_value.filter.return_value.first.return_value = jugador_falso

    resultado = crud.obtener_jugador(db_mock, 1)

    assert resultado.id == 1
    assert resultado.nombre == "Ana Torres"


def test_obtener_jugador_inexistente(db_mock):
    db_mock.query.return_value.filter.return_value.first.return_value = None

    resultado = crud.obtener_jugador(db_mock, 999)

    assert resultado is None


def test_obtener_jugadores_lista(db_mock):
    jugadores_falsos = [
        models.Jugador(id=1, nombre="Ana Torres", correo="ana@correo.com"),
        models.Jugador(id=2, nombre="Luis Gómez", correo="luis@correo.com"),
    ]
    db_mock.query.return_value.all.return_value = jugadores_falsos

    resultado = crud.obtener_jugadores(db_mock)

    assert len(resultado) == 2


def test_actualizar_jugador_existente(db_mock):
    jugador_falso = models.Jugador(id=1, nombre="Ana Torres", correo="ana@correo.com")
    db_mock.query.return_value.filter.return_value.first.return_value = jugador_falso

    datos = schemas.JugadorUpdate(nombre="Ana María Torres")
    resultado = crud.actualizar_jugador(db_mock, 1, datos)

    assert resultado.nombre == "Ana María Torres"
    db_mock.commit.assert_called_once()


def test_actualizar_jugador_inexistente(db_mock):
    db_mock.query.return_value.filter.return_value.first.return_value = None

    datos = schemas.JugadorUpdate(nombre="Nombre Nuevo")
    resultado = crud.actualizar_jugador(db_mock, 999, datos)

    assert resultado is None


def test_eliminar_jugador_existente(db_mock):
    jugador_falso = models.Jugador(id=1, nombre="Ana Torres", correo="ana@correo.com")
    db_mock.query.return_value.filter.return_value.first.return_value = jugador_falso

    resultado = crud.eliminar_jugador(db_mock, 1)

    assert resultado == jugador_falso
    db_mock.delete.assert_called_once_with(jugador_falso)
    db_mock.commit.assert_called_once()


def test_eliminar_jugador_inexistente(db_mock):
    db_mock.query.return_value.filter.return_value.first.return_value = None

    resultado = crud.eliminar_jugador(db_mock, 999)

    assert resultado is None


def test_jugador_correo_invalido():
    with pytest.raises(ValueError):
        schemas.JugadorCreate(nombre="Pedro", correo="esto-no-es-un-correo")


def test_jugador_nombre_vacio_permite_string_vacio():
    # Pydantic no rechaza string vacío por defecto, esto documenta el comportamiento actual
    jugador = schemas.JugadorCreate(nombre="", correo="test@correo.com")
    assert jugador.nombre == ""