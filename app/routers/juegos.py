from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import random

from app import schemas, crud
from app.database import get_db
from app.federation import consultar_uno

router = APIRouter(prefix="/juegos", tags=["Juegos"])


def _elegir_al_azar(juego_dict, pets, error_pets, tareas, error_tareas):
    """
    Pega una mascota y una tarea al azar al diccionario del juego.
    Si la lista llega vacia (porque la nube no tiene datos, o porque
    fallo la conexion), se pone None en vez de romper, y se deja
    constancia del motivo en *_error para que se pueda mostrar en
    la demo que el sistema sigue respondiendo aunque una nube falle.
    """
    juego_dict["mascota_relacionada"] = random.choice(pets) if pets else None
    juego_dict["mascota_error"] = None if pets else (error_pets or "sin datos disponibles")

    juego_dict["tarea_relacionada"] = random.choice(tareas) if tareas else None
    juego_dict["tarea_error"] = None if tareas else (error_tareas or "sin datos disponibles")

    return juego_dict


@router.post("/", response_model=schemas.JuegoResponse)
def crear(juego: schemas.JuegoCreate, db: Session = Depends(get_db)):
    return crud.crear_juego(db, juego)


@router.get("/")
async def listar(request: Request, db: Session = Depends(get_db)):
    token = request.headers.get("Authorization", "")
    trace_id = getattr(request.state, "trace_id", None)

    juegos = crud.obtener_juegos(db)

    # Se traen las listas UNA sola vez (no una llamada por cada juego),
    # y se elige al azar para cada uno a partir de esas mismas listas.
    pets, error_pets = await consultar_uno("aws", "/pets", {}, token, trace_id)
    tareas, error_tareas = await consultar_uno("objetiva", "/api/v2/tareas", {}, token, trace_id)

    resultado = []
    for juego in juegos:
        data = schemas.JuegoResponse.model_validate(juego).model_dump()
        resultado.append(_elegir_al_azar(data, pets, error_pets, tareas, error_tareas))
    return resultado


@router.get("/{juego_id}")
async def obtener(juego_id: int, request: Request, db: Session = Depends(get_db)):
    juego = crud.obtener_juego(db, juego_id)
    if not juego:
        raise HTTPException(status_code=404, detail="Juego no encontrado")

    token = request.headers.get("Authorization", "")
    trace_id = getattr(request.state, "trace_id", None)

    pets, error_pets = await consultar_uno("aws", "/pets", {}, token, trace_id)
    tareas, error_tareas = await consultar_uno("objetiva", "/api/v2/tareas", {}, token, trace_id)

    data = schemas.JuegoResponse.model_validate(juego).model_dump()
    return _elegir_al_azar(data, pets, error_pets, tareas, error_tareas)


@router.patch("/{juego_id}", response_model=schemas.JuegoResponse)
def actualizar(juego_id: int, datos: schemas.JuegoUpdate, db: Session = Depends(get_db)):
    juego = crud.actualizar_juego(db, juego_id, datos)
    if not juego:
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    return juego


@router.delete("/{juego_id}")
def eliminar(juego_id: int, db: Session = Depends(get_db)):
    juego = crud.eliminar_juego(db, juego_id)
    if not juego:
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    return {"mensaje": f"Juego {juego_id} eliminado correctamente"}


@router.api_route("/", methods=["QUERY"], response_model=list[schemas.JuegoResponse])
def buscar(filtros: schemas.JuegoFiltro, db: Session = Depends(get_db)):
    return crud.filtrar_juegos(
        db,
        genero=filtros.genero,
        plataforma=filtros.plataforma,
        precio_min=filtros.precio_min,
        precio_max=filtros.precio_max,
        disponible=filtros.disponible,
    )