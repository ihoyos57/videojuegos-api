import os
import asyncio
import logging
import httpx

from app.cache import cached_async

logger = logging.getLogger("trace")

REMOTOS = {
    "aws": os.getenv("AWS_API_URL"),
    "objetiva": os.getenv("OBJETIVA_API_URL"),
    # "azure": os.getenv("AZURE_API_URL"),  # se agrega cuando tengan la URL
}


async def _consultar(client, origen, base_url, ruta, params, token, trace_id=None):
    if not base_url:
        logger.warning(f"[trace_id={trace_id}] {origen}: URL no configurada")
        return origen, [], "URL no configurada"

    logger.info(f"[trace_id={trace_id}] Consultando {origen} -> {base_url}{ruta}")

    try:
        headers = {}
        if token:
            headers["Authorization"] = token
        if trace_id:
            headers["X-Trace-Id"] = trace_id
        r = await client.get(f"{base_url}{ruta}", params=params, headers=headers, timeout=5.0)
        r.raise_for_status()
        logger.info(f"[trace_id={trace_id}] {origen} respondió OK ({r.status_code})")
        return origen, r.json(), None
    except Exception as e:
        logger.error(f"[trace_id={trace_id}] {origen} FALLÓ: {e}")
        return origen, [], str(e)


async def consultar_remotos(ruta, params, token, trace_id=None):
    """Consulta TODAS las nubes remotas en paralelo (usado por /agregado/*)."""
    async with httpx.AsyncClient() as client:
        resultados = await asyncio.gather(
            *[_consultar(client, o, u, ruta, params, token, trace_id) for o, u in REMOTOS.items()]
        )
    datos, errores = [], {}
    for origen, items, error in resultados:
        if error:
            errores[origen] = error
        for item in items:
            item["origen"] = origen
        datos.extend(items)
    return datos, errores


@cached_async(key_prefix="consultar_uno", ignorar_en_clave=("trace_id",))
async def consultar_uno(origen, ruta, params, token, trace_id=None):
   
    base_url = REMOTOS.get(origen)
    async with httpx.AsyncClient() as client:
        _, items, error = await _consultar(client, origen, base_url, ruta, params, token, trace_id)
    return items, error