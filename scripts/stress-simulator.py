#!/usr/bin/env python3
"""Simulador de estrés por etapa para el quality gate del Canary Deployment.

Qué hace:
  1. Genera carga REAL sobre la URL pública del servicio (la que reparte el tráfico),
     en fases con concurrencia creciente (rampa).
  2. Cuenta qué track atendió cada petición leyendo la cabecera X-App-Track y
     comprueba que el reparto observado coincide con el porcentaje de la etapa.
  3. Evalúa por track: tasa de 5xx (límite Wilson 95%), tasa de 4xx, p95 y timeouts.
  4. Si la etapa tiene canary > 0 prueba además el endpoint nuevo de v3 contra la
     URL etiquetada del canary (la URL pública puede mandarlo a stable, que no lo tiene).
  5. Sale con código 0 (pasa) o 2 (falla -> el rollout debe volver a la etapa 0).

Las peticiones públicas usan rutas /api/v2/... porque existen en AMBAS revisiones.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))


def env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("inf")
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, math.ceil(p * len(ordered)) - 1))
    return ordered[idx]


def wilson_upper(errors: int, total: int, z: float = 1.96) -> float:
    if total <= 0:
        return 1.0
    p = errors / total
    den = 1 + z * z / total
    center = p + z * z / (2 * total)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return min(1.0, (center + margin) / den)


def error_rate_ok(summary: dict, limit: float, min_wilson_samples: int = 385) -> bool:
    """Con muestra grande usa el límite Wilson 95%; con muestra pequeña (p. ej. 10% de
    tráfico) el límite Wilson es matemáticamente demasiado holgado/estricto, así que
    se usa la tasa observada (y la prueba directa al canary aporta la muestra grande)."""
    if not summary["requests"]:
        return True
    if summary["requests"] >= min_wilson_samples:
        return summary["rate_5xx_wilson_upper_95"] <= limit
    return summary["rate_5xx"] <= limit


def hit(base: str, path: str, extra: dict | None = None) -> tuple[int, float, str]:
    """Una petición -> (status, latencia_ms, track). 599 = red/timeout."""
    headers = {"User-Agent": "videojuegos-stress-simulator/1.0", **(extra or {})}
    req = urllib.request.Request(base.rstrip("/") + path, headers=headers)
    started = time.perf_counter()
    track, status = "unknown", 599
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            resp.read()
            status = resp.status
            track = resp.headers.get("X-App-Track", "unknown")
    except urllib.error.HTTPError as exc:
        status = exc.code
        track = exc.headers.get("X-App-Track", "unknown")
        exc.read()
    except Exception:
        pass
    return status, (time.perf_counter() - started) * 1000, track


def summarize(samples: list[tuple[int, float, str]]) -> dict:
    total = len(samples)
    if total == 0:
        return {"requests": 0, "http_2xx": 0, "http_4xx": 0, "http_5xx_or_network": 0,
                "rate_4xx": 0.0, "rate_5xx": 0.0, "rate_5xx_wilson_upper_95": 0.0,
                "p50_ms": None, "p95_ms": None, "p99_ms": None}
    lat = [s[1] for s in samples]
    e5 = sum(s[0] >= 500 for s in samples)
    e4 = sum(400 <= s[0] < 500 for s in samples)
    return {
        "requests": total,
        "http_2xx": sum(200 <= s[0] < 300 for s in samples),
        "http_4xx": e4,
        "http_5xx_or_network": e5,
        "rate_4xx": round(e4 / total, 5) if total else 1,
        "rate_5xx": round(e5 / total, 5) if total else 1,
        "rate_5xx_wilson_upper_95": round(wilson_upper(e5, total), 5),
        "p50_ms": round(percentile(lat, .50), 2),
        "p95_ms": round(percentile(lat, .95), 2),
        "p99_ms": round(percentile(lat, .99), 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", type=int, required=True, help="Número de etapa (0,1,2,3)")
    ap.add_argument("--canary-percent", type=int, required=True, help="Porcentaje esperado hacia canary")
    ap.add_argument("--public-url", default=os.getenv("PUBLIC_URL", ""))
    ap.add_argument("--canary-url", default=os.getenv("CANARY_URL", ""))
    ap.add_argument("--requests", type=int, default=int(os.getenv("STRESS_REQUESTS", "600")),
                    help="Total de peticiones públicas de la etapa")
    ap.add_argument("--ramp", default=os.getenv("STRESS_RAMP", "5,10,20"),
                    help="Concurrencias por fase, separadas por coma (rampa de estrés)")
    ap.add_argument("--public-path", default=os.getenv("STRESS_PUBLIC_PATHS", "/api/v2/juegos/,/api/v2/jugadores/"),
                    help="Rutas presentes en stable Y canary, separadas por coma")
    ap.add_argument("--report-dir", default="reports")
    a = ap.parse_args()

    if not a.public_url:
        ap.error("Falta --public-url / PUBLIC_URL")
    if a.canary_percent > 0 and not a.canary_url:
        ap.error("Falta --canary-url / CANARY_URL para etapas con canary > 0")

    max_5xx = env_float("MAX_5XX_RATE", 0.01)
    max_4xx = env_float("MAX_4XX_RATE", 0.05)
    max_p95 = env_float("MAX_P95_LATENCY_MS", 500)
    max_regress = env_float("MAX_P95_REGRESSION_PERCENT", 20)
    min_canary_samples = int(os.getenv("MIN_CANARY_SAMPLES", "30"))

    # Inyección de fallos (demo de rollback): solo el track canary reacciona a estas
    # cabeceras y solo si su revisión se desplegó con ENABLE_CANARY_FAULT_INJECTION=true.
    fault = os.getenv("STRESS_FAULT", "").strip().lower()          # error | latency | ""
    fault_from = int(os.getenv("STRESS_FAULT_FROM_STAGE", "1"))
    fault_headers: dict | None = None
    if fault and a.stage >= fault_from:
        token = os.getenv("CANARY_FAULT_TOKEN", "")
        if not token:
            ap.error("STRESS_FAULT requiere CANARY_FAULT_TOKEN")
        fault_headers = {"X-Canary-Fault": fault, "X-Canary-Fault-Token": token}
        print(f"[etapa {a.stage}] inyectando fallo '{fault}' (solo afecta al canary)")

    paths = [p.strip() for p in a.public_path.split(",") if p.strip()]
    phases = [int(c) for c in a.ramp.split(",") if c.strip()]
    per_phase = max(1, a.requests // len(phases))

    # ---- 0) Calentamiento: el canary estaba en 0% y puede tener 0 instancias; los arranques
    #         en frío no son una regresión del código, así que no se miden.
    if a.canary_percent > 0 and a.canary_url:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            list(pool.map(lambda _: hit(a.canary_url, "/api/v2/juegos/"), range(int(os.getenv("WARMUP_REQUESTS", "25")))))
        print(f"[etapa {a.stage}] calentamiento del canary completado")

    # ---- 1) Carga pública con rampa de concurrencia --------------------------------
    samples: list[tuple[int, float, str]] = []
    phase_reports = []
    for idx, conc in enumerate(phases, 1):
        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=conc) as pool:
            chunk = list(pool.map(lambda i: hit(a.public_url, paths[i % len(paths)], fault_headers), range(per_phase)))
        samples.extend(chunk)
        phase_reports.append({"phase": idx, "concurrency": conc, "requests": per_phase,
                              "duration_s": round(time.time() - t0, 2),
                              "p95_ms": round(percentile([c[1] for c in chunk], .95), 2)})
        print(f"[etapa {a.stage}] fase {idx}/{len(phases)} concurrencia={conc} ok")

    by_track: dict[str, list] = defaultdict(list)
    for s in samples:
        by_track[s[2]].append(s)
    stable = summarize(by_track.get("stable", []))
    canary = summarize(by_track.get("canary", []))
    unknown = len(by_track.get("unknown", []))

    # ---- 2) Reparto observado vs esperado ------------------------------------------
    n = len(samples)
    observed = len(by_track.get("canary", [])) / n * 100 if n else 0.0
    p = a.canary_percent / 100
    # tolerancia = 3 desviaciones estándar binomiales + 2 puntos de margen
    tol = (3 * math.sqrt(p * (1 - p) / n) * 100 + 2) if n else 100
    split_ok = (observed == 0.0) if a.canary_percent == 0 else abs(observed - a.canary_percent) <= tol
    if a.canary_percent == 100:
        split_ok = len(by_track.get("stable", [])) == 0

    # ---- 3) Endpoint nuevo de v3 contra la URL etiquetada canary --------------------
    v3_direct = None
    if a.canary_url:
        n_direct = int(os.getenv("DIRECT_SAMPLES", "100"))
        game_id = 1
        try:  # usa un juego real para que /disponibilidad no devuelva 404 de relleno
            req = urllib.request.Request(a.canary_url.rstrip("/") + "/api/v3/juegos/",
                                         headers=fault_headers or {})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                items = json.loads(resp.read().decode("utf-8"))
                if isinstance(items, list) and items:
                    game_id = items[0].get("id", 1)
        except Exception:
            pass
        # secuencial: línea base sin carga
        direct = [hit(a.canary_url, "/api/v3/juegos/", fault_headers) for _ in range(n_direct)]
        direct += [hit(a.canary_url, f"/api/v3/juegos/{game_id}/disponibilidad", fault_headers)
                   for _ in range(n_direct)]
        v3_direct = summarize(direct)
        # el header solo se evalúa en respuestas recibidas; los timeouts ya cuentan como 5xx/red
        v3_direct["tracks_seen"] = sorted({s_[2] for s_ in direct if s_[0] != 599})
        v3_direct["game_id_probado"] = game_id

    # ---- 4) Checks -----------------------------------------------------------------
    checks = {
        "sin_respuestas_sin_cabecera_track": unknown == 0,
        "reparto_coincide_con_la_etapa": split_ok,
        "stable_5xx": error_rate_ok(stable, max_5xx),
    }
    if a.canary_percent > 0:
        checks["muestra_canary_suficiente"] = canary["requests"] >= min_canary_samples
        checks["canary_5xx"] = error_rate_ok(canary, max_5xx)
        checks["canary_4xx"] = canary["rate_4xx"] <= max_4xx
        checks["canary_p95_abs"] = (canary["p95_ms"] or 0) <= max_p95
        min_reg = int(os.getenv("MIN_REGRESSION_SAMPLES", "200"))
        regression_skipped = canary["requests"] < min_reg
        if (stable["requests"] and canary["requests"] and stable["p95_ms"] and stable["p95_ms"] > 0
                and not regression_skipped):
            regress = (canary["p95_ms"] / stable["p95_ms"] - 1) * 100
            # Regresión relativa solo cuenta si además supera un piso absoluto (ms):
            # evita falsos rollbacks por ruido cuando ambos p95 son de pocos ms.
            floor = env_float("MIN_REGRESSION_ABS_MS", 50)
            checks["canary_p95_regresion"] = regress <= max_regress or (canary["p95_ms"] - stable["p95_ms"]) <= floor
        else:
            regress = None
    else:
        regress = None
    if v3_direct is not None:
        checks["v3_directo_sin_5xx"] = error_rate_ok(v3_direct, max_5xx)
        checks["v3_directo_p95"] = (v3_direct["p95_ms"] or 0) <= max_p95
        checks["v3_directo_header_canary"] = v3_direct["tracks_seen"] == ["canary"]

    failed = [k for k, v in checks.items() if not v]
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": a.stage,
        "expected_canary_percent": a.canary_percent,
        "observed_canary_percent": round(observed, 2),
        "split_tolerance_points": round(tol, 2),
        "ramp": phase_reports,
        "stable": stable,
        "canary": canary,
        "v3_direct_canary_url": v3_direct,
        "p95_regression_percent": None if regress is None else round(regress, 2),
        "p95_regression_note": ("omitida: muestra canary menor que MIN_REGRESSION_SAMPLES (p95 poco fiable)"
                                if a.canary_percent > 0 and regress is None else None),
        "thresholds": {"max_5xx_wilson": max_5xx, "max_4xx": max_4xx,
                       "max_p95_ms": max_p95, "max_p95_regression_percent": max_regress},
        "checks": checks,
        "failed_checks": failed,
        "fault_injected": fault if fault_headers else None,
        "decision": "advance" if not failed else "rollback_to_stage_0",
    }
    os.makedirs(a.report_dir, exist_ok=True)
    path = os.path.join(a.report_dir, f"stress-stage{a.stage}-{int(time.time())}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())