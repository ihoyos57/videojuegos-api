from pydantic import BaseModel, EmailStr
from datetime import datetime


class JugadorBase(BaseModel):
    nombre: str
    correo: EmailStr


class JugadorCreate(JugadorBase):
    pass


class JugadorUpdate(BaseModel):
    nombre: str | None = None
    correo: EmailStr | None = None


class JugadorResponse(JugadorBase):
    id: int
    fecha_registro: datetime

    class Config:
        from_attributes = True

class JuegoBase(BaseModel):
    nombre: str
    genero: str
    plataforma: str
    precio: float
    stock: int


class JuegoCreate(JuegoBase):
    pass


class JuegoUpdate(BaseModel):
    nombre: str | None = None
    genero: str | None = None
    plataforma: str | None = None
    precio: float | None = None
    stock: int | None = None


class JuegoResponse(JuegoBase):
    id: int

    class Config:
        from_attributes = True

class JuegoFiltro(BaseModel):
    genero: str | None = None
    plataforma: str | None = None
    precio_min: float | None = None
    precio_max: float | None = None
    disponible: bool | None = None

class CompraCreate(BaseModel):
    jugador_id: int
    juego_id: int
    cantidad: int


class CompraResponse(BaseModel):
    id: int
    fecha: datetime
    cantidad: int
    total: float
    jugador_id: int
    juego_id: int

    class Config:
        from_attributes = True