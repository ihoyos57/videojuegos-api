from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Jugador(Base):
    __tablename__ = "jugadores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(150), unique=True, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    # compras = relationship("Compra", back_populates="jugador")  # se activa en la Fase 9


class Juego(Base):
    __tablename__ = "juegos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    genero = Column(String(50), nullable=False)
    plataforma = Column(String(50), nullable=False)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)

    # compras = relationship("Compra", back_populates="juego")  # se activa en la Fase 9