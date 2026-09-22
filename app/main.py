from fastapi import FastAPI
from sqlalchemy import text

from app.database import Base, engine
from app import models
from app.routers import jugadores, juegos, compras
from app.routers import agregado


app = FastAPI(title="API de Videojuegos")

Base.metadata.create_all(bind=engine)

app.include_router(jugadores.router)
app.include_router(juegos.router)
app.include_router(compras.router)
app.include_router(agregado.router)


@app.get("/")
def root():
    return {"mensaje": "API de Videojuegos funcionando"}


@app.get("/test-db")
def test_db():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        version = result.fetchone()

    return {
        "conexion": "exitosa",
        "postgres_version": version[0]
    }