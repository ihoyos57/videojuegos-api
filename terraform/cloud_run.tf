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

  depends_on = [
    google_project_service.required,
    google_project_iam_member.cloud_sql_client,
    google_secret_manager_secret_iam_member.password_access
  ]
}
