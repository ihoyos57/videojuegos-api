from fastapi import APIRouter, Request
from app.federation import consultar_remotos
from app.cache import cached_async, cache_stats, invalidate

router = APIRouter(prefix="/agregado", tags=["Agregado"])



@cached_async("agregado_pets", ignorar_en_clave=("trace_id",))
async def _consultar_pets(params_items, token, trace_id=None):
    return await consultar_remotos("/pets", dict(params_items), token, trace_id)


@router.get("/pets")
async def mascotas_de_aws(request: Request):
    token = request.headers.get("Authorization", "")
    trace_id = getattr(request.state, "trace_id", None)
    params_items = tuple(sorted(request.query_params.items()))
    datos, errores = await _consultar_pets(params_items, token, trace_id)
    return {"datos": datos, "errores": errores}


@cached_async("agregado_tareas", ignorar_en_clave=("trace_id",))
async def _consultar_tareas(params_items, token, trace_id=None):
    return await consultar_remotos("/tareas", dict(params_items), token, trace_id)


@router.get("/tareas")
async def tareas_de_objetiva(request: Request):
    token = request.headers.get("Authorization", "")
    trace_id = getattr(request.state, "trace_id", None)
    params_items = tuple(sorted(request.query_params.items()))
    datos, errores = await _consultar_tareas(params_items, token, trace_id)
    return {"datos": datos, "errores": errores}


@router.get("/cache-stats")
def ver_estadisticas_cache():
    """Para mostrarle al profesor: hits, misses, entradas activas y TTL."""
    return cache_stats()


@router.post("/cache-invalidar")
def limpiar_cache(prefijo: str | None = None):
    """Limpia toda la cache, o solo las entradas de un prefijo (ej: 'agregado_tareas')."""
    return invalidate(prefijo)