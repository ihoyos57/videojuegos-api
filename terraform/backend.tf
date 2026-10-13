terraform {
  backend "gcs" {
    bucket = "videojuegos-api-2026-ihoyos-tfstate"
    prefix = "videojuegos-api/terraform/state"
  }
}
