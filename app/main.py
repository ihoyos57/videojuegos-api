from fastapi import FastAPI
from sqlalchemy import text
from app.database import engine

app = FastAPI(title="API de Videojuegos")

@app.get("/")
def root():
    return {"mensaje": "API de Videojuegos funcionando"}

@app.get("/test-db")
def test_db():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        version = result.fetchone()
    return {"conexion": "exitosa", "postgres_version": version[0]}