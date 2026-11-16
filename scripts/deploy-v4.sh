#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${GOOGLE_CLOUD_PROJECT:?}" "${AWS_API_URL:?}" "${CHAOS_TOKEN:?}" "${TF_VAR_database_password:?}"
export REGION=${REGION:-us-central1}
export TF_VAR_project_id="$GOOGLE_CLOUD_PROJECT"
export TF_VAR_region="$REGION"
terraform -chdir=terraform apply -auto-approve
export IMAGE="$(terraform -chdir=terraform output -raw artifact_registry_repository_url)/api:v4.0.0"
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet
docker build --platform linux/amd64 -t "$IMAGE" .
docker push "$IMAGE"
gcloud container clusters get-credentials videojuegos-chaos --region "$REGION" --project "$GOOGLE_CLOUD_PROJECT"
export RUNTIME_SA=$(terraform -chdir=terraform output -raw runtime_service_account_email)
export SQL_CONNECTION=$(terraform -chdir=terraform output -raw cloud_sql_connection_name)
export DB_USER=${TF_VAR_database_user:-videojuegos_app}
export DB_NAME=${TF_VAR_database_name:-videojuegos_db}
export DB_SCHEMA=${DB_SCHEMA:-public}
export CHAOS_ENABLED=${CHAOS_ENABLED:-false}
kubectl create namespace chaos --dry-run=client -o yaml | kubectl apply -f -
# Secret bytes go through stdin, not shell argument values.
python3 - <<'PYSECRET' | kubectl apply -f -
import json, os
print(json.dumps({'apiVersion':'v1','kind':'Secret','metadata':{'name':'api-secrets','namespace':'chaos'},'type':'Opaque','stringData':{'DB_PASSWORD':os.environ['TF_VAR_database_password'],'CHAOS_TOKEN':os.environ['CHAOS_TOKEN']}}))
PYSECRET
# Only substitute known template variables.
envsubst '${IMAGE} ${RUNTIME_SA} ${SQL_CONNECTION} ${DB_USER} ${DB_NAME} ${DB_SCHEMA} ${AWS_API_URL} ${CHAOS_ENABLED}' < k8s-api.yaml | kubectl apply -f -
kubectl -n chaos rollout status deployment/videojuegos --timeout=600s
kubectl -n chaos get pods,service
