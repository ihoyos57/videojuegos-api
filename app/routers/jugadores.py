from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app import schemas, crud
from app.database import get_db
from app.enriquecer import obtener_entidades_companeros, agregar_relacionados, construir_respuesta_lista

router = APIRouter(prefix="/jugadores", tags=["Jugadores"])


@router.post("/", response_model=schemas.JugadorResponse)
def crear(jugador: schemas.JugadorCreate, db: Session = Depends(get_db)):
    return crud.crear_jugador(db, jugador)


# OJO: se quitó response_model de aquí a propósito. Si lo dejamos,
# FastAPI filtra la respuesta y elimina los campos extra
# (mascota_relacionada, tarea_relacionada) porque no están en
# schemas.JugadorResponse.
@router.get("/")
async def listar(request: Request, db: Session = Depends(get_db)):
    jugadores = crud.obtener_jugadores(db)
    items = [schemas.JugadorResponse.model_validate(j).model_dump() for j in jugadores]

    pets, error_pets, tareas, error_tareas = await obtener_entidades_companeros(request)
    return construir_respuesta_lista("jugadores", items, pets, error_pets, tareas, error_tareas)


@router.get("/{jugador_id}")
async def obtener(jugador_id: int, request: Request, db: Session = Depends(get_db)):
    jugador = crud.obtener_jugador(db, jugador_id)
    if not jugador:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")

    pets, error_pets, tareas, error_tareas = await obtener_entidades_companeros(request)

    data = schemas.JugadorResponse.model_validate(jugador).model_dump()
    return agregar_relacionados(data, pets, error_pets, tareas, error_tareas)


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