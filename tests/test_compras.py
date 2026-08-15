import pytest
from fastapi import HTTPException
from app import crud, models, schemas


def test_crear_compra_exitosa(db_mock):
    jugador_falso = models.Jugador(id=1, nombre="Ana Torres", correo="ana@correo.com")
    juego_falso = models.Juego(id=1, nombre="Elden Ring", genero="RPG", plataforma="PC", precio=50.0, stock=10)

    db_mock.query.return_value.filter.return_value.first.side_effect = [jugador_falso, juego_falso]

    datos = schemas.CompraCreate(jugador_id=1, juego_id=1, cantidad=2)
    resultado = crud.crear_compra(db_mock, datos)

    assert resultado.total == 100.0
    assert juego_falso.stock == 8
    db_mock.add.assert_called_once()
    db_mock.commit.assert_called_once()


def test_crear_compra_jugador_inexistente(db_mock):
    db_mock.query.return_value.filter.return_value.first.side_effect = [None]

    datos = schemas.CompraCreate(jugador_id=999, juego_id=1, cantidad=1)

    with pytest.raises(HTTPException) as exc_info:
        crud.crear_compra(db_mock, datos)

    assert exc_info.value.status_code == 404
    assert "jugador no existe" in exc_info.value.detail.lower()


def test_crear_compra_juego_inexistente(db_mock):
    jugador_falso = models.Jugador(id=1, nombre="Ana Torres", correo="ana@correo.com")
    db_mock.query.return_value.filter.return_value.first.side_effect = [jugador_falso, None]

    datos = schemas.CompraCreate(jugador_id=1, juego_id=999, cantidad=1)

    with pytest.raises(HTTPException) as exc_info:
        crud.crear_compra(db_mock, datos)

    assert exc_info.value.status_code == 404
    assert "juego no existe" in exc_info.value.detail.lower()


def test_crear_compra_stock_insuficiente(db_mock):
    jugador_falso = models.Jugador(id=1, nombre="Ana Torres", correo="ana@correo.com")
    juego_falso = models.Juego(id=1, nombre="Elden Ring", genero="RPG", plataforma="PC", precio=50.0, stock=3)

    db_mock.query.return_value.filter.return_value.first.side_effect = [jugador_falso, juego_falso]

    datos = schemas.CompraCreate(jugador_id=1, juego_id=1, cantidad=10)

    with pytest.raises(HTTPException) as exc_info:
        crud.crear_compra(db_mock, datos)

    assert exc_info.value.status_code == 400
    assert "stock insuficiente" in exc_info.value.detail.lower()
    assert juego_falso.stock == 3  # el stock NO debe cambiar si la compra falla


def test_crear_compra_cantidad_invalida(db_mock):
    jugador_falso = models.Jugador(id=1, nombre="Ana Torres", correo="ana@correo.com")
    juego_falso = models.Juego(id=1, nombre="Elden Ring", genero="RPG", plataforma="PC", precio=50.0, stock=10)

    db_mock.query.return_value.filter.return_value.first.side_effect = [jugador_falso, juego_falso]

    datos = schemas.CompraCreate(jugador_id=1, juego_id=1, cantidad=0)

    with pytest.raises(HTTPException) as exc_info:
        crud.crear_compra(db_mock, datos)

    assert exc_info.value.status_code == 400


def test_calcular_total_correctamente(db_mock):
    jugador_falso = models.Jugador(id=1, nombre="Ana Torres", correo="ana@correo.com")
    juego_falso = models.Juego(id=1, nombre="Elden Ring", genero="RPG", plataforma="PC", precio=25.5, stock=10)

    db_mock.query.return_value.filter.return_value.first.side_effect = [jugador_falso, juego_falso]

    datos = schemas.CompraCreate(jugador_id=1, juego_id=1, cantidad=4)
    resultado = crud.crear_compra(db_mock, datos)

    assert resultado.total == 102.0  # 25.5 * 4


def test_obtener_compra_existente(db_mock):
    compra_falsa = models.Compra(id=1, cantidad=2, total=100.0, jugador_id=1, juego_id=1)
    db_mock.query.return_value.filter.return_value.first.return_value = compra_falsa

    resultado = crud.obtener_compra(db_mock, 1)

    assert resultado.id == 1
    assert resultado.total == 100.0


def test_obtener_compras_lista(db_mock):
    compras_falsas = [
        models.Compra(id=1, cantidad=2, total=100.0, jugador_id=1, juego_id=1),
        models.Compra(id=2, cantidad=1, total=50.0, jugador_id=1, juego_id=2),
    ]
    db_mock.query.return_value.all.return_value = compras_falsas

    resultado = crud.obtener_compras(db_mock)

    assert len(resultado) == 2


def test_eliminar_compra_existente(db_mock):
    compra_falsa = models.Compra(id=1, cantidad=2, total=100.0, jugador_id=1, juego_id=1)
    db_mock.query.return_value.filter.return_value.first.return_value = compra_falsa

    resultado = crud.eliminar_compra(db_mock, 1)

    assert resultado == compra_falsa
    db_mock.delete.assert_called_once_with(compra_falsa)


def test_eliminar_compra_inexistente(db_mock):
    db_mock.query.return_value.filter.return_value.first.return_value = None

    resultado = crud.eliminar_compra(db_mock, 999)

    assert resultado is None