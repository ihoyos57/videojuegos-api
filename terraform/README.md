# Infraestructura como código con Terraform

## 1. Descripción

Configuración de Terraform para aprovisionar en Google Cloud la infraestructura de la API de videojuegos. Cada servicio está en un módulo independiente dentro de `modules/`, y cada archivo de la raíz solo invoca su módulo.

## 2. Servicios de Google Cloud

| Servicio | Módulo | Función |
|---|---|---|
| Cloud Run | `modules/cloud_run` | Ejecuta la API en pruebas y producción |
| Cloud SQL | `modules/cloud_sql` | PostgreSQL 16 (edición Enterprise, `db-f1-micro`) |
| Artifact Registry | `modules/artifact_registry` | Imágenes Docker de la API |
| Secret Manager | `modules/secret_manager` | Contraseña de la base de datos |
| IAM | `modules/iam` | Cuenta de servicio de ejecución y permisos |
| Service Usage | `modules/apis` | Habilita las APIs de Google Cloud necesarias |
| Cloud Storage | (creado a mano) | Bucket con el estado remoto de Terraform |

## 3. Organización

```
terraform/
├── apis.tf                → module "apis"
├── artifact_registry.tf   → module "artifact_registry"
├── cloud_sql.tf           → module "cloud_sql"
├── cloud_run.tf           → module "cloud_run" (uno por entorno)
├── iam.tf                 → module "iam"
├── secret_manager.tf      → module "secret_manager"
├── variables.tf, outputs.tf, providers.tf, versions.tf, backend.tf
├── terraform.tfvars.example
└── modules/
    └── <servicio>/ main.tf, variables.tf, outputs.tf
```

El estado se guarda en el bucket `videojuegos-api-2026-ihoyos-tfstate` (ver `backend.tf`).

## 4. Requisitos previos

- Terraform y Google Cloud CLI instalados.
- Un proyecto de Google Cloud con facturación activa.
- Autenticación local: `gcloud auth application-default login`.

## 5. Configuración

```powershell
terraform -chdir=terraform init
Copy-Item terraform\terraform.tfvars.example terraform\terraform.tfvars
```

Edita `terraform.tfvars` y cambia `database_password`. Ese archivo está ignorado por Git: nunca publiques contraseñas ni archivos de estado.

## 6. Validación

```powershell
terraform -chdir=terraform fmt -check -recursive
terraform -chdir=terraform validate
```

## 7. Despliegue por etapas

Cloud Run necesita una imagen ya publicada, por eso el despliegue va en dos etapas controladas por la variable `deploy_cloud_run` (por defecto `false`).

**Etapa 1: infraestructura base**

```powershell
terraform -chdir=terraform plan
terraform -chdir=terraform apply
```

Crea APIs, Artifact Registry, Cloud SQL, Secret Manager e IAM.

**Publicar la imagen:** un `push` a `main` ejecuta el pipeline de pruebas, que construye y publica la imagen en Artifact Registry.

**Etapa 2: Cloud Run**

```powershell
terraform -chdir=terraform plan -var deploy_cloud_run=true
terraform -chdir=terraform apply -var deploy_cloud_run=true
```

Crea los servicios `videojuegos-api-testing` y `videojuegos-api-production`. Los pipelines actualizan después la imagen; Terraform ignora ese cambio (`ignore_changes`).

## 8. Entornos

| Entorno | Servicio | Esquema PostgreSQL |
|---|---|---|
| Pruebas | `videojuegos-api-testing` | `schema_testing` |
| Producción | `videojuegos-api-production` | `schema_production` |

Ambos usan la misma instancia y base de datos con esquemas separados. La aplicación crea el esquema al arrancar. Las URL se obtienen con:

```powershell
terraform -chdir=terraform output
```

## 9. Costos y seguridad

- Cloud SQL genera costo mientras exista. Está configurada sin copias de seguridad y sin protección contra eliminación, a propósito, para poder destruirla al terminar.
- La instancia tiene IPv4 pública, pero Cloud Run se conecta por el socket `/cloudsql`; no se autoriza ninguna red.
- La contraseña de la base de datos vive en Secret Manager y en el secreto `TF_VAR_database_password` de GitHub.
- Los servicios de Cloud Run son públicos (`allUsers`) porque la API no tiene autenticación.

## 10. Destrucción

```powershell
terraform -chdir=terraform plan -destroy
terraform -chdir=terraform destroy
```

Elimina todos los recursos gestionados y los datos de la base. El bucket del estado no está gestionado por Terraform y debe borrarse aparte si ya no se necesita. Revisa después la facturación de Google Cloud.

## 11. Automatización

| Workflow | Disparador | Qué hace |
|---|---|---|
| `Terraform - Infraestructura` | Manual | `validate`, `plan`, `apply` o `destroy`, con la opción `deploy_cloud_run` |
  ## Infraestructura y despliegue

  La infraestructura en Google Cloud se crea con Terraform (carpeta `terraform/`)
  y se despliega con GitHub Actions. Ver [terraform/README.md](terraform/README.md).

Los workflows se autentican con Workload Identity Federation, sin claves de cuenta de servicio guardadas. `plan`, `apply` y `destroy` desde GitHub requieren que la cuenta `github-actions-deployer` tenga permisos adicionales sobre el proyecto y el bucket del estado.