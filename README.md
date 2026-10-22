# Presto

API de finanzas e inversiones con marketplace de préstamos. Presto custodia los
fondos de los usuarios y mueve dinero entre ellos (monedas ARS y USD).

Stack: Django 5.x + DRF + PostgreSQL 16 + JWT (simplejwt) + Celery/Redis.

Las reglas del proyecto viven en [AGENTS.md](AGENTS.md): es la fuente de verdad.
La arquitectura está en [docs/architecture.md](docs/architecture.md) y el estado
del trabajo en [HANDOFF.md](HANDOFF.md).

## Estructura

```
config/            # settings por entorno, urls, wsgi/asgi, celery
apps/core/         # utilidades transversales (BaseModel, money, excepciones, paginación)
apps/identity/     # usuarios, auth JWT, perfil, KYC
apps/ledger/       # libro mayor de doble entrada (cuentas, movimientos, reversos)
apps/offers/       # ofertas de préstamo del prestamista
apps/matching/     # búsqueda, comparación y recomendación (solo lectura)
apps/loans/        # préstamos tomados, cuotas y estados
apps/investments/  # plazos fijos
apps/budgets/      # presupuestos, categorías y gastos
apps/reports/      # reportes de solo lectura y exportación a CSV
apps/notifications/# avisos por email
docs/              # arquitectura, ADRs y guías de despliegue
deploy/            # proxy inverso (Caddy) y backup de PostgreSQL
```

## Requisitos

- Docker + Docker Compose
- `make` es **opcional**: los targets de abajo son atajos. Si no lo tenés, usá
  directamente los comandos de Docker Compose que aparecen en cada target.

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
make audit          # pip-audit: vulnerabilidades conocidas de las dependencias
```

Sin `make`, los equivalentes:

```sh
docker compose up --build -d
docker compose run --rm web python -m pytest -v
docker compose run --rm web ruff check . && docker compose run --rm web ruff format --check .
docker compose run --rm web lint-imports
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py makemigrations
```

Tareas periódicas (beat, UTC):

| Hora | Tarea | Qué hace |
|---|---|---|
| 00:05 | `apps.loans.tasks.mark_overdue_loans` | Vence las cuotas atrasadas y deja el préstamo en default |
| 00:10 | `apps.loans.tasks.notify_installments_due_soon` | Avisa las cuotas que vencen en los próximos días |
| 00:15 | `apps.investments.tasks.settle_investments` | Liquida los plazos fijos vencidos |
| 00:20 | `apps.loans.tasks.notify_overdue_installments` | Avisa las cuotas atrasadas |

Las dos primeras también se pueden correr a mano:
`python manage.py mark_overdue_loans` y `python manage.py settle_investments`.

## Modo demo

Con `DEMO_MODE=true` la aplicación corre como demostración:

- el dinero es simulado (depositos y retiros de prueba);
- los avisos de las notificaciones salen por consola, en los logs del worker;
- el system check `ledger.E001` no bloquea el dinero simulado.

El compose de desarrollo ya lo trae activado. La guía completa está en
[docs/deploy-demo.md](docs/deploy-demo.md).

## API

- Prefijo `/api/v1/`
- Esquema OpenAPI: `/api/schema/` — Swagger UI: `/api/docs/`
- Django admin: `/admin/`
- Chequeo de estado: `/health/`
- Modo de la instancia: `/api/v1/meta/`

| App | Endpoints |
|---|---|
| identity | `POST /api/v1/auth/register/`, `POST /api/v1/auth/login/`, `POST /api/v1/auth/token/refresh/`, `GET/PATCH /api/v1/auth/me/`, `GET/POST /api/v1/kyc/`, `GET /api/v1/kyc/{id}/` |
| ledger | `GET/POST /api/v1/ledger/accounts/`, `GET /api/v1/ledger/accounts/{id}/balance/`, `GET/POST /api/v1/ledger/transactions/`, `GET /api/v1/ledger/transactions/{id}/` |
| offers | `GET/POST /api/v1/offers/`, `GET/PATCH /api/v1/offers/{id}/` (el PATCH también expira la oferta) |
| matching | `GET /api/v1/matching/offers/`, `POST /api/v1/matching/comparisons/` |
| loans | `GET/POST /api/v1/loans/`, `GET /api/v1/loans/{id}/`, `POST /api/v1/loans/{id}/installments/{number}/pay/` |
| investments | `GET /api/v1/investments/products/`, `GET/POST /api/v1/investments/positions/`, `GET /api/v1/investments/positions/{id}/` |
| budgets | `GET/POST /api/v1/budgets/`, `GET/PATCH /api/v1/budgets/{id}/`, `GET /api/v1/budgets/{id}/status/`, `GET/POST /api/v1/budgets/categories/`, `GET/PATCH /api/v1/budgets/categories/{id}/`, `GET/POST /api/v1/budgets/expenses/` |
| reports | `GET /api/v1/reports/spending/`, `GET /api/v1/reports/investments/`, `GET /api/v1/reports/loans/`, `GET /api/v1/reports/movements/` |
| notifications | `GET /api/v1/notifications/`, `GET/PUT /api/v1/notifications/preferences/` |

Los errores usan un formato uniforme:

```json
{ "error": { "code": "validation_error", "message": "...", "details": {} } }
```

## Desarrollo

```sh
docker compose up --build -d
docker compose run --rm web python -m pytest -v
```

El hook de pre-commit corre `ruff`, `ruff format` e `import-linter`:

```sh
pip install pre-commit
pre-commit install
```

## Producción

El compose de producción (`docker-compose.prod.yml`) levanta Django + Gunicorn,
PostgreSQL, Redis, el worker de Celery, el beat y, opcionalmente, el proxy
inverso con TLS (perfil `proxy`) y los backups diarios (perfil `backup`).

```sh
cp .env.prod.example .env.prod   # completá los secretos
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

La guía de despliegue está en [docs/deploy-demo.md](docs/deploy-demo.md): incluye
el paso a paso para **Oracle Cloud (Ubuntu 24.04 ARM) + DuckDNS + Vercel**, la
compatibilidad ARM, los valores de concurrencia recomendados según la RAM y el
procedimiento de restauración de backups.
