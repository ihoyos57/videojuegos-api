output "artifact_registry_repository_id" {
  description = "Identificador del repositorio de imágenes Docker"
  value       = module.artifact_registry.repository_id
}

output "artifact_registry_repository_url" {
  description = "URL del repositorio de imágenes Docker"
  value       = module.artifact_registry.repository_url
}

output "cloud_sql_connection_name" {
  description = "Identificador de conexión de Cloud SQL"
  value       = module.cloud_sql.connection_name
}

output "cloud_sql_database_name" {
  description = "Nombre de la base de datos PostgreSQL"
  value       = module.cloud_sql.database_name
}

output "testing_api_url" {
  description = "URL pública de la API de pruebas (null si Cloud Run no está desplegado)"
  value       = try(module.cloud_run["testing"].service_url, null)
}

output "production_api_url" {
  description = "URL pública de la API de producción (null si Cloud Run no está desplegado)"
  value       = try(module.cloud_run["production"].service_url, null)
}