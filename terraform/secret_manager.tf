module "secret_manager" {
  source = "./modules/secret_manager"

  project_id   = var.project_id
  secret_value = var.database_password
}
