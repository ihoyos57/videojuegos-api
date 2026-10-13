module "cloud_sql" {
  source = "./modules/cloud_sql"

  project_id        = var.project_id
  region            = var.region
  database_name     = var.database_name
  database_user     = var.database_user
  database_tier     = var.database_tier
  database_password = var.database_password

  depends_on = [module.apis]
}