"""
enriquecer.py — Lógica compartida para pegar entidades de los
compañeros (AWS y Azure/Objetiva) a CUALQUIERA de tus 3 entidades
propias (juegos, jugadores, compras).

Se usa igual desde juegos.py, jugadores.py y compras.py: así
garantizamos que los 3 se comporten exactamente igual, como pide
el enunciado.
"""

import random
from fastapi import Request
from app.federation import consultar_uno


async def obtener_entidades_companeros(request: Request):
    """
    Trae, EN TIEMPO REAL, la lista de pets (AWS) y tareas (Azure).
    Gracias a la caché en consultar_uno, si ya se pidió hace menos
    de 30s no se repite la llamada de red.
    """
    token = request.headers.get("Authorization", "")
    trace_id = getattr(request.state, "trace_id", None)

    pets, error_pets = await consultar_uno("aws", "/pets", {}, token, trace_id)
    tareas, error_tareas = await consultar_uno("objetiva", "/api/v2/tareas", {}, token, trace_id)

    return pets, error_pets, tareas, error_tareas


def agregar_relacionados(data: dict, pets, error_pets, tareas, error_tareas) -> dict:
    """
    Pega una mascota y una tarea al azar al diccionario de TU entidad
    (juego, jugador o compra — no importa cuál).

    Si la nube remota SÍ tiene datos, se pega UN objeto al azar
    (no una lista). Si la nube remota no tiene datos (lista vacía)
    o falló la conexión, se deja una lista vacía [] en vez de null,
    como pediste — así siempre queda claro visualmente que "no hay
    nada", sin usar null.
    """
    data["mascota_relacionada"] = random.choice(pets) if pets else []
    data["tarea_relacionada"] = random.choice(tareas) if tareas else []

    # Se deja el motivo del fallo solo si lo hubo, para que sea fácil
    # de depurar en la demo sin ensuciar la respuesta cuando todo va bien.
    if error_pets:
        data["mascota_error"] = error_pets
    if error_tareas:
        data["tarea_error"] = error_tareas

    return data