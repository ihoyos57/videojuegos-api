from app.cache import cache_stats
from fastapi import APIRouter, Request
from app.federation import consultar_remotos

router = APIRouter(prefix="/agregado", tags=["Agregado"])

@cached_async("agregado_pets")
async def _consultar_pets(params_items, token):
    return await consultar_remotos("/pets", dict(params_items), token)


@router.get("/pets")
async def mascotas_de_aws(request: Request):
    token = request.headers.get("Authorization", "")
    params = dict(request.query_params)
    datos, errores = await _consultar_pets(params, token)
    return {"datos": datos, "errores": errores}

@cached_async("agregado_tareas")
async def _consultar_tareas(params_items, token):
    return await consultar_remotos("/tareas", dict(params_items), token)

@router.get("/tareas")
async def tareas_de_objetiva(request: Request):
    token = request.headers.get("Authorization", "")
    params = dict(request.query_params)
    datos, errores = await _consultar_tareas(params, token)
    return {"datos": datos, "errores": errores}

@router.get("/cache-stats")
def ver_estadisticas_cache():
    """Para mostrarle al profesor: hits, misses, entradas activas y TTL."""
    return cache_stats()
 


 