module "apis" {
  source = "./modules/apis"

  project_id = var.project_id

  apis = [
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "container.googleapis.com",
    "compute.googleapis.com",
    "monitoring.googleapis.com",
    "secretmanager.googleapis.com",
    "sqladmin.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
  ]
}