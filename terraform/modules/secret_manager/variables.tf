variable "project_id" {
  type = string
}

variable "secret_id" {
  type = string
  default = "videojuegos-db-password"
}

variable "secret_value" {
  type      = string
  sensitive = true
}