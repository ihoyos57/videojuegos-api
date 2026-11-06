from dotenv import load_dotenv

load_dotenv()

import os
from fastapi import FastAPI, Request
from sqlalchemy import text
from app.database import Base, engine
from app import models
from app.routers import jugadores, juegos, compras, v3
from prometheus_fastapi_instrumentator import Instrumentator
from app.observability.fault_injection import aplicar_fallo_canary

APP_VERSION = os.getenv("APP_VERSION", "2.0.1")
APP_TRACK = os.getenv("APP_TRACK", "stable")

app = FastAPI(title="API de Videojuegos", version=APP_VERSION)

@app.middleware("http")
async def identify_release(request: Request, call_next):
    fallo = await aplicar_fallo_canary(request)
    if fallo is not None:
        fallo.headers["X-App-Version"] = APP_VERSION
        fallo.headers["X-App-Track"] = APP_TRACK
        return fallo
    response = await call_next(request)
    response.headers["X-App-Version"] = APP_VERSION
    response.headers["X-App-Track"] = APP_TRACK
    return response

Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# Mantiene el esquema existente. La funcionalidad V3 no requiere cambios destructivos
# ni nuevas columnas: el estado de inventario se calcula a partir de stock.
Base.metadata.create_all(bind=engine)

# Rutas originales preservadas para clientes actuales.
app.include_router(jugadores.router)
app.include_router(juegos.router)
app.include_router(compras.router)

# Versionado explícito coexistente: api/v2 conserva el contrato y api/v3 añade
# disponibilidad enriquecida sin alterar tablas ni respuestas anteriores.
app.include_router(jugadores.router, prefix="/api/v2")
app.include_router(juegos.router, prefix="/api/v2")
app.include_router(compras.router, prefix="/api/v2")
app.include_router(jugadores.router, prefix="/api/v3")
app.include_router(juegos.router, prefix="/api/v3")
app.include_router(compras.router, prefix="/api/v3")
    
app.include_router(v3.router, prefix="/api/v3")


@app.get("/")
def root():
    return {"mensaje": "API de Videojuegos funcionando"}

@app.get("/test-db")
def test_db():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        version = result.fetchone()
    return {"conexion": "exitosa", "postgres_version": version[0]}
