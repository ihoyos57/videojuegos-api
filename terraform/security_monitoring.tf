# Monitoring is opt-in so applying an unrelated V4 change does not surprise
# the currently running stack. Logs come from the GKE container's JSON stdout.
resource "google_logging_metric" "security_honeytoken" {
  count   = var.enable_security_monitoring ? 1 : 0
  project = var.project_id
  name    = "security_honeytoken_count"
  filter  = "resource.type=\"k8s_container\" AND jsonPayload.event=\"security_event\" AND jsonPayload.action=\"honeytoken_touched\""
  depends_on = [module.apis]
}

resource "google_logging_metric" "security_heartbeat" {
  count   = var.enable_security_monitoring ? 1 : 0
  project = var.project_id
  name    = "security_heartbeat_count"
  filter  = "resource.type=\"k8s_container\" AND jsonPayload.event=\"security_heartbeat\""
  depends_on = [module.apis]
}

resource "google_monitoring_alert_policy" "security_honeytoken" {
  count        = var.enable_security_monitoring ? 1 : 0
  project      = var.project_id
  display_name = "Videojuegos security honeytoken touched"
  combiner     = "OR"
  conditions {
    display_name = "Decoy path hit"
    condition_threshold {
      filter          = "resource.type=\"k8s_container\" AND metric.type=\"logging.googleapis.com/user/security_honeytoken_count\""
      duration        = "0s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_DELTA"
      }
    }
  }
  depends_on = [google_logging_metric.security_honeytoken]
}

resource "google_monitoring_alert_policy" "security_heartbeat_absent" {
  count        = var.enable_security_monitoring ? 1 : 0
  project      = var.project_id
  display_name = "Videojuegos security heartbeat absent"
  combiner     = "OR"
  conditions {
    display_name = "Heartbeat absent for 120 seconds"
    condition_absent {
      filter   = "resource.type=\"k8s_container\" AND metric.type=\"logging.googleapis.com/user/security_heartbeat_count\""
      duration = "120s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_DELTA"
      }
    }
  }
  depends_on = [google_logging_metric.security_heartbeat]
}
