module "iam" {
  source = "./modules/iam"

  project_id                     = var.project_id
  database_secret_name           = module.secret_manager.secret_name
  deployer_service_account_email = var.deployer_service_account_email

  depends_on = [module.apis]
}