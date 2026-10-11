resource "google_artifact_registry_repository" "api" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repository_id
  description   = "Imagenes Docker de la API de videojuegos"
  format        = "DOCKER"
}
