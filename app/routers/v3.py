from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud

router = APIRouter(tags=["V3 - Funcionalidades nuevas"])

@router.get("/juegos/{juego_id}/disponibilidad")
def disponibilidad_juego(juego_id: int, db: Session = Depends(get_db)):
    juego = crud.obtener_juego(db, juego_id)
    if not juego:
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    disponible = juego.stock > 0
    return {
        "juego_id": juego.id,
        "nombre": juego.nombre,
        "stock": juego.stock,
        "disponible": disponible,
        "estado_inventario": "disponible" if disponible else "agotado",
        "mensaje": "Hay unidades disponibles" if disponible else "Producto agotado",
    }
