# INFORME DEL GAME DAY DE SEGURIDAD — máximo 10 páginas

**Estado: PLANTILLA, NO EVIDENCIA REAL DE NUBE.** Sustituir cada PENDIENTE con cifras de eventos medidos antes de la entrega, y exportar a PDF ≤10 páginas. No sustituir con métricas de resiliencia DevOps.

## 1. Integrantes, alcance y control de cambios

Guillermo Andrés Duque Pineda: control máquina AWS; Isabella Hoyos Orrego: telemetría / IA GCP; ambos: recuperación S3. Infraestructura AWS ECS + GCP GKE, integrada por `/pets/raw` y `/juegos/raw`. Fecha y ventana UTC **PENDIENTES**. Checklist de reglas de compromiso **PENDIENTE FIRMAS**.

## 2. Inventario de controles y estado estable

Inventario por capa, ISO Anexo A, MITRE ATT&CK/D3FEND y fronteras: `DEFENSA-GAMEDAY.md`. Inserte: número de controles activos, cobertura de logging efectiva, muestras CloudWatch/GCP, estado de las alarmas, muestras normales `traceId` **PENDIENTE**. MTTD y MTTC de referencia si medibles **PENDIENTES**.

## 3. Hipótesis registradas ANTES de la ronda 0

- E1 identidad: alerta ≤3 min, contención ≤1 min, cobertura 1/1 y FPR ≤5%, solicitud con alcance/origen no esperado.
- E3 telemetría: pérdida de latido alerta ≤3 min, señuelo ≤3 min y ninguna ejecución autónoma de IA.
- E4 datos: R1 RPO/RTO no peores que R0, última revisión y hash restaurados.

## 4. Método, cronología UTC minuto a minuto y radio

| Experimento | Inicio UTC | Fin UTC | Traza/alarma | Acción/resultado |
|---|---|---|---|---|
| E1 R0 | PENDIENTE | PENDIENTE | PENDIENTE | GET autenticación antes del control |
| E1 R1 | PENDIENTE | PENDIENTE | PENDIENTE | rechazo con prueba efímera |
| E3 R0 | PENDIENTE | PENDIENTE | PENDIENTE | ausencia de heartbeat/decoy sin regla |
| E3 R1 | PENDIENTE | PENDIENTE | PENDIENTE | alerta GCP por ausencia y decoy |
| E4 R0 | PENDIENTE | PENDIENTE | PENDIENTE | sobreescritura de objeto sintético |
| E4 R1 | PENDIENTE | PENDIENTE | PENDIENTE | recuperación desde copia WORM |

Adjuntar por cada fila `probes.jsonl`, logs con mismo `traceId`, captura de alerta, marca de fin/contención y hash del archivo. No considerar `HTTP 401` una *detección en SIEM* sin evidencia de la alarma.

## 5. Resultados de las rondas (N/D hasta medición)

| Experimento / señal | R0 | R1 | Cambio | ¿Cumple hipótesis? |
|---|---|---|---|---|
| E1 MTTD en segundos | N/D | N/D | N/D | PENDIENTE |
| E1 MTTC en segundos | N/D | N/D | N/D | PENDIENTE |
| E1 cobertura (técnicas detectadas/emuladas) | N/D | N/D | N/D | PENDIENTE |
| E1 tasa falsos positivos | N/D | N/D | N/D | PENDIENTE |
| E3 MTTD (heartbeat/decoy) | N/D | N/D | N/D | PENDIENTE |
| E3 MTTC | N/D | N/D | N/D | PENDIENTE |
| E3 cobertura y falsos positivos | N/D | N/D | N/D | PENDIENTE |
| E4 RPO segundos | N/D | N/D | N/D | PENDIENTE |
| E4 RTO segundos | N/D | N/D | N/D | PENDIENTE |
| E4 última revisión restaurada | N/D | N/D | N/D | PENDIENTE |

## 6. Evidencias de controles como código y dos mejoras/estudiante

Reglas AWS `terraform/security_detection.tf`, GCP `terraform/security_monitoring.tf`, casos positivos/negativos y resultados CI. AWS: (1) proof aud/TTL/replay y (2) alarma nativa. GCP: (1) monitor de latido y (2) honeytoken detectado. Consignar hashes de commits, enlaces a runs CI, alarmas, screenshots y registro de la efectividad **PENDIENTE**.

## 7. IA y prompt injection (2 rondas reales del modelo)

Fuente del dato: `security/fixtures/ai-prompt-injection.jsonl` con `juego_nombre` hostil. OWASP ASI01 / ATLAS AML.T0051. Modelo y versión **PENDIENTE**; respuesta R0 **PENDIENTE**; respuesta R1 **PENDIENTE**. Comparación humano contra telemetría: aciertos **PENDIENTE**, alucinaciones **PENDIENTE**, medidas rechazadas y razón **PENDIENTE**. El modelo no tiene herramientas y toda remediación necesita aprobación humana. No afirmar resistencia de un modelo basándose solo en `ai_review.py`.

## 8. Tendencias, recuperación, riesgos residuales

Instrumentadas: 2026 agentes/IA con humano aprobador (OWASP) y honeytokens (CSA/CISA). Capturas de sus señales **PENDIENTE**. Riesgos: HMAC con secreto estático compartido; replay cache local entre réplicas; suplantación de origen si se conoce el secreto; ausencia de log por contenedor vs per-pod monitoring; dependencia de Cloud Monitoring; object lock sólo en bucket laboratorio; no respaldo completo de SQL. Experimentos siguientes: OIDC federado con aud y key rotation; alerta de múltiples réplicas; recuperación de DB transaccional.

## 9. Reversión y conclusiones

Cronología de STOP, verificación de `/health/*`, estado de ECS/GKE, alarmas, objeto restaurado y bitácoras **PENDIENTE**. Dictamen por hipótesis y limitaciones honestas, sin atribuir al sistema global mediciones de un objeto aislado. Este informe es distinto al entregable DevOps de latencia/503.
