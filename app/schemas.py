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