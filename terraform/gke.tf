resource "google_container_cluster" "chaos" {
  name                = "videojuegos-chaos"
  location            = var.region
  project             = var.project_id
  enable_autopilot    = true
  deletion_protection = false
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
  depends_on = [module.apis, google_project_iam_member.node_default, google_project_iam_member.node_artifact_reader]
}
resource "google_service_account_iam_member" "gke_identity" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${module.iam.runtime_service_account_email}"
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[chaos/api-ksa]"
  depends_on         = [google_container_cluster.chaos]
}
data "google_project" "current" {
  project_id = var.project_id
}
resource "google_project_iam_member" "node_artifact_reader" {
  project    = var.project_id
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
  depends_on = [module.apis]
}
resource "google_project_iam_member" "node_default" {
  project    = var.project_id
  role       = "roles/container.defaultNodeServiceAccount"
  member     = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
  depends_on = [module.apis]
}
output "gke_cluster_name" { value = google_container_cluster.chaos.name }
output "runtime_service_account_email" { value = module.iam.runtime_service_account_email }
