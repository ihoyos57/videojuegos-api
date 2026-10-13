module "artifact_registry" {
  source = "./modules/artifact_registry"

  project_id    = var.project_id
  region        = var.region
  repository_id = "videojuegos-api"

  depends_on = [module.apis]
}