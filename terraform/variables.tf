variable "project_id" {
  description = "ID del proyecto de Google Cloud"
  type        = string
}

variable "region" {
  description = "Región de Google Cloud"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Entorno de infraestructura"
  type        = string
  default     = "dev"
}

variable "database_name" {
  description = "Nombre de la base de datos PostgreSQL"
  type        = string
  default     = "videojuegos_db"
}

variable "database_user" {
  description = "Usuario de PostgreSQL"
  type        = string
  default     = "videojuegos_app"
}

variable "database_tier" {
  description = "Tamaño de la instancia Cloud SQL; revisar costos antes de crearla"
  type        = string
  default     = "db-f1-micro"
}

variable "container_image" {
  description = "Imagen Docker de la API publicada en Artifact Registry"
  type        = string
  default     = "us-central1-docker.pkg.dev/videojuegos-api-2026-ihoyos/videojuegos-api/api:latest"
}
