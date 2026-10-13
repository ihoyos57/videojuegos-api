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
