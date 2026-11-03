"""Inyección de fallos segura y limitada a la revisión canary."""
from __future__ import annotations

import asyncio
import hmac
import os
from fastapi import Request
from fastapi.responses import JSONResponse


async def aplicar_fallo_canary(request: Request) -> JSONResponse | None:
   
    if os.getenv("APP_TRACK", "stable").lower() != "canary":
        return None
    if os.getenv("ENABLE_CANARY_FAULT_INJECTION", "false").lower() != "true":
        return None

    fault = request.headers.get("X-Canary-Fault", "").strip().lower()
    if not fault:
        return None
    expected = os.getenv("CANARY_FAULT_TOKEN", "")
    supplied = request.headers.get("X-Canary-Fault-Token", "")
    if not expected or not hmac.compare_digest(expected, supplied):
        return JSONResponse(status_code=403, content={"detail": "Inyección de fallos no autorizada"})

    if fault == "latency":
        try:
            delay = min(max(float(os.getenv("CANARY_FAULT_LATENCY_SECONDS", "2")), 0.1), 10.0)
        except ValueError:
            delay = 2.0
        await asyncio.sleep(delay)
        return None
    if fault == "error":
        return JSONResponse(status_code=500, content={"detail": "Fallo canary simulado"})
    return JSONResponse(status_code=400, content={"detail": "Tipo de fallo no válido"})
