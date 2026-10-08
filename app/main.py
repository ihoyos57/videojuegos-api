from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI
from sqlalchemy import text
from app.database import Base, engine
from app import models
from app.routers import jugadores, juegos, compras
from prometheus_fastapi_instrumentator import Instrumentator
from app.middleware import TraceIdMiddleware


app = FastAPI(title="API de Videojuegos")

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

Base.metadata.create_all(bind=engine)

app.include_router(jugadores.router)
app.include_router(juegos.router)
app.include_router(compras.router)
app.add_middleware(TraceIdMiddleware)


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