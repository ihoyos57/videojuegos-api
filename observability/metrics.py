"""Métricas Prometheus propias del servicio (se envían a Grafana Cloud vía Alloy).

Alloy raspa /metrics dentro de la instancia y añade las etiquetas track,
app_version y revision, por lo que aquí no hace falta etiquetar por versión.

Señales cubiertas:
  - Tráfico, errores y latencia: las expone prometheus_fastapi_instrumentator.
  - Saturación: process_cpu_seconds_total / process_resident_memory_bytes
    (colectores por defecto) + límites del contenedor (cgroup) definidos abajo.
  - Negocio: videojuegos_compras_creadas_total y videojuegos_ventas_monto_total.
"""
from __future__ import annotations

import os
from pathlib import Path

from prometheus_client import Counter, Gauge

COMPRAS_CREADAS = Counter(
    "videojuegos_compras_creadas_total",
    "Compras confirmadas correctamente por esta instancia.",
)
VENTAS_MONTO = Counter(
    "videojuegos_ventas_monto_total",
    "Suma del total (moneda del catálogo) de las compras confirmadas.",
)

APP_INFO = Gauge(
    "videojuegos_app_info",
    "Identidad de la revisión en ejecución (valor siempre 1).",
    ["app_version", "track", "revision"],
)
APP_INFO.labels(
    app_version=os.getenv("APP_VERSION", "unknown"),
    track=os.getenv("APP_TRACK", "stable"),
    revision=os.getenv("K_REVISION", "local"),
).set(1)


def _memory_limit_bytes() -> float:
    """Límite de memoria del contenedor (cgroup v2, luego v1). 0 si no hay límite."""
    for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            raw = Path(path).read_text().strip()
        except OSError:
            continue
        if raw.isdigit() and int(raw) < 1 << 60:
            return float(raw)
    return 0.0


def _cpu_limit_cores() -> float:
    """Límite de CPU del contenedor en núcleos (cgroup v2). 0 si no hay límite."""
    try:
        quota, period = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if quota != "max":
            return int(quota) / int(period)
    except (OSError, ValueError):
        pass
    return 0.0


Gauge("videojuegos_memory_limit_bytes", "Límite de memoria del contenedor.").set_function(_memory_limit_bytes)
Gauge("videojuegos_cpu_limit_cores", "Límite de CPU del contenedor en núcleos.").set_function(_cpu_limit_cores)


def registrar_compra_creada(total: float | None = None) -> None:
    """Incrementa las métricas de negocio. Nunca lanza: la compra ya fue confirmada."""
    COMPRAS_CREADAS.inc()
    if total is not None:
        try:
            VENTAS_MONTO.inc(float(total))
        except (TypeError, ValueError):
            pass
