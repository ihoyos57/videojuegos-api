# API RESTful de Videojuegos

API RESTful desarrollada en Python con FastAPI para la gestión de una tienda de videojuegos, incluyendo jugadores, catálogo de juegos y compras, con persistencia real en PostgreSQL, pruebas unitarias, contenedores Docker y pipelines de integración continua.

**Versión:** `v1.0.0`

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

**Versión actual:** `v1.0.0`
