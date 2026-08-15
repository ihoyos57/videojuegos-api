from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas, crud
from app.database import get_db

router = APIRouter(prefix="/compras", tags=["Compras"])


@router.post("/", response_model=schemas.CompraResponse)
def crear(compra: schemas.CompraCreate, db: Session = Depends(get_db)):
    return crud.crear_compra(db, compra)


@router.get("/", response_model=list[schemas.CompraResponse])
def listar(db: Session = Depends(get_db)):
    return crud.obtener_compras(db)


@router.get("/{compra_id}", response_model=schemas.CompraResponse)
def obtener(compra_id: int, db: Session = Depends(get_db)):
    compra = crud.obtener_compra(db, compra_id)
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    return compra


@router.delete("/{compra_id}")
def eliminar(compra_id: int, db: Session = Depends(get_db)):
    compra = crud.eliminar_compra(db, compra_id)
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    return {"mensaje": f"Compra {compra_id} eliminada correctamente"}