# Guía operativa del final de Defensa en Profundidad — 2 integrantes

**No ejecutar contra las nubes hasta que los dos acepten `DEFENSA-GAMEDAY.md`.** Las APIs están funcionando; ejecutar una fase, verificar salud y conservar evidencia antes de la siguiente. Los comandos son ejemplos de Bash para CloudShell y Cloud Shell/GKE, no deben ejecutarse a ciegas. **No hacer `terraform destroy`.** El programa del game day toca únicamente GET y objetos sintéticos aislados.

## Paso 0 — preparar repositorios sin filtrar secretos

Cada ZIP trae fuente, Terraform y workflows sin `.git`, `.env`, `terraform.tfvars` ni `node_modules`. Descomprimir en una **copia de trabajo** de los repositorios existentes y llevar SOLO los archivos nuevos/cambiados a las ramas del proyecto real. Conservar backend Terraform original y credenciales actuales FUERA de Git. No ejecutar `terraform init` con un backend nuevo que termine planeando recrear recursos. Comparar `terraform plan` antes de aplicar. Repos: AWS `BlazeGDP/Veterinaria-API` y GCP `ihoyos57/videojuegos-api`.

```bash
# En la carpeta de cada repo, para comprobar compatibilidad local:
# AWS:
npm ci && npm run build
node --test tests-v4/integration.cjs tests-security/identity.test.cjs
PYTHONPATH=. python -m unittest discover -s tests-security -p 'test_*.py'
python security/offline_gate.py --out evidence/security-offline-gate.json
# GCP:
pip install -r requirements.txt pytest
PYTHONPATH=. pytest tests-v4 tests-security -q
python security/offline_gate.py --out evidence/security-offline-gate.json
```

Los resultados de estos comandos son **pruebas de código**, NO MTTD/MTTC de nube. Publicar y ejecutar `.github/workflows/security-gate.yml` para conservar artifact de CI. `git status` debe mostrar que **no** se suben credenciales, reportes con tokens, `.env` ni archivos `.tfvars` reales.

## Paso 1 — preparar monitoreo y línea base

AWS: CloudShell `us-east-2`; verificar servicio ECS y ALB real. Recoger `GET /health` o rutas de salud existentes y `GET /pets/raw`. CloudWatch Logs Insights (usar Log Group real, no asumir):

```text
fields @timestamp, @message
| filter @message like /server_span|security_event/
| sort @timestamp desc
| limit 100
```

GCP: en Cloud Shell con proyecto propio y cluster `videojuegos-chaos`:

```bash
gcloud config set project "$GOOGLE_CLOUD_PROJECT"
gcloud container clusters get-credentials videojuegos-chaos --region "${REGION:-us-central1}"
kubectl -n chaos get deployment videojuegos -o wide
kubectl -n chaos get pods -l app=videojuegos
kubectl -n chaos get events --sort-by=.lastTimestamp | tail -20
gcloud logging read 'resource.type="k8s_container" AND jsonPayload.event="server_span"' --limit=20 --format=json
```

Medir estado normal ANTES de cada ronda: nombre de alarma, estado, 2 pods Ready, health, proporción de señales de controles por capa. Guardar fecha y origen de cada captura. La ruta `GET /pets/raw` en V4 puede estar abierta: registrar esa falla como línea base, sin describir el control como si ya existiese.

## Paso 2 — ronda 0 identidad AWS (control tal como está hoy)

Confirmar AWS `SECURITY_AUTH_MODE=off` (predeterminado) y GCP `SECURITY_AUTH_MODE=off`, para no romper integración. Usar URL AWS **HTTPS**. El script demanda `SERVICE_AUTH_SECRET` sólo para generar la prueba; esta variable se obtiene en la fase siguiente (si aún no hay secret, usar un valor temporal aleatorio para *probar que la ruta abierta no verifica tokens*; NO enviarlo a terceros). Registrar `sentAt`, `receivedAt` y `traceId`.

```bash
# Copiar token por un canal seguro, sin imprimirlo en logs:
export SERVICE_AUTH_SECRET="$(python -c 'import secrets;print(secrets.token_urlsafe(36))')"
python security/identity_probe.py --url "$AWS_HTTPS_URL" --round 0 \
  --out evidence/security/identity-r0.jsonl --allow-owned-target
```

R0 `normal_legacy`, `unauthorized_reuse`, `uncredentialed_in_baseline` responden 200 si la ruta permanece pública. Este es **un defecto medido**, no se considera contención exitosa. Recolectar CloudWatch y constatar si existe alarma. Si no existe, reportar MTTD `N/D`; no fingir cero.

## Paso 3 — desplegar mejoras, sin interrumpir flujo

1. **AWS**: revisar plan, Terraform agrega secreto `project/security-identity` y metric filter/alarm. `TF_VAR_security_auth_mode=off TF_VAR_enable_security_alerts=true terraform -chdir=terraform plan -out=security-plan`. Si hay reemplazos inesperados o borrado de RDS, **STOP**. Aplicar solo plan aprobado, mantener `off` en el primer despliegue.
2. Extraer en CloudShell, sin eco ni commit:

```bash
export SECRET_ARN="$(terraform -chdir=terraform output -raw security_identity_secret_arn)"
export SERVICE_AUTH_SECRET="$(aws secretsmanager get-secret-value --secret-id "$SECRET_ARN" --query SecretString --output text --region us-east-2)"
# Pasar la variable a GCP mediante un canal seguro del equipo, NO repositorios/CHAT/CI.
```

3. **GCP**: preparar variables originales (`TF_VAR_database_password`, `CHAOS_TOKEN`, `AWS_API_URL`, `GOOGLE_CLOUD_PROJECT`, backend Terraform ya existente), y el `SERVICE_AUTH_SECRET` recibido. Habilitar sin anunciar protección AWS aún:

```bash
export SECURITY_AUTH_MODE=protected
export SECURITY_HEARTBEAT_ENABLED=true
export SECURITY_HONEYTOKEN_PATH="/.well-known/sec-lab-$(python -c 'import secrets; print(secrets.token_hex(12))')"
export TF_VAR_enable_security_monitoring=true
# Revisar terraform -chdir=terraform plan; si no hay cambios destructivos:
bash scripts/deploy-v4.sh
```

4. Verificar GCP `/juegos/` aún consume `/pets/raw` en AWS `off`. Habilitar AWS al final:

```bash
export TF_VAR_security_auth_mode=protected TF_VAR_enable_security_alerts=true
terraform -chdir=terraform plan -out=security-protected.tfplan
# Solo tras verificar que no hay replace destructivo:
terraform -chdir=terraform apply security-protected.tfplan
```

El despliegue AWS también necesita la imagen de aplicación nueva (`src/security/service-auth.ts`); de lo contrario Terraform solo cambiará la variable, no el código. Construir/publicar imagen mediante el pipeline existente y verificar digest antes del último apply. El sistema no detecta por sí solo si su imagen es la versión nueva.

**Rollback seguro:** primero poner AWS `security_auth_mode=off` y aplicarlo, luego GCP `SECURITY_AUTH_MODE=off` si se necesita; esto evita que GCP quede enviando tokens que AWS rechace. Confirmar salud, registrar rollback. `SERVICE_AUTH_SECRET` en GCP no debe imprimirse.

## Paso 4 — ronda 1 identidad y correlación

```bash
python security/identity_probe.py --url "$AWS_HTTPS_URL" --round 1 \
  --out evidence/security/identity-r1.jsonl --allow-owned-target
# Obtener los eventos AWS (configurar grupo y rango reales):
aws logs filter-log-events --region us-east-2 --log-group-name "$AWS_LOG_GROUP" \
  --filter-pattern '"security_event"' --output json > evidence/security/aws-security-events.json
aws cloudwatch describe-alarm-history --region us-east-2 \
  --alarm-name "$AWS_ALARM_NAME" --output json > evidence/security/aws-alarm-history.json
```

Esperado *a verificar*: normal scoped 200; token reutilizado, audiencia errónea, vencido, secreto legado 401. Mismo `traceId` en prueba HTTP y `security_event` en CloudWatch. ALARMA: screenshot/UTC de estado ALARM y retorno a OK; CloudWatch agrega por minuto, no necesariamente conserva el traceId en la propia alarma. Para MTTD usar sello de la alarma en monitor; para MTTC respuesta HTTP bloqueada. Cargar `security/metrics.py` únicamente con alertas normalizadas **reales**, no con el archivo `.example`.

## Paso 5 — telemetría + IA GCP, dos rondas

R0: `SECURITY_HEARTBEAT_ENABLED=false`, `SECURITY_HONEYTOKEN_PATH` vacío, sin políticas nuevas. Verificar en Logs ausencia de eventos de seguridad y **no afirmar MTTD=0**. En R1 las métricas y alarmas deben existir tras `TF_VAR_enable_security_monitoring=true`, el heartbeat activo y una línea base de al menos tres latidos por pod; revisar `gcloud monitoring policies list` o la consola de Cloud Monitoring.

Para emular pérdida de señal **sin apagar logs**:

```bash
# R1, temporal, solo deployment videojuegos propio:
kubectl -n chaos set env deployment/videojuegos SECURITY_HEARTBEAT_PAUSED=true
kubectl -n chaos rollout status deployment/videojuegos --timeout=600s
# Registrar UTC al último heartbeat del log. Esperar el evento nativo de condición absent.
# STOP / reversión, SIEMPRE:
kubectl -n chaos set env deployment/videojuegos SECURITY_HEARTBEAT_PAUSED=false
kubectl -n chaos rollout status deployment/videojuegos --timeout=600s
```

Si la alarma por ausencia no pasa a ALARM, no inventar resultado: revisar métrica por pod y Cloud Monitoring. Probar honeytoken usando **exactamente** el valor del Deployment:

```bash
python security/telemetry_probe.py --url "$GCP_HTTPS_URL" \
  --honeytoken-path "$SECURITY_HONEYTOKEN_PATH" \
  --out evidence/security/honeytoken-r1.jsonl --allow-owned-target
gcloud logging read 'resource.type="k8s_container" AND jsonPayload.action="honeytoken_touched"' \
  --limit 50 --format json > evidence/security/gcp-honeytoken-logs.json
```

El HTTP esperado del señuelo es **404 deliberado**, y debe existir evento `security_event` con `traceId`. Medir hora de alerta y compararla con el probe. Prueba negativa: GET `/health/live` no debe disparar señal de honeytoken. Con una única prueba no declarar FPR estadístico de tráfico global.

Para ataque sobre IA y uso analítico real del modelo (sin herramientas) con datos sintéticos:

```bash
python security/ai_review.py --events security/fixtures/ai-prompt-injection.jsonl \
  --out evidence/security/ai-review
python security/model_trial.py --events security/fixtures/ai-prompt-injection.jsonl \
  --round 0 --out evidence/security/ai-r0.json --send
python security/model_trial.py --events security/fixtures/ai-prompt-injection.jsonl \
  --round 1 --out evidence/security/ai-r1.json --send
```

`model_trial.py` necesita `OPENAI_API_KEY` y genera **costos externos**. Si no se usa API, ejecutar el prompt manualmente con un modelo y conservar la salida sin secretos. Rellenar `review.json` contrastando hallazgos vs eventos; una frase de un modelo no es evidencia de una acción real. Comparar dos rondas y cerrar el flujo con aprobación humana de cualquier remediación (se recomienda ninguna para demo).

## Paso 6 — experimento grupal: un objeto de mascota sintética en S3

Crear dos buckets **nuevos y dedicados** para el juego, jamás apuntar al bucket de estado Terraform; elegir nombres con `sec-lab` y sufijo único. En AWS us-east-2, el segundo se crea con Object Lock (no se puede habilitar de manera retroactiva en todas las configuraciones). Crear manualmente siguiendo consola o:

```bash
aws s3api create-bucket --bucket "$SEC_PRIMARY_BUCKET" --region us-east-2 \
  --create-bucket-configuration LocationConstraint=us-east-2
aws s3api create-bucket --bucket "$SEC_BACKUP_BUCKET" --region us-east-2 \
  --create-bucket-configuration LocationConstraint=us-east-2 --object-lock-enabled-for-bucket
aws s3api put-bucket-versioning --bucket "$SEC_PRIMARY_BUCKET" --versioning-configuration Status=Enabled
aws s3api put-bucket-versioning --bucket "$SEC_BACKUP_BUCKET" --versioning-configuration Status=Enabled
aws s3api put-public-access-block --bucket "$SEC_PRIMARY_BUCKET" --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-public-access-block --bucket "$SEC_BACKUP_BUCKET" --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

Cada ronda usa una **clave única** `security-game-day/<UUID>/synthetic-record.json`; nunca escribe/sobrescribe registros reales. `--execute-live --affirm-owned` obligatorio. En R0 se conserva respaldo de rev1 y sobrescribe rev2; R1 respaldo retenido WORM de rev2. Ambas rondas restauran con hash SHA-256, miden pérdida y tiempo. Dado que la fuente primaria original en V4 es SQL, esto demuestra solo el alcance mínimo del objeto de prueba de la rúbrica.

```bash
python security/data_recovery.py --primary-bucket "$SEC_PRIMARY_BUCKET" \
  --backup-bucket "$SEC_BACKUP_BUCKET" --round 0 \
  --out evidence/security/data-r0.json --execute-live --affirm-owned
python security/data_recovery.py --primary-bucket "$SEC_PRIMARY_BUCKET" \
  --backup-bucket "$SEC_BACKUP_BUCKET" --round 1 \
  --out evidence/security/data-r1.json --execute-live --affirm-owned
```

**Advertencia:** R1 crea un objeto en retención COMPLIANCE por 1 día, no se podrá borrar antes; gestionar costos y permisos del grupo. RPO aquí = antigüedad del último punto recuperable en el instante de inyección; observar también `dataLossRevisions`. RTO = tiempo entre inicio de la sobreescritura y verificación final SHA-256. Anotar que un respaldo en cuenta igual no es copia air-gapped.

## Paso 7 — producto final y sustentación individual

- Entregar por repo: código, Terraform/manifest, CI exitoso, `evidence/security` de **ejecución real**, alertas y bitácoras fechadas correlacionadas, informe propio ≤10 páginas y comparación 6 rondas (R0/R1 de cada experimento). Enlazar runs GitHub.
- En sustentación: mostrar estado estable de ambas nubes, ejecutar una prueba con STOP, confirmar alerta monitoreo, comparar dos rondas, mostrar rechazo/latido/backup/restauración y revertir. Ambos deben poder explicar el experimento del otro.
- No hay cifras cloud preinventadas. Los archivos `INFORME-DEFENSA-PENDIENTE.md` y `metrics.py` indican exactamente lo que falta obtener.
