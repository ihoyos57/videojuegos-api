from sqlalchemy.orm import Session
from app import models, schemas


def crear_jugador(db: Session, jugador: schemas.JugadorCreate):
    nuevo_jugador = models.Jugador(**jugador.model_dump())
    db.add(nuevo_jugador)
    db.commit()
    db.refresh(nuevo_jugador)
    return nuevo_jugador


def obtener_jugadores(db: Session):
    return db.query(models.Jugador).all()


def obtener_jugador(db: Session, jugador_id: int):
    return db.query(models.Jugador).filter(models.Jugador.id == jugador_id).first()


def actualizar_jugador(db: Session, jugador_id: int, datos: schemas.JugadorUpdate):
    jugador = obtener_jugador(db, jugador_id)
    if not jugador:
        return None
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(jugador, campo, valor)
    db.commit()
    db.refresh(jugador)
    return jugador


def eliminar_jugador(db: Session, jugador_id: int):
    jugador = obtener_jugador(db, jugador_id)
    if not jugador:
        return None
    db.delete(jugador)
    db.commit()
    return jugador

def crear_juego(db: Session, juego: schemas.JuegoCreate):
    nuevo_juego = models.Juego(**juego.model_dump())
    db.add(nuevo_juego)
    db.commit()
    db.refresh(nuevo_juego)
    return nuevo_juego


def obtener_juegos(db: Session):
    return db.query(models.Juego).all()


def obtener_juego(db: Session, juego_id: int):
    return db.query(models.Juego).filter(models.Juego.id == juego_id).first()


def actualizar_juego(db: Session, juego_id: int, datos: schemas.JuegoUpdate):
    juego = obtener_juego(db, juego_id)
    if not juego:
        return None
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(juego, campo, valor)
    db.commit()
    db.refresh(juego)
    return juego


def eliminar_juego(db: Session, juego_id: int):
    juego = obtener_juego(db, juego_id)
    if not juego:
        return None
    db.delete(juego)
    db.commit()
    return juego


def filtrar_juegos(db: Session, genero: str | None = None, plataforma: str | None = None,
                    precio_min: float | None = None, precio_max: float | None = None,
                    disponible: bool | None = None):
    query = db.query(models.Juego)

    if genero:
        query = query.filter(models.Juego.genero == genero)
    if plataforma:
        query = query.filter(models.Juego.plataforma == plataforma)
    if precio_min is not None:
        query = query.filter(models.Juego.precio >= precio_min)
    if precio_max is not None:
        query = query.filter(models.Juego.precio <= precio_max)
    if disponible is True:
        query = query.filter(models.Juego.stock > 0)
    elif disponible is False:
        query = query.filter(models.Juego.stock == 0)

    return query.all()