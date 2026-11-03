"""Métrica de negocio acumulativa enviada a Cloud Monitoring por instancia."""
from __future__ import annotations

import logging
import os
import socket
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
_PROCESS_START = datetime.now(timezone.utc)
_PURCHASE_COUNT = 0
_LOCK = threading.Lock()


def registrar_compra_creada() -> None:
    """Incrementa compras confirmadas y publica el acumulado de esta instancia.

    Cada instancia de Cloud Run tiene su propia serie temporal (generic_task),
    evitando intervalos DELTA solapados cuando llegan compras concurrentes.
    """
    global _PURCHASE_COUNT
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or os.getenv("PROJECT_ID")
    if not project_id:
        logger.debug("Sin proyecto GCP: se omite la métrica de compra.")
        return

    try:
        from google.cloud import monitoring_v3
        from google.protobuf.timestamp_pb2 import Timestamp

        with _LOCK:
            _PURCHASE_COUNT += 1
            current_count = _PURCHASE_COUNT
            now = datetime.now(timezone.utc)

            client = monitoring_v3.MetricServiceClient()
            start = Timestamp()
            start.FromDatetime(_PROCESS_START)
            end = Timestamp()
            end.FromDatetime(now)

            series = monitoring_v3.TimeSeries()
            series.metric.type = "custom.googleapis.com/videojuegos/compras_creadas"
            series.metric.labels["app_version"] = os.getenv("APP_VERSION", "unknown")
            series.metric.labels["track"] = os.getenv("APP_TRACK", "stable")
            series.resource.type = "generic_task"
            series.resource.labels["project_id"] = project_id
            series.resource.labels["location"] = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
            series.resource.labels["namespace"] = os.getenv("K_SERVICE", "videojuegos-api")
            series.resource.labels["job"] = os.getenv("K_REVISION", "local")
            series.resource.labels["task_id"] = os.getenv("HOSTNAME", socket.gethostname())

            point = monitoring_v3.Point()
            point.interval.start_time = start
            point.interval.end_time = end
            point.value.int64_value = current_count
            series.points.append(point)
            series.metric_kind = monitoring_v3.MetricDescriptor.MetricKind.CUMULATIVE
            series.value_type = monitoring_v3.MetricDescriptor.ValueType.INT64
            client.create_time_series(name=f"projects/{project_id}", time_series=[series], timeout=3.0)
    except Exception:
        # La compra ya fue confirmada: un fallo de telemetría no revierte negocio.
        logger.exception("No fue posible enviar compras_creadas a Cloud Monitoring.")
