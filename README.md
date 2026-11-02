# API RESTful de Videojuegos

API RESTful desarrollada en Python con FastAPI para la gestión de una tienda de videojuegos, incluyendo jugadores, catálogo de juegos y compras, con persistencia real en PostgreSQL, pruebas unitarias, contenedores Docker y pipelines de integración continua.

**Versión:** `v4.0.0` (API v3 canary)

---

## Tabla de contenido

- [Descripción general](#descripción-general)
- [Tecnologías utilizadas](#tecnologías-utilizadas)
- [Entidades y relaciones](#entidades-y-relaciones)
- [Endpoints principales](#endpoints-principales)
- [El verbo HTTP QUERY](#el-verbo-http-query)
- [Arquitectura](#arquitectura)
- [Cómo ejecutar el proyecto](#cómo-ejecutar-el-proyecto)
- [Variables de entorno](#variables-de-entorno)
- [Pruebas y cobertura](#pruebas-y-cobertura)
- [Docker](#docker)
- [Ambientes: Testing y Production](#ambientes-testing-y-production)
- [CI/CD](#cicd)
- [Estructura del proyecto](#estructura-del-proyecto)

---

## Descripción general

Este proyecto implementa una API RESTful completa para una tienda de videojuegos, con lógica de negocio real: verificación de existencia de jugadores y juegos, validación de stock disponible, cálculo automático de totales de compra, y actualización de inventario.

## Tecnologías utilizadas

| Componente | Tecnología |
|---|---|
| Lenguaje / Framework | Python 3.11 + FastAPI |
| Base de datos | PostgreSQL |
| ORM | SQLAlchemy |
| Validación de datos | Pydantic |
| Pruebas | Pytest + pytest-cov + pytest-mock |
| Contenedores | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Documentación interactiva | Swagger UI (`/docs`) |

## Entidades y relaciones

- **Jugador**: `id`, `nombre`, `correo` (único), `fecha_registro`
- **Juego**: `id`, `nombre`, `genero`, `plataforma`, `precio`, `stock`
- **Compra**: `id`, `fecha`, `cantidad`, `total`, `jugador_id` (FK), `juego_id` (FK)

Relaciones: `Jugador 1:N Compra` y `Juego 1:N Compra`.

## Endpoints principales

### Jugadores (`/jugadores`)
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/jugadores/` | Crear jugador |
| GET | `/jugadores/` | Listar jugadores |
| GET | `/jugadores/{id}` | Obtener jugador por id |
| PATCH | `/jugadores/{id}` | Actualizar jugador |
| DELETE | `/jugadores/{id}` | Eliminar jugador |

### Juegos (`/juegos`)
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/juegos/` | Crear juego |
| GET | `/juegos/` | Listar juegos |
| GET | `/juegos/{id}` | Obtener juego por id |
| PATCH | `/juegos/{id}` | Actualizar juego |
| DELETE | `/juegos/{id}` | Eliminar juego |
| QUERY | `/juegos/` | Filtrar juegos (género, plataforma, precio, disponibilidad) |

### Compras (`/compras`)
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/compras/` | Crear compra (valida stock, calcula total, actualiza inventario) |
| GET | `/compras/` | Listar compras |
| GET | `/compras/{id}` | Obtener compra por id |
| DELETE | `/compras/{id}` | Eliminar compra |

## El verbo HTTP QUERY

`GET /juegos/` no permite un cuerpo de petición según el estándar HTTP clásico, y `POST` implica semánticamente "crear". El verbo **QUERY** (estandarizado en [RFC 10008](https://www.ietf.org/), junio 2026) resuelve esto: es un método de solo lectura que sí admite un body, ideal para filtros complejos.

Ejemplo de uso (Swagger no soporta este verbo de forma nativa; se recomienda `curl`):

```bash
curl -X QUERY http://localhost:8000/juegos/ \
  -H "Content-Type: application/json" \
  -d '{"genero": "RPG", "disponible": true}'
```

Cuerpo de filtro admitido (`JuegoFiltro`):

```json
{
  "genero": "RPG",
  "plataforma": "PC",
  "precio_min": 20.0,
  "precio_max": 60.0,
  "disponible": true
}
```

## Arquitectura

```
Cliente (Swagger / curl / Postman)
        │
        ▼
   FastAPI (Routers)
        │
        ▼
  Capa de negocio (crud.py)
        │
        ▼
 SQLAlchemy (Modelos + Sesión)
        │
        ▼
     PostgreSQL
```

Separación en capas: los *routers* solo reciben la petición HTTP y delegan a `crud.py`, que contiene la lógica de negocio real y habla con la base de datos a través del ORM.

## Cómo ejecutar el proyecto

### Requisitos
- Python 3.11+
- PostgreSQL (local o vía Docker)
- pip

### Instalación local

```bash
git clone https://github.com/ihoyos57/videojuegos-api.git
cd videojuegos-api
python -m venv venv
venv\Scripts\Activate.ps1        # Windows
pip install -r requirements.txt
```

Crea un archivo `.env` en la raíz (basado en `.env.example`) con tu cadena de conexión a PostgreSQL.

### Ejecutar el servidor

```bash
uvicorn app.main:app --reload
```

Accede a la documentación interactiva en:

```
http://127.0.0.1:8000/docs
```

## Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DATABASE_URL` | Cadena de conexión a PostgreSQL | `postgresql://usuario:contraseña@localhost:5432/videojuegos_db` |
| `DB_SCHEMA` | Schema de PostgreSQL a utilizar | `public`, `schema_testing`, `schema_production` |

Ver plantillas de referencia: `.env.example`, `.env.testing.example`, `.env.production.example`. **Los archivos `.env` reales nunca se suben al repositorio.**

## Pruebas y cobertura

El proyecto cuenta con pruebas unitarias que utilizan *mocks* para aislar la lógica de negocio de la base de datos real.

```bash
pytest tests/ -v
```

Reporte de cobertura:

```bash
pytest --cov=app tests/
```

**Cobertura actual: 86%** (supera el mínimo de 60% para Testing y 85% para Production).

## Docker

El proyecto incluye `Dockerfile` y `docker-compose.yml` para levantar la aplicación junto con PostgreSQL en contenedores.

```bash
docker compose up --build
```

Servicios levantados:
- `db`: PostgreSQL
- `api-testing`: API en ambiente de Testing (puerto `8001`)
- `api-production`: API en ambiente de Production (puerto `8002`)

## Ambientes: Testing y Production

Ambos ambientes comparten el mismo servidor PostgreSQL, pero están completamente aislados mediante **schemas** distintos:

| Ambiente | Schema | Puerto (Docker) |
|---|---|---|
| Testing | `schema_testing` | `8001` |
| Production | `schema_production` | `8002` |

Cada ambiente tiene su propio archivo de variables de entorno (`.env.testing`, `.env.production`), nunca compartidos ni subidos al repositorio.

## CI/CD

El proyecto utiliza **GitHub Actions** como herramienta SaaS de integración y despliegue continuo, con dos pipelines completamente independientes:

| Pipeline | Disparador | Cobertura mínima (Quality Gate) |
|---|---|---|
| `testing.yml` | Push/PR a rama de testing | ≥ 60% |
| `production.yml` | Push/PR a `main` | ≥ 85% |

Cada pipeline ejecuta: obtención de código → instalación de dependencias → pruebas unitarias → validación de cobertura → despliegue condicional. **Si alguna prueba falla o la cobertura no alcanza el mínimo, el pipeline se detiene y no despliega.**

## Estructura del proyecto

```
videojuegos-api/
├── app/
│   ├── main.py            # Punto de entrada de la aplicación
│   ├── database.py        # Configuración de conexión a PostgreSQL
│   ├── models.py          # Modelos SQLAlchemy
│   ├── schemas.py         # Esquemas Pydantic
│   ├── crud.py            # Lógica de negocio
│   └── routers/
│       ├── jugadores.py
│       ├── juegos.py
│       └── compras.py
├── tests/                 # Pruebas unitarias
├── .github/workflows/     # Pipelines de CI/CD
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Control de versiones

Este proyecto sigue [versionado semántico](https://semver.org/) y utiliza [GitMoji](https://gitmoji.dev/) en todos los commits.

**Versión actual:** `v3.0.0`


---

# Canary Deployment — API v2 estable / API v3 canary

## Alcance de esta entrega

La estrategia Canary reutiliza **Google Cloud Run**, Artifact Registry, Cloud SQL y GitHub Actions que ya forman parte de este repositorio. No se cambia el dominio funcional de videojuegos ni se reemplaza su base de datos.

- **Stable:** API `2.0.1`, track `stable`, mantiene el contrato anterior.
- **Canary:** API `3.0.0`, track `canary`, expone `/api/v3` y la nueva consulta de disponibilidad.
- Ambas rutas versionadas conviven: `/api/v2` y `/api/v3`. Las rutas originales (`/juegos`, `/jugadores`, `/compras`) se mantienen para no romper consumidores existentes.
- Todas las respuestas HTTP incluyen `X-App-Version` y `X-App-Track`.

## Arquitectura del despliegue

```mermaid
flowchart TD
    U[Clientes] --> CR[Google Cloud Run - videojuegos-api-production]
    CR -->|100% inicial / etapas 90-10, 50-50, 0-100| R{Traffic splitting}
    R --> S[Revisión stable - API 2.0.1]
    R --> C[Revisión canary - API 3.0.0]
    S --> DB[(Cloud SQL PostgreSQL)]
    C --> DB
    GH[GitHub Actions] --> AR[Artifact Registry - imagen por digest SHA256]
    AR --> C
    GH -->|gcloud update-traffic| R
```

**Proveedor:** Google Cloud Platform (GCP), Cloud Run en `us-central1`.

**Enrutamiento:** Cloud Run administra el reparto de tráfico entre revisiones del mismo servicio. La revisión `canary` recibe una URL etiquetada para pruebas de humo en etapa 0, sin tráfico público. GitHub Actions modifica los porcentajes mediante `gcloud run services update-traffic`.

## Plan de etapas y horneado

El workflow manual `.github/workflows/rollout-canary.yml` ejecuta las etapas en orden. El horneado predeterminado es de 120 segundos por etapa y se puede parametrizar a 180 o 240 segundos.

| Etapa | Tráfico stable | Tráfico canary | Acceso / observación |
|---|---:|---:|---|
| 0 | 100% | 0% | Pruebas internas por URL etiquetada `canary`; smoke test y cabeceras |
| 1 | 90% | 10% | 120 s de horneado y comprobación HTTP |
| 2 | 50% | 50% | 120 s de horneado y comprobación HTTP |
| 3 | 0% | 100% | Promoción completa y verificación de cabeceras |

El script `scripts/canary-rollout.sh` realiza el reparto, espera el bake time y comprueba disponibilidad. Si falla el control HTTP, devuelve el 100% a la revisión `stable`. El workflow `rollback-canary.yml` permite ejecutar un rollback manual y genera un reporte descargable como artefacto de Actions.

## Versiones y evidencia por petición

| Header HTTP | Stable | Canary |
|---|---|---|
| `X-App-Version` | `2.0.1` | `3.0.0` |
| `X-App-Track` | `stable` | `canary` |

Rutas versionadas:
- `GET /api/v2/juegos/`, `/api/v2/jugadores/`, `/api/v2/compras/`: contrato estable.
- `GET /api/v3/juegos/`, `/api/v3/jugadores/`, `/api/v3/compras/`: contrato V3.
- `GET /api/v3/juegos/{id}/disponibilidad`: nueva funcionalidad V3 que devuelve stock, `disponible`, `estado_inventario` y un mensaje legible.

Para comprobar la versión atendida:

```bash
curl -i https://URL_DEL_SERVICIO/api/v3/juegos/
```

Para probar V3 sin tráfico público se utiliza la URL de revisión etiquetada `canary` que publica Cloud Run.

## Compatibilidad de datos: Expand/Contract

La funcionalidad nueva de V3 calcula la disponibilidad a partir de la columna `stock` ya existente. No agrega ni elimina columnas, no cambia tipos, no modifica claves foráneas y no altera las tablas `jugadores`, `juegos` o `compras`.

- **Expand:** se publica el código V3 que lee el esquema actual y calcula el estado de inventario en tiempo de consulta.
- **Convivencia:** V2 y V3 consultan las mismas columnas y relaciones compatibles con la versión anterior.
- **Contract:** no se ejecuta una contracción ni una migración destructiva en este release. Cualquier limpieza futura se pospone hasta retirar V2 y dejar de necesitar rollback.

Por tanto, el rollback de tráfico a V2 no depende de revertir cambios de base de datos. La funcionalidad V3 no modifica colas ni caché; el proyecto no incorpora esos componentes.

## Artefacto inmutable y release

La imagen de Canary se publica en Artifact Registry con un tag único basado en el release y el SHA del commit; Cloud Run se despliega usando la referencia `@sha256:...`, no una etiqueta mutable. El tag semántico de Git para esta entrega es `v3.0.0`.

Todos los commits nuevos deben usar GitMoji y mensajes SemVer coherentes, por ejemplo:

```bash
git add .
git commit -m ":rocket: implement canary deployment for api v3"
git tag -a v3.0.0 -m "Release v3.0.0 - Canary Deployment"
git push origin main --tags
```

## Workflows

1. `terraform.yml`: despliega la revisión estable y la etiqueta `stable`.
2. `deploy-canary.yml`: desde el tag `v3.0.0`, construye la imagen por digest, despliega Canary con 0% público y verifica la URL etiquetada.
3. `rollout-canary.yml`: ejecuta el rollout progresivo parametrizado.
4. `rollback-canary.yml`: restaura el 100% de tráfico a Stable.

Configura en GitHub Actions las variables `GCP_WORKLOAD_IDENTITY_PROVIDER` y `GCP_DEPLOY_SERVICE_ACCOUNT` (o `GCP_SERVICE_ACCOUNT`), y concede a esa cuenta los permisos necesarios para Cloud Run y Artifact Registry. No almacenes credenciales dentro del repositorio.
