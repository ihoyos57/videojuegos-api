"""
cache.py — Caché en memoria con expiración (TTL) e invalidación manual.

No depende de servicios externos (no Redis, no Memorystore): usa
cachetools.TTLCache, que vive en la memoria del proceso de tu API.
Sirve perfecto para cachear respuestas de entidades que tú mismo
consultas (ej. datos de tus compañeros por HTTP, o resultados
costosos de tu propia base de datos).

Uso típico:

    from cache import cached, invalidate, cache_stats

    @cached(key_prefix="peer_animal")
    def obtener_animal(animal_id: int):
        # lógica costosa: llamada HTTP a la API de un compañero,
        # o consulta pesada a la BD
        ...
        return resultado

Cada vez que llames obtener_animal(5), si ya está en caché y no ha
expirado, se devuelve al instante sin repetir el trabajo. Si expiró
(o nunca se llamó), se ejecuta la función real y se guarda el
resultado.
"""

import time
import functools
from cachetools import TTLCache

# TTL de 30 segundos: lo que se guarda en caché vive exactamente
# ese tiempo antes de expirar y forzar un recálculo.
TTL_SEGUNDOS = 30
TAMANO_MAXIMO = 256

_cache = TTLCache(maxsize=TAMANO_MAXIMO, ttl=TTL_SEGUNDOS)

# Métricas simples de aciertos/fallos, útiles si luego las expones
# en tu endpoint de monitoreo (la rúbrica pide métricas de caché).
_stats = {"hits": 0, "misses": 0}


def _build_key(prefix: str, args, kwargs) -> str:
    return f"{prefix}:{args}:{sorted(kwargs.items())}"

def cached(key_prefix: str):
    """
    Decorador: cachea el resultado de la función durante TTL_SEGUNDOS.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = _build_key(key_prefix, args, kwargs)

            if key in _cache:
                _stats["hits"] += 1
                return _cache[key]

            _stats["misses"] += 1
            resultado = func(*args, **kwargs)
            _cache[key] = resultado
            return resultado

        return wrapper
    return decorator


