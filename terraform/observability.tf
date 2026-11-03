
# Observabilidad nativa para el servicio de Cloud Run production.
# El dashboard compara las revisiones; las alertas notifican degradaciones.

resource "google_project_iam_member" "cloud_run_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${module.iam.runtime_service_account_email}"
}

resource "google_monitoring_dashboard" "canary" {
  project        = var.project_id
  dashboard_json = file("${path.module}/../observability/dashboard.json")
}

resource "google_monitoring_alert_policy" "canary_latency_p95" {
  project      = var.project_id
  display_name = "Videojuegos API - Latencia p95 elevada"
  combiner     = "OR"

  conditions {
    display_name = "Latencia p95 superior a 500 ms en Cloud Run"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"videojuegos-api-production\" AND resource.labels.revision_name=monitoring.regex.full_match(\".*-v3-.*\") AND metric.type=\"run.googleapis.com/request_latencies\""
      comparison      = "COMPARISON_GT"
      threshold_value = 500
      duration        = "120s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_PERCENTILE_95"
      }

      trigger {
        count = 1
      }
    }
  }

  documentation {
    content   = "Revisar el dashboard Videojuegos API - Canary Observability. El quality gate del workflow ejecuta rollback si el canary incumple los SLO."
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "1800s"
  }

  depends_on = [google_project_iam_member.cloud_run_metric_writer]
}

resource "google_monitoring_alert_policy" "canary_cpu" {
  project      = var.project_id
  display_name = "Videojuegos API - CPU elevada"
  combiner     = "OR"

  conditions {
    display_name = "Percentil 95 de utilización de CPU superior al 80%"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"videojuegos-api-production\" AND resource.labels.revision_name=monitoring.regex.full_match(\".*-v3-.*\") AND metric.type=\"run.googleapis.com/container/cpu/utilizations\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.80
      duration        = "180s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_PERCENTILE_95"
      }

      trigger {
        count = 1
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

resource "google_monitoring_alert_policy" "canary_memory" {
  project      = var.project_id
  display_name = "Videojuegos API - Memoria elevada"
  combiner     = "OR"

  conditions {
    display_name = "Percentil 95 de utilización de memoria superior al 85%"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"videojuegos-api-production\" AND resource.labels.revision_name=monitoring.regex.full_match(\".*-v3-.*\") AND metric.type=\"run.googleapis.com/container/memory/utilizations\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.85
      duration        = "180s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_PERCENTILE_95"
      }

      trigger {
        count = 1
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

resource "google_monitoring_alert_policy" "canary_5xx" {
  project      = var.project_id
  display_name = "Videojuegos API - Incremento de errores HTTP 5xx"
  combiner     = "OR"

  conditions {
    display_name = "Se detectan errores 5xx en Cloud Run"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"videojuegos-api-production\" AND resource.labels.revision_name=monitoring.regex.full_match(\".*-v3-.*\") AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.01
      duration        = "120s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }

      trigger {
        count = 1
      }
    }
  }

  documentation {
    content   = "Se detectó una tasa sostenida de respuestas HTTP 5xx. Consultar el dashboard y ejecutar/validar rollback del canary."
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

resource "google_project_iam_member" "github_monitoring_viewer" {
  project = var.project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${var.deployer_service_account_email}"
}
