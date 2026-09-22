from fastapi import APIRouter, Request
from app.federation import consultar_remotos

router = APIRouter(prefix="/agregado", tags=["Agregado"])

@router.get("/pets")
async def mascotas_de_aws(request: Request):
    token = request.headers.get("Authorization", "")
    params = dict(request.query_params)
    datos, errores = await consultar_remotos("/pets", params, token)
    return {"datos": datos, "errores": errores}