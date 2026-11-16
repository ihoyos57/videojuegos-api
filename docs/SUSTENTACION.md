# Guía de sustentación individual

## Demostración de cinco momentos

1. Mostrar ambas APIs activas y dos pods GKE listos. Hacer un GET con traceparent fijo y localizar el traceId en las dos nubes. Explicar por qué raw no genera recursión.
2. Abrir el experimento JSON: estado estable, hipótesis falsable, objetivo, radio, duración, abortos y rollback. Ejecutar desde Actions o mostrar su journal y reproducir durante la ventana acordada.
3. Enseñar el tablero con estado estable y las dos rondas. Distinguir p95 global de intervalos; mostrar carga idéntica y diferencia de solicitudes completadas como efecto del fallo.
4. Mostrar timeout y respuesta parcial actuando. Explicar que la disponibilidad local puede conservarse mientras el flujo completo pierde completitud. No prometer juegos/mascotas vivos cuando la otra nube está caída.
5. Retirar cabeceras, esperar el timeout y mostrar recuperación completa. Desactivar CHAOS_ENABLED en ambos despliegues al cerrar la ventana.

## Preguntas que deben poder responder ambos

- ¿Qué diferencia hay entre probar un fallo conocido y formular una hipótesis? El experimento puede refutar una expectativa sobre un sistema bajo condiciones medidas; no basta ejecutar una excepción y decir que pasó.
- ¿Qué es el estado estable? Comportamiento observado bajo el perfil fijo, registrado numéricamente antes del fallo. No equivale sólo a health=200.
- ¿Por qué 1500 ms y 1%? Son objetivos propuestos para una API interactiva de laboratorio y una disponibilidad local de 99%; deben acordarse antes y contrastarse con la línea base, no elegirse después para que pase.
- ¿Qué mide cada integrante? AWS p95 E2E; GCP tasa de error local. Completitud remota es una métrica diagnóstica separada.
- ¿Qué ocurre si ronda 0 no refuta? La demostración de mejora es insuficiente; revisar que realmente se activó el fallo, alcance, carga y diagnóstico. No fabricar datos ni cambiar sólo una ronda.
- ¿Qué es una cascada? Un fallo de dependencia convierte peticiones válidas del consumidor en errores; GCP sin protección transforma 503 remoto en 502 local.
- ¿Por qué no reintentar? Una dependencia caída puede recibir una tormenta de reintentos y la latencia se amplifica. Se eligieron timeout y respuesta parcial; un circuito o bulkhead serían siguientes mejoras basadas en diagnóstico.
- ¿Por qué no caché? Se requiere lectura realtime. La respuesta degradada es explícita, no un objeto antiguo presentado como actual.
- ¿Qué es radio de impacto? Aquí son sólo GET sintéticos autenticados, no todas las cuentas, bases ni tráfico. Un fallo de pod real tendría otro radio y exigiría otro plan.
- ¿Qué es MTTR? Tiempo de recuperación desde el fallo hasta volver al criterio acordado. Esta entrega verifica recuperación y guarda su instante, pero no usa MTTR como métrica objetivo ni lo confunde con el timeout.
- ¿Qué es presupuesto de error? Fallos tolerables según el SLO y su ventana. Una ventana de prueba de 90 s no demuestra un SLO mensual.
- ¿Qué es game day? Ejecución acordada con responsables, observabilidad, condiciones de aborto y reversión probada.
- ¿Qué madurez tiene esta solución? Laboratorio con automatización, radio acotado y evidencia comparable; no caos aleatorio en producción sin límites.
- ¿Qué hace Kubernetes aquí? Ejecuta dos réplicas y las reemplaza si fallan; readiness evita enviar tráfico a una API sin DB y liveness comprueba proceso. No se usa Kubernetes para afirmar que un 503 remoto desaparece automáticamente.
- ¿Qué antipatrones se evitan? Cambiar carga entre rondas, ocultar fallos bajo HTTP 200 sin medir completitud, falta de reversión, inyectar a terceros o confundir datos simulados con evidencia de nube.

Ensayar las respuestas con resultados propios. La rúbrica asigna 60% a la sustentación individual; cada integrante debe conocer AWS, GCP, los dos fallos, la observabilidad y la puerta de calidad.
