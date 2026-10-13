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
  for_each = var.deploy_cloud_run ? local.environments : {}

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
  service_account_email    = module.iam.runtime_service_account_email

  depends_on = [
    module.apis,
    module.iam,
  ]
}

variable "deployer_service_account_email" {
  description = "Cuenta de servicio de GitHub Actions que despliega en Cloud Run"
  type        = string
  default     = "github-actions-deployer@videojuegos-api-2026-ihoyos.iam.gserviceaccount.com"
}