variable "project_id" {
  description = "ID del proyecto de Google Cloud"
  type        = string
}

variable "runtime_account_id" {
  description = "ID de la cuenta de servicio con la que se ejecuta Cloud Run"
  type        = string
  default     = "videojuegos-api-runtime"
}

variable "database_secret_name" {
  description = "Nombre del secreto con la contraseña de PostgreSQL"
  type        = string
}

variable "deployer_service_account_email" {
  description = "Cuenta de servicio que usa GitHub Actions para desplegar"
  type        = string
}