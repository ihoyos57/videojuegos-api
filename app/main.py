from fastapi import FastAPI

app = FastAPI(title="API de Videojuegos")

@app.get("/")
def root():
    return {"mensaje": "API de Videojuegos funcionando"}