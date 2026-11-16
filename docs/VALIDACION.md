# Validación realizada y límites

Se compiló NestJS y se probaron las integraciones con un servidor HTTP local. Se verificaron listas, IDs, lectura nueva sin caché, un solo objeto remoto, trazas, ausencia de recursión, 404 y fallos autenticados con vencimiento. FastAPI fue probado con las dependencias fijadas en requirements.txt y SQLite aislado.

Se ejecutaron ambos experimentos mediante Chaos Toolkit y k6 0.54.0, con el perfil completo de 90 segundos por medición. El entorno fue local: FastAPI con SQLite y middleware AWS real sobre handlers Fastify de fixture, NO ECS/RDS/GKE/Cloud SQL. Las dos puertas finalizaron correctamente y verificaron recuperación. Estos resultados comprueban el mecanismo, no son evidencia de las cuentas de los estudiantes.

Resultado local de este repositorio:

```json
{
  "experiment": "gcp-unavailable",
  "fault": "unavailable",
  "measured": {
    "steady": {
      "p95_ms": 25.5704275,
      "local_error": 0,
      "complete": 1,
      "requests": 1791
    },
    "round0": {
      "p95_ms": 20.250880399999996,
      "local_error": 1,
      "complete": 0,
      "requests": 1805
    },
    "round1": {
      "p95_ms": 15.4257211,
      "local_error": 0,
      "complete": 0,
      "requests": 1815
    }
  },
  "gate": true,
  "metric": "local_error",
  "threshold": 0.01,
  "before": 1,
  "after": 0,
  "variation_percent": -100.0,
  "hypothesis_refuted_round0": true,
  "recovered": true
}
```

Los JSON declarativos fueron validados por Chaos Toolkit. Terraform fmt y parseo HCL pasaron; init descargó los proveedores de ambos proyectos. Terraform validate con los proveedores no pudo completar porque este entorno bloquea sus sockets Unix. Ejecutar validate y plan en CloudShell antes de aplicar. No se realizó despliegue, validación IAM, comprobación de costos, release ni medición real en las cuentas de los estudiantes.

Las pruebas locales no reemplazan la línea base y las dos rondas de cada integrante en nube. No cambiar el informe final para atribuir estos números a AWS/GCP. Los scripts generan nuevas evidencias con las URLs reales.
