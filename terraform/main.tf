locals {
  environments = {
    testing = {
      service_name = "videojuegos-api-testing"
      db_schema    = "schema_testing"
    }
    production = {
      service_name = "videojuegos-api-production"
      db_schema    = "schema_production"
    }
  }
}

module "artifact_registry" {
  source = "./modules/artifact_registry"

  project_id    = var.project_id
  region        = var.region
  repository_id = "videojuegos-api"
}

module "cloud_sql" {
  source = "./modules/cloud_sql"

  project_id        = var.project_id
  region            = var.region
  database_name     = var.database_name
  database_user     = var.database_user
  database_tier     = var.database_tier
  database_password = var.database_password
}

module "secret_manager" {
  source = "./modules/secret_manager"

  project_id   = var.project_id
  secret_value = var.database_password
}

resource "google_service_account" "cloud_run" {
  project      = var.project_id
  account_id   = "videojuegos-api-runtime"
  display_name = "Cuenta de servicio para la API de videojuegos"

}

resource "google_project_iam_member" "cloud_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_secret_manager_secret_iam_member" "password_access" {
  project   = var.project_id
  secret_id = module.secret_manager.secret_name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}


module "cloud_run" {
  source   = "./modules/cloud_run"
  for_each = local.environments

  project_id               = var.project_id
  region                   = var.region
  service_name             = each.value.service_name
  container_image          = var.container_image
  database_connection_name = module.cloud_sql.connection_name
  database_name            = module.cloud_sql.database_name
  database_user            = module.cloud_sql.database_user
  database_password_secret = module.secret_manager.secret_name
  db_schema                = each.value.db_schema
  environment              = each.key
  service_account_email    = google_service_account.cloud_run.email

}