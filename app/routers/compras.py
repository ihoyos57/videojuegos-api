from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app import schemas, crud
from app.database import get_db
from app.enriquecer import obtener_entidades_companeros, agregar_relacionados

router = APIRouter(prefix="/compras", tags=["Compras"])


@router.post("/", response_model=schemas.CompraResponse)
def crear(compra: schemas.CompraCreate, db: Session = Depends(get_db)):
    return crud.crear_compra(db, compra)


@router.get("/")
async def listar(request: Request, db: Session = Depends(get_db)):
    compras = crud.obtener_compras(db)
    pets, error_pets, tareas, error_tareas = await obtener_entidades_companeros(request)

    resultado = []
    for compra in compras:
        data = schemas.CompraResponse.model_validate(compra).model_dump()
        resultado.append(agregar_relacionados(data, pets, error_pets, tareas, error_tareas))
    return resultado


@router.get("/{compra_id}")
async def obtener(compra_id: int, request: Request, db: Session = Depends(get_db)):
    compra = crud.obtener_compra(db, compra_id)
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")

    pets, error_pets, tareas, error_tareas = await obtener_entidades_companeros(request)

    data = schemas.CompraResponse.model_validate(compra).model_dump()
    return agregar_relacionados(data, pets, error_pets, tareas, error_tareas)


@router.delete("/{compra_id}")
def eliminar(compra_id: int, db: Session = Depends(get_db)):
    compra = crud.eliminar_compra(db, compra_id)
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    return {"mensaje": f"Compra {compra_id} eliminada correctamente"}