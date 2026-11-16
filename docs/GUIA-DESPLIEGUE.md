# Guía de despliegue y ejecución V4 AWS y GCP

Esta entrega adapta la rúbrica a dos estudiantes: dos APIs en dos nubes, dos hipótesis y dos fallos de naturaleza distinta. AWS Veterinaria es el coordinador del flujo principal y consulta juegos en GCP. Videojuegos también permite el flujo inverso hacia mascotas. No hay una tercera nube. No se incluye agotamiento de recursos como tercer experimento, por la adaptación solicitada a dos integrantes.

La entrega proporciona implementación, infraestructura, experimentos y generación de evidencias. La aprobación académica requiere ejecutar en sus cuentas, registrar resultados reales, completar el diagnóstico, publicar el release y sustentar. No se presentan mediciones locales como pruebas de AWS o GCP. Los umbrales de abajo son criterios propuestos; el estado estable se mide antes de inyectar y el proceso se detiene si no los alcanza.

## 1 Preparar los repositorios existentes

Descomprimir cada ZIP en una carpeta nueva. Copiar su contenido al repositorio original correspondiente, conservando la carpeta `.git` de ese repositorio. El ZIP es una sustitución del árbol de trabajo, no una suma indiscriminada de archivos: eliminar los workflows canary anteriores y la carpeta `terraform-canary` después de comprobar que ya no administra recursos. Conservar el historial Git y los backends de Terraform de la entrega anterior si siguen existiendo recursos.

Los originales adjuntos permanecen como copia de referencia. Los ZIP no contienen `.env`, contraseñas, `node_modules`, estados Terraform, proveedores descargados ni compilados. `.terraform.lock.hcl` sí se conserva. No copiar archivos de configuración antiguos con credenciales al nuevo commit.

En cada repositorio:

```bash
git checkout -b feat/v4-chaos
# Copiar aquí el contenido del ZIP correspondiente.
git status --short
git add .
git commit -m "✨ feat: implementar V4 multicloud e ingeniería del caos"
git push -u origin feat/v4-chaos
```

Los comandos siguientes se ejecutan en Bash de AWS CloudShell o Google Cloud Shell, en la raíz del repositorio correspondiente; no son comandos PowerShell. Pueden clonar esa rama en cada consola o subir y descomprimir el ZIP. GitHub Actions necesita que `.github/workflows` esté en la raíz del repositorio.

## 2 Instalar herramientas y acordar el experimento

En ambas consolas, si Terraform o k6 no están disponibles:

```bash
bash scripts/install-tools.sh
export PATH="$HOME/bin:$PATH"
terraform version
k6 version
docker version
```

El instalador usa Terraform 1.11.4 y k6 0.54.0 para Linux x86_64. Terraform ya instalado de versión compatible puede usarse. Ejecutar `export PATH` de nuevo al abrir otra consola si hace falta. Google Cloud Shell debe tener `kubectl`, `gke-gcloud-auth-plugin` y `envsubst`; comprobarlos con `command -v`. Si falta `envsubst`: `sudo apt-get update && sudo apt-get install -y gettext-base`.

Acuerden ventana, URLs, responsable de detener la prueba y datos sintéticos. Generar UNA vez un token compartido y guardarlo de forma privada; no subirlo a Git:

```bash
openssl rand -hex 32
```

Copiar el mismo resultado al introducir `CHAOS_TOKEN` en las dos consolas y al crear el secreto de GitHub. El mecanismo exige al menos 32 caracteres, `CHAOS_ENABLED=true`, token correcto y cabecera de vencimiento. No se deja un fallo global activo. Para máxima sencillez se mantienen los balanceadores HTTP del laboratorio; el token limita la activación pero no convierte HTTP en transporte cifrado. No usar información real ni exponer este laboratorio como servicio de producción.

## 3 Desplegar AWS primero

En AWS CloudShell, dentro del repositorio Veterinaria:

```bash
export AWS_DEFAULT_REGION=us-east-2
aws sts get-caller-identity
read -rsp 'Token compartido: ' TF_VAR_chaos_token; echo
export TF_VAR_chaos_token
export TF_VAR_peer_api_url=""
export TF_VAR_chaos_enabled=false
export TF_VAR_image_tag=v4.0.0
```

Si conservas el bucket anterior, poner SU nombre, sin crear otro estado para la misma infraestructura:

```bash
export TF_STATE_BUCKET='NOMBRE_REAL_DEL_BUCKET_TFSTATE'
```

Sólo si ya destruiste toda la infraestructura anterior y necesitas un bucket nuevo:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export TF_STATE_BUCKET="veterinaria-tfstate-${ACCOUNT_ID}-us-east-2"
aws s3api create-bucket --bucket "$TF_STATE_BUCKET" --region us-east-2 \
  --create-bucket-configuration LocationConstraint=us-east-2
aws s3api put-bucket-versioning --bucket "$TF_STATE_BUCKET" \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$TF_STATE_BUCKET" \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

No ejecutar `create-bucket` si ya existe. La clave de estado conserva `api-restful-veterinaria/v3/terraform.tfstate` por compatibilidad; el nombre no cambia la versión de la aplicación.

```bash
terraform -chdir=terraform init -reconfigure -backend-config="bucket=$TF_STATE_BUCKET"
terraform -chdir=terraform validate
terraform -chdir=terraform plan
# Revisar que el plan corresponda únicamente a este proyecto.
bash scripts/deploy-v4.sh
export AWS_API_URL=$(terraform -chdir=terraform output -raw api_url)
curl -fsS "$AWS_API_URL/health"
```

El script crea ECR primero, construye y publica la imagen y aplica el resto. ECS inicializa las tablas de forma idempotente antes de arrancar NestJS. Conserva VPC, ALB, ECS/Fargate, RDS, Secrets Manager, CloudWatch y CloudFront del diseño anterior. No necesita el proveedor OIDC de GitHub bloqueado anteriormente por tu organización: este despliegue usa la sesión de CloudShell y el pipeline de caos sólo necesita las URLs y el token.

Mientras la URL GCP esté vacía, los GET locales devuelven `integration.status=degraded` y `juego=null`. Es normal durante el arranque por etapas. Guardar la URL de AWS para tu compañera. Para sus GET de mascotas también puede usarse la salida HTTPS `metrics_https_url` de CloudFront: reenvía GET sin caché, aunque conserve ese nombre histórico.

## 4 Desplegar GCP con Kubernetes

En Google Cloud Shell, raíz del repositorio Videojuegos:

```bash
export GOOGLE_CLOUD_PROJECT='ID_REAL_DEL_PROYECTO'
export REGION=us-central1
gcloud config set project "$GOOGLE_CLOUD_PROJECT"
gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com \
  iam.googleapis.com compute.googleapis.com container.googleapis.com \
  artifactregistry.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com
read -rsp 'Contraseña de PostgreSQL: ' TF_VAR_database_password; echo
export TF_VAR_database_password
read -rsp 'Mismo token compartido: ' CHAOS_TOKEN; echo
export CHAOS_TOKEN
export AWS_API_URL='URL_REAL_DE_AWS'
export CHAOS_ENABLED=false
export TF_VAR_project_id="$GOOGLE_CLOUD_PROJECT"
export TF_VAR_region="$REGION"
```

Si conservan Cloud SQL, introducir la contraseña de ese usuario o decidir conscientemente rotarla. No cambiar el nombre de proyecto, instancia ni backend para intentar recuperar recursos ya existentes. La cuenta que ejecuta Terraform necesita crear los recursos y asignaciones IAM declarados.

La configuración heredada necesita una cuenta de servicio de despliegue. Si ya existe, usar su correo en `TF_VAR_deployer_service_account_email`. Para una instalación nueva:

```bash
gcloud iam service-accounts create v4-deployer --display-name='Despliegue V4'
export TF_VAR_deployer_service_account_email="v4-deployer@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"
```

No se genera una clave JSON. Esta variable permite conservar las asignaciones del módulo IAM anterior; el despliegue manual lo realiza tu sesión actual.

Backend: si ya hay infraestructura, usar el bucket y prefijo originales. En el ZIP recibido eran el bucket del proyecto anterior y el prefijo `videojuegos-api/terraform/state`. Para una cuenta/proyecto limpio:

```bash
export GCP_STATE_BUCKET="${GOOGLE_CLOUD_PROJECT}-tfstate-v4"
gcloud storage buckets create "gs://$GCP_STATE_BUCKET" --location="$REGION" \
  --uniform-bucket-level-access
gcloud storage buckets update "gs://$GCP_STATE_BUCKET" --versioning
```

Con el bucket elegido:

```bash
terraform -chdir=terraform init -reconfigure \
  -backend-config="bucket=$GCP_STATE_BUCKET" \
  -backend-config="prefix=videojuegos-api/terraform/state"
terraform -chdir=terraform validate
terraform -chdir=terraform plan
```

V4 usa GKE Autopilot, manteniendo los módulos Cloud SQL, Artifact Registry e IAM. `deploy_cloud_run=false` retira los servicios Cloud Run del estado anterior cuando estaban activos; revisar ese cambio antes de aplicar. Sus datos de Cloud SQL no se eliminan por retirar Cloud Run. Si necesitan conservar temporalmente Cloud Run, establecer `TF_VAR_deploy_cloud_run=true` con su imagen anterior válida durante la transición.

```bash
# Nueva instalación: public. Para conservar datos de la V3 en Cloud Run:
# export DB_SCHEMA=schema_production
export DB_SCHEMA=public
bash scripts/deploy-v4.sh
kubectl -n chaos get pods
kubectl -n chaos get svc videojuegos
```

Esperar a que `EXTERNAL-IP` tenga valor. El script crea el Secret por stdin, usa Workload Identity para el proxy Cloud SQL, publica la imagen y despliega dos réplicas. Las probes HTTP comprueban proceso y base de datos por separado. Cada contenedor tiene requests/limits; el proxy arranca antes de la API.

```bash
GCP_IP=$(kubectl -n chaos get svc videojuegos -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
export GCP_API_URL="http://$GCP_IP"
curl -fsS "$GCP_API_URL/health/ready"
```

Guardar esa URL para AWS. No usar las IP de pods: se usa el Service LoadBalancer. Si no aparece una IP o faltan permisos, revisar `kubectl -n chaos describe pods` y eventos antes de continuar.

## 5 Cerrar la conexión y crear datos sintéticos

De nuevo en AWS CloudShell:

```bash
export TF_VAR_peer_api_url='http://IP_PUBLICA_DEL_SERVICE_GCP'
terraform -chdir=terraform apply
aws ecs wait services-stable \
  --cluster "$(terraform -chdir=terraform output -raw ecs_cluster_name)" \
  --services "$(terraform -chdir=terraform output -raw ecs_service_name)"
export AWS_API_URL=$(terraform -chdir=terraform output -raw api_url)
export GCP_API_URL="$TF_VAR_peer_api_url"
python3 scripts/seed-v4.py
```

La semilla crea un owner, pet y appointment, además de un juego, jugador y compra. Muestra los IDs reales: no asume que el primero sea 1. Cada ejecución agrega un conjunto nuevo, por lo que basta ejecutar una vez. Si ya tienen datos sintéticos adecuados, pueden omitirla; debe existir al menos un juego y una mascota para que el flujo completo sea válido.

```bash
curl -fsS "$AWS_API_URL/owners"
curl -fsS "$AWS_API_URL/pets"
curl -fsS "$AWS_API_URL/appointments"
curl -fsS "$GCP_API_URL/juegos/"
curl -fsS "$GCP_API_URL/jugadores/"
curl -fsS "$GCP_API_URL/compras/"
# Sustituir 1 por un ID real devuelto por la semilla:
curl -fsS "$AWS_API_URL/owners/1"
curl -fsS "$GCP_API_URL/juegos/1"
```

Contrato V4 AWS: `{ "data": [...], "juego": {...}, "integration": {"status":"ok","reason":null,"live":true}, "traceId":"..." }`. Por ID, `data` es el objeto local; para listas, contiene toda la lista local con sus filtros y relaciones. GCP usa `mascota` en lugar de `juego`. Es un cambio de contrato mayor y por eso la versión es 4.0.0. POST/PATCH/DELETE conservan sus contratos. `/appointments/summary` sigue disponible como funcionalidad local, sin enriquecimiento.

`/pets/raw` y `/juegos/raw` consultan únicamente la base local y nunca llaman a otra nube. Las llamadas normales no se cachean; el objeto se selecciona aleatoriamente sobre la lista leída en esa petición. Aleatorio no significa diferente cada vez. Un ID local inexistente mantiene 404 y no se enriquece. Una lista remota vacía produce `reason=peer_empty` en AWS o error de validación de la dependencia en GCP; no se inventa un objeto.

## 6 Activar caos únicamente para la ventana acordada

En AWS:

```bash
export TF_VAR_chaos_enabled=true
terraform -chdir=terraform apply
aws ecs wait services-stable \
  --cluster "$(terraform -chdir=terraform output -raw ecs_cluster_name)" \
  --services "$(terraform -chdir=terraform output -raw ecs_service_name)"
```

En GCP:

```bash
kubectl -n chaos set env deployment/videojuegos CHAOS_ENABLED=true
kubectl -n chaos rollout status deployment/videojuegos --timeout=600s
```

Ambas APIs deben usar el mismo token. No basta activar una de ellas: GCP propaga la solicitud de 503 al endpoint de mascotas en AWS.

La falla AWS añade 3000 ms dentro del presupuesto de la llamada saliente a GCP. La ronda 0 permite 6000 ms y propaga errores; la ronda 1 limita esa operación completa a 800 ms y retorna datos locales con `juego=null`. Si el timeout vence antes de abrir la conexión remota, no habrá span GCP para esa petición: es el comportamiento esperado, no una traza perdida.

La falla GCP produce respuestas 503 sostenidas en `/pets/raw` de AWS, sólo para las solicitudes firmadas por token de ese experimento. No tumba todos los pods ni afecta peticiones normales. La ronda 0 convierte el error remoto en 502; la ronda 1 responde con los juegos locales y `mascota=null`. Dos patrones por integrante: timeout de dependencia y degradación elegante sin caché. No se agregan reintentos ni circuit breaker porque no hacen falta para las dos hipótesis seleccionadas.

## 7 Ejecutar el experimento declarativo

En cada repositorio, con Python 3.11 o posterior y k6 en PATH:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r chaos/requirements.txt
export CHAOS_WINDOW_ACK=yes
read -rsp 'Token compartido: ' CHAOS_TOKEN; echo
export CHAOS_TOKEN
# AWS: URL de Veterinaria. GCP: URL de Videojuegos.
export BASE_URL='URL_REAL_DE_LA_API_DE_ESTE_REPOSITORIO'
bash scripts/chaos-gate.sh
```

Ejecutar una API a la vez durante la entrega para que los experimentos de los integrantes no se influyan. El script elige el experimento del repositorio; no hay que editar JSON ni código para elegir la ronda. Tarda aproximadamente cinco minutos: estado estable sin falla, ronda 0 sin protección, reversión, ronda 1 protegida y reversión final.

Perfil fijo por medición: 15 s hasta 5 usuarios virtuales, 60 s a 5 usuarios y 15 s hasta cero, una solicitud por iteración y pausa de 200 ms. Los usuarios mantienen el mismo perfil; la cantidad de solicitudes completadas puede variar como consecuencia del fallo. No cambiar carga, duración ni umbral entre rondas. Antes de ejecutar, acuerden p95 AWS <1500 ms y error local GCP <=1%; son metas, no supuestos de rendimiento medido.

El estado estable exige integración completa >=99%, error local <=1% y p95 <1500 ms, medidos con el mismo perfil. Si falla, se detiene antes de inyectar. La puerta exige que la ronda 0 refute la hipótesis y la ronda 1 la cumpla, además de recuperación posterior. Si no se reproduce el fallo, también falla: no se fabrica una mejora. El runner aborta si falla el control sin caos, si una ronda supera 115 s o si el error local de la ronda protegida supera 50% después de 10 s.

Al finalizar, `evidence/FECHA_UTC/` contiene resúmenes, muestras crudas, ventanas, logs k6 con traceId de muestra, `comparison.json`, `journal.json`, `recovery.json`, tablero `dashboard.html` y borrador de informe. `dashboard.html` superpone ambas rondas sobre tiempo relativo e identifica las ventanas absolutas. La inyección dura mientras se generan solicitudes del perfil; al acabar puede haber solicitudes en vuelo hasta su timeout.

**No interpretar respuesta parcial como éxito del flujo completo.** `local_error` mide continuidad del servicio local; `integration_complete` mide si llegó también el dato remoto. Durante indisponibilidad se espera que esta última disminuya, aun cuando la protección conserve HTTP 200 y datos locales.

## 8 Ver el tablero y recoger las trazas

Opción más simple: descargar `dashboard.html` de los artefactos del pipeline y abrirlo en el navegador. No necesita servidor ni acceso a Grafana. Contiene curvas temporales, p95 global, tasa de error, completitud y la comparación porcentual real.

Para Grafana en vivo, en un equipo Linux con Docker Compose y k6 donde ejecuten el experimento:

```bash
read -rsp 'Contraseña local Grafana: ' GRAFANA_ADMIN_PASSWORD; echo
export GRAFANA_ADMIN_PASSWORD
docker compose -f observability/v4/compose.yaml up -d
export PUSHGATEWAY_URL=http://127.0.0.1:9091
# Ejecutar scripts/chaos-gate.sh desde este mismo equipo con BASE_URL y token.
```

Abrir `http://localhost:3001`, usuario `admin` y la contraseña indicada. El tablero “V4 multicloud dos integrantes” está provisionado. Muestra ventana, p95 acumulado, error local y completitud por experimento y ronda; Prometheus conserva ambas rondas. Ajustar el rango de tiempo al experimento. Los puertos están ligados al equipo local, no al público. Esta alternativa no requiere cambiar los jobs antiguos de Grafana Cloud; el tablero HTML es siempre generado incluso si no hay Pushgateway. No dejar simultáneamente dos conjuntos de Compose usando los mismos puertos.

Trazas: las dos APIs propagan `traceparent` W3C y devuelven `X-Trace-Id`; emiten spans JSON a los logs. No se instaló un backend OTel/Tempo: la evidencia distribuida se reconstruye buscando el mismo traceId en los logs de ambas nubes.

```bash
# Una llamada manual con correlación fija, antes de la inyección:
curl -i -H 'traceparent: 00-0123456789abcdef0123456789abcdef-0123456789abcdef-01' \
  "$AWS_API_URL/owners"
# AWS CloudShell:
aws logs tail /ecs/api-restful-veterinaria --since 10m --format short
# Si cambiaste project_name, consultar terraform/cloudwatch.tf para el grupo exacto.
# GCP Cloud Shell:
kubectl -n chaos logs -l app=videojuegos -c api --prefix --since=10m --max-log-requests=10
```

Guardar en el repositorio los extractos correlacionados, capturas y el informe final de máximo seis páginas. El borrador generado ayuda, pero deben añadir observaciones del fallo, hallazgos inesperados y explicación propia. No adjuntar miles de líneas sin interpretación. Revisar `docs/MATRIZ-RUBRICA.md` y `docs/SUSTENTACION.md`.

## 9 Puerta de calidad en GitHub Actions

Cada repositorio incluye un workflow `V4 Chaos quality gate` de ejecución manual. Fusionar la rama a la rama principal para que aparezca `Run workflow`.

En Settings → Secrets and variables → Actions:

| Tipo | Nombre | Valor |
|---|---|---|
| Variable de repositorio | `CHAOS_BASE_URL` | URL de la API de ese repositorio, sin ruta de entidad |
| Secret de repositorio | `CHAOS_TOKEN` | Mismo token compartido de las dos APIs |

Actions → V4 Chaos quality gate → Run workflow → marcar ventana acordada. No necesita credenciales AWS/GCP porque sólo realiza peticiones de prueba a las URLs desplegadas. Sí necesita que la inyección esté habilitada en ambas APIs. La ejecución queda roja si el objetivo no se cumple; el paso de artefactos usa `always()` para conservar evidencias incluso al fallar. Evitar correr los dos repositorios a la vez: la exclusión automática sólo opera dentro de cada repositorio.

## 10 Informe y release final

Abrir el tablero y el borrador generado. Completar la sección de diagnóstico con traceId reales y explicar por qué se degrada la métrica. Registrar los resultados numéricos del estado estable, las dos rondas, variación porcentual, recuperación, captura o enlace al tablero y backlog. El informe de este curso es independiente del informe de Defensa en Profundidad.

Guardar los resultados definitivos, no el token ni configuraciones privadas. `evidence` está ignorado para no subir por accidente todas las ejecuciones; seleccionar la definitiva:

```bash
git add -f evidence/FECHA_DE_LA_EJECUCION/
git add docs/
git commit -m "📝 docs: registrar evidencia real y diagnóstico de caos"
git push
# Sólo después de revisar y fusionar a la rama principal:
git checkout main
git pull --ff-only
git tag -a v4.0.0 -m "🚀 release: V4 multicloud y caos"
git push origin v4.0.0
```

El workflow `Release V4` publica un GitHub Release desde el tag. Si ya existe `v4.0.0`, no sobrescribirlo: usar una nueva versión SemVer y actualizar VERSION/metadatos. Usar GitMoji también en los commits posteriores. La fecha de la rúbrica es 18 de noviembre de 2026, antes de iniciar la clase; la demostración debe estar funcionando en ambas nubes ese día.

## 11 Revertir y cerrar la ventana

Interrumpir el comando de carga elimina las cabeceras de nuevas solicitudes; las que están en curso están acotadas. Esperar al menos siete segundos y repetir un GET sin cabeceras: debe devolver `integration.status=ok`, un objeto remoto y los datos locales.

En AWS:

```bash
export TF_VAR_chaos_enabled=false
terraform -chdir=terraform apply
```

En GCP:

```bash
kubectl -n chaos set env deployment/videojuegos CHAOS_ENABLED=false
kubectl -n chaos rollout status deployment/videojuegos
```

No ejecutar otro despliegue con `CHAOS_ENABLED=true` después del cierre. Si no vuelve a estado estable, diagnosticar conectividad, datos y pods antes de repetir. No resolverlo relajando el gate sin una nueva hipótesis acordada.

## 12 Eliminar al finalizar la evaluación

Conservar la solución activa durante la sustentación. Cuando ya no se necesite, en GCP eliminar primero el Service/Deployment para que se retire el balanceador:

```bash
kubectl delete namespace chaos
# Confirmar la eliminación del Service/LoadBalancer antes de destruir GKE.
terraform -chdir=terraform destroy
```

En AWS, con el backend correcto y variables requeridas aún disponibles:

```bash
terraform -chdir=terraform destroy
```

Estos comandos destruyen también las bases de datos del laboratorio; exportar primero cualquier dato que necesiten conservar. Los buckets de estado se crearon fuera de Terraform y permanecen; los logs creados automáticamente, imágenes/artifact registry y recursos de versiones antiguas deben revisarse por separado. No declarar costo cero sólo porque finalizó `destroy`: comprobar las consolas de facturación y los recursos restantes en las regiones usadas. GKE, RDS/Cloud SQL, NAT y balanceadores generan cargos mientras existan.

Para el monitoreo local: `docker compose -f observability/v4/compose.yaml down`. Añadir `-v` sólo si quieren borrar también el histórico local de Grafana/Prometheus.

## Referencias técnicas

- Chaos Toolkit, experimento declarativo y reversión: https://chaostoolkit.org/reference/api/experiment/
- Cloud SQL desde GKE con Workload Identity: https://docs.cloud.google.com/sql/docs/postgres/connect-kubernetes-engine
- k6, umbrales y salida de error: https://grafana.com/docs/k6/latest/using-k6/thresholds/
- k6, resumen programático: https://grafana.com/docs/k6/latest/results-output/end-of-test/custom-summary/
