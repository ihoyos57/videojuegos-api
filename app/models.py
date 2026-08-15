from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Jugador(Base):
    __tablename__ = "jugadores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(150), unique=True, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    compras = relationship("Compra", back_populates="jugador")


class Juego(Base):
    __tablename__ = "juegos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    genero = Column(String(50), nullable=False)
    plataforma = Column(String(50), nullable=False)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)

    compras = relationship("Compra", back_populates="juego")


class Compra(Base):
    __tablename__ = "compras"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    cantidad = Column(Integer, nullable=False)
    total = Column(Float, nullable=False)

    jugador_id = Column(Integer, ForeignKey("jugadores.id"), nullable=False)
    juego_id = Column(Integer, ForeignKey("juegos.id"), nullable=False)

    jugador = relationship("Jugador", back_populates="compras")
    juego = relationship("Juego", back_populates="compras")