#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?}"
REGION="${REGION:?}"
SERVICE="${SERVICE:?}"
BAKE_SECONDS="${BAKE_SECONDS:-120}"
API_PATH="${API_PATH:-/api/v3/juegos/}"

mkdir -p reports
REPORT="reports/canary-rollout-$(date -u +%Y%m%dT%H%M%SZ).json"

SERVICE_JSON=$(gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --format=json)
STABLE_REV=$(printf '%s' "$SERVICE_JSON" | jq -r '[.status.traffic[] | select(.tag=="stable") | .revisionName][0] // empty')
CANARY_REV=$(printf '%s' "$SERVICE_JSON" | jq -r '[.status.traffic[] | select(.tag=="canary") | .revisionName][0] // empty')
test -n "$STABLE_REV" && test -n "$CANARY_REV" || { echo "Faltan tags stable/canary."; exit 1; }

BASE_URL=$(printf '%s' "$SERVICE_JSON" | jq -r '.status.url')
CANARY_URL=$(printf '%s' "$SERVICE_JSON" | jq -r '[.status.traffic[] | select(.tag=="canary") | .url][0]')
verify_revision() {
  local url="$1" expected_version="$2" expected_track="$3"
  local headers body
  headers=$(mktemp); body=$(mktemp)
  curl --retry 5 --retry-delay 3 --retry-connrefused -fsS -D "$headers" "$url$API_PATH" -o "$body"
  grep -qi "^X-App-Version: $expected_version" "$headers"
  grep -qi "^X-App-Track: $expected_track" "$headers"
  rm -f "$headers" "$body"
}
bake_and_check() {
  local percent="$1"
  echo "Aplicando etapa: canary=${percent}% / stable=$((100-percent))%; bake=${BAKE_SECONDS}s"
  gcloud run services update-traffic "$SERVICE" --project "$PROJECT_ID" --region "$REGION" \
    --to-revisions "$STABLE_REV=$((100-percent)),$CANARY_REV=$percent"
  sleep "$BAKE_SECONDS"
  local good=0 bad=0
  for i in $(seq 1 60); do
    if curl -fsS --max-time 10 "$BASE_URL$API_PATH" >/dev/null; then good=$((good+1)); else bad=$((bad+1)); fi
    sleep 1
  done
  if [ "$good" -lt 55 ] || [ "$bad" -gt 5 ]; then
    echo "Quality gate falló; rollback automático a stable."
    gcloud run services update-traffic "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --to-revisions "$STABLE_REV=100"
    exit 1
  fi
  verify_revision "$CANARY_URL" "3.0.0" "canary"
}
verify_revision "$CANARY_URL" "3.0.0" "canary"
bake_and_check 10
bake_and_check 50
gcloud run services update-traffic "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --to-revisions "$CANARY_REV=100"
sleep "$BAKE_SECONDS"
verify_revision "$CANARY_URL" "3.0.0" "canary"
cat > "$REPORT" <<EOF
{"result":"promoted","stable_revision":"$STABLE_REV","canary_revision":"$CANARY_REV","traffic_stages":[{"canary":0,"stable":100},{"canary":10,"stable":90},{"canary":50,"stable":50},{"canary":100,"stable":0}],"bake_seconds_per_stage":$BAKE_SECONDS}
EOF
cat "$REPORT"
