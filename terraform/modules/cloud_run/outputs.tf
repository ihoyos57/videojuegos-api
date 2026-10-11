output "service_url" {
  description = "URL pública del servicio Cloud Run"
  value       = google_cloud_run_v2_service.api.uri
}