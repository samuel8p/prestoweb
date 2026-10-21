# Presto

API de finanzas e inversiones con marketplace de préstamos. Presto custodia los
fondos de los usuarios y mueve dinero entre ellos (monedas ARS y USD).

Stack: Django 5.x + DRF + PostgreSQL 16 + JWT (simplejwt) + Celery/Redis.

## Estructura

```
config/            # settings por entorno, urls, wsgi/asgi, celery
apps/core/         # utilidades transversales (BaseModel, money, excepciones, paginación)
apps/identity/     # usuarios, auth JWT, perfil, KYC
apps/ledger/       # libro mayor de doble entrada
```

Las reglas del proyecto viven en [AGENTS.md](AGENTS.md): es la fuente de verdad.

## Requisitos

- Docker + Docker Compose

## Comandos

```sh
make up             # levanta db, redis, web, worker y beat
make down           # detiene los servicios
make test           # pytest con cobertura
make lint           # ruff check + ruff format --check + import-linter
make migrate        # aplica migraciones
make makemigrations # genera migraciones faltantes
make shell          # shell de Django
make worker         # celery -A config worker (en primer plano)
make beat           # celery -A config beat (en primer plano)
```

Tareas periódicas (beat, UTC): `mark_overdue_loans` a las 00:05 y
`settle_investments` a las 00:15.

## API

- Prefijo `/api/v1/`
- Esquema OpenAPI: `/api/schema/` — Swagger UI: `/api/docs/`
- Django admin: `/admin/`

Endpoints de identity:

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/auth/register/` | Registro de usuario (5 por hora) |
| POST | `/api/v1/auth/login/` | Login JWT (5 por minuto) |
| POST | `/api/v1/auth/token/refresh/` | Renueva el access token rotando el refresh |
| GET/PATCH | `/api/v1/auth/me/` | Perfil propio |
| GET/POST | `/api/v1/kyc/` | Estado y solicitud de verificación KYC |
| GET | `/api/v1/kyc/{id}/` | Detalle de una verificación propia |

Los errores usan un formato uniforme:

```json
{ "error": { "code": "validation_error", "message": "...", "details": {} } }
```

## Desarrollo

```sh
docker compose up --build -d
docker compose run --rm web pytest -v
```

El hook de pre-commit corre `ruff`, `ruff format` e `import-linter`:

```sh
pip install pre-commit
pre-commit install
```
