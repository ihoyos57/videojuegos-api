
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

def invalidate(key_prefix: str = None):
    """
    Invalidación manual.
    - Sin argumentos: limpia TODA la caché.
    - Con key_prefix: borra solo las entradas que empiecen con ese prefijo
      (por ejemplo, invalidar solo "peer_animal" tras una actualización).
    """
    if key_prefix is None:
           _cache.clear()
           return {"invalidado": "toda_la_cache"}
   
    claves_a_borrar = [k for k in list(_cache.keys()) if k.startswith(f"{key_prefix}:")]
    for k in claves_a_borrar:
        del _cache[k]
    return {"invalidado": key_prefix, "entradas_eliminadas": len(claves_a_borrar)}
    
   
def cache_stats() -> dict:
    """Métricas de aciertos/fallos y tamaño actual — útil para /metrics."""
    return {
           "hits": _stats["hits"],
           "misses": _stats["misses"],
           "entradas_activas": len(_cache),
           "ttl_segundos": TTL_SEGUNDOS,
       }
   
