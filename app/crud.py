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