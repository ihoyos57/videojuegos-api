from dotenv import load_dotenv
import asyncio
from contextlib import suppress

load_dotenv()

import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.security.telemetry import emit, heartbeat_loop
from sqlalchemy import text
from app.database import Base, engine
from app import models
from app.routers import jugadores, juegos, compras, v3
from prometheus_fastapi_instrumentator import Instrumentator

APP_VERSION = os.getenv("APP_VERSION", "4.0.0")
APP_TRACK = os.getenv("APP_TRACK", "stable")

app = FastAPI(title="API de Videojuegos", version=APP_VERSION)

@app.on_event("startup")
async def start_security_heartbeat():
    app.state.security_heartbeat_task = asyncio.create_task(heartbeat_loop())

@app.on_event("shutdown")
async def stop_security_heartbeat():
    task = getattr(app.state, 'security_heartbeat_task', None)
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

@app.middleware('http')
async def security_honeytoken(request: Request, call_next):
    # Deliberately never return secret data or invoke another service.
    decoy_path = os.getenv('SECURITY_HONEYTOKEN_PATH', '')
    if decoy_path.startswith('/.well-known/') and request.url.path == decoy_path:
        from secrets import token_hex
        trace_id = request.headers.get('x-trace-id') or token_hex(16)
        emit('security_event', experiment='telemetry', technique='DECOY_PROBE',
             action='honeytoken_touched', outcome='alert', traceId=trace_id,
             source='http_path')
        return JSONResponse({'detail':'Not Found'},status_code=404,headers={'X-Trace-Id':trace_id})
    return await call_next(request)


@app.middleware("http")
async def identify_release(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-App-Version"] = APP_VERSION
    response.headers["X-App-Track"] = APP_TRACK
    return response

Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# Mantiene el esquema existente. La funcionalidad V3 no requiere cambios destructivos
# ni nuevas columnas: el estado de inventario se calcula a partir de stock.
with engine.begin() as schema_connection:
    if engine.dialect.name == "postgresql":
        schema_connection.execute(text("SELECT pg_advisory_xact_lock(44004000)"))
    Base.metadata.create_all(bind=schema_connection)

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

from app.multicloud import install
install(app)

@app.get("/health/live")
def live():
    return {"status": "ok"}

@app.get("/health/ready")
def ready():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready"}
