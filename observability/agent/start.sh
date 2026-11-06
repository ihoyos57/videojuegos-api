#!/bin/sh
# Arranca el agente de métricas (si hay credenciales) y luego la API.
# Si el agente falla o no está configurado, la API arranca igualmente.
set -u
AGENT_DIR="${AGENT_DIR:-/etc/agent}"
PORT="${PORT:-8080}"

if [ -n "${GRAFANA_METRICS_TOKEN:-}" ] && [ -n "${GRAFANA_REMOTE_WRITE_URL:-}" ] && [ -n "${GRAFANA_METRICS_USER:-}" ]; then
  umask 077
  printf '%s' "$GRAFANA_METRICS_TOKEN" > /tmp/grafana-token
  unset GRAFANA_METRICS_TOKEN            # la API no necesita ver el token
  INSTANCE_ID="$(cut -c1-8 /proc/sys/kernel/random/uuid)"
  sed \
    -e "s|__SERVICE__|${K_SERVICE:-videojuegos-api}|" \
    -e "s|__TRACK__|${APP_TRACK:-stable}|" \
    -e "s|__VERSION__|${APP_VERSION:-unknown}|" \
    -e "s|__REVISION__|${K_REVISION:-local}|" \
    -e "s|__RW_URL__|${GRAFANA_REMOTE_WRITE_URL}|" \
    -e "s|__RW_USER__|${GRAFANA_METRICS_USER}|" \
    -e "s|__PORT__|${PORT}|" \
    -e "s|__INSTANCE__|${INSTANCE_ID}|" \
    "$AGENT_DIR/prometheus-agent.yml.tmpl" > /tmp/prometheus-agent.yml
  prometheus --enable-feature=agent \
    --config.file=/tmp/prometheus-agent.yml \
    --storage.agent.path=/tmp/agent-data \
    --web.listen-address=127.0.0.1:9090 \
    --log.level=warn &
  echo "[obs] agente de métricas iniciado (instancia ${INSTANCE_ID})"
else
  echo "[obs] sin credenciales de Grafana: agente desactivado"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
