# Matriz de la rúbrica adaptada a dos estudiantes

| Criterio | Implementación o archivo | Evidencia que debe entregar el equipo |
|---|---|---|
| Dos APIs completas en nubes diferentes | NestJS ECS AWS y FastAPI GKE GCP | URLs activas y CRUD sintético |
| Flujo síncrono y correlación | multicloud.ts / app/multicloud.py, traceparent y spans JSON | Mismo traceId en ambas nubes |
| Kubernetes mínimo 2 réplicas | GKE Terraform y k8s-api.yaml | kubectl get pods y describe con probes/recursos |
| Plataforma como código | Terraform, manifests, experimentos JSON | Commit y release del mismo código desplegado |
| Generador fijo y reproducible | load/profile.js, k6 0.54.0 | Logs y ndjson de carga idéntica |
| Herramienta declarativa más interruptor propio | Chaos Toolkit + cabeceras autenticadas | Journal y logs del fallo inyectado |
| Dos fallos distintos por dos integrantes | Latencia AWS y 503 dependencia consumida por GCP | Ambas ejecuciones con hipótesis individuales |
| Hipótesis, radio, duración, aborto y reversión | Cada JSON y chaos_actions.py | recovery.json y control sin falla |
| Estado estable numérico medido | Ronda steady de 90 s | steady.json y comparación real |
| Ronda 0 sin protección | Cabecera baseline autorizada | Hipótesis refutada en medición, no suposición |
| Dos patrones por integrante | Timeout de dependencia y respuesta parcial | Ronda 1 y logs de timeout/degradación |
| Comparación mismo perfil y fallo | Runner usa el mismo profile.js y tipo de fallo | Tabla, variación y conclusión automática |
| Tablero simultáneo | dashboard.html y Grafana opcional | Captura con ambas rondas y ventana de inyección |
| Diagnóstico, no sólo síntoma | Spans JSON correlacionados y guía | Interpretación propia del mecanismo con traceId |
| Chaos gate en CI/CD | .github/workflows/chaos-gate.yml | Ejecución de Actions y artefactos; rojo si falla |
| Informe máximo 6 páginas | Generador de borrador y plantilla | Completar diagnóstico y revisar extensión final |
| GitMoji, SemVer y release | VERSION, metadatos y release.yml | Commits con emoji y release etiquetado |
| Sustentación individual 60% | SUSTENTACION.md | Cada integrante explica y demuestra ambas nubes |
| IA declarada | README e informe | Explicar qué se aceptó y descartó |

Se elimina el tercer integrante, tercera nube y tercer fallo de agotamiento de recursos según la adaptación solicitada. No se reduce el mínimo explícito de dos réplicas Kubernetes ni los dos patrones por integrante. No se afirma cumplimiento de evidencias aún no ejecutadas.
