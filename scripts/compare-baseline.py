#!/usr/bin/env python3
"""Prueba concurrente y comparación HTTP directa entre stable y canary."""
from __future__ import annotations
import concurrent.futures
import json
import math
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

STABLE_URL = os.environ["STABLE_URL"].rstrip("/")
CANARY_URL = os.environ["CANARY_URL"].rstrip("/")
STABLE_PATH = os.getenv("STABLE_PATH", "/api/v2/juegos/")
CANARY_PATH = os.getenv("CANARY_PATH", "/api/v3/juegos/")
REQUESTS = int(os.getenv("REQUESTS_PER_REVISION", "1000"))
CONCURRENCY = int(os.getenv("CONCURRENCY", "20"))
TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
MAX_5XX = float(os.getenv("MAX_5XX_RATE", "0.01"))
MAX_4XX = float(os.getenv("MAX_4XX_RATE", "0.05"))
MAX_P95_MS = float(os.getenv("MAX_P95_LATENCY_MS", "500"))
MAX_REGRESSION = float(os.getenv("MAX_P95_REGRESSION_PERCENT", "20"))
MIN_REQUESTS = int(os.getenv("MIN_REQUESTS_PER_REVISION", "1000"))
MAX_CPU = float(os.getenv("MAX_CPU_UTILIZATION", "0.80"))
MAX_MEMORY = float(os.getenv("MAX_MEMORY_UTILIZATION", "0.85"))
PROJECT_ID = os.getenv("PROJECT_ID", "")
REGION = os.getenv("REGION", "us-central1")
SERVICE = os.getenv("SERVICE", "videojuegos-api-production")


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("inf")
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(p * len(ordered)) - 1))
    return ordered[index]


def wilson_upper_bound(errors: int, total: int, z: float = 1.96) -> float:
    """Límite superior Wilson al 95% para la proporción de errores."""
    if total <= 0:
        return 1.0
    p = errors / total
    denominator = 1 + z * z / total
    center = p + z * z / (2 * total)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return min(1.0, (center + margin) / denominator)


def request_once(base: str, path: str) -> tuple[int, float]:
    url = base + path
    req = urllib.request.Request(url, headers={"User-Agent": "videojuegos-canary-quality-gate/1.0"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.read()
    except Exception:
        status = 599
    return status, (time.perf_counter() - started) * 1000


def run_track(name: str, base: str, path: str) -> dict:
    started = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        results = list(pool.map(lambda _: request_once(base, path), range(REQUESTS)))
    statuses = [status for status, _ in results]
    latencies = [latency for _, latency in results]
    total = len(results)
    return {
        "track": name,
        "requests": total,
        "duration_seconds": round(time.time() - started, 3),
        "http_2xx": sum(200 <= s < 300 for s in statuses),
        "http_4xx": sum(400 <= s < 500 for s in statuses),
        "http_5xx_or_network": sum(s >= 500 for s in statuses),
        "error_rate_4xx": round(sum(400 <= s < 500 for s in statuses) / total, 5) if total else 1,
        "error_rate_5xx": round(sum(s >= 500 for s in statuses) / total, 5) if total else 1,
        "error_rate_5xx_wilson_upper_95": round(wilson_upper_bound(sum(s >= 500 for s in statuses), total), 5),
        "latency_p50_ms": round(percentile(latencies, .50), 2),
        "latency_p95_ms": round(percentile(latencies, .95), 2),
        "latency_p99_ms": round(percentile(latencies, .99), 2),
    }



def cloud_monitoring_max(revision: str, metric_type: str) -> float:
    """Obtiene el máximo reciente de una métrica nativa de Cloud Run."""
    token = os.getenv("GOOGLE_OAUTH_ACCESS_TOKEN")
    if not token:
        token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=10)
    metric_filter = (
        'resource.type="cloud_run_revision" '
        f'AND resource.labels.service_name="{SERVICE}" ' 
        f'AND resource.labels.revision_name="{revision}" ' 
        f'AND resource.labels.location="{REGION}" ' 
        f'AND metric.type="{metric_type}"'
    )
    params = urllib.parse.urlencode({
        "filter": metric_filter,
        "interval.startTime": start.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "interval.endTime": end.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "aggregation.alignmentPeriod": "60s",
        "aggregation.perSeriesAligner": "ALIGN_MAX",
        "pageSize": "100",
    })
    url = f"https://monitoring.googleapis.com/v3/projects/{PROJECT_ID}/timeSeries?{params}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    values: list[float] = []
    for series in payload.get("timeSeries", []):
        for point in series.get("points", []):
            value = point.get("value", {})
            raw = value.get("doubleValue", value.get("int64Value"))
            if raw is not None:
                values.append(float(raw))
    if not values:
        raise RuntimeError(f"Sin datos recientes de Cloud Monitoring: {metric_type} / {revision}")
    return max(values)


def read_resource_metrics(revision: str) -> dict:
    last_error = None
    for attempt in range(4):
        try:
            return {
                "cpu_utilization_max": round(cloud_monitoring_max(revision, "run.googleapis.com/container/cpu/utilizations"), 4),
                "memory_utilization_max": round(cloud_monitoring_max(revision, "run.googleapis.com/container/memory/utilizations"), 4),
            }
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(30)
    raise RuntimeError(f"No se pudieron consultar CPU/memoria de {revision}: {last_error}")


def main() -> int:
    # Ambos tracks se prueban simultáneamente para reducir sesgo temporal.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as outer:
        stable_future = outer.submit(run_track, "stable", STABLE_URL, STABLE_PATH)
        canary_future = outer.submit(run_track, "canary", CANARY_URL, CANARY_PATH)
        stable = stable_future.result()
        canary = canary_future.result()

    regression = ((canary["latency_p95_ms"] / stable["latency_p95_ms"]) - 1) * 100 if stable["latency_p95_ms"] > 0 else 0
    resource_metrics_error = None
    try:
        stable_resources = read_resource_metrics(os.environ["STABLE_REVISION"])
        canary_resources = read_resource_metrics(os.environ["CANARY_REVISION"])
    except Exception as exc:
        stable_resources = None
        canary_resources = None
        resource_metrics_error = str(exc)
    checks = {
        "minimum_sample": stable["requests"] >= MIN_REQUESTS and canary["requests"] >= MIN_REQUESTS,
        "stable_5xx_slo_95_confidence": stable["error_rate_5xx_wilson_upper_95"] <= MAX_5XX,
        "canary_5xx_slo_95_confidence": canary["error_rate_5xx_wilson_upper_95"] <= MAX_5XX,
        "canary_4xx_slo": canary["error_rate_4xx"] <= MAX_4XX,
        "canary_p95_slo": canary["latency_p95_ms"] <= MAX_P95_MS,
        "p95_regression_slo": regression <= MAX_REGRESSION,
        "canary_cpu_slo": canary_resources is not None and canary_resources["cpu_utilization_max"] <= MAX_CPU,
        "canary_memory_slo": canary_resources is not None and canary_resources["memory_utilization_max"] <= MAX_MEMORY,
    }
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "concurrency_per_revision": CONCURRENCY,
        "stable": stable,
        "canary": canary,
        "stable_resources": stable_resources,
        "canary_resources": canary_resources,
        "resource_metrics_error": resource_metrics_error,
        "p95_regression_percent": round(regression, 2),
        "thresholds": {"max_5xx_rate_wilson_upper_95": MAX_5XX, "max_4xx_rate": MAX_4XX, "max_p95_latency_ms": MAX_P95_MS,
                       "max_p95_regression_percent": MAX_REGRESSION, "max_cpu_utilization": MAX_CPU, "max_memory_utilization": MAX_MEMORY, "minimum_requests": MIN_REQUESTS},
        "checks": checks,
        "decision": "promote" if all(checks.values()) else "rollback",
    }
    print(json.dumps(report, indent=2))
    os.makedirs("reports", exist_ok=True)
    with open(f"reports/comparison-{int(time.time())}.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0 if report["decision"] == "promote" else 2


if __name__ == "__main__":
    raise SystemExit(main())
