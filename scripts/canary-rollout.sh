#!/usr/bin/env bash
# Rollout progresivo Canary en Cloud Run con simulador de estrés por etapa.
#
#   Etapa 0 -> 0%   (solo pruebas internas por URL etiquetada canary)
#   Etapa 1 -> 10%  \
#   Etapa 2 -> 50%   > cada una: aplica tráfico, estresa la URL pública, hornea
#   Etapa 3 -> 100% /
#
# Si el simulador falla en cualquier etapa (errores, lentitud, reparto incorrecto)
# se vuelve a la ETAPA 0: 100% stable, la revisión canary sigue desplegada y etiquetada.
set -Eeuo pipefail

: "${PROJECT_ID:?PROJECT_ID es obligatorio}"
: "${REGION:?REGION es obligatorio}"
: "${SERVICE:?SERVICE es obligatorio}"

BAKE_SECONDS="${BAKE_SECONDS:-120}"
EXPECTED_CANARY_VERSION="${CANARY_VERSION:-3.0.0}"
# Porcentajes de las etapas 1, 2 y 3 (parametrizable desde el workflow).
STAGES="${STAGES:-10 50 100}"
export STRESS_REQUESTS="${STRESS_REQUESTS:-600}"
export STRESS_RAMP="${STRESS_RAMP:-5,10,20}"
# Umbrales de aborto del simulador: la única fuente de verdad es observability/slo.yaml.
eval "$(python scripts/canary-gate.py --print-env)"

mkdir -p reports
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT="reports/canary-rollout-${RUN_ID}.json"
STAGE_LOG="$(mktemp)"

SERVICE_JSON=$(gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --format=json)
STABLE_REV=$(jq -r '[.status.traffic[] | select(.tag=="stable") | .revisionName][0] // empty' <<<"$SERVICE_JSON")
CANARY_REV=$(jq -r '[.status.traffic[] | select(.tag=="canary") | .revisionName][0] // empty' <<<"$SERVICE_JSON")
STABLE_URL=$(jq -r '[.status.traffic[] | select(.tag=="stable") | .url][0] // empty' <<<"$SERVICE_JSON")
CANARY_URL=$(jq -r '[.status.traffic[] | select(.tag=="canary") | .url][0] // empty' <<<"$SERVICE_JSON")
PUBLIC_URL=$(jq -r '.status.url' <<<"$SERVICE_JSON")

if [[ -z "$STABLE_REV" || -z "$CANARY_REV" || -z "$STABLE_URL" || -z "$CANARY_URL" ]]; then
  echo "No se encontraron las revisiones/URLs etiquetadas stable y canary." >&2
  exit 1
fi
export PUBLIC_URL CANARY_URL

write_report() {  # $1=resultado  $2=etapa fallida (o "")  $3=motivo
  jq -n \
    --arg result "$1" --arg failed_stage "$2" --arg reason "$3" \
    --arg stable "$STABLE_REV" --arg canary "$CANARY_REV" \
    --arg version "$EXPECTED_CANARY_VERSION" --argjson bake "$BAKE_SECONDS" \
    --slurpfile stages "$STAGE_LOG" \
    '{result:$result, failed_stage:$failed_stage, reason:$reason,
      stable_revision:$stable, canary_revision:$canary, canary_version:$version,
      bake_seconds_per_stage:$bake, stages:$stages}' > "$REPORT"
  cat "$REPORT"
}

# Vuelve a la etapa 0: 100% stable, canary sigue etiquetada y sin tráfico público.
back_to_stage_0() {
  local stage="$1" reason="$2"
  echo "ETAPA ${stage} FALLÓ (${reason}). Volviendo a etapa 0 (100% stable, 0% canary)..." >&2
  bash scripts/rollback-canary.sh "Etapa ${stage}: ${reason}"
  gcloud run services update-traffic "$SERVICE" --project "$PROJECT_ID" --region "$REGION" \
    --update-tags "canary=${CANARY_REV}" >/dev/null
  # Comprobación: la URL pública ya no debe responder desde canary.
  local track
  track=$(curl -fsS -D - -o /dev/null "$PUBLIC_URL/" | tr -d '\r' | awk -F': ' 'tolower($1)=="x-app-track"{print $2}')
  echo "Tras el rollback la URL pública responde track=${track:-desconocido}" >&2
  write_report "rolled_back_to_stage_0" "$stage" "$reason"
}

verify_identity() {  # $1=url $2=track esperado $3=versión esperada (opcional)
  local headers; headers=$(mktemp)
  if ! curl --retry 5 --retry-delay 2 --retry-connrefused -fsS -D "$headers" "$1/" -o /dev/null; then
    rm -f "$headers"; return 1
  fi
  grep -qi "^X-App-Track: ${2}" "$headers" || { rm -f "$headers"; return 1; }
  if [[ -n "${3:-}" ]]; then
    grep -qi "^X-App-Version: ${3}" "$headers" || { rm -f "$headers"; return 1; }
  fi
  rm -f "$headers"
}

# Ejecuta el simulador para una etapa y registra su resumen.
run_stress() {  # $1=etapa  $2=% canary esperado
  local stage="$1" percent="$2" rc=0
  python scripts/stress-simulator.py --stage "$stage" --canary-percent "$percent" \
    --public-url "$PUBLIC_URL" --canary-url "$CANARY_URL" || rc=$?
  local last; last=$(ls -t reports/stress-stage"${stage}"-*.json 2>/dev/null | head -1 || true)
  if [[ -n "$last" ]]; then
    jq -c '{stage, expected_canary_percent, observed_canary_percent, decision, failed_checks,
            stable_p95_ms: .stable.p95_ms, canary_p95_ms: .canary.p95_ms}' "$last" >> "$STAGE_LOG"
  fi
  return "$rc"
}

# ---------------- Etapa 0: 0% público, pruebas internas ----------------
echo "== ETAPA 0: 0% público =="
verify_identity "$STABLE_URL" stable "" || { echo "La revisión stable no responde como se espera." >&2; exit 1; }
verify_identity "$CANARY_URL" canary "$EXPECTED_CANARY_VERSION" || { back_to_stage_0 0 "identidad canary inválida"; exit 1; }
STAGE=0
if ! run_stress 0 0; then back_to_stage_0 0 "simulador de estrés falló en etapa 0"; exit 1; fi

# ---------------- Etapas 1..3 ----------------
STAGE=0
for PERCENT in $STAGES; do
  STAGE=$((STAGE + 1))
  echo "== ETAPA ${STAGE}: canary=${PERCENT}% / stable=$((100 - PERCENT))% =="
  if [[ "$PERCENT" -eq 100 ]]; then
    TARGET="${CANARY_REV}=100"
  else
    TARGET="${STABLE_REV}=$((100 - PERCENT)),${CANARY_REV}=${PERCENT}"
  fi
  gcloud run services update-traffic "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --to-revisions "$TARGET"

  START=$(date +%s)
  # El estrés corre sobre la URL pública mientras el tráfico ya está repartido.
  if ! run_stress "$STAGE" "$PERCENT"; then
    back_to_stage_0 "$STAGE" "simulador de estrés falló (errores, lentitud o reparto incorrecto)"
    exit 1
  fi
  # Puerta de análisis: decide promover/abortar con las métricas de Grafana Cloud
  # y los umbrales de observability/slo.yaml (stable vs canary).
  if ! python scripts/canary-gate.py --stage "$STAGE" --canary-percent "$PERCENT" --stage-start "$START"; then
    back_to_stage_0 "$STAGE" "la puerta de análisis (Grafana) decidió abortar"
    exit 1
  fi
  # Horneado: completa el tiempo mínimo de observación de la etapa.
  ELAPSED=$(( $(date +%s) - START ))
  if (( ELAPSED < BAKE_SECONDS )); then
    echo "Horneando $((BAKE_SECONDS - ELAPSED))s adicionales (bake time total ${BAKE_SECONDS}s)..."
    sleep $((BAKE_SECONDS - ELAPSED))
  fi
  echo "Etapa ${STAGE} aprobada."
done

write_report "promoted" "" ""