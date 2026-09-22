import os
import asyncio
import httpx

REMOTOS = {
    "aws": os.getenv("AWS_API_URL"),
    # "azure": os.getenv("AZURE_API_URL"),  # se agrega cuando tengas la URL
}

async def _consultar(client, origen, base_url, ruta, params, token):
    if not base_url:
        return origen, [], "URL no configurada"
    try:
        headers = {"Authorization": token} if token else {}
        r = await client.get(f"{base_url}{ruta}", params=params, headers=headers, timeout=5.0)
        r.raise_for_status()
        return origen, r.json(), None
    except Exception as e:
        return origen, [], str(e)

async def consultar_remotos(ruta, params, token):
    async with httpx.AsyncClient() as client:
        resultados = await asyncio.gather(
            *[_consultar(client, o, u, ruta, params, token) for o, u in REMOTOS.items()]
        )
    datos, errores = [], {}
    for origen, items, error in resultados:
        if error:
            errores[origen] = error
        for item in items:
            item["origen"] = origen
        datos.extend(items)
    return datos, errores