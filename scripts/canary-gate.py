#!/usr/bin/env python3
"""Puerta de análisis (quality gate) del despliegue canary.

Consulta Grafana Cloud (API de Prometheus) y compara el canary contra el baseline
stable usando los umbrales versionados en observability/slo.yaml.

Decisión por etapa:
  PROMOVER -> exit 0   (todas las métricas en zona de promoción y muestra suficiente)
  ABORTAR  -> exit 2   (alguna métrica en zona de aborto, o se agotaron los reintentos)
  PAUSA    -> espera `pause.retry_seconds` y vuelve a evaluar (hasta `pause.max_retries`)

Variables de entorno:
  GRAFANA_PROM_URL           p. ej. https://prometheus-prod-66-prod-us-east-3.grafana.net/api/prom
  GRAFANA_METRICS_USER       ID de instancia de Prometheus (número)
  GRAFANA_METRICS_READ_TOKEN token con scope metrics:read
  GRAFANA_URL, GRAFANA_API_TOKEN   (opcional) para marcar en el dashboard cada decisión
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("Falta PyYAML: pip install pyyaml")

SLO_FILE = os.getenv("SLO_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "observability", "slo.yaml"))


def load_slo() -> dict:
    with open(SLO_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ----------------------------- consultas a Grafana -----------------------------
def render(query: str, slo: dict, track: str, window: str) -> str:
    values = {
        "service": slo["service"]["name"], "track": track, "window": window,
        "cpu_cores": slo["container"]["cpu_cores"], "memory_bytes": slo["container"]["memory_bytes"],
    }
    for key, val in values.items():
        query = query.replace("{{" + key + "}}", str(val))
    return query


def prom_query(query: str) -> float | None:
    """Ejecuta una consulta instantánea. None si no hay datos o el valor es NaN."""
    base = os.environ["GRAFANA_PROM_URL"].rstrip("/")
    cred = f'{os.environ["GRAFANA_METRICS_USER"]}:{os.environ["GRAFANA_METRICS_READ_TOKEN"]}'
    req = urllib.request.Request(
        f"{base}/api/v1/query?" + urllib.parse.urlencode({"query": query}),
        headers={"Authorization": "Basic " + base64.b64encode(cred.encode()).decode()},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    if payload.get("status") != "success":
        raise RuntimeError(f"Grafana respondió {payload}")
    result = payload["data"]["result"]
    if not result:
        return None
    value = float(result[0]["value"][1])
    return None if math.isnan(value) or math.isinf(value) else value


def collect(slo: dict, track: str, window: str) -> dict:
    q = {name: prom_query(render(text, slo, track, window)) for name, text in slo["queries"].items()}
    total = q["requests"] or 0.0
    errors5, errors4 = (q["requests_5xx"] or 0.0), (q["requests_4xx"] or 0.0)
    return {
        "requests": round(total, 1),
        "error_rate_5xx": errors5 / total if total > 0 else None,
        "error_rate_4xx": errors4 / total if total > 0 else None,
        "latency_p50_ms": q["latency_p50_ms"], "latency_p95_ms": q["latency_p95_ms"],
        "latency_p99_ms": q["latency_p99_ms"],
        "cpu_utilization": q["cpu_utilization"], "memory_utilization": q["memory_utilization"],
    }


# --------------------------------- evaluación ---------------------------------
def zone(value: float | None, promote_max: float, abort_max: float) -> str:
    if value is None:
        return "sin_datos"
    if value <= promote_max:
        return "promote"
    return "pause" if value <= abort_max else "abort"


def evaluate(slo: dict, canary: dict, stable: dict) -> tuple[str, list[dict], list[str]]:
    thresholds, sample = slo["slo"], slo["sample"]
    checks: list[dict] = []
    reasons: list[str] = []

    if canary["requests"] < sample["min_requests_canary"]:
        reasons.append(f'muestra insuficiente del canary: {canary["requests"]:.0f} < {sample["min_requests_canary"]}')
        return "pause", checks, reasons

    for name in ("error_rate_5xx", "error_rate_4xx", "latency_p95_ms", "cpu_utilization", "memory_utilization"):
        t = thresholds[name]
        checks.append({"metric": name, "value": canary[name], "promote_max": t["promote_max"],
                       "abort_max": t["abort_max"], "zone": zone(canary[name], t["promote_max"], t["abort_max"])})

    # Comparación contra el baseline (solo si stable tiene muestra suficiente en la ventana).
    t = thresholds["latency_p95_regression_percent"]
    c95, s95 = canary["latency_p95_ms"], stable["latency_p95_ms"]
    if stable["requests"] >= sample["min_requests_stable"] and c95 is not None and s95:
        pct = (c95 / s95 - 1) * 100
        z = "promote" if (c95 - s95) <= t["min_abs_diff_ms"] else zone(pct, t["promote_max"], t["abort_max"])
        checks.append({"metric": "latency_p95_regression_percent", "value": round(pct, 2),
                       "promote_max": t["promote_max"], "abort_max": t["abort_max"], "zone": z})
    else:
        checks.append({"metric": "latency_p95_regression_percent", "value": None, "promote_max": t["promote_max"],
                       "abort_max": t["abort_max"], "zone": "omitida",
                       "note": f'stable con {stable["requests"]:.0f} peticiones (mínimo {sample["min_requests_stable"]})'})

    aborts = [c for c in checks if c["zone"] == "abort"]
    if aborts:
        reasons += [f'{c["metric"]}={c["value"]:.4g} > {c["abort_max"]}' for c in aborts]
        return "abort", checks, reasons
    pending = [c for c in checks if c["zone"] in ("pause", "sin_datos")]
    if pending:
        reasons += [f'{c["metric"]} en zona {c["zone"]} (valor {c["value"]})' for c in pending]
        return "pause", checks, reasons
    return "promote", checks, reasons


# ---------------------------------- anotación ----------------------------------
def annotate(text: str, tags: list[str]) -> None:
    """Marca la decisión en el dashboard de Grafana. Nunca interrumpe la decisión."""
    url, token = os.getenv("GRAFANA_URL"), os.getenv("GRAFANA_API_TOKEN")
    if not url or not token:
        return
    try:
        body = json.dumps({"time": int(time.time() * 1000), "tags": ["canary-gate"] + tags, "text": text}).encode()
        req = urllib.request.Request(url.rstrip("/") + "/api/annotations", data=body, method="POST",
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as exc:  # noqa: BLE001
        print(f"[gate] no se pudo anotar en Grafana: {exc}", file=sys.stderr)


# ------------------------------------ main ------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", type=int)
    ap.add_argument("--canary-percent", type=int)
    ap.add_argument("--stage-start", type=int, help="Epoch en que empezó la etapa (define la ventana de análisis)")
    ap.add_argument("--settle-seconds", type=int, help="Sobrescribe rollout.scrape_settle_seconds")
    ap.add_argument("--retry-seconds", type=int, help="Sobrescribe pause.retry_seconds")
    ap.add_argument("--report-dir", default="reports")
    ap.add_argument("--print-env", action="store_true", help="Imprime los umbrales de aborto como variables de entorno")
    a = ap.parse_args()
    slo = load_slo()

    if a.print_env:  # usado por canary-rollout.sh: slo.yaml es la única fuente de verdad
        s = slo["slo"]
        print(f'export MAX_5XX_RATE={s["error_rate_5xx"]["abort_max"]}')
        print(f'export MAX_4XX_RATE={s["error_rate_4xx"]["abort_max"]}')
        print(f'export MAX_P95_LATENCY_MS={s["latency_p95_ms"]["abort_max"]}')
        print(f'export MAX_P95_REGRESSION_PERCENT={s["latency_p95_regression_percent"]["abort_max"]}')
        return 0
    if a.stage is None or a.canary_percent is None:
        ap.error("--stage y --canary-percent son obligatorios")

    settle = a.settle_seconds if a.settle_seconds is not None else slo["rollout"]["scrape_settle_seconds"]
    retry = a.retry_seconds if a.retry_seconds is not None else slo["pause"]["retry_seconds"]
    max_retries = slo["pause"]["max_retries"]
    print(f"[gate] etapa {a.stage} ({a.canary_percent}% canary): esperando {settle}s a que Grafana reciba las últimas muestras")
    time.sleep(settle)

    decision, checks, reasons, canary, stable, window = "pause", [], [], {}, {}, ""
    for attempt in range(max_retries + 1):
        # La ventana empieza con la etapa: no se mezclan datos de etapas anteriores.
        window = f"{int(time.time() - a.stage_start) + 15}s" if a.stage_start else slo["rollout"]["evaluation_window"]
        canary = collect(slo, slo["service"]["canary_track"], window)
        stable = collect(slo, slo["service"]["stable_track"], window)
        decision, checks, reasons = evaluate(slo, canary, stable)
        print(f"[gate] intento {attempt + 1}/{max_retries + 1} ventana={window} canary={canary['requests']:.0f} "
              f"stable={stable['requests']:.0f} -> {decision.upper()} {reasons}")
        if decision != "pause":
            break
        if attempt < max_retries:
            time.sleep(retry)
    if decision == "pause":
        decision = "abort"
        reasons.append(f"reintentos de pausa agotados ({max_retries})")

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(), "stage": a.stage,
        "canary_percent": a.canary_percent, "window": window, "decision": decision.upper(),
        "reasons": reasons, "canary": canary, "stable": stable, "checks": checks,
    }
    os.makedirs(a.report_dir, exist_ok=True)
    with open(os.path.join(a.report_dir, f"gate-stage{a.stage}-{int(time.time())}.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))

    verb = "PROMOVER" if decision == "promote" else "ABORTAR (rollback a 100% stable)"
    annotate(f"Etapa {a.stage} ({a.canary_percent}% canary): {verb}. {'; '.join(reasons)}",
             [f"stage-{a.stage}", decision])
    return 0 if decision == "promote" else 2


if __name__ == "__main__":
    raise SystemExit(main())
