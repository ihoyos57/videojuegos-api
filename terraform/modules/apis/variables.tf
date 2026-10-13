variable "project_id" {
  description = "ID del proyecto de Google Cloud"
  type        = string
}

variable "apis" {
  description = "APIs de Google Cloud que se deben habilitar"
  type        = set(string)
}