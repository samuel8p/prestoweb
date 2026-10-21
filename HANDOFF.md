# HANDOFF — Presto

> Documento de traspaso para retomar el trabajo. La fuente de verdad del proyecto es
> [AGENTS.md](AGENTS.md); este documento describe el **estado real** del repo, las
> decisiones tomadas y lo que falta. Todo lo que está aquí fue **verificado** con los
> comandos del §10; si algo no se comprobó, dice explícitamente "sin verificar".
>
> **Última actualización:** 2026-10-21 · rama `main` · HEAD `b3cbf8b` · 73 commits
> (74 después de este commit). `main` está sincronizada con `origin/main` y el árbol
> de trabajo está limpio.

---

## 1. Proyecto

Presto es una API de finanzas e inversiones con marketplace de préstamos.
El usuario puede publicar ofertas de préstamo, buscar y comparar ofertas como
prestatario, aceptar un préstamo, pagar sus cuotas e invertir su saldo a plazo
fijo. Presto custodia los fondos de los usuarios y los mueve entre ellos en dos
monedas: **ARS** y **USD**, sin conversión implícita.

El backend es **API-only** (no hay frontend en el repo). Todo movimiento de
dinero pasa por el `ledger`, un libro mayor de doble entrada con idempotencia,
reversos y saldo nunca negativo en las billeteras de usuario.

**Hoja de ruta:** Fase 0 (Cimientos) **completa**. Fase 1 **completa** (1A identity
+ 1B ledger). Bloques 3 (offers+matching), 4 (loans) y 5 (investments) **completos**.
El **Bloque 6** (budgets/reports/notifications) está **en curso**: la
infraestructura de Celery (worker, beat y tasks periódicas) y la app **`budgets`**
(gastos categorizados y presupuestos mensuales) ya están; `reports` y
`notifications` todavía no. Falta el **Bloque 7** (payments con proveedor real).

**Decisiones de negocio ya confirmadas por el cliente:** la regla de "gastado" de
los presupuestos (O4) está resuelta y esperando implementación (§11.2). Las
demás siguen abiertas (§11.1).

## 2. Stack y versiones

| Área | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.12+ (la imagen usa 3.12) |
| Framework | Django | `>=5.2,<6` (instalado: 5.2.18) |
| API | Django REST Framework | 3.18.3 |
| Auth | JWT con `djangorestframework-simplejwt` | 5.5.1 (con `token_blacklist`) |
| Documentación | `drf-spectacular` | 0.30.0 |
| Base de datos | PostgreSQL | 16 (contenedor `db`) |
| Cache/broker | Redis | 7-alpine (contenedor `redis`) |
| Tareas async | Celery | 5.6.3 (en uso: `config/celery.py`, worker y beat en el compose) |
| Tests | `pytest` + `pytest-django` + `pytest-cov` + `factory_boy` | pytest 9.1.1 / pytest-django 4.14.0 / pytest-cov 7.1.0 / factory_boy 3.3.3 |
| Lint / formato | `ruff` (E, F, I, B, UP; línea 100; comillas simples) | — |
| Límites entre apps | `import-linter` | 2.15 (11 contratos activos) |
| Hooks | `pre-commit` (ruff, ruff-format, import-linter) | 4.7.0 (instalado en el host) |
| Contenedores | Docker + Docker Compose | — |
| CI | GitHub Actions (`.github/workflows/ci.yml`, jobs `quality`, `migrations`, `tests`) | — |

Base de datos: una sola, PostgreSQL 16, un solo despliegue (monolito modular).
Sin dependencias agregadas desde el Bloque 5: `celery` y `redis` ya estaban en
`pyproject.toml` y en el `Dockerfile`.

## 3. Estructura del repositorio

```
.
├── AGENTS.md                     # fuente de verdad del proyecto (§1-§17)
├── README.md                     # quickstart, endpoints, formato de error
├── HANDOFF.md                    # este documento
├── Makefile                      # up, down, test, lint, migrate, shell, makemigrations,
│                                 #   worker, beat, celery-tasks
├── docker-compose.yml            # db, redis, web, worker, beat (localhost only)
├── docker-compose.prod.yml        # producción: sin puertos de db/redis, secretos por env
├── Dockerfile                    # python:3.12-slim + deps de pyproject.toml
├── pytest.ini                    # DJANGO_SETTINGS_MODULE + --ds=config.settings.test
├── pyproject.toml                # deps + config de ruff
├── .importlinter                 # 11 contratos de límites entre apps
├── .pre-commit-config.yaml       # ruff, ruff-format, import-linter
├── .github/workflows/ci.yml      # ruff, import-linter, spectacular, makemigrations, pytest
├── .env.example                  # SOLO placeholders, nunca secretos reales
├── apps/
│   ├── core/                     # transversales: BaseModel, money, exceptions,
│   │   └── tests/                #   pagination, exception_handler, test_openapi, test_celery
│   ├── identity/                 # User, Profile, KYCVerification; auth JWT
│   │   └── tests/
│   ├── ledger/                   # Account, LedgerTransaction, LedgerEntry
│   │   └── tests/
│   ├── offers/                   # Offer (plazo fijo, TNA anual) + permissions.py
│   │   └── tests/
│   ├── matching/                 # solo lectura: búsqueda y comparación
│   │   └── tests/
│   ├── loans/                    # Loan, OfferTermsSnapshot, Installment
│   │   ├── management/commands/  #   mark_overdue_loans
│   │   ├── tasks.py              #   task Celery mark_overdue_loans
│   │   └── tests/
│   ├── investments/              # InvestmentProduct, Position (plazo fijo)
│   │   ├── management/commands/  #   settle_investments
│   │   ├── tasks.py              #   task Celery settle_investments
│   │   └── tests/
│   └── budgets/                  # Category, Budget, Expense (gastos categorizados)
│       └── tests/
├── config/
│   ├── settings/                 # base, local, test, production
│   ├── celery.py                 # app de Celery + beat schedule diario
│   ├── urls.py                   # /api/v1/ + /api/schema/ + /api/docs/ + /admin/
│   ├── wsgi.py, asgi.py
└── docs/
    └── adr/
        ├── 0001-celery-redis-cola-y-scheduler.md
        └── 0002-budgets-derivacion-del-gasto.md
```

Apps existentes: `core`, `identity`, `ledger`, `offers`, `matching`, `loans`,
`investments`, `budgets`. **No existen** (aún): `reports`, `notifications`,
`payments`. `docs/architecture.md` **tampoco existe**.

## 4. Entorno local e invariantes del dinero

- Docker + Docker Compose (único requisito; todo corre en contenedores).
- Puertos publicados **solo en localhost**: `127.0.0.1:5432` (Postgres),
  `127.0.0.1:6379` (Redis), `127.0.0.1:8000` (web). `worker` y `beat` no publican
  puertos.
- El código se monta como volumen (`.:/app`), así que los cambios se reflejan
  sin reconstruir la imagen.
- `web` corre `manage.py migrate` y después `runserver` en `0.0.0.0:8000`.
  `worker` corre `celery -A config worker -l info` y `beat` corre
  `celery -A config beat -l info --schedule /var/celerybeat/celerybeat-schedule`
  (estado del scheduler en un volumen Docker, fuera del working tree).
- `DJANGO_SETTINGS_MODULE` del servicio web: `config.settings.local`
  (`config.settings.test` solo para los tests, `config.settings.production` para
  producción).
- Variables de entorno: ver `.env.example` (placeholders, sin secretos).

### Invariantes del ledger (requisitos de negocio, garantizados en código y en la DB)

1. **El saldo no negativo aplica solo a `user_wallet`.** Una billetera de usuario
   nunca puede quedar negativa (`CheckConstraint(balance >= 0)` en `Account`). Las
   cuentas de contrapartida (`custody`, `system`) representan el mundo exterior y
   **pueden** quedar negativas: eso es correcto, no un bug.
2. **`idempotency_key` es única por `(usuario, clave)`, no global.** Se guarda
   además un `request_hash` del payload: misma clave **y** mismo hash devuelven la
   operación original; misma clave **y** hash distinto devuelven `409`. Ante un
   `IntegrityError` por concurrencia, el service reintenta y devuelve la original.
3. **La suma de saldos por moneda es cero.** Con `balance = créditos - débitos`, la
   suma de **todos** los saldos de una moneda da 0:
   `Σ(custody) + Σ(system) = -Σ(user_wallet)`. Hay un test de invariante que lo
   verifica por moneda después de depósitos, retiros, transferencias, préstamos e
   inversiones.

## 5. Convenciones y flujo de trabajo

- **AGENTS.md manda.** Si una instrucción contradice AGENTS.md, se avisa antes de
  actuar.
- **Nombres de campos, clases y funciones en inglés**; docstrings de
  `services.py` / `selectors.py` en español; comentarios y logs en español.
- **Capas obligatorias** (AGENTS §5.1): `views.py` finas → `services.py` (escritura)
  / `selectors.py` (lectura) → `models.py`. Nada de lógica de negocio en
  serializers, signals ni `save()`.
- **Límites entre apps** verificados con `import-linter`: cada app usa de otra
  solo su `services.py` y `selectors.py`, nunca `models`, `views` ni
  `serializers`. Las referencias entre apps se guardan como `UUIDField`; **no hay
  ForeignKey entre apps de dominio** (dentro de una misma app sí, ver
  `investments.Position.product`).
- **Dinero**: siempre `Decimal`, nunca `float`; los montos viajan como string
  decimal en la API; un único redondeo, en `core/money.py`; nunca se mezclan
  monedas ni se convertiría sin tipo de cambio explícito.
- **API** (AGENTS §8): prefijo `/api/v1/`, recursos en plural e inglés, importes
  como string, UUIDs públicos, paginación obligatoria, formato de error uniforme
  `{"error": {"code", "message", "details"}}`, `drf-spectacular` en todas las
  vistas.
- **Seguridad** (AGENTS §9): aislamiento por usuario con un test por endpoint,
  secretos solo por variables de entorno, throttling en login/registro, KYC
  obligatorio para operar con dinero, auditoría en operaciones financieras.
- **Testing** (AGENTS §10): `pytest` + `factory_boy` contra **PostgreSQL real**
  (nunca SQLite); cobertura mínima **90%** en `services.py` de `ledger` y de
  `budgets` (cuando exista) y **80%** general.
- **TDD** por comportamiento: test rojo → implementación mínima → verde, con la
  salida real de pytest registrada. No se tocan tests para que pasen.
- **Commits**: Conventional Commits en inglés, uno por funcionalidad, con
  `ruff`, `lint-imports` y `pytest` en verde antes de cada commit. Nunca se usa
  `--no-verify`.
- Ramas: `main` (siempre desplegable) y `feature/*` / `fix/*`.

## 6. Estado actual

### 6.1 Commits (log real y completo, `git log --oneline`)

Los 6 commits anteriores de este mismo `HANDOFF.md` están listados; este commit
no puede listarse a sí mismo (tras el push, `git log --oneline | wc -l` da
**82**).

| Commit | Asunto |
|---|---|---|
| `45eefa8` | chore(infra): add the production docker compose |
| `89d6f49` | feat(core): add the health check endpoint |
| `6efb50f` | feat(identity): require approved kyc on the views that move money |
| `92f2e1a` | chore(budgets): import-linter contracts, coverage gate and ADR |
| `9125429` | feat(budgets): budgets api |
| `9f1a546` | feat(budgets): monthly spending per category and currency |
| `91b3858` | feat(budgets): categorize ledger movements as personal expenses |
| `e18b0a7` | feat(budgets): budgets app with categories and monthly budgets |
| `82793c2` | feat(loans): link loan movements to the ledger and expose the breakdown |
| `29f9b96` | feat(ledger): movement detail selector with legs and reversal state |
| `b3cbf8b` | docs: register the celery infrastructure decision |
| `7fe012f` | test(loans,investments): cover the management commands and their celery tasks |
| `393b422` | chore(infra): run the celery worker and beat in docker compose |
| `c1bb3e7` | feat(investments): celery task to settle matured positions |
| `9f4edd0` | feat(loans): celery task to mark overdue loans |
| `2133337` | feat(core): celery configuration with redis broker and daily beat schedule |
| `a93c2d2` | fix(openapi): generate a clean OpenAPI schema with no warnings |
| `c4be917` | docs: refine handoff |
| `ed9e602` | docs: list the handoff commits in the section 6 log table |
| `57b1cf4` | docs: refine handoff sections per client review |
| `cffd42e` | docs: add handoff document with current repo state |
| `867d1fa` | chore: ignore generated openapi schema files |
| `0cfb2ea` | test(investments): concurrency and ledger invariant coverage |
| `39707da` | feat(investments): api endpoints, admin and import-linter contracts |
| `1b2199d` | feat(investments): open and settle fixed term positions |
| `7ebf030` | feat(ledger): transfers between a user wallet and a counterpart account |
| `1ba05b9` | feat(investments): investment product and position models |
| `f1d97fe` | feat(core,ledger): simple interest helper and configurable movement type |
| `098e745` | docs: register Block 5 investments decisions in AGENTS.md |
| `675ad76` | test(loans): concurrency, idempotency and isolation coverage |
| `b19b4be` | feat(loans): api endpoints, selectors and import-linter contracts |
| `7b9d0c5` | feat(loans): accept offer, pay installment and mark overdue services |
| `b9e0ded` | feat(ledger,offers): internal third-party transfer and offer acceptance |
| `a176f12` | feat(loans): loan, offer terms snapshot and installment models |
| `42569d3` | docs: register Block 4 loans decisions in AGENTS.md |
| `266cdbc` | test(offers): cover error branches of views and permission |
| `c5338dd` | feat(matching): search by amount range instead of exact amount |
| `40ca761` | feat(matching): marketplace search and comparison endpoints |
| `5c36dd8` | feat(matching): search and comparison selectors |
| `abb5336` | feat(offers): offer model, services, selectors and API |
| `5bd3bea` | feat(core): french amortization helpers in money.py |
| `d48fe62` | docs: register Block 3 decisions and new phase order in AGENTS.md |
| `b2d6dcb` | test(ledger): custody equals negative sum of user wallets |
| `16f5029` | test(ledger): api coverage for withdrawals and transfers |
| `4bb1263` | feat(ledger): transaction listing includes movements touching user accounts |
| `f0a73c6` | test(ledger): concurrency tests against real PostgreSQL |
| `3ec686b` | feat(ledger): api endpoints and admin reversal action |
| `1d7f387` | feat(ledger): services and selectors for deposits, withdrawals, transfers and reversals |
| `a876038` | feat(ledger): postgres triggers for double entry and immutability |
| `2bbacd9` | feat(ledger): account, transaction and entry models |
| `d07a4f2` | docs: register Phase 1B ledger decisions in AGENTS.md and add import-linter contracts |
| `127de6e` | chore: add .gitattributes with LF line endings |
| `5aa5004` | ci: add coverage gate and document project in README |
| `819cd15` | fix: flatten duplicated config package |
| `3de20bb` | chore: ignore coverage and import-linter cache artifacts |
| `d418176` | test(identity): cover openapi schema, kyc permission and model branches |
| `4eb59ef` | feat(identity): kyc resolution action in django admin |
| `6b61282` | feat(identity): auth, profile and kyc API endpoints |
| `ad00056` | feat(core): uniform api error handler |
| `2351bd7` | feat(identity): services and selectors for registration, profile and kyc |
| `efafa8d` | feat(identity): kyc verification model with pending uniqueness |
| `d48490b` | feat(identity): profile model |
| `7562c2a` | feat(identity): email-only user model with custom manager |
| `a66fd7b` | chore(deps): add pytest-cov for coverage reporting |
| `67b0ef2` | docs: register Phase 1A decisions and naming corrections in AGENTS.md |
| `6826e28` | fix: pre-commit import-linter hook rev and args |
| `ea1edb4` | fix: import-linter forbidden contract |
| `7d5cf6c` | test: remove obsolete test_simple |
| `3b3e401` | fix: tests use test settings |
| `7d571fc` | fix: import-linter contract |
| `def5baf` | fix: pytest and ruff config |
| `9442e63` | feat: import-linter config, pre-commit hooks, ruff updates |
| `39198aa` | feat: pre-commit, import-linter, Makefile, CI |
| `886cf55` | style: ruff format codebase |
| `654cc03` | fix: Django 5.x constraint, pytest test settings, web localhost port |
| `b0dbd58` | feat: Block C |
| `e27b2fc` | fix: docker-compose add source volume mount for live code reload |
| `ff28c71` | feat: add core money/tests, models/tests, identity user/tests |
| `f1f92ce` | fix: docker-compose ports localhost only, web serves runserver, test config updated |
| `3e701e5` | feat: Docker configuration, PostgreSQL settings and pytest integration |
| `9aa1eab` | feat: initial project skeleton with Docker-ready config, settings, pyproject and gitignore |
| `31098f8` | docs: add project rules |
| `8ec366e` | first commit |

### 6.2 Estado por fase / bloque

| Fase / Bloque | Estado | Resumen |
|---|---|---|
| **Fase 0 — Bloque A** Cimientos | ✅ completa | Estructura del repo, settings por entorno, `BaseModel` (UUID + timestamps), `core/money.py` con `Decimal` y `User` con login por email. |
| **Fase 0 — Bloque B** Docker/Postgres | ✅ completa | `Dockerfile`, `docker-compose.yml` con PostgreSQL 16, Redis, web, worker y beat; puertos publicados solo en localhost; los tests corren contra Postgres real. |
| **Fase 0 — Bloque C** TDD core+identity | ✅ completa | Primer ciclo rojo→verde: tests de `core.money`, `core.models` y del `User`; configuración de pytest para usar los settings de test. |
| **Fase 0 — Bloque D** Calidad | ✅ completa | `ruff` + `ruff-format`, `.importlinter` con contratos entre apps, hooks de `pre-commit`, `Makefile` y CI con `makemigrations --check`, `--cov-fail-under=80` y validación del OpenAPI. |
| **Fase 1A — identity** | ✅ completa | `User` sin `username`, `Profile`, `KYCVerification` con una sola pendiente por usuario, JWT con rotación y blacklist, throttles por scope, `exception_handler` con el formato de AGENTS §8 y resolución de KYC desde el admin. |
| **Fase 1B — ledger** | ✅ completa | `Account` / `LedgerTransaction` / `LedgerEntry`, saldo desnormalizado, triggers de doble entrada e inmutabilidad, idempotencia por `(usuario, clave)`, depósitos simulados, reversos solo staff, API y acción de reverso en el admin. |
| **Bloque 3 — offers + matching** | ✅ completa | `Offer` con TNA anual en `%`, amortización francesa en `core/money.py`, búsqueda por rango de montos, comparación de ofertas (cuota, interés, costo total) y API del marketplace. |
| **Bloque 4 — loans** | ✅ completa | `Loan` / `OfferTermsSnapshot` / `Installment`, aceptación atómica con snapshot inmutable, pago de cuotas en orden, marcado de vencidos, máquina de estados y API con aislamiento por partes. |
| **Bloque 5 — investments (plazo fijo)** | ✅ completa | `InvestmentProduct` (solo staff) y `Position` de plazo fijo, apertura atómica contra la cuenta `system`, liquidación idempotente con interés simple y API de productos y posiciones. |
| **Bloque 6a — infraestructura Celery** | ✅ completa | `config/celery.py` (broker Redis, sin result backend persistente, UTC), beat diario, servicios `worker` y `beat` en el compose, tasks `mark_overdue_loans` (00:05 UTC) y `settle_investments` (00:15 UTC). ADR 0001. |
| **Bloque 6b — `budgets`** | ✅ completa | `Category`, `Budget` y `Expense`; gastos categorizados sobre movimientos del ledger (el importe se deriva, no se guarda), presupuestos mensuales por categoría y moneda, API y contratos de import-linter. ADR 0002. |
| **Bloque 6c — `reports`** | ❌ no empezada | Solo lectura; sin modelos ni endpoints especificados (ver §11.4). |
| **Bloque 6d — `notifications`** | ❌ no empezada | Ya tiene la cola y el worker; falta el modelo, los disparadores, las tareas de email y la configuración de email. |
| **Bloque 7 — payments (proveedor real)** | ❌ no empezada | Hoy los depósitos y retiros son simulados y el system check `ledger.E001` los bloquea en producción. |

### 6.3 Funcionalidades implementadas (por app)

- **`core`**: `BaseModel` (UUID + timestamps), `money.py` (`round_two`, `money`,
  `monthly_rate_from_annual_tna`, `french_installment`, `simple_interest`,
  `french_total_interest`, `french_total_cost`), `exceptions.py` (`DomainError`,
  `InsufficientFunds`, `InvalidAmount`, `KYCNotCompleted`), `pagination.py`
  (`StandardPagination`), `exception_handler.py` (formato de error de AGENTS §8).
- **`identity`**: `User` (email como login, sin `username`), `Profile`,
  `KYCVerification` (una sola `pending` por usuario), JWT con rotación y
  blacklist, throttles `login` 5/min y `register` 5/hora, resolución de KYC desde
  el admin.
- **`ledger`**: `Account` (saldo desnormalizado), `LedgerTransaction`,
  `LedgerEntry`; services `deposit`, `withdraw`, `transfer`,
  `transfer_between_users` (interno), `transfer_to_counterpart` /
  `transfer_from_counterpart` (internos) y `reverse_transaction` (solo staff);
  triggers de PostgreSQL para doble entrada e inmutabilidad; API de cuentas,
  saldos y movimientos (paginación por cursor).
- **`offers` / `matching`**: publicación de ofertas (KYC requerido), búsqueda por
  rango de montos (`amount_min` / `amount_max`), comparación de 2+ ofertas.
- **`loans`**: aceptación atómica de oferta con snapshot inmutable, cronograma
  francés persistido, pago de cuotas en orden y por importe completo, marcado de
  vencidos, máquina de estados `active|paid|defaulted`, API con aislamiento por
  partes (un tercero recibe `404`).
- **`investments`**: productos de plazo fijo (solo staff vía admin), apertura
  atómica contra la cuenta `system`, liquidación idempotente con interés simple,
  API de productos y posiciones.
- **`budgets`**: `Category` (etiqueta de gasto del usuario), `Budget` (límite
  mensual de una categoría en una moneda, con umbral de alerta en porcentaje) y
  `Expense` (movimiento del ledger atribuido a una categoría). El **importe no se
  guarda**: se deriva del ledger al leer. API de categorías, presupuestos, estado
  y gastos.
- **Celery**: app, worker, beat, dos tasks periódicas y su cobertura de tests.
- **Chequeo de salud**: `GET /health/` (fuera de `/api/v1/`, sin autenticación y
  sin throttle) devuelve 200 con `{"status": "ok"}` si la base responde un
  `SELECT 1` y 503 con `{"status": "unavailable"}` si no responde. No expone
  detalles internos ni secretos.

### 6.4 Estado verificado (2026-10-21, comandos del §10)

| Chequeo | Comando | Resultado |
|---|---|---|
| Tests | `docker compose run --rm web pytest -q` | **504 passed** |
| Cobertura total | `... pytest --cov=apps --cov-report=term` | **98,81%** (81 statements sin cubrir de 6814) |
| Cobertura de budgets | `... pytest apps/budgets --cov=apps.budgets.services --cov-fail-under=90` | **100%** en `budgets/services.py` (umbral de la CI: 90%) |
| Cobertura por módulo | idem | `identity/*` 100% · `ledger/services.py` 93% · `ledger/views.py` 100% · `ledger/selectors.py` 100% · `offers/views.py` 100% · `offers/permissions.py` 100% · `loans/services.py` 99% · `loans/tasks.py` 100% · `investments/services.py` 99% · `investments/tasks.py` 100% · `matching/views.py` 97% |
| Lint | `ruff check .` | All checks passed |
| Formato | `ruff format --check .` | 151 files already formatted |
| Límites entre apps | `lint-imports` | **16 kept, 0 broken** |
| Migraciones | `makemigrations --check --dry-run` | No changes detected |
| System checks | `manage.py check` | System check identified no issues |
| OpenAPI | `spectacular --validate --fail-on-warn --file schema.yml` | **PASA: 0 errores, 0 warnings** (lo mismo que corre la CI) |
| Docker | `docker compose ps` | **5 servicios Up**: `db`, `redis`, `web`, `worker`, `beat` |
| Worker | `docker compose logs worker` | `transport: redis://redis:6379/0`, `results: disabled://`, 2 tasks registradas, `ready.` |
| Beat | `celery -A config inspect conf` | `mark_overdue_loans_diario` → crontab `5 0 * * *`; `settle_investments_diario` → `15 0 * * *` |
| End-to-end | `celery -A config call apps.loans.tasks.mark_overdue_loans` | task `received` y `succeeded` en el worker |
| Migraciones de budgets | `manage.py migrate` | `budgets.0001_initial`, `budgets.0002_expense` y `loans.0002_...` aplicadas |
| Endpoints de budgets (runtime) | `curl` contra el `web` local | crear categoría 201, listar 200 paginado, crear presupuesto 201, duplicado 409, sin token 401 |
| Compose de producción | `docker compose -f docker-compose.prod.yml config` | válido (5 servicios) |
| Compose de producción (arranque real) | `docker compose -f docker-compose.prod.yml -p presto-prod up -d --build` | `db`, `redis` y `web` **healthy**, `worker` y `beat` Up, `/health/` → 200 `{"status": "ok"}` |
| Estado del repo | `git status` | limpio; `main` al día con `origin/main` |

**Logs de evidencia** (fuera del repo, en `A:\Samuel\`): `tdd_6.log` (ciclos
RED/GREEN del bloque Celery), `verif_6.txt` (verificación completa de ese
cambio), `schema_check.txt` + `schema.yml` (OpenAPI), `estado_bloque_6.txt`
(informe de estado previo), `tdd_1a.log` … `tdd_5.log` y `verif_1a.txt` …
`verif_5.txt` (bloques anteriores).

## 7. Decisiones técnicas

Solo las decisiones **nuevas** de los bloques 1A → 6a. Las de AGENTS.md §17 (sin
cambio de rationale) ya están registradas allí y no se repiten.

| # | Decisión | Motivo |
|---|---|---|
| D1 | `User` sin `username`, con `UserManager` propio por email | El login es por email; mantener `username` obligaba a duplicar el dato y a romper `create_user` |
| D2 | `Account.balance` **desnormalizado** con `CheckConstraint(balance >= 0)` **solo** para `user_wallet` | El saldo se deriva de sus asientos, pero materializarlo permite un `SELECT` barato y una restricción de no-negatividad en la base; `custody` y `system` reflejan el mundo exterior y pueden quedar negativas |
| D3 | Doble entrada garantizada con un **constraint trigger diferido** de PostgreSQL + triggers que bloquean `UPDATE`/`DELETE` | La regla de §6 debe vivir en la base, no solo en Python; diferido porque los asientos se insertan en varias sentencias |
| D4 | `idempotency_key` única por `(created_by_user_id, idempotency_key)` con `request_hash` | La clave es única **por usuario**, no global: dos usuarios distintos pueden usar la misma clave. El hash distingue "reintento" de "payload distinto" (409) |
| D5 | Bloqueo de cuentas con `select_for_update` **en orden ascendente por `id`** | Evita deadlocks entre transferencias cruzadas; el orden determinista es la única forma de garantizarlo |
| D6 | `ledger.transfer_between_users` (interno) + `transfer_to_counterpart` / `transfer_from_counterpart` | Los flujos de préstamos e inversiones mueven saldo entre usuarios o contra cuentas sin usuario (`user_id = NULL`), que no se pueden resolver con `transfer_between_users` |
| D7 | `Loan` con estados `active` \| `paid` \| `defaulted` (el `pending` no se usa) | El préstamo nace `active` al aceptar la oferta; `pending` era un estado muerto |
| D8 | La última cuota ajusta su **parte de capital** (el interés absorbe el redondeo acumulado) | El importe de la cuota es constante y la suma de capitales es exactamente el principal |
| D9 | Reversos **solo staff** y **sin endpoint** (acción del admin) | Un reverso corrige un movimiento ya registrado, no es una operación del usuario; el admin es la única vía y por eso el rol staff es la barrera |
| D10 | `Offer.interest_rate` es **TNA anual en `%`**; la cuota mensual se calcula una sola vez en `core/money.py` | Una sola fuente de verdad para el cronograma; sin redondeos intermedios |
| D11 | La búsqueda de ofertas filtra por **rango** (`amount_min` / `amount_max`) | El préstamo toma el **monto completo** de la oferta, así que el filtro es un rango |
| D12 | `matching` es solo lectura y se apoya únicamente en `offers.selectors` | La app no escribe estado y no debe conocer el modelo de `offers` (verificado por `import-linter`) |
| D13 | `InvestmentProduct` se da de alta **solo por staff en el admin**; la API solo lista | Los productos son la oferta comercial de la plataforma; se gobiernan por staff, no por API pública |
| D14 | Sin cancelación anticipada de inversiones | No hay un camino de negocio definido; agregarlo después, no ahora |
| D15 | `simple_interest` con base **365 días** | Convención simple y auditable para un plazo fijo |
| D16 | `EXCEPTION_HANDLER` propio en `core` con el formato de §8 | Uniformidad de errores; el código propio de la excepción se usa salvo en los status genéricos (400/401/403/404/405/429) |
| D17 | `pytest.ini` con `addopts = --ds=config.settings.test` | El `DJANGO_SETTINGS_MODULE` del entorno tiene prioridad sobre el ini; el flag `--ds` lo pisa y garantiza settings de test |
| D18 | `config/settings/test.py` **no** sobrescribe `DATABASES['default']['NAME']` | pytest-django crea `test_<NAME>` solo; tocar el `NAME` rompía la creación de la base de test |
| D19 | Celery con **Redis como broker** y **sin result backend persistente** (`CELERY_TASK_IGNORE_RESULT`, `CELERY_RESULT_BACKEND = None`) | Las tareas del proyecto producen efectos, no resultados; no se agrega `django-celery-results` ni ninguna dependencia nueva (AGENTS §3) |
| D20 | Las tasks viven en la app dueña (`apps/loans/tasks.py`, `apps/investments/tasks.py`), no en `core` | AGENTS §4 prescribe `tasks.py` por app; además `core` no puede importar `loans`/`investments` (contrato `core-isolation`) |
| D21 | Task y management command **comparten el `service`**: la task es un adaptador delgado | Una sola implementación de la regla de negocio; el command queda como vía manual y de recuperación sin duplicar lógica |
| D22 | Beat diario en **UTC** (`00:05` y `00:15`), con `crontab` en `config/celery.py` | `TIME_ZONE` del proyecto es UTC; el schedule se referencia por **nombre de task**, así que `config/celery.py` no importa apps de dominio |
| D23 | Estado del scheduler en un **volumen Docker** (`celerybeat:/var/celerybeat`) | Evita el archivo dentro del working tree (ensuciaría `git status`) sin agregar `django-celery-beat` |
| D24 | `CELERY_TASK_ALWAYS_EAGER = True` en `config/settings/test.py` | La suite no debe depender de Redis: los tests siguen corriendo contra PostgreSQL real |
| D25 | El gasto **no guarda importe**: `Expense` guarda usuario, categoría y `ledger_transaction_id`, y el monto se **deriva del ledger al leer** | El ledger es la fuente de verdad (decisión O4): la app no puede guardar una copia que contradiga al ledger. ADR 0002 |
| D26 | `Budget.category` es una **ForeignKey dentro de la misma app** (columna `category_id`) | AGENTS §5.2 solo prohíbe las FK *entre apps*; el "(UUID, sin FK)" de AGENTS §7 respondía a que el modelo de categorías no existía. ADR 0002 |
| D27 | `Installment.ledger_transaction_id` y `Loan.ledger_transaction_id` guardan el movimiento del pago y del desembolso, y `loans.selectors` expone el desglose en primitivos | Es la única forma limpia de aplicar el tratamiento interés/capital sin parsear claves de idempotencia ni compartir modelos entre apps |
| D28 | Las reglas de gasto están en una **función pura** (`_classify_movement`) y se derivan en **lote** | Permite probar las reglas defensivas (transferencia entre cuentas propias) sin construir movimientos imposibles, y evita el N+1 al calcular un presupuesto |
| D29 | Los conflictos (categoría o presupuesto duplicado, movimiento ya categorizado) usan `APIException` con `status_code = 409` | Sigue el patrón del ledger (`IdempotencyKeyConflict`) y el `exception_handler` devuelve el código propio en los status no genéricos |
| D30 | `identity.permissions.KycApprovedForUnsafeMethods` agrega `IsKycApproved` solo a los métodos que no son de lectura | Da el `403` temprano y explícito de AGENTS §9.9 sin cambiar los `GET`. Los services siguen validando KYC (defense in depth) |
| D31 | `/health/` es una vista de Django (no DRF) fuera de `/api/v1/` | Es un endpoint operativo: sin autenticación, sin throttle y fuera del esquema OpenAPI |
| D32 | `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` en los settings de producción | El proxy inverso termina TLS delante: sin esto, `SECURE_SSL_REDIRECT` respondía 301 y el chequeo de salud fallaba |
| D33 | `docker-compose.prod.yml` no monta el código fuente: la imagen lo lleva | En producción el código va en la imagen (el `Dockerfile` hace `COPY . .`); el montaje del compose de desarrollo es solo para recargar |

## 8. Problemas y resoluciones

| # | Problema | Resolución |
|---|---|---|
| P1 | `relation "auth_group" does not exist` en cada test: pytest-django creaba `test_presto` **sin** las tablas de `django.contrib.auth` | Causa raíz: `apps/identity` **no tenía carpeta `migrations/`**. Se generó `apps/identity/migrations/0001_initial.py` |
| P2 | `apps/ledger/tests/test_concurrency.py` fallaba con `MultipleObjectsReturned` al hacer `get(user_id=..., kind=USER_WALLET)` | Un usuario tiene una billetera **por moneda**: faltaba el filtro `currency`. Se corrigió el test (no el código) |
| P3 | Los tests de `loans`/`investments` fallaban con `Account matching query does not exist` | La billetera se crea dentro de la transacción atómica que se revierte. Se ajustaron las aserciones a `wallet is None or wallet.balance == 0` |
| P4 | Los tests de préstamos a 3 meses fallaban con `InsufficientFunds` al pagar la última cuota | El costo total (capital + interés) de un préstamo de 3 meses al 24% TNA **supera** el capital desembolsado: el prestatario necesita saldo extra. Se financió explícitamente en el test y se documentó |
| P5 | `pytest` usaba `config.settings.local` en vez de los settings de test | El `DJANGO_SETTINGS_MODULE` del entorno tiene prioridad sobre `pytest.ini`; se resolvió con `addopts = --ds=config.settings.test` (ver D17) |
| P6 | `import-linter` reportaba "0 kept, 0 broken" sin ejecutar ningún contrato | La sección debe ser `[importlinter:contract:<nombre>]`, no `[importlinter.contracts.<nombre>]`. Verificado mostrando "1 broken" con un import prohibido de prueba y revirtiendo |
| P7 | `import-linter` marcaba la cadena **indirecta** `ledger → identity.selectors → identity.models` | Las tablas de `identity` son internas de esa app; se activó `allow_indirect_imports = True` (la importación directa sigue prohibida) |
| P8 | El hook de `import-linter` en pre-commit fallaba (`pathspec 'v2.15.0'`, `No such option '--config-file'`) | El tag real es `v2.15` y la opción es `--config`. Corregidos en `.pre-commit-config.yaml` |
| P9 | El servicio web estaba caído (`WSGI application 'config.wsgi.application' could not be loaded`) | Sobraba el paquete `config/config/` y faltaban `config/__init__.py`, `config/settings/__init__.py`, `config/wsgi.py`, `config/asgi.py`. Se aplanó la estructura (commit `819cd15`) |
| P10 | La migración que cambia `id` de `BigAutoField` a `UUIDField` fallaba con `cannot cast type bigint to uuid` | Base de desarrollo con datos: se recreó la base y se regeneró la migración inicial con el modelo ya corregido |
| P11 | `makemigrations` generaba una migración `0002_alter_user_id` que no se podía aplicar | Se aplicó el modelo definitivo antes de generar la migración |
| P12 | Los tests de `loans` e `investments` violaban el contrato de `import-linter` importando `ledger.models` / `offers.models` | Se reemplazaron por los selectores y servicios públicos y por literales de estado |
| P13 | `spectacular` genera el esquema con 1 error y 7 warnings | **Resuelto**: `serializer_class` en `InstallmentPayView` (+ `request=None`), `ENUM_NAME_OVERRIDES` y `operation_id` explícito en los 5 pares lista/detalle. La CI valida el esquema con `--validate --fail-on-warn` |
| P14 | `pytest.raises(Exception)` disparaba el linter `B017` | Se reemplazó por la excepción concreta (`InsufficientFunds`) |
| P15 | El test de equivalencia command↔task de `settle_investments` falló con `assert 0 == 1` | El command liquida **todas** las posiciones vencidas, no solo una: el test estaba mal, no el código. Se corrigió el test para aislar cada camino (crear el dato del command, correrlo, recién entonces crear el dato de la task) |
| P16 | El hook de `import-linter` de `pre-commit` falla en el host con `Executable 'lint-imports' not found` | El hook usa `language: system` y en este host `lint-imports.exe` vive en `C:\Users\samue\AppData\Roaming\Python\Python315\Scripts`, que **no está en el PATH**. Antes de commitear: `export PATH="/c/Users/samue/AppData/Roaming/Python/Python315/Scripts:$PATH"`. No es un problema del repo |
| P22 | Con `SECURE_SSL_REDIRECT=True` y `SECURE_PROXY_SSL_HEADER=None` (el valor real del proyecto), `/health/` respondía **301** y el healthcheck del contenedor expiraba | Se agregó `SECURE_PROXY_SSL_HEADER` a los settings de producción (el proxy termina TLS) y el healthcheck envía `X-Forwarded-Proto: https`. Verificado con el stack real: `web` queda **healthy** |
| P23 | El `docker-compose.prod.yml` no parseaba: el valor del healthcheck tenía `:` sin comillas | Se entrecomilló el valor YAML del bloque `test` |
| P18 | El test del filtro de período falló con `IntegrityError: ledger_ledgertransaction rows are immutable: UPDATE is not allowed` | El ledger es inmutable (trigger de PostgreSQL): **no se puede mover la fecha de un movimiento**. El test se reformuló para comparar el mismo movimiento en su mes y en otro período, sin tocar el ledger |
| P19 | `pytest.raises(Exception)` en un test de budgets disparaba el linter `B017` | Se reemplazó por la excepción concreta (`NotAnExpense`) |
| P20 | El primer test de `test_spending.py` usaba un usuario ficticio (UUID sin `User`) y fallaba con `KYCNotCompleted` | El ledger exige KYC para mover saldo: la app budgets tiene su propio `create_approved_user()` en `apps/budgets/tests/factories.py`, como las otras apps |
| P21 | Al escribir este documento, una palabra quedó corrupta (caracteres CJK en §11.2) | Se detectó escaneando los caracteres fuera del alfabeto esperado y se corrigió |
| P17 | En el entorno local los depósitos y retiros simulados están **deshabilitados** | `docker-compose.yml` **no** define `LEDGER_SIMULATED_DEPOSITS_ENABLED` y `base.py` la default a `False` → el endpoint de movimientos devuelve 400 en local (salvo que el `.env` la encienda). En `config/settings/test.py` sí está en `True`. **Desalineación preexistente, no resuelta** |

## 9. Notas y glosario

- **TNA**: tasa nominal anual, en porcentaje (`24.00` = 24% TNA). La tasa mensual
  equivalente es `TNA / 100 / 12`; la efectiva, `(1 + TNA/100)^(1/12) - 1`. En el
  repo se usa la nominal.
- **`custody` / `system`**: cuentas de contrapartida sin `user_id`. `custody`
  representa los fondos custodiados (y el exterior: depósitos y retiros);
  `system`, la contraparte de las inversiones. Con `balance = créditos - débitos`,
  la suma de **todos** los saldos de una moneda es **cero**.
- **`Idempotency-Key`**: header HTTP obligatorio en los POST que crean o mueven
  dinero (`/api/v1/loans/`, `/api/v1/investments/positions/`,
  `/api/v1/ledger/transactions/`). La unicidad es **por `(usuario, clave)`**.
- **`request_hash`**: SHA-256 canónico del payload, guardado junto a la clave.
- **KYC**: `identity.selectors.is_kyc_approved(user_id)` es el único punto de
  entrada para exigir verificación. `apps/identity/permissions.py::IsKycApproved`
  replica la regla a nivel HTTP (hoy **ninguna vista la usa**; los services ya
  exigen KYC, así que la capa HTTP es defense in depth).
- **Una billetera por usuario y moneda**: `UniqueConstraint(user_id, currency)`
  para `kind = user_wallet`. Por eso **hoy es imposible** una transferencia entre
  cuentas propias del mismo usuario (sería la misma cuenta, o currencies
  distintas → `CurrencyMismatch`).
- **Gasto categorizado**: un movimiento del ledger atribuido a una categoría
  del usuario. Lo que se guarda es la clasificación, **no el importe**: el
  monto se deriva del ledger al leer (`budgets.selectors`).
- **Presupuesto mensual**: límite de gasto de una categoría en una moneda. El
  mes es el calendario en UTC y nunca se suman ARS y USD.
- **Sin implementar todavía**: `reports`, `notifications`, `payments`
  (proveedor real), `docker-compose.prod.yml` (exigido por AGENTS §4),
  `docs/architecture.md` y el envío del esquema OpenAPI al frontend.
- **Sin verificar**: no se ejecutó nunca un despliegue real, ni
  `docker-compose.prod.yml` (no existe), ni el flujo contra un proveedor de pagos
  real, ni producción con HTTPS/Sentry/backups.

## 10. Cómo ejecutar y validar

Todos los comandos se ejecutan **desde la raíz del repo**. Los que necesitan el
contenedor se ejecutan con `docker compose run --rm web ...`.

### Levantar / bajar el entorno

```sh
make up        # docker compose up --build -d
make down      # docker compose down
docker compose ps
```

`docker compose ps` debe mostrar **5 servicios Up**: `db`, `redis`, `web`,
`worker`, `beat`.

### Tests

```sh
make test      # docker compose run --rm web python -m pytest -v
```

Resultado esperado: **504 passed**. Con cobertura:

```sh
docker compose run --rm web pytest -v --cov=apps --cov-report=term-missing
```

### Lint, formato y límites entre apps

```sh
make lint      # ruff check . + ruff format --check . + import-linter
```

Equivalentes sueltos:

```sh
docker compose run --rm web ruff check .
docker compose run --rm web ruff format --check .
docker compose run --rm web lint-imports      # alias de import-linter
docker compose run --rm web import-linter
```

Los hooks de git se validan en el **host** (pre-commit corre hooks, no pytest):

```sh
export PATH="/c/Users/samue/AppData/Roaming/Python/Python315/Scripts:$PATH"   # ver P16
python -m pre_commit run --all-files
```

### Migraciones y schema

```sh
make makemigrations   # docker compose run --rm web python manage.py makemigrations
make migrate          # docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py makemigrations --check --dry-run
docker compose run --rm web python manage.py check
```

### OpenAPI (esquema)

```sh
docker compose run --rm web python manage.py spectacular --validate --fail-on-warn --file schema.yml
```

> Este comando **PASA**: 0 errores y 0 warnings. Es el mismo que corre la CI
> (job *quality*); la CI falla si aparece cualquier warning.

### Management commands

```sh
docker compose run --rm web python manage.py mark_overdue_loans   # cuotas vencidas -> overdue
docker compose run --rm web python manage.py settle_investments    # posiciones vencidas -> matured
```

### Celery (worker, beat y tasks)

```sh
make worker        # celery -A config worker -l info (en primer plano)
make beat          # celery -A config beat -l info
make celery-tasks  # lista las tasks registradas
docker compose up -d && docker compose ps    # db, redis, web, worker, beat
docker compose logs -f worker
docker compose logs -f beat
docker compose exec -T worker celery -A config inspect conf    # muestra el beat_schedule
```

Tareas registradas y horario (beat, UTC):

| Task | Cuándo | Qué hace |
|---|---|---|
| `apps.loans.tasks.mark_overdue_loans` | todos los días a las 00:05 | marca las cuotas vencidas (`overdue`) y los préstamos (`defaulted`) |
| `apps.investments.tasks.settle_investments` | todos los días a las 00:15 | liquida las posiciones vencidas (capital + interés) |

En los tests las tasks corren en el proceso (`CELERY_TASK_ALWAYS_EAGER`), así que
la suite no necesita Redis.

### Chequeo de salud

```sh
curl -s http://127.0.0.1:8000/health/
# {"status": "ok"}         -> 200 si la base responde
# {"status": "unavailable"} -> 503 si la base no responde
```

Es público (sin autenticación), sin throttle, y **no** está en el esquema
OpenAPI: es un endpoint operativo, no de la API de negocio.

### Producción (docker-compose.prod.yml)

El archivo exige un `.env.prod` (o variables de entorno) con, al menos,
`POSTGRES_PASSWORD`, `DJANGO_SECRET_KEY` y `DJANGO_ALLOWED_HOSTS`. No tiene
ningún secreto escrito dentro.

```sh
docker compose -f docker-compose.prod.yml config                    # valida el archivo
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f web
```

- Servicios: `db`, `redis`, `web` (gunicorn), `worker` y `beat`.
- `db` y `redis` **no** publican puertos; `web` escucha en `127.0.0.1:8000`
  para el proxy inverso (Nginx o Caddy) que termina TLS.
- `restart: unless-stopped` en los cinco servicios.
- Healthchecks: `pg_isready` en `db`, `redis-cli ping` en `redis` y `/health/`
  en `web`.
- Volúmenes persistentes: `pg_data` (base) y `celerybeat` (estado del
  scheduler).
- **`beat` corre una sola instancia**: el worker se puede escalar, el
  scheduler no.

### Otros

```sh
docker compose run --rm web python manage.py shell     # shell de Django (necesita TTY)
docker compose logs -f
docker compose exec db psql -U presto -d presto
```

### Verificación completa (lo que corre la CI)

```sh
docker compose run --rm web ruff check .
docker compose run --rm web ruff format --check .
docker compose run --rm web lint-imports
docker compose run --rm web python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yml
docker compose run --rm web python manage.py makemigrations --check --dry-run
docker compose run --rm web pytest -v --cov=apps --cov-report=term-missing --cov-fail-under=80
docker compose run --rm web pytest apps/budgets --cov=apps.budgets.services --cov-fail-under=90
```

## Endpoints disponibles

Extraídos del `URLConf` del proyecto (`get_resolver()`), no de memoria. Todas
requieren autenticación JWT salvo `auth/register`, `auth/login` y
`auth/token/refresh`.

### `identity`

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/auth/register/` | Registra un usuario (throttle 5/hora) |
| POST | `/api/v1/auth/login/` | Devuelve `access` + `refresh` (throttle 5/min) |
| POST | `/api/v1/auth/token/refresh/` | Rota el refresh y blacklista el anterior |
| GET, PATCH | `/api/v1/auth/me/` | Perfil propio (`PATCH` actualiza el `Profile`) |
| GET, POST | `/api/v1/kyc/` | Estado KYC propio / solicitar verificación |
| GET | `/api/v1/kyc/{verification_id}/` | Detalle de una verificación propia (404 si es de otro) |

### `ledger`

| Método | Ruta | Descripción |
|---|---|---|
| GET, POST | `/api/v1/ledger/accounts/` | Lista las cuentas propias / crea la `user_wallet` |
| GET | `/api/v1/ledger/accounts/{account_id}/balance/` | Saldo de una cuenta propia |
| GET, POST | `/api/v1/ledger/transactions/` | Lista movimientos (cursor) / crea `deposit`, `withdrawal` o `transfer` |
| GET | `/api/v1/ledger/transactions/{transaction_id}/` | Detalle de un movimiento propio |

### `offers` y `matching`

| Método | Ruta | Descripción |
|---|---|---|
| GET, POST | `/api/v1/offers/` | Lista las ofertas propias / publica una oferta |
| GET, PATCH | `/api/v1/offers/{offer_id}/` | Detalle / actualiza o expira la oferta propia |
| GET | `/api/v1/matching/offers/` | Busca ofertas activas (filtros `currency`, `amount_min`, `amount_max`, `max_rate`, `term_months`, `ordering`) |
| POST | `/api/v1/matching/comparisons/` | Compara 2+ ofertas (body: `offer_ids`) |

### `loans`

| Método | Ruta | Descripción |
|---|---|---|
| GET, POST | `/api/v1/loans/` | Lista los préstamos propios / acepta una oferta |
| GET | `/api/v1/loans/{loan_id}/` | Detalle con snapshot y cuotas (404 si es de otro) |
| POST | `/api/v1/loans/{loan_id}/installments/{number}/pay/` | Paga una cuota (solo el prestatario, en orden) |

### `investments`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/investments/products/` | Lista los productos de plazo fijo activos |
| GET, POST | `/api/v1/investments/positions/` | Lista las posiciones propias / abre una inversión |
| GET | `/api/v1/investments/positions/{position_id}/` | Detalle de una posición propia (404 si es de otro) |

### Fuera de `/api/v1/`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/schema/` | Esquema OpenAPI (JSON) |
| GET | `/api/docs/` | Swagger UI |
| — | `/admin/` | Django admin (solo staff): usuarios, perfiles, KYC, cuentas, transacciones, asientos, productos y posiciones de inversión |

---

## 11. Próximos pasos

Orden real de lo que falta, de mayor a menor prioridad.

1. **Bloque 6c — app `reports`** (solo lectura) y **6d — `notifications`** (emails
   vía Celery). Es la tarea recomendada: el andamiaje (Celery, ledger, usuarios y
   `budgets`) está listo. Para `reports` y `notifications` **faltan
   especificaciones** (modelos, endpoints, disparadores): hay que cerrarlas con
   el cliente antes de codear (§11.4).
2. **`Goal`** (AGENTS §7): no se implementó porque no estaba en el alcance de
   `budgets`; queda pendiente de pedido explícito.
3. **Bloque 7 — `payments` con proveedor real** (al final, a propósito). Hoy los
   depósitos y retiros son **simulados** y están apagados en producción por el
   system check `ledger.E001`: `ledger.withdraw` es alcanzable por HTTP pero
   **siempre devuelve 400** en producción.
4. ✅ **`docker-compose.prod.yml`**: creado y verificado (config válido y stack
   levantado de verdad). Pendiente de producción: el proxy inverso con TLS, los
   backups automáticos y el despliegue real en el VPS.
5. **Producción**: el endpoint **`/health/`** y el `docker-compose.prod.yml` ya
   están. Falta la integración con **Sentry**, los **backups automáticos
   diarios** de PostgreSQL con prueba periódica de restauración, el **proxy
   inverso con HTTPS** y el **CORS** explícito para el front
   (`CORS_ALLOWED_ORIGINS`, sin `*`).
6. **Documentación**: falta `docs/architecture.md`. Los ADRs de las decisiones
   grandes siguen sin escribirse (saldo desnormalizado, contrato diferido de doble
   entrada, orden `offers+matching → loans → investments → payments`).
7. ✅ **`IsKycApproved` en las vistas que mueven dinero**: aplicado a los
   movimientos del ledger, la publicación de ofertas, la aceptación de préstamos,
   el pago de cuotas y la apertura de posiciones de inversión. Los `GET` no cambian
   y los services siguen validando KYC.
8. **Cobertura de vistas por debajo de 100%**: `loans/views.py` 94%,
   `matching/views.py` 97%, `investments/views.py` 95%. No es un bloqueo (los
   umbrales de AGENTS §10 son 90% en `ledger`/`budgets` y 80% general).
9. **Agregar `budgets` al umbral de cobertura del 90%** en la CI cuando exista la
   app.
10. **Envío del esquema OpenAPI al frontend**: queda pendiente, así como la
    configuración de CORS real para el front.

### 11.1 Decisiones abiertas con el cliente

Estas decisiones **no son técnicas**: cambian el producto, el modelo de negocio o
el marco legal. No hay una respuesta "correcta" en el código, así que **no se
implementan hasta que el cliente defina el criterio**.

| # | Decisión abierta | Qué hay que definir | Qué bloquea |
|---|---|---|---|
| O1 | **Proveedor de pagos** | Cuál es el proveedor (PSP, banco, pasarela), qué operaciones soporta (depósito, retiro, transferencia), si hay API de webhooks firmados, comisiones, tiempos de liquidación y si el saldo del ledger se replica contra la cuenta del proveedor | Toda la app `payments` (Bloque 7) y el camino de depósitos/retiros, hoy simulados |
| O2 | **Marco regulatorio de la custodia** | Si Presto es una **plataforma de inversión** o un **agente de custodia**; qué entidad regulada respalda los saldos; si los fondos van a una cuenta segregada en un banco o a una cuenta del proveedor; requisitos de capital mínimo, seguro de depósitos y reporte de saldos | El modelo de cuentas `custody` / `system` y si Presto puede llamar "custodia" a lo que hace hoy |
| O3 | **Presto asume el rendimiento de los plazos fijos** | Si la tasa que se muestra está garantizada por Presto o si el rendimiento depende del instrumento que respalda la posición; qué pasa si el rendimiento real es menor que el prometido; si hay un fondo de garantía o un spread de riesgo; quién asume la diferencia | El modelo de `Position` e `InvestmentProduct` (hoy el interés es un `Decimal` fijo calculado al abrir) y el marketing del producto |
| O5 | **PLA/FT (prevención de lavado)** | Umbrales de Reporte de Operaciones Sospechosas (ROS), identificación del beneficiario final, screening contra listas de sanciones, reglas de monitoreo de patrones (velocidad, montos, estructuración), documentación de la operatoria, plazos de conservación y responsable asignado | El alcance de `identity` (más allá del KYC actual) y de `payments`; también define auditoría y retención de datos |
| O6 | **CFT (costo financiero total)** | Si el cliente quiere el costo financiero total —capital + interés— **en la comparación de ofertas** (hoy `matching.compare_offers` ya devuelve cuota, interés total y costo total: la pregunta es de exposición y de etiquetado, no de cálculo), y si ese CFT debe compararse contra el costo de otras alternativas del usuario (crédito, plazo fijo, efectivo) | La presentación de `POST /api/v1/matching/comparisons/` y los reportes; el cálculo ya existe en `core/money.py` (`french_total_cost`) |

### 11.2 Decisiones de negocio CONFIRMADAS (ya no se consultan)

**O4 — Regla de "gastado" en presupuestos: RESUELTA por el cliente** (2026-10-21).
Criterio firmado:

1. El **ledger es la fuente de verdad** del dinero y de los saldos.
2. Se implementa un **registro de gastos personales con categorías**, vinculado a
   los movimientos del ledger cuando corresponda. **No duplicar movimientos ni
   mantener registros financieros contradictorios.**
3. Los **presupuestos mensuales** calculan el gasto acumulado **por categoría y
   moneda**.
4. Las **transferencias entre cuentas propias** y los **movimientos de
   inversión** **no cuentan como gastos**.
5. Los **pagos de préstamos** no se contabilizan automáticamente como gasto
   total: el tratamiento de **intereses y capital** hay que definirlo y probarlo
   según los modelos existentes.
6. Los **movimientos sin categoría no se asignan automáticamente** a presupuestos.
7. **No mezclar ARS con USD** ni convertir monedas.
8. Se respeta el acceso entre apps **solo por `services.py` y `selectors.py`**, sin
   FK entre apps de dominio.
9. **No alterar** la integridad, inmutabilidad ni idempotencia del ledger.
10. `AGENTS.md` **no se modifica** sin autorización explícita.
11. `reports` y `notifications` **no** se implementan en esa tarea.

Estas decisiones **están escritas, implementadas y probadas**: la app `budgets` existe
(modelos, servicios, selectores, API y tests). La implementación se detalla en §11.3
y en el ADR 0002.

### 11.3 Cómo quedó implementada la app `budgets` (referencia para mantenerla)

La decisión O4 (§11.2) ya está implementada. Esto es lo que quedó, para que
cualquiera que retome el bloque sepa qué hay y por qué:

**Lo que existe y hay que usar**

- `apps/ledger/models.py`: `Account` (`user_id`, `currency`, `kind` ∈
  `user_wallet|custody|system`, `balance`), `LedgerTransaction` (`type` ∈
  `deposit|withdrawal|transfer|interest|fee|reversal`, `created_by_user_id`,
  `destination_account_id`, `occurred_at`, `reverses`), `LedgerEntry`
  (`ledger_transaction`, `account`, `direction` ∈ `debit|credit`, `amount`,
  `currency`).
- `apps/ledger/services.py`: `deposit` (custody → wallet), `withdraw`
  (wallet → custody), `transfer` (wallet → wallet), `transfer_between_users`
  (interno), `transfer_to_counterpart` / `transfer_from_counterpart` (internos,
  contra `custody`/`system`), `reverse_transaction` (solo staff).
- `apps/ledger/selectors.py`: `get_account_for_user`, `list_accounts_for_user`,
  `get_user_wallet`, `get_balance`, `list_transactions_for_user`,
  `get_balance_breakdown`, `get_transaction`. **No hay** ningún selector que
  exponga las *patas* (entries) de un movimiento ni el estado de reversión: hay
  que agregarlos si `budgets` los necesita.
- `apps/loans/models.py`: `Installment` con `principal_amount`,
  `interest_amount` y `amount` (el split ya está en el modelo).
- `apps/loans/services.py::pay_installment` llama a
  `transfer_between_users(... amount=installment.amount ...,
  idempotency_key=f'loan-{loan.id}-installment-{number}')` y **descarta** la
  `LedgerTransaction` devuelta: **no hay forma hoy de ir de un movimiento del
  ledger a su cuota**. Lo mismo con `_disburse`
  (`idempotency_key=f'loan-{loan.id}-disbursement'`).
- `apps/investments/services.py::open_position` mueve el saldo a la cuenta
  `system` con `transfer_to_counterpart` (tipo `transfer`).
- Restricción clave: **una billetera por usuario y moneda** ⇒ hoy es imposible
  una transferencia entre cuentas propias del mismo usuario; la regla del cliente
  ("no cuentan como gastos") hay que implementarla igual, de forma defensiva.

**Reglas que se deducen de las decisiones del cliente**

- Movimiento **no categorizado** → no cuenta en ningún presupuesto (nada se
  categoriza solo).
- Un movimiento es **gasto** si sale de la billetera del usuario y su contrapartida
  no es la propia billetera del usuario:
  - crédito en `custody` (un `withdrawal`) → gasto por el importe del débito;
  - crédito en `system` (apertura de inversión) → **no** es gasto;
  - crédito en otra `user_wallet` → gasto por el importe del débito, **excepto**
    el pago de una cuota de préstamo, donde solo cuenta el **interés** (el capital
    es amortización de deuda, no consumo) y el **desembolso** del préstamo (el
    dinero del prestamista se convierte en un activo, no es consumo) no cuenta.
- Cada presupuesto se evalúa en **una sola moneda** y contra los gastos de esa
  misma moneda: nunca se mezclan ARS y USD.

**Decisiones de implementación que se tomaron**

1. **Dónde vive el importe.** El gasto guarda **solo la categorización**
   (usuario, categoría e id del movimiento) y el presupuesto **deriva** el
   importe del ledger al leer, con una consulta por lote (sin N+1). Así no hay
   una copia de los importes que pueda contradecir al ledger.
2. **Enlace movimiento ↔ cuota de préstamo.** `Installment.ledger_transaction_id`
   y `Loan.ledger_transaction_id` guardan el movimiento del pago y del
   desembolso; `loans.selectors.list_loan_movement_breakdowns` devuelve el
   desglose en primitivos (tipo, capital, interés, moneda) y
   `get_loan_movement_breakdown` la versión de un movimiento.
3. **Lectura del movimiento.** `ledger.selectors.list_movement_details` expone
   las patas (cuenta, kind, usuario, dirección, importe, moneda) y si el
   movimiento fue revertido, en un lote; `get_movement_detail` resuelve uno.
   `budgets` nunca importa `ledger.models`.
4. **Reversos.** Un movimiento revertido no cuenta: el selector lo marca con
   `is_reversed` y el cálculo lo excluye (probado con un movimiento categorizado y
   después revertido por staff).
5. **Categoría.** `Budget.category` es una FK **dentro de la misma app**
   (columna `category_id`), como `investments.Position.product`. AGENTS §5.2 lo
   permite y AGENTS §7 **no se modificó** (su §17 exige autorización).
6. **Gastos manuales.** No hay: todo gasto proviene de un movimiento del ledger.
7. **Presupuesto mensual.** `Budget.period = 'monthly'`, mes calendario en UTC
   (`TIME_ZONE`) y `alert_threshold` es un porcentaje entre 0 y 100 con
   `CheckConstraint` en la base; el importe que dispara la alerta se calcula con
   `core.money.round_two`.
8. **`Goal`** (AGENTS §7) quedó **fuera**: no estaba en el alcance pedido.

**Contratos de `import-linter` agregados** (el CI los corre y si el chequeo
falla el cambio no se acepta): `budgets-only-services-and-selectors` (budgets
llega a `ledger`, `loans`, `identity` y `offers` solo por sus `services.py` y
`selectors.py`) más `ledger-no-budgets`, `loans-no-budgets`,
`identity-no-budgets` y `offers-no-budgets`.

**Cobertura**: AGENTS §10 exige **90%** en `budgets/services.py` y hay que sumar
ese umbral a la CI.

### 11.4 Huecos de especificación de `reports` y `notifications` (cerrar antes de codear)

- `reports`: sin modelos, sin endpoints, sin criterios de agregación, sin formato
  de exportación, sin política de rango de fechas. AGENTS §4 solo dice "Resúmenes y
  exportaciones" y §15 "reports (resúmenes y exportaciones)".
- `notifications`: sin modelo (¿registro de avisos? ¿preferencias del usuario?),
  sin eventos disparadores (¿pago de cuota próximo a vencer? ¿vencimiento? ¿liquidez
  de inversión?), sin backend de email definido, sin idempotencia especificada.

---

## 12. Comandos de management y datos de prueba

### Management commands implementados

| Comando | Qué hace |
|---|---|
| `python manage.py mark_overdue_loans` | Marca las cuotas vencidas (`overdue`) y sus préstamos (`defaulted`) |
| `python manage.py settle_investments` | Liquida las posiciones de inversión vencidas (capital + interés) |

Los dos commands siguen siendo la vía manual: comparten el `service` con las tasks
de Celery, que corren solas una vez por día desde el beat.

### Datos de prueba

- No hay fixtures JSON: todo se arma con `factory_boy` en
  `apps/<app>/tests/factories.py`.
- Helpers para KYC aprobada: `create_approved_user()` en
  `apps/ledger/tests/factories.py`, `apps/offers/tests/factories.py`,
  `apps/loans/tests/factories.py` y `apps/investments/tests/factories.py`
  (crean el usuario con `identity.services`).
- Los constraints de la base se ejercitan contra **PostgreSQL real** (nunca
  SQLite) y los tests de concurrencia usan `transaction=True` + hilos con
  conexión propia.
- `settings.LEDGER_SIMULATED_DEPOSITS_ENABLED = True` **solo** en
  `config/settings/test.py`; en `production.py` depende de la variable de entorno
  y el system check `ledger.E001` impide que quede activa. Ojo: en el entorno
  **local** tampoco está activa (ver P17).

---

## 13. Reglas para Claude (y para cualquier IA que retome el proyecto)

1. **`AGENTS.md` es la fuente de verdad.** Si una instrucción contradice
   `AGENTS.md`, **avisá antes de actuar** y pedí confirmación. **No modifiques
   `AGENTS.md` sin autorización explícita del desarrollador** (su §17 exige que
   todo cambio quede registrado con su aprobación).
2. **No inventes requisitos.** Si una regla de negocio no está documentada ni se
   deduce del código, **preguntá** en lugar de decidir por tu cuenta. Distingá
   entre lo que el cliente confirmó (§11.2), lo que está abierto (§11.1) y lo que
   falta definir (§11.4).
3. **Respetá la arquitectura**: monolito modular, una sola base PostgreSQL, sin
   microservicios, sin brokers de mensajes, sin dependencias nuevas sin
   justificación y aprobación.
4. **TDD estricto**: test primero, verificá que falla por la razón esperada,
   implementación mínima, verificá que pasa, refactor con todo en verde. Registrá
   la salida real de pytest. **Nunca** modifiques un test para que pase.
5. **Commits atómicos en inglés** con Conventional Commits (`feat:`, `fix:`,
   `test:`, `docs:`, `chore:`), uno por funcionalidad, con `ruff`,
   `lint-imports` y `pytest` en verde antes de cada commit. **Nunca**
   `--no-verify`.
6. **Capas y límites**: nada de lógica de negocio en `views.py`, serializers,
   signals ni `save()`; entre apps solo se usan `services.py` y `selectors.py`;
   sin ForeignKey entre apps de dominio (usar `UUIDField`); `core` no importa
   otras apps. Todo con `import-linter` verificable.
7. **Reglas de dinero**: `Decimal` siempre, un solo redondeo en
   `core/money.py`, nunca mezclar monedas, idempotencia por `(usuario, clave)`,
   `transaction.atomic()` + `select_for_update()` cuando haya carrera, y no
   tocar la integridad, inmutabilidad ni idempotencia del ledger.
8. **Verificá antes de declarar**: suite completa, cobertura, `ruff`,
   `lint-imports`, `manage.py check`, `makemigrations --check --dry-run` y, si
   tocaste infraestructura, el arranque real de Docker. **No declares terminado
   nada que no hayas verificado.**
9. **Actualizá `HANDOFF.md`** al cerrar cada bloque, con los resultados reales.
10. **Preguntá antes de tocar** los management commands, el schema del ledger o
    los contratos de `import-linter`: son parte del contrato del dominio.
11. **En `budgets`, el importe del gasto no se guarda.** Se deriva del ledger al
    leer (`budgets.selectors.analyze_movement_spending`). Si hay que cambiar una
    regla de gasto, se cambia la función pura `_classify_movement` y sus tests, no
    se agrega un campo con el importe.

---

## 14. Registro

| Fecha | Cambio |
|---|---|
| 2026-10-21 | Documento creado: estado real del repo (63 commits), estado verificado de los checks, decisiones D1-D18, problemas P1-P14, endpoints reales extraídos del `URLConf`, comandos de ejecución validados y orden de los próximos pasos. **Nota**: `HANDOFF.md` **no existía** en el repo (ni en el árbol de trabajo, ni en el historial de git de ninguna rama, ni en el filesystem): se creó desde cero siguiendo la estructura de secciones indicada. |
| 2026-10-21 | Ajustes pedidos por el cliente: §6.2 ahora es un resumen de 1-2 líneas por bloque (sin el detalle de archivos por commit); §4 pasó a "Requisitos, entorno local e invariantes del dinero" con los tres invariantes del ledger (saldo no negativo solo en `user_wallet`, `idempotency_key` única por `(usuario, clave)`, suma de saldos por moneda = 0) y §9 los referencia; §11.1 nueva con las decisiones abiertas con el cliente. |
| 2026-10-21 | Tercer ajuste pedido por el cliente: §6.2 sin la columna de commits; §11.1 con O5 renombrado a PLA/FT y O6 nuevo sobre CFT (costo financiero total) en la comparación de ofertas; §11 renombra Fase 2 → Bloque 6 y Fase 3 → Bloque 7, suma el ítem de programar `mark_overdue_loans` y `settle_investments` con Celery beat, el ítem de Producción (/health/, Sentry, backups, HTTPS, CORS) y aclara que `IsKycApproved` es una capa extra porque los services ya exigen KYC. |
| 2026-10-21 | **Esquema OpenAPI arreglado**: `spectacular --validate --fail-on-warn` pasa con **0 errores y 0 warnings** y se agregó a la CI (job *quality*). `InstallmentPayView` declara `serializer_class` (+ `request=None` porque no lee body), `ENUM_NAME_OVERRIDES` nombra `LoanStatusEnum` y `PositionStatusEnum`, y las 5 pares lista/detalle tienen `operation_id` explícito. Regresión cubierta en `apps/core/tests/test_openapi.py` (380 tests). |
| 2026-10-21 | **Infraestructura de Celery (primer cambio del Bloque 6)**: `config/celery.py` (broker Redis, sin result backend persistente, UTC), beat diario con `mark_overdue_loans` (00:05) y `settle_investments` (00:15), servicios `worker` y `beat` en el compose con volumen persistente para el scheduler, tasks en `apps/loans/tasks.py` y `apps/investments/tasks.py` que delegan en los services existentes (los management commands no se modifican), y tests de tasks y de commands (407 tests). Decisiones y consecuencias en `docs/adr/0001-celery-redis-cola-y-scheduler.md`. `AGENTS.md` **no** se modificó (pendiente de aprobación del desarrollador). |
| 2026-10-21 | **O4 resuelta por el cliente** (criterio completo en §11.2). La app `budgets` **no** se implementó: el trabajo se detuvo en el análisis del código. Se deja el análisis verificado y las decisiones de implementación pendientes en §11.3 para retomar. |
| 2026-10-21 | **Tres mejoras chicas**: `6efb50f` aplica `IsKycApproved` a las vistas que mueven dinero (movimientos del ledger, publicar oferta, aceptar préstamo, pagar cuota, abrir posición) con un mixin que solo afecta los métodos que no son de lectura; `89d6f49` agrega `GET /health/` (200 `{"status": "ok"}` / 503 `{"status": "unavailable"}`, público y fuera del esquema OpenAPI); `45eefa8` crea `docker-compose.prod.yml` (db, redis, web con gunicorn, worker y beat; sin puertos de db/redis, secretos por entorno, `restart: unless-stopped`, healthchecks y volúmenes persistentes) y ajusta `SECURE_PROXY_SSL_HEADER` en producción para que el chequeo de salud no reciba un 301. **504 tests pasan**, cobertura 98,81%. El stack de producción se levantó de verdad: `db`, `redis` y `web` healthy, `worker` y `beat` Up y `/health/` respondiendo 200. |
| 2026-10-21 | **Bloque 6b implementado: app `budgets`** en 7 commits: `29f9b96` selector de patas y reversión en el ledger, `82793c2` `ledger_transaction_id` en `Installment`/`Loan` + selector de desglose, `e18b0a7` app con `Category` y `Budget`, `91b3858` service de categorización, `9f1a546` cálculo del gasto acumulado por categoría y moneda, `9125429` API y OpenAPI sin warnings, `92f2e1a` contratos de import-linter, umbral de cobertura del 90% en la CI y ADR 0002. **491 tests pasan**, cobertura total 98,85% y `budgets/services.py` al 100%. Migraciones: `budgets.0001_initial`, `budgets.0002_expense` y `loans.0002_installment_ledger_transaction_id_and_more`. Los endpoints quedaron verificados en runtime real contra el `web` local (crear categoría 201, listar 200 paginado, crear presupuesto 201, duplicado 409, sin token 401). |
| 2026-10-21 | **Reescritura del documento** para traspaso a Claude: §2 con el stack real (Celery 5.6.3 en uso), §3 con el árbol real (celery.py, tasks.py, ADR 0001), §5 con las reglas de API/seguridad/testing, §6.3 con los módulos verificados, §6.4 con la tabla de verificaciones comprobadas hoy (407 tests, 99,07% de cobertura, 11 contratos, 5 servicios Up), §7 con D19-D24 (Celery), §8 con P15-P17, §9 corregido (una billetera por moneda; depósitos simulados apagados en local), §10 con los comandos reales (`docker compose ps` muestra 5 servicios), §11 con el bloque 6b como tarea recomendada y §11.3 con el contexto técnico de `budgets`, §11.4 con los huecos de especificación de `reports`/`notifications`, **§13 nueva con las reglas para Claude** y §14 el registro. Se eliminaron datos obsoletos (conteo de commits, "374 passed", "3 servicios Up", `docs/adr/` vacío) sin perder decisiones vigentes. |
