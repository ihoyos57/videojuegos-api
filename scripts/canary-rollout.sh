#!/usr/bin/env bash
set -Eeuo pipefail

: "${PROJECT_ID:?PROJECT_ID es obligatorio}"
: "${REGION:?REGION es obligatorio}"
: "${SERVICE:?SERVICE es obligatorio}"

BAKE_SECONDS="${BAKE_SECONDS:-120}"
EXPECTED_CANARY_VERSION="${CANARY_VERSION:-3.0.0}"
mkdir -p reports
REPORT="reports/canary-rollout-$(date -u +%Y%m%dT%H%M%SZ).json"

rollback() {
  echo "Quality gate falló. Restaurando 100% del tráfico a stable..." >&2
  bash scripts/rollback-canary.sh "Quality gate incumplido durante rollout"
}

SERVICE_JSON=$(gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --format=json)
STABLE_REV=$(jq -r '[.status.traffic[] | select(.tag=="stable") | .revisionName][0] // empty' <<<"$SERVICE_JSON")
CANARY_REV=$(jq -r '[.status.traffic[] | select(.tag=="canary") | .revisionName][0] // empty' <<<"$SERVICE_JSON")
STABLE_URL=$(jq -r '[.status.traffic[] | select(.tag=="stable") | .url][0] // empty' <<<"$SERVICE_JSON")
CANARY_URL=$(jq -r '[.status.traffic[] | select(.tag=="canary") | .url][0] // empty' <<<"$SERVICE_JSON")
BASE_URL=$(jq -r '.status.url' <<<"$SERVICE_JSON")

if [[ -z "$STABLE_REV" || -z "$CANARY_REV" || -z "$STABLE_URL" || -z "$CANARY_URL" ]]; then
  echo "No se encontraron las revisiones/URLs etiquetadas stable y canary." >&2
  exit 1
fi

export STABLE_URL CANARY_URL
export STABLE_REVISION="$STABLE_REV" CANARY_REVISION="$CANARY_REV"
export REQUESTS_PER_REVISION="${REQUESTS_PER_REVISION:-1000}"
export CONCURRENCY="${CONCURRENCY:-20}"
export MIN_REQUESTS_PER_REVISION="${MIN_REQUESTS_PER_REVISION:-1000}"
export MAX_5XX_RATE="${MAX_5XX_RATE:-0.01}"
export MAX_4XX_RATE="${MAX_4XX_RATE:-0.05}"
export MAX_P95_LATENCY_MS="${MAX_P95_LATENCY_MS:-500}"
export MAX_P95_REGRESSION_PERCENT="${MAX_P95_REGRESSION_PERCENT:-20}"
export MAX_CPU_UTILIZATION="${MAX_CPU_UTILIZATION:-0.80}"
export MAX_MEMORY_UTILIZATION="${MAX_MEMORY_UTILIZATION:-0.85}"
export PROJECT_ID REGION SERVICE
export GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)"

verify_identity() {
  local url="$1" expected_track="$2" expected_version="$3"
  local headers
  headers=$(mktemp)
  if ! curl --retry 5 --retry-delay 2 --retry-connrefused -fsS -D "$headers" "$url/" -o /dev/null; then
    rm -f "$headers"; return 1
  fi
  grep -qi "^X-App-Track: ${expected_track}" "$headers" || { rm -f "$headers"; return 1; }
  if [[ -n "$expected_version" ]]; then
    grep -qi "^X-App-Version: ${expected_version}" "$headers" || { rm -f "$headers"; return 1; }
  fi
  rm -f "$headers"
}

run_gate() {
  local stage="$1"
  echo "Esperando ${BAKE_SECONDS}s para etapa canary=${stage}%..."
  sleep "$BAKE_SECONDS"
  if ! python scripts/compare-baseline.py; then
    rollback
    exit 1
  fi
  echo "Quality gate aprobado para etapa ${stage}%."
}

verify_identity "$STABLE_URL" stable "" || { echo "La revisión stable no responde como se espera." >&2; exit 1; }
verify_identity "$CANARY_URL" canary "$EXPECTED_CANARY_VERSION" || { rollback; exit 1; }

for PERCENT in 10 50; do
  echo "Aplicando canary=${PERCENT}% / stable=$((100-PERCENT))%"
  gcloud run services update-traffic "$SERVICE" --project "$PROJECT_ID" --region "$REGION" \
    --to-revisions "${STABLE_REV}=$((100-PERCENT)),${CANARY_REV}=${PERCENT}"
  run_gate "$PERCENT"
done

echo "Aplicando canary=100% / stable=0%"
gcloud run services update-traffic "$SERVICE" --project "$PROJECT_ID" --region "$REGION" \
  --to-revisions "${CANARY_REV}=100"
run_gate 100

cat > "$REPORT" <<JSON
{
  "result": "promoted",
  "stable_revision": "$STABLE_REV",
  "canary_revision": "$CANARY_REV",
  "canary_version": "$EXPECTED_CANARY_VERSION",
  "traffic_stages": [
    {"canary": 0, "stable": 100},
    {"canary": 10, "stable": 90},
    {"canary": 50, "stable": 50},
    {"canary": 100, "stable": 0}
  ],
  "bake_seconds_per_stage": $BAKE_SECONDS,
  "comparison": "Concurrent direct requests against stable and canary tagged revision URLs"
}
JSON
cat "$REPORT"
