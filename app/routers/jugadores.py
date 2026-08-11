from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas, crud
from app.database import get_db

router = APIRouter(prefix="/jugadores", tags=["Jugadores"])


@router.post("/", response_model=schemas.JugadorResponse)
def crear(jugador: schemas.JugadorCreate, db: Session = Depends(get_db)):
    return crud.crear_jugador(db, jugador)


@router.get("/", response_model=list[schemas.JugadorResponse])
def listar(db: Session = Depends(get_db)):
    return crud.obtener_jugadores(db)


@router.get("/{jugador_id}", response_model=schemas.JugadorResponse)
def obtener(jugador_id: int, db: Session = Depends(get_db)):
    jugador = crud.obtener_jugador(db, jugador_id)
    if not jugador:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    return jugador


@router.patch("/{jugador_id}", response_model=schemas.JugadorResponse)
def actualizar(jugador_id: int, datos: schemas.JugadorUpdate, db: Session = Depends(get_db)):
    jugador = crud.actualizar_jugador(db, jugador_id, datos)
    if not jugador:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    return jugador


@router.delete("/{jugador_id}")
def eliminar(jugador_id: int, db: Session = Depends(get_db)):
    jugador = crud.eliminar_jugador(db, jugador_id)
    if not jugador:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    return {"mensaje": f"Jugador {jugador_id} eliminado correctamente"}