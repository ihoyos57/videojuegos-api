output "enabled_apis" {
  description = "APIs habilitadas en el proyecto"
  value       = [for api in google_project_service.required : api.service]
}