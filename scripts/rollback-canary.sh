#!/usr/bin/env bash
set -euo pipefail
PROJECT_ID="${PROJECT_ID:?}"
REGION="${REGION:?}"
SERVICE="${SERVICE:?}"
REASON="${1:-Manual rollback}"
mkdir -p reports
SERVICE_JSON=$(gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --format=json)
STABLE_REV=$(printf '%s' "$SERVICE_JSON" | jq -r '[.status.traffic[] | select(.tag=="stable") | .revisionName][0] // empty')
test -n "$STABLE_REV" || { echo "No se encontró revisión stable etiquetada."; exit 1; }
gcloud run services update-traffic "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --to-revisions "$STABLE_REV=100" --set-tags "stable=$STABLE_REV"
printf '{"result":"rollback","stable_revision":"%s","reason":"%s"}\n' "$STABLE_REV" "$(printf '%s' "$REASON" | sed 's/"/\\"/g')" > "reports/rollback-$(date -u +%Y%m%dT%H%M%SZ).json"
