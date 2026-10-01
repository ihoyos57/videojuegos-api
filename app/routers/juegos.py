from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import schemas, crud
from app.database import get_db
from app.enriquecer import obtener_entidades_companeros, agregar_relacionados

router = APIRouter(prefix="/juegos", tags=["Juegos"])


@router.post("/", response_model=schemas.JuegoResponse)
def crear(juego: schemas.JuegoCreate, db: Session = Depends(get_db)):
    return crud.crear_juego(db, juego)


@router.get("/")
async def listar(request: Request, db: Session = Depends(get_db)):
    juegos = crud.obtener_juegos(db)
    pets, error_pets, tareas, error_tareas = await obtener_entidades_companeros(request)

    resultado = []
    for juego in juegos:
        data = schemas.JuegoResponse.model_validate(juego).model_dump()
        resultado.append(agregar_relacionados(data, pets, error_pets, tareas, error_tareas))
    return resultado


@router.get("/{juego_id}")
async def obtener(juego_id: int, request: Request, db: Session = Depends(get_db)):
    juego = crud.obtener_juego(db, juego_id)
    if not juego:
        raise HTTPException(status_code=404, detail="Juego no encontrado")

    pets, error_pets, tareas, error_tareas = await obtener_entidades_companeros(request)

    data = schemas.JuegoResponse.model_validate(juego).model_dump()
    return agregar_relacionados(data, pets, error_pets, tareas, error_tareas)


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