import random
from fastapi import Request
from app.federation import consultar_uno


async def obtener_entidades_companeros(request: Request):
   
    token = request.headers.get("Authorization", "")
    trace_id = getattr(request.state, "trace_id", None)

    pets, error_pets = await consultar_uno("aws", "/pets", {}, token, trace_id)
    tareas, error_tareas = await consultar_uno("objetiva", "/api/v2/tareas", {}, token, trace_id)

    # Filtro defensivo: la API de AWS tiene un bug confirmado donde a
    # veces mezcla un objeto de "tarea" dentro de la lista de /pets.
    # Una mascota de verdad siempre trae el campo "especie"; si no lo
    # tiene, no es una mascota y se descarta antes de elegir al azar.
    pets = [p for p in pets if isinstance(p, dict) and "especie" in p]

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


def construir_respuesta_lista(
    nombre_coleccion: str,
    items: list,
    pets, error_pets, tareas, error_tareas,
) -> dict:
    
    respuesta = {
        nombre_coleccion: items,
        "mascota_relacionada": random.choice(pets) if pets else [],
        "tarea_relacionada": random.choice(tareas) if tareas else [],
    }
    if error_pets:
        respuesta["mascota_error"] = error_pets
    if error_tareas:
        respuesta["tarea_error"] = error_tareas
    return respuesta