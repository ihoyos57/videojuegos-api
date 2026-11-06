FROM prom/prometheus:v2.55.1 AS prometheus

FROM python:3.11-slim

WORKDIR /app
ARG APP_VERSION=2.0.1
ENV APP_VERSION=${APP_VERSION}
ENV APP_TRACK=stable

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Agente de métricas (binario estático) que envía /metrics a Grafana Cloud.
COPY --from=prometheus /bin/prometheus /usr/local/bin/prometheus
COPY observability/agent/ /etc/agent/
RUN sed -i 's/\r$//' /etc/agent/start.sh /etc/agent/prometheus-agent.yml.tmpl && chmod +x /etc/agent/start.sh

COPY app ./app
CMD ["/etc/agent/start.sh"]
