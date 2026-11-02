import pytest
from fastapi import HTTPException

from app import crud, schemas


def crear_jugador(db, correo="jugador@example.com"):
    datos = schemas.JugadorCreate(
        nombre="Ana",
        correo=correo,
    )
    return crud.crear_jugador(db, datos)


def crear_juego(db, nombre="Minecraft", stock=10, precio=50.0):
    datos = schemas.JuegoCreate(
        nombre=nombre,
        genero="Aventura",
        plataforma="PC",
        precio=precio,
        stock=stock,
    )
    return crud.crear_juego(db, datos)


# JUGADORES

def test_crear_y_obtener_jugador(db):
    jugador = crear_jugador(db)

    encontrado = crud.obtener_jugador(db, jugador.id)

    assert encontrado is not None
    assert encontrado.nombre == "Ana"
    assert encontrado.correo == "jugador@example.com"


def test_listar_jugadores(db):
    crear_jugador(db, "ana@example.com")
    crear_jugador(db, "juan@example.com")

    assert len(crud.obtener_jugadores(db)) == 2


def test_actualizar_jugador(db):
    jugador = crear_jugador(db)

    actualizado = crud.actualizar_jugador(
        db,
        jugador.id,
        schemas.JugadorUpdate(nombre="Ana María"),
    )

    assert actualizado.nombre == "Ana María"


def test_eliminar_jugador(db):
    jugador = crear_jugador(db)

    eliminado = crud.eliminar_jugador(db, jugador.id)

    assert eliminado is not None
    assert crud.obtener_jugador(db, jugador.id) is None


def test_actualizar_jugador_inexistente(db):
    resultado = crud.actualizar_jugador(
        db, 999, schemas.JugadorUpdate(nombre="Nuevo")
    )

    assert resultado is None


# JUEGOS

def test_crear_y_obtener_juego(db):
    juego = crear_juego(db)

    encontrado = crud.obtener_juego(db, juego.id)

    assert encontrado.nombre == "Minecraft"
    assert encontrado.stock == 10


def test_actualizar_juego(db):
    juego = crear_juego(db)

    actualizado = crud.actualizar_juego(
        db,
        juego.id,
        schemas.JuegoUpdate(stock=7),
    )

    assert actualizado.stock == 7


def test_eliminar_juego(db):
    juego = crear_juego(db)

    crud.eliminar_juego(db, juego.id)

    assert crud.obtener_juego(db, juego.id) is None


def test_filtrar_juegos_por_genero(db):
    crear_juego(db, "Minecraft")
    otro = schemas.JuegoCreate(
        nombre="FIFA",
        genero="Deportes",
        plataforma="PlayStation",
        precio=100.0,
        stock=3,
    )
    crud.crear_juego(db, otro)

    resultados = crud.filtrar_juegos(db, genero="Aventura")

    assert len(resultados) == 1
    assert resultados[0].nombre == "Minecraft"


def test_filtrar_juegos_por_precio_y_disponibilidad(db):
    crear_juego(db, "Disponible", stock=5, precio=40.0)
    crear_juego(db, "Agotado", stock=0, precio=30.0)

    resultados = crud.filtrar_juegos(
        db,
        precio_min=35,
        precio_max=45,
        disponible=True,
    )

    assert len(resultados) == 1
    assert resultados[0].nombre == "Disponible"


# COMPRAS

def test_crear_compra_y_actualizar_stock(db):
    jugador = crear_jugador(db)
    juego = crear_juego(db, stock=10, precio=25.0)

    compra = crud.crear_compra(
        db,
        schemas.CompraCreate(
            jugador_id=jugador.id,
            juego_id=juego.id,
            cantidad=2,
        ),
    )

    assert compra.total == 50.0
    assert compra.cantidad == 2
    assert crud.obtener_juego(db, juego.id).stock == 8


def test_compra_con_jugador_inexistente(db):
    juego = crear_juego(db)

    with pytest.raises(HTTPException) as error:
        crud.crear_compra(
            db,
            schemas.CompraCreate(
                jugador_id=999,
                juego_id=juego.id,
                cantidad=1,
            ),
        )

    assert error.value.status_code == 404
    assert error.value.detail == "El jugador no existe"


def test_compra_con_juego_inexistente(db):
    jugador = crear_jugador(db)

    with pytest.raises(HTTPException) as error:
        crud.crear_compra(
            db,
            schemas.CompraCreate(
                jugador_id=jugador.id,
                juego_id=999,
                cantidad=1,
            ),
        )

    assert error.value.status_code == 404
    assert error.value.detail == "El juego no existe"


def test_compra_con_cantidad_cero(db):
    jugador = crear_jugador(db)
    juego = crear_juego(db)

    with pytest.raises(HTTPException) as error:
        crud.crear_compra(
            db,
            schemas.CompraCreate(
                jugador_id=jugador.id,
                juego_id=juego.id,
                cantidad=0,
            ),
        )

    assert error.value.status_code == 400
    assert error.value.detail == "La cantidad debe ser mayor a cero"


def test_compra_con_stock_insuficiente(db):
    jugador = crear_jugador(db)
    juego = crear_juego(db, stock=1)

    with pytest.raises(HTTPException) as error:
        crud.crear_compra(
            db,
            schemas.CompraCreate(
                jugador_id=jugador.id,
                juego_id=juego.id,
                cantidad=2,
            ),
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Stock insuficiente para esta compra"


def test_eliminar_compra(db):
    jugador = crear_jugador(db)
    juego = crear_juego(db)

    compra = crud.crear_compra(
        db,
        schemas.CompraCreate(
            jugador_id=jugador.id,
            juego_id=juego.id,
            cantidad=1,
        ),
    )

    eliminada = crud.eliminar_compra(db, compra.id)

    assert eliminada is not None
    assert crud.obtener_compra(db, compra.id) is None

