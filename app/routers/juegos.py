from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas, crud
from app.database import get_db

router = APIRouter(prefix="/juegos", tags=["Juegos"])


@router.post("/", response_model=schemas.JuegoResponse)
def crear(juego: schemas.JuegoCreate, db: Session = Depends(get_db)):
    return crud.crear_juego(db, juego)


@router.get("/", response_model=list[schemas.JuegoResponse])
def listar(db: Session = Depends(get_db)):
    return crud.obtener_juegos(db)


@router.get("/{juego_id}", response_model=schemas.JuegoResponse)
def obtener(juego_id: int, db: Session = Depends(get_db)):
    juego = crud.obtener_juego(db, juego_id)
    if not juego:
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    return juego


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