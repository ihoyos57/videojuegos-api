\# Infraestructura como código con Terraform



\## 1. Descripción



Este directorio contiene la configuración de Terraform para aprovisionar la infraestructura de la API de videojuegos en Google Cloud.



La infraestructura está organizada en módulos para facilitar su mantenimiento y reutilización.



\## 2. Servicios de Google Cloud



La configuración contempla los siguientes servicios:



\- \*\*Cloud Run:\*\* ejecución de la API en los entornos de pruebas y producción.

\- \*\*Cloud SQL:\*\* base de datos PostgreSQL.

\- \*\*Artifact Registry:\*\* almacenamiento de imágenes Docker.

\- \*\*Secret Manager:\*\* almacenamiento del secreto de la contraseña de la base de datos.

\- \*\*IAM y cuentas de servicio:\*\* permisos para que la API acceda a los recursos necesarios.



Los recursos solo se crean cuando se ejecuta una aplicación de Terraform autorizada.



\## 3. Organización



\- `main.tf`: conexión de los módulos y configuración general.

\- `variables.tf`: variables de configuración.

\- `providers.tf`: proveedor de Google Cloud.

\- `versions.tf`: versiones de Terraform y del proveedor.

\- `terraform.tfvars.example`: ejemplo de variables.

\- `modules/`: módulos independientes para los servicios de infraestructura.



\## 4. Requisitos previos



\- Tener Terraform instalado.

\- Tener Google Cloud CLI instalado.

\- Disponer de un proyecto de Google Cloud con facturación configurada.

\- Tener permisos suficientes para administrar los recursos.

\- Autenticarse con una cuenta autorizada de Google Cloud.



\## 5. Configuración



Desde la raíz del repositorio, inicializa Terraform:



```powershell

terraform -chdir=terraform init

```



Crea el archivo local `terraform/terraform.tfvars` a partir de `terraform/terraform.tfvars.example` y configura los valores correspondientes.



No publiques contraseñas, archivos `.tfvars` con secretos ni archivos de estado en Git.



\## 6. Validación



Comprueba el formato:



```powershell

terraform -chdir=terraform fmt -check -recursive

```



Valida la configuración:



```powershell

terraform -chdir=terraform validate

```



Estas comprobaciones no crean infraestructura.



\## 7. Revisar cambios antes de desplegar



Después de configurar las credenciales y las variables, genera un plan:



```powershell

terraform -chdir=terraform plan

```



Revisa todos los recursos que se crearán, modificarán o eliminarán antes de autorizar cualquier despliegue.



\## 8. Despliegue de infraestructura



El despliegue debe realizarse únicamente después de verificar:



\- El proyecto de Google Cloud seleccionado.

\- Las APIs requeridas y los permisos.

\- Las variables y los secretos.

\- El costo estimado de los recursos.

\- La imagen Docker disponible para Cloud Run.



Cuando se autorice el despliegue, se puede aplicar el plan revisado:



```powershell

terraform -chdir=terraform apply

```



Este comando puede crear recursos facturables. No lo ejecutes sin autorización y revisión previa.



\## 9. Destrucción de infraestructura



Para revisar qué recursos se eliminarían:



```powershell

terraform -chdir=terraform plan -destroy

```



La eliminación requiere autorización explícita y una revisión de sus consecuencias. Puede eliminar recursos y datos almacenados. Una vez revisado el plan, la destrucción se puede realizar con:



```powershell

terraform -chdir=terraform destroy

```



Eliminar recursos no garantiza que no existan otros cargos pendientes, almacenamiento residual u otros servicios activos. Comprueba también la sección de facturación de Google Cloud.



\## 10. Entornos



La configuración contempla dos entornos de Cloud Run:



\- \*\*Pruebas:\*\* servicio `videojuegos-api-testing`, esquema `schema\_testing`.

\- \*\*Producción:\*\* servicio `videojuegos-api-production`, esquema `schema\_production`.



Ambos están configurados para utilizar la base de datos PostgreSQL definida por Terraform. Antes del despliegue, deben verificarse los permisos y la creación de los esquemas.



\## 11. Automatización



El workflow de GitHub Actions `Terraform - Infraestructura` permite validar la configuración y solicitar un plan de Terraform.



La validación no despliega recursos. Cualquier automatización futura de despliegue o destrucción debe incorporar autenticación segura, revisión del plan y controles de autorización.

