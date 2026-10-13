resource "google_service_account" "cloud_run" {
  project      = var.project_id
  account_id   = var.runtime_account_id
  display_name = "Cuenta de servicio para la API de videojuegos"
}

resource "google_project_iam_member" "cloud_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_secret_manager_secret_iam_member" "password_access" {
  secret_id = var.database_secret_name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_service_account_iam_member" "deployer_uses_runtime" {
  service_account_id = google_service_account.cloud_run.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.deployer_service_account_email}"
}