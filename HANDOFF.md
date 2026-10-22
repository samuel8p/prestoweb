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
El **Bloque 6** (budgets/reports/notifications) está **completo**: la
infraestructura de Celery, la app **`budgets`** (gastos categorizados y
presupuestos mensuales), la app **`reports`** (cuatro reportes de solo lectura) y
la app **`notifications`** (avisos por email) ya están. Falta el **Bloque 7**
(payments con proveedor real).

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
├── docker-compose.yml            # db, redis, web, worker, beat (localhost only, DEMO_MODE)
├── deploy/
│   ├── Caddyfile                  # proxy inverso con TLS automático (perfil proxy)
│   ├── entrypoint.sh              # roles `web` y `worker` de la misma imagen
│   └── backup-postgres.sh         # backup diario de PostgreSQL con rotación
├── docker-compose.prod.yml        # producción: sin puertos de db/redis, secretos por env
├── Dockerfile                    # python:3.12-slim + deps + usuario `presto` sin root
├── pytest.ini                    # DJANGO_SETTINGS_MODULE + --ds=config.settings.test
├── pyproject.toml                # deps + config de ruff
├── .importlinter                 # 28 contratos de límites entre apps
├── .pre-commit-config.yaml       # ruff, ruff-format, import-linter
├── .github/workflows/ci.yml      # ruff, import-linter, spectacular, makemigrations, pytest
├── .env.example                  # SOLO placeholders, nunca secretos reales
├── .env.prod.example              # variables de producción (mismo criterio)
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
│   ├── budgets/                  # Category, Budget, Expense (gastos categorizados)
│   │   └── tests/
│   ├── reports/                  # reportes de solo lectura (sin modelos)
│   │   ├── export.py              #   exportación a CSV
│   │   └── tests/
│   └── notifications/             # avisos por email (sin FK a otras apps)
│       ├── emails.py              #   armado de los emails
│       ├── receivers.py           #   receptores de las señales emisoras
│       ├── tasks.py               #   tarea de envío
│       └── tests/
├── config/
│   ├── settings/                 # base, local, test, production
│   ├── celery.py                 # app de Celery + beat schedule diario
│   ├── urls.py                   # /api/v1/ + /api/schema/ + /api/docs/ + /admin/
│   ├── wsgi.py, asgi.py
├── tests/                         # suite end-to-end (cruza todas las apps)
│   └── test_end_to_end.py         #   flujo completo en ARS y USD
└── docs/
    ├── architecture.md             # arquitectura real: apps, capas, invariantes
    ├── audit-final.md              # auditoría final: hallazgos y "requiere decisión"
    ├── agents-changelog-proposal.md  # texto propuesto para AGENTS.md §17 (sin aplicarlo)
    ├── deploy-demo.md              # modo demo: email por consola (logs del worker)
    ├── deploy-northflank.md        # Northflank (plan gratuito) + Vercel
    └── adr/
        ├── 0001-celery-redis-cola-y-scheduler.md
        ├── 0002-budgets-derivacion-del-gasto.md
        ├── 0003-reports-reportes-de-solo-lectura.md
        ├── 0004-notifications-avisos-por-email.md
        ├── 0005-saldo-desnormalizado.md
        ├── 0006-doble-entrada-diferida.md
        └── 0007-orden-de-las-apps.md
```

Apps existentes: `core`, `identity`, `ledger`, `offers`, `matching`, `loans`,
`investments`, `budgets`, `reports`, `notifications`. **No existe** (aún):
`payments`.

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
- Los contenedores de la aplicación (`web`, `worker`, `beat`) corren como el
  usuario **`presto`** (uid 1000), no como root. Por eso el bytecode, la cache
  de pytest, la de ruff y la cobertura van a `/tmp`: el código del proyecto
  viene montado como volumen del host y ahí el contenedor no puede escribir.
- Variables de entorno: ver `.env.example` (placeholders, sin secretos). Las que
  importan: `DEMO_MODE` (modo demostración), `LEDGER_SIMULATED_DEPOSITS_ENABLED`
  (dinero simulado) y, solo en producción, `SECURE_HSTS_SECONDS` (HSTS).

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

Los commits anteriores de este mismo `HANDOFF.md` están listados; este commit no
puede listarse a sí mismo (tras el push, `git log --oneline | wc -l` da
**161**).

| Commit | Asunto |
|---|---|
| `eac2451` | fix(schema): declare the empty body of the kyc status |
| `e5ce13e` | feat(investments): add the currency to the positions list |
| `2a9cede` | feat(ledger): add the amount and the currency to the movements list |
| `bc4cd23` | docs: close the openapi contract corrections |
| `4eee318` | fix(schema): declare the demo mode header |
| `8dfc81a` | fix(schema): declare the error responses and the nullable kyc |
| `cb20141` | fix(schema): declare the parameters and the csv of the reports |
| `6471b42` | fix(schema): declare the idempotency key and the body of the refresh |
| `49054e8` | docs: add the api contract written by the frontend |
| `a037d1c` | fix(schema): declare the real pagination of the list endpoints |
| `d34cfb5` | docs: refresh the commit log of the handoff |
| `1923169` | chore(config): the development env example comes in demo mode |
| `72f299f` | docs: add OpenAPI schema |
| `ee198e0` | docs: add how to run the demo locally to the readme |
| `595f567` | docs: fix the stale numbers and the tree of the handoff |
| `33e415d` | chore: ignore logs, dumps, backups and key files |
| `87d55ff` | docs(handoff): register the northflank delivery |
| `b5d14fd` | docs(deploy): guide for northflank and the vercel front |
| `86f3aca` | fix(deploy): write the beat schedule where the container can |
| `8b50de8` | feat(core): serve the admin static files from the application |
| `bc14a78` | docs(deploy): document the resources of the free plans |
| `06d2b32` | feat(core): answer the health check before the host validation |
| `b88e5fb` | feat(deploy): serve the web and the worker with the same image |
| `cf55020` | feat(deploy): allow the worker to run the beat embedded |
| `2c87325` | feat(core): connect with the urls of the managed services |
| `6cbc82f` | docs(handoff): register the cors and the oracle cloud delivery |
| `57c2f89` | docs(deploy): guide for Oracle Cloud, DuckDNS and Vercel |
| `538944a` | chore(infra): make the production concurrency configurable |
| `b179fd0` | docs(deploy): verify and document the arm64 compatibility |
| `3ee2f62` | feat(core): enable the cors headers for the front |
| `e27332f` | docs: close the audit decisions and update the handoff |
| `b875471` | feat(ledger): restrict the currency to ARS and USD in the database |
| `caac920` | ci: check the production settings with the deploy check |
| `307e2a6` | chore(deps): audit the dependencies for known vulnerabilities |
| `301beca` | docs(agents): register the decisions of the last blocks in the changelog |
| `330cd91` | docs(handoff): update the handoff after the final audit |
| `8a1c99b` | docs(agents): propose the changelog entries for AGENTS.md |
| `d9b6377` | docs(audit): add the findings of the correction phase |
| `2972006` | test(e2e): add the end to end suite |
| `71eaeae` | fix(infra): keep the linters cache out of the project directory |
| `12b099e` | fix(structure): add the missing package markers |
| `c462f18` | docs(architecture): document the architecture and the pending ADRs |
| `d2a2979` | docs(readme): rewrite the readme with the real project |
| `22c00d2` | docs(config): document every environment variable in the examples |
| `9d34696` | chore(infra): run the application containers as a non-root user |
| `9714456` | fix(deploy): make the production health check pass |
| `471ca4e` | chore(quality): keep the formatting stable across ruff versions |
| `c46a6c6` | fix(offers): lock the offer on update and expire |
| `c5933b1` | test(budgets): cover the category detail and the concurrent categorization |
| `b6d2a51` | fix(security): enable the django password validators and hsts |
| `4589a41` | docs: add the final backend audit |
| `9e28f68` | docs: register the complete demo mode in the handoff |
| `4560912` | docs: complete the demo mode guide and enable it in the dev stack |
| `52915b5` | chore(infra): daily postgres backup with rotation |
| `5b567e7` | chore(infra): demo mode, explicit CORS and optional TLS proxy in production |
| `813e43c` | feat(core): public meta endpoint and the demo mode header |
| `9ef8560` | feat(core): demo mode setting for the simulated money |
| `c77e5f9` | feat(core): demo mode sends the notification emails to the worker logs |
| `329b090` | docs: register the notifications app in the handoff |
| `a4e51d2` | chore(notifications): import-linter contracts, coverage gate and ADR |
| `79d0a77` | feat(notifications): notifications api |
| `0ae71d3` | feat(notifications): budget alert when the spending crosses the threshold |
| `1ca99a3` | feat(notifications): alert when an investment is settled |
| `454fa87` | feat(notifications): alerts for the installments due soon and overdue |
| `a9bb4a9` | feat(notifications): celery task to send the notification emails |
| `cc1d359` | feat(notifications): notifications app with models and services |
| `90cdb03` | docs: register the reports app in the handoff |
| `9599982` | chore(reports): import-linter contracts, coverage gate and ADR |
| `73b62f1` | feat(reports): csv export for the four reports |
| `2a75626` | feat(reports): investments report |
| `5fef54f` | feat(reports): loans report |
| `593a34b` | feat(reports): spending report |
| `b68975f` | feat(reports): movements report |
| `4bb5fe7` | feat(reports): reports app and parameter validation |
| `7120813` | docs: register the kyc permission, health check and production compose |
| `45eefa8` | chore(infra): add the production docker compose |
| `89d6f49` | feat(core): add the health check endpoint |
| `6efb50f` | feat(identity): require approved kyc on the views that move money |
| `ee845fd` | docs: register the budgets app in the handoff |
| `92f2e1a` | chore(budgets): import-linter contracts, coverage gate and ADR |
| `9125429` | feat(budgets): budgets api |
| `9f1a546` | feat(budgets): monthly spending per category and currency |
| `91b3858` | feat(budgets): categorize ledger movements as personal expenses |
| `e18b0a7` | feat(budgets): budgets app with categories and monthly budgets |
| `82793c2` | feat(loans): link loan movements to the ledger and expose the breakdown |
| `29f9b96` | feat(ledger): movement detail selector with legs and reversal state |
| `f4d6759` | docs: rewrite handoff for the next agent with the verified project state |
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
| `cffd42e` | docs: add handoff document with current repo state - Section 6: real git log table (62 commits), per phase/block status with the files   touched by each commit, and the checks verified on 2026-10-21 - Section 7: technical decisions D1-D18 with rationale - Section 8: problems P1-P14 and how each was resolved - Section 10: verified commands, including the OpenAPI validation one - Section 11: real remaining work, starting with the OpenAPI schema fix - New section: real /api/v1/ routes extracted from the URLConf - Section 13: registry entry |
| `867d1fa` | chore: ignore generated openapi schema files |
| `0cfb2ea` | test(investments): concurrency and ledger invariant coverage - Two concurrent openings with the same key return the same position and create one - Two concurrent settlements pay the position only once - Ledger invariant: counterparties equal the negative of the user wallets, and the   total balance per currency is zero, with investments included - ledger.selectors.get_balance_breakdown exposes the invariant publicly - investments/services.py coverage: 99% (minimum 90%) - 374 tests pass |
| `39707da` | feat(investments): api endpoints, admin and import-linter contracts - Endpoints /api/v1/investments/: products lists the active products, positions lists   the own ones, POST opens a position with the Idempotency-Key header and GET shows the   detail; third parties get 404 - Admin: products are created only by staff, positions are read only - import-linter: investments-only-services-and-selectors and ledger-no-investments - 370 tests pass |
| `1b2199d` | feat(investments): open and settle fixed term positions - open_position requires approved KYC, an active product, amount >= min_amount and the   product currency; in one transaction.atomic it moves the money to the system account   through the ledger, stores the position and computes the simple interest - settle_matured_positions pays capital and interest from the system account, once per   position, with the interest as a ledger movement of type interest - management command settle_investments - 357 tests pass |
| `7ebf030` | feat(ledger): transfers between a user wallet and a counterpart account - transfer_to_counterpart and transfer_from_counterpart move money between a user_wallet   and the custody/system account, which has no user and cannot be resolved by   transfer_between_users - Same balance, locking order and idempotency rules as the rest of the ledger - Public constants SYSTEM_COUNTERPART and CUSTODY_COUNTERPART for other apps - 340 tests pass |
| `1ba05b9` | feat(investments): investment product and position models - InvestmentProduct: fixed_term type, currency, term_days, annual_rate_tna, min_amount,   status active|matured|cancelled, positive constraints (migration 0001) - Position: user_id UUIDField, product FK, amount, status active|matured, opened_at,   maturity_date, interest_amount and idempotency key per (user_id, key) with request_hash - 336 tests pass |
| `f1d97fe` | feat(core,ledger): simple interest helper and configurable movement type - core.money.simple_interest computes amount * tna/100 * days/365 with a single rounding - ledger.services.transfer_between_users accepts a movement_type so the investments   settlement can register an interest movement; balance and locking rules unchanged - 328 tests pass |
| `098e745` | docs: register Block 5 investments decisions in AGENTS.md - New phase order: investments -> budgets/reports/notifications -> payments last - New section: rules for investments (simple interest, atomic opening, settlement,   no early cancellation, system account as counterpart, staff only products) - Section 7: InvestmentProduct and Position with English field names - Section 17: Block 5 decisions log |
| `675ad76` | test(loans): concurrency, idempotency and isolation coverage - Concurrent acceptance of the same offer: only one borrower succeeds - Concurrent payment of the same installment: only one succeeds - Concurrent acceptance with the same idempotency key: a single loan with its schedule - Recovery from an IntegrityError race returns the original loan - API tests: lender without funds, double payment, lender paying, unknown loan and   unknown installment - loans/services.py coverage: 99% (minimum 90%) - 321 tests pass |
| `b19b4be` | feat(loans): api endpoints, selectors and import-linter contracts - Endpoints /api/v1/loans/: POST accepts an offer with the Idempotency-Key header, GET lists   the loans of the user as borrower or lender, GET /{id}/ returns the snapshot and the   installments, POST /{id}/installments/{number}/pay/ pays an installment - Only the parties see a loan; third parties get 404, the lender gets 403 when paying - ledger.selectors.get_user_wallet added for cross-app reads - import-linter: loans-only-services-and-selectors, ledger-no-loans, offers-no-loans - 311 tests pass |
| `7b9d0c5` | feat(loans): accept offer, pay installment and mark overdue services - accept_offer runs in one transaction.atomic: locks and accepts the offer, stores the   immutable snapshot, persists the French schedule and disburses lender to borrower;   rolls back everything when the lender has no funds - build_installment_schedule keeps the installment constant and adjusts the last capital part   so the sum of capitals equals the principal exactly - pay_installment: only the borrower, in order, full amount; loan becomes paid on the last one - mark_overdue and change_loan_status with the valid transition machine - management command mark_overdue_loans - 301 tests pass |
| `b9e0ded` | feat(ledger,offers): internal third-party transfer and offer acceptance - ledger.services.transfer_between_users moves money between two users initiated by a   third party, with type transfer, description and idempotency key; balance rules unchanged - offers.services.accept_offer locks the offer, rejects inactive offers and own offers - offers.selectors.get_offer_locked returns the offer with select_for_update - 277 tests pass |
| `a176f12` | feat(loans): loan, offer terms snapshot and installment models - Loan with states active|paid|defaulted (pending is not used) and idempotency key   unique per (borrower_user_id, idempotency_key) plus request_hash - OfferTermsSnapshot one to one with loan, immutable by default - Installment with unique number per loan and positive amount constraints - Migration 0001 - 269 tests pass |
| `42569d3` | docs: register Block 4 loans decisions in AGENTS.md - New section: rules for loans (atomic offer acceptance, third-party initiated disbursement,   French schedule with last installment adjusting principal, installment payment order,   overdue marking, state machine, visibility) - Sections 6 and 7: Loan states are active|paid|defaulted, pending is not used - Section 17: Block 4 decisions log and block order (Block 4 = loans, Block 5 = payments) |
| `266cdbc` | test(offers): cover error branches of views and permission - 7 new API tests: expired offer, invalid amount, missing KYC, unknown offer, cross access - 4 permission tests: approved KYC, without KYC, anonymous, message - apps/offers/views.py 100%, apps/offers/permissions.py 100% - 253 tests pass |
| `c5338dd` | feat(matching): search by amount range instead of exact amount - The loan takes the full offer amount, so the search filters by amount_min/amount_max - offers.selectors.search_active_offers and matching.search_offers updated - Query params of GET /api/v1/matching/offers/ updated and validated - AGENTS.md documents the range filter rule - 244 tests pass |
| `40ca761` | feat(matching): marketplace search and comparison endpoints - GET /api/v1/matching/offers/ with currency, amount, max_rate, term_months filters and   rate|term|amount ordering, paginated - POST /api/v1/matching/comparisons/ returns installment, total interest and total cost - All views documented with drf-spectacular - 241 tests pass |
| `5c36dd8` | feat(matching): search and comparison selectors - search_offers searches active offers with currency/amount/max_rate/term_months filters   and rate|term|amount ordering, built on offers.selectors only - compare_offers returns installment, total interest and total cost per offer using   core/money.py french helpers - Domain exceptions in apps/matching/exceptions.py - 228 tests pass |
| `abb5336` | feat(offers): offer model, services, selectors and API - Offer model: lender_user_id UUIDField, amount, currency, TNA annual interest rate,   term_months, requirements, status active|expired|accepted (migration 0001) - services: create_offer (requires approved KYC, does not reserve funds), update_offer,   expire_offer; only the owner can act on its offers - selectors: get_offer, list_offers_for_lender, get_active_offer, search_active_offers   with currency/amount/max_rate/term_months filters and rate|term|amount ordering - API /api/v1/offers/: list own, create, detail, patch (update or expire) - import-linter: offers-no-identity-models, offers-no-matching, matching-no-offers-models - 219 tests pass |
| `5bd3bea` | feat(core): french amortization helpers in money.py - monthly_rate_from_annual_tna converts annual TNA percent to the monthly rate - french_installment computes the monthly installment with Decimal, rounding once - french_total_interest and french_total_cost for the comparison - InvalidAmount raised for invalid principal, rate or months - 9 money tests pass |
| `d48fe62` | docs: register Block 3 decisions and new phase order in AGENTS.md - New phase order: offers + matching -> loans -> payments - New section: rules for offers and matching (TNA annual rate, French installment in   core/money.py, creating an offer does not reserve funds, lender needs approved KYC,   matching is read only and only uses offers.selectors, offers does not import matching) - Section 7: Offer fields with English names and TNA semantics - Section 17: Block 3 decisions log |
| `b2d6dcb` | test(ledger): custody equals negative sum of user wallets - Invariant test per currency after deposits, withdrawals and transfers - 178 tests pass |
| `16f5029` | test(ledger): api coverage for withdrawals and transfers - 14 API tests: success paths, KYC 403, insufficient funds 400, invalid currency/amount,   missing destination, currency mismatch, non wallet destination and cross access - Removed dead code: unreachable fallback in views.create_transaction and   unused selectors.get_counterpart_account - ledger/views.py 100%, ledger/selectors.py 100%, ledger/services.py 93% - 177 tests pass |
| `4bb1263` | feat(ledger): transaction listing includes movements touching user accounts - list_transactions_for_user now matches created_by_user_id or entries on the user's accounts - Isolation test: movements of other users stay invisible - 163 tests pass |
| `f0a73c6` | test(ledger): concurrency tests against real PostgreSQL - Concurrent deposits with the same idempotency key create a single transaction - Concurrent withdrawals never leave a negative user_wallet balance - Concurrent transfers conserve the total balance (no lost update) - Balance invariant holds after concurrent movements - Threads with their own connections, transaction=True - ledger/services.py coverage: 93% (minimum 90%) - 161 tests pass |
| `3ec686b` | feat(ledger): api endpoints and admin reversal action - Endpoints /api/v1/ledger/: accounts, accounts/{id}/balance, transactions, transactions/{id} - Idempotency-Key header required; same key with different payload returns 409 - KYC failure returns 403, domain errors mapped to 400 - Admin action reverse_transactions calls services.reverse_transaction (staff only, no endpoint) - Core exception handler uses the exception own code for non generic statuses - 157 tests pass |
| `1d7f387` | feat(ledger): services and selectors for deposits, withdrawals, transfers and reversals - services: deposit, withdraw, transfer, reverse_transaction, create_user_wallet - Accounts locked with select_for_update in ascending id order; balance only changed in services - Idempotency per (created_by_user_id, idempotency_key) with request_hash: same hash returns   original, different hash raises conflict, IntegrityError race returns the original - KYC approved required via identity.selectors.is_kyc_approved - System check fails when LEDGER_SIMULATED_DEPOSITS_ENABLED is on in production (uses DJANGO_ENV) - import-linter: allow indirect imports for ledger -> identity.selectors - ledger/services.py coverage: 90% (minimum 90%) |
| `a876038` | feat(ledger): postgres triggers for double entry and immutability - Deferred constraint trigger: sum(debits) = sum(credits) per transaction at commit - Triggers blocking UPDATE/DELETE on LedgerTransaction and LedgerEntry - Migration 0002 - 107 tests pass |
| `2bbacd9` | feat(ledger): account, transaction and entry models - Account with denormalized balance, UUIDField user_id (no FK) and per-kind uniqueness - CheckConstraint balance>=0 only for user_wallet; counterpart accounts may go negative - LedgerTransaction with idempotency per (created_by_user_id, idempotency_key), request_hash   and single reversal per original - LedgerEntry with amount > 0 constraint - Migration 0001 - 100 tests pass |
| `d07a4f2` | docs: register Phase 1B ledger decisions in AGENTS.md and add import-linter contracts - Section 6: new 'Reglas adicionales del ledger' (denormalized balance, deferred constraint   trigger, immutability triggers, idempotency per user+key, transfers, reversals, simulated   deposits, KYC requirement, cross-app limits) - Section 7: Account/LedgerTransaction/LedgerEntry with denormalized balance and constraints - Section 17: Phase 1B decisions and the 4 resolved AGENTS.md conflicts - .importlinter: ledger-no-identity-models and identity-no-ledger contracts - apps/ledger: app skeleton so the contracts resolve |
| `127de6e` | chore: add .gitattributes with LF line endings |
| `5aa5004` | ci: add coverage gate and document project in README - CI runs pytest with --cov=apps and --cov-fail-under=80 - pytest-cov added to CI dependencies - README with structure, commands, API endpoints and error format |
| `819cd15` | fix: flatten duplicated config package - Remove leftover config/config/ package and duplicate config/manage.py - Add config/__init__.py, config/settings/__init__.py, config/wsgi.py, config/asgi.py - WSGI/ASGI now point to config.settings.local and load correctly - Web service stays Up and serves /api/v1/, /api/schema/ and /admin/ |
| `3de20bb` | chore: ignore coverage and import-linter cache artifacts |
| `d418176` | test(identity): cover openapi schema, kyc permission and model branches - Schema endpoints and IsKycApproved permission coverage - Superuser validation branches and model __str__ methods - apps/identity coverage: 100% (minimo 80%) - 87 tests pass |
| `4eb59ef` | feat(identity): kyc resolution action in django admin - KYCVerificationAdmin with approve_kyc and reject_kyc actions calling services.resolve_kyc - Admin registered for User, Profile and KYCVerification - Admin URLs mounted at /admin/ - 77 tests pass |
| `6b61282` | feat(identity): auth, profile and kyc API endpoints - Endpoints /api/v1/: auth/register, auth/login, auth/token/refresh, auth/me, kyc, kyc/{id} - JWT login with refresh rotation and blacklist, scoped throttles (login 5/min, register 5/hour) - IsKycApproved permission implements AGENTS section 9.9 rule - DRF + simplejwt + spectacular settings, uniform error handler wired - 73 tests pass |
| `ad00056` | feat(core): uniform api error handler - apps/core/exception_handler.py normalizes DRF errors to AGENTS section 8 format - Body shape: error.code, error.message, error.details - 46 tests pass |
| `2351bd7` | feat(identity): services and selectors for registration, profile and kyc - services: register_user (user+profile atomic), submit_kyc, resolve_kyc with audit log - selectors: get_profile, get_kyc_for_user, is_kyc_approved - Domain exceptions in apps/identity/exceptions.py - 41 tests pass |
| `efafa8d` | feat(identity): kyc verification model with pending uniqueness - KYCVerification FK to User with request history - Fields: status, requested_at, resolved_at, resolved_by_user_id, documents - Conditional UniqueConstraint: one pending verification per user - Migration 0004 - 23 tests pass |
| `d48490b` | feat(identity): profile model - Profile 1:1 with User (phone_number, date_of_birth, country ISO 3166-1 alpha-2) - Country validated with RegexValidator - Migration 0003 - 18 tests pass |
| `7562c2a` | feat(identity): email-only user model with custom manager - User without username field (UUID primary key, unique email) - UserManager.create_user/create_superuser keyed by email - Migration 0002 removes username column - Tests: 7 identity model tests + 7 core tests pass |
| `a66fd7b` | chore(deps): add pytest-cov for coverage reporting |
| `67b0ef2` | docs: register Phase 1A decisions and naming corrections in AGENTS.md - Loan states in English: active/pending/paid/defaulted - Account without amount field (balance derived from entries) - KYCVerification with English field names - signals.py as documented exception for cross-app imports - Phase 1A decisions (a-f) and extras recorded in section 17 |
| `6826e28` | fix: pre-commit import-linter hook rev and args - rev: v2.15.0 -> v2.15 (tag does not exist upstream) - args: --config-file -> --config (option renamed in v2.x) - Verified on host: ruff, ruff-format and import-linter hooks all pass |
| `ea1edb4` | fix: import-linter forbidden contract - .importlinter: forbidden type with source_modules/forbidden_modules - apps.core cannot import apps.identity - Verified: 1 kept when clean, 1 broken with import chain shown when violated |
| `7d5cf6c` | test: remove obsolete test_simple - Deleted apps/core/tests/test_simple.py (placeholder heredado) - pytest now collects 10 tests |
| `3b3e401` | fix: tests use test settings - pytest.ini: add addopts = --ds=config.settings.test - Overrides DJANGO_SETTINGS_MODULE env var from docker-compose (config.settings.local) - pytest header now shows: settings: config.settings.test (from option) |
| `7d571fc` | fix: import-linter contract - .importlinter: core isolation contract (independence type) - apps.core cannot import apps.identity - Verified: 1 kept when clean, 1 broken when forbidden import added - All checks pass: lint-imports, ruff, pytest |
| `def5baf` | fix: pytest and ruff config - pytest.ini: minimal DJANGO_SETTINGS_MODULE=config.settings.test - config/settings/test.py: removed DATABASES override (pytest-django creates test_<NAME>) - pyproject.toml: moved select to [tool.ruff.lint], consolidated ignore/per-file-ignores - All checks pass: pytest 11 passed, ruff check, ruff format |
| `9442e63` | feat: import-linter config, pre-commit hooks, ruff updates - .importlinter: core isolation from domain apps (independence contract) - .pre-commit-config.yaml: ruff check, ruff format, import-linter (v2.15.0) - pyproject.toml: ruff config with select=[E,F,I,B,UP], line-length=100 - apps/core/money.py: ruff format fix - All checks pass: ruff, format, pytest (10 passed) |
| `39198aa` | feat: pre-commit, import-linter, Makefile, CI - .pre-commit-config.yaml: ruff check, ruff format, import-linter - .importlinter: core isolation from domain apps - Makefile: up, down, test, lint, migrate, shell, makemigrations - .github/workflows/ci.yml: ruff, import-linter, makemigrations --check, pytest on PostgreSQL 16 |
| `886cf55` | style: ruff format codebase - Single quotes, 100 char line length - Import sorting with isort (apps, config first-party) - Format all Python files via ruff format |
| `654cc03` | fix: Django 5.x constraint, pytest test settings, web localhost port - pyproject.toml: Django>=5.2,<6, pytest-django>=4.0, ruff config - Dockerfile: install deps with Django 5.x constraint - pytest.ini: DJANGO_SETTINGS_MODULE=config.settings.test - docker-compose.yml: web port 127.0.0.1:8000:8000 |
| `b0dbd58` | feat: Block C - core money/models tests, identity User tests - test_money.py: round_two, money functions with Decimal (3 tests pass) - test_models.py: BaseModel field definitions (4 tests pass) - test_user.py: email login, uniqueness, str (3 tests pass) - User model: UUID primary key, email as USERNAME_FIELD - base.py: remove deprecated SHA1PasswordHasher - test.py: use presto_test DB for isolated tests - pytest.ini: standard django_db marker config All 10 tests pass GREEN via docker compose run --rm web pytest |
| `e27b2fc` | fix: docker-compose add source volume mount for live code reload |
| `ff28c71` | feat: add core money/tests, models/tests, identity user/tests - test_money.py: round_two and money Decimal functions - test_models.py: BaseModel UUID and timestamp tests - test_user.py: User email login and str representation - test.py: use existing presto DB for tests - pytest.ini: basic django_db marker config |
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
| **Bloque 6c — `reports`** | ✅ completa | Cuatro reportes de solo lectura (gasto por categoría, préstamos, inversiones y movimientos) con una moneda por reporte, rango de hasta 12 meses y exportación CSV. ADR 0003. |
| **Bloque 6d — `notifications`** | ✅ completa | Avisos por email de cuatro eventos (cuota por vencer, cuota vencida, inversión liquidada, alerta de presupuesto) con idempotencia por evento, preferencias por usuario, API de lectura y señales definidas por las apps emisoras. ADR 0004. |
| **Bloque 7 — payments (proveedor real)** | ❌ no empezada | Hoy los depósitos y retiros son simulados y el system check `ledger.E001` los bloquea en producción. |
| **Auditoría final y pulido** | ✅ completa | Auditoría de solo lectura (`docs/audit-final.md`: 0 críticos, 2 altos, 9 medios, 8 bajos) y corrección de todo lo crítico, alto y medio: validadores de contraseña de Django, HSTS en producción, carrera de las ofertas, contenedores sin root, health check de producción, tests faltantes (detalle de categoría, concurrencia de budgets), suite end-to-end, `docs/architecture.md`, ADR 0005-0007 y README al día. |
| **Autorizaciones del 2026-10-21** | ✅ completa | Los cuatro puntos autorizados: el registro de la §17 de `AGENTS.md` aplicado (solo el changelog), `pip-audit` como dependencia de desarrollo con su puerta en la CI, `manage.py check --deploy` con los settings de producción en la CI y el `CheckConstraint` de moneda (`ARS`/`USD`) en `ledger.Account` y `ledger.LedgerEntry` con su migración. |
| **Bloque 7 — despliegue en Northflank (plan gratuito)** | ✅ completa | La misma imagen sirve para el web y el worker (comando `web` / `worker` vía el entrypoint), conexión por URL a las bases administradas (parseo propio con la stdlib y `DB_SSLMODE`), beat embebido opcional (`CELERY_EMBED_BEAT`), migraciones al arrancar (`RUN_MIGRATIONS`), health check que responde antes de validar el `Host`, estáticos del admin con whitenoise y la guía `docs/deploy-northflank.md`. |
| **Bloque 8 — el esquema OpenAPI describe la API real** | ✅ completa | El frontend mandó sus diferencias (`docs/backend-contract.md`) y el esquema quedó corregido: la paginación real de cada listado, el header `Idempotency-Key`, los parámetros y el CSV de los reportes, los errores de cada operación, el KYC nullable y la cabecera `X-Presto-Mode`. Un test de contrato llama a la API real y compara cada respuesta con lo declarado. Los huecos de **comportamiento** (el importe de los movimientos y la moneda de las posiciones) quedaron en `docs/audit-final.md` §5 |
| **Bloque 9 — los dos listados con los datos que faltaban** | ✅ completa | El listado de movimientos del ledger suma el **importe** (la pata del usuario, con su signo ✓, ADR 0008 ✓) y la **moneda** ✓, y el listado de posiciones suma la **moneda** del producto ✓. Los dos cambios son **aditivos** (solo lectura ✓, no se saca ni se renombra nada ✓) y no hacen N+1 ✓ (hay tests que lo comprueban ✓). El esquema regenerado ✓ y el test de contrato cubre los campos nuevos ✓ |
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
- **`reports`**: cuatro reportes de solo lectura, sin modelos ni migraciones:
  `spending` (gasto por categoría), `loans` (resumen como prestatario y
  prestamista), `investments` (posiciones, capital invertido e interés) y
  `movements` (movimientos del ledger con `is_reversed`). Todos piden `currency`
  (`ARS` o `USD`) y aceptan `from`/`to` (por defecto, el mes calendario actual
  en UTC, máximo 12 meses). `?export=csv` devuelve el CSV.
- **`notifications`**: `Notification` (usuario, evento, referencia, estado
  `pending|sent|failed`) y `NotificationPreference`. Cuatro eventos avisados por
  email: cuota por vencer, cuota vencida, inversión liquidada y alerta de
  presupuesto. Las apps emisoras (`loans`, `investments`, `budgets`) definen las
  señales y `notifications` tiene los receptores, que crean el aviso y encolan
  el envío con `transaction.on_commit`.
- **Celery**: app, worker, beat, tasks periódicas y su cobertura de tests.
- **Chequeo de salud**: `GET /health/` (fuera de `/api/v1/`, sin autenticación y
  sin throttle) devuelve 200 con `{"status": "ok"}` si la base responde un
  `SELECT 1` y 503 con `{"status": "unavailable"}` si no responde. No expone
  detalles internos ni secretos.

### 6.4 Estado verificado (2026-10-21, comandos del §10)

Verificación del cierre de la auditoría final (todos los comandos ejecutados
contra el código de este bloque):

| Chequeo | Comando | Resultado |
|---|---|---|
| Tests | `docker compose run --rm web python -m pytest -q` | **700 passed** |
| Cobertura total | `... pytest --cov=apps --cov-report=term` | **99%** (`ledger/services.py` 93%, `budgets/services.py` 99%, `loans/services.py` 99%, `investments/services.py` 99%, `offers/services.py` 97%, `notifications/*` 100%, `reports/selectors.py` 98%) |
| Cobertura de budgets | `... pytest apps/budgets --cov=apps.budgets.services --cov-fail-under=90` | **99%** en `budgets/services.py` (umbral de la CI: 90%) |
| Lint | `ruff check .` | All checks passed |
| Formato | `ruff format --check .` | 248 files already formatted |
| Límites entre apps | `lint-imports --cache-dir /tmp/import-linter-cache` | **28 kept, 0 broken** |
| Migraciones | `makemigrations --check --dry-run` | No changes detected |
| System checks | `manage.py check` | System check identified no issues (0 silenced) |
| OpenAPI | `spectacular --validate --fail-on-warn --file schema.yml` | **PASA: 0 errores, 0 warnings** (lo mismo que corre la CI) |
| `check --deploy` (producción) | `manage.py check --deploy --fail-level WARNING` con los settings de producción | **PASA: no issues (1 silenced)**; es el mismo paso que corre la CI |
| Auditoría de dependencias | `pip-audit .` (también `make audit`) | **No known vulnerabilities found** |
| Docker (desarrollo) | `docker compose up --build -d` | **5 servicios Up**: `db`, `redis`, `web`, `worker`, `beat`; los tres de la aplicación corren como `uid=1000(presto)` |
| Flujo real (desarrollo) | `curl` contra el `web` local | registro 201, login 200, KYC 201, depósito simulado 201, saldo 1500.00 ARS, reporte 200, sin token 401, sin `Idempotency-Key` 400 |
| Docker (producción, demo) | `docker compose -p presto-prod -f docker-compose.prod.yml --env-file .env.prod up -d --build` con `DEMO_MODE=true` | `db`, `redis` y `web` **healthy**, `worker` y `beat` Up; `/health/` 200, `/api/v1/meta/` 200 `{"mode":"demo","simulated_money":true}`, depósito simulado 201 y **suma de saldos por moneda = 0.00** |
| Bajada del stack de producción | `docker compose -p presto-prod -f docker-compose.prod.yml down -v` | contenedores, red y volúmenes eliminados (no queda ningún `presto-prod*`) |
| Suite end-to-end | `pytest tests/test_end_to_end.py` | 1 passed (ARS y USD, flujo completo, invariante del ledger) |
| CORS (stack de producción) | preflight `OPTIONS` con `Origin: https://presto-front.vercel.app` | 200 con `access-control-allow-origin: https://presto-front.vercel.app`, `authorization` permitido y **sin** `access-control-allow-credentials`; un origen no permitido no recibe el header |
| Depósito en producción (demo) | `manage.py shell` con `ledger.services.deposit` | 201, saldo 1000.00 ARS y **suma por moneda = 0.00** |
| arm64 | `docker buildx imagetools inspect` + `buildx build --platform linux/arm64` | `python:3.12-slim`, `postgres:16`, `redis:7-alpine` y `caddy:2-alpine` publican **linux/arm64**; la imagen del proyecto compila para arm64 y `uname -m` da `aarch64` |
| Concurrencia de producción | `docker compose -p presto-prod logs worker` | `concurrency: 2 (prefork)` (default del compose) |
| Simulación Northflank (local) | imagen única como `web` y como `worker` con `CELERY_EMBED_BEAT=true`, `DATABASE_URL` y `REDIS_URL` a un Postgres y un Redis de prueba | web con migraciones aplicadas y `/health/` **200 con el Host interno**; el resto de los endpoints siguen con 400 ante un Host desconocido; el worker levanta el beat embebido con el schedule del proyecto (4 tareas) y registra las 5 tasks; depósito simulado 1500.00 ARS con **suma por moneda = 0.00**; preflight CORS 200 con el origen permitido. Bajada con `docker compose -p presto-nf-test ... down -v` (sin rastros) |
| Contrato del esquema | `pytest tests/test_openapi_contract.py` | 55 passed: la paginación, el header `Idempotency-Key`, los parámetros y el CSV de los reportes, los errores (401 de cada operación protegida, 404 de un recurso ajeno, 409 de un duplicado) y el KYC nullable |
| Esquema versionado | `manage.py spectacular --file docs/openapi.yaml --validate --fail-on-warn` | 0 errores, 0 warnings; el test verifica que el archivo versionado es el que genera el código |
| Estáticos del admin | petición real a `/admin/` con el stack de producción | antes: 404 en `/static/admin/css/base.css`; ahora **200 text/css** (22 KB) |
| Parseo de URLs | `DATABASE_URL` con clave percent-encoded y `DB_SSLMODE` | `p@ss:w/rd` des-codificado y `OPTIONS={'sslmode': 'require'}`; sin `DATABASE_URL` el comportamiento de siempre |
| Worker | `docker compose logs worker` | `transport: redis://redis:6379/0`, `results: disabled://`, 5 tasks registradas, `ready.` |
| Beat | `celery -A config inspect conf` | 4 entradas: `mark_overdue_loans_diario` (00:05), `notify_installments_due_soon_diario` (00:10), `settle_investments_diario` (00:15) y `notify_overdue_installments_diario` (00:20) |
| Tareas en el worker | `docker compose logs worker` | 5 tasks registradas: `mark_overdue_loans`, `settle_investments`, `notify_installments_due_soon`, `notify_overdue_installments`, `send_notification_email` |
| Modo demo (stack de desarrollo) | `curl /api/v1/meta/` | `{"mode":"demo","simulated_money":true}` + cabecera `X-Presto-Mode: demo` |
| Modo demo (stack de producción) | el mismo arranque con `DEMO_MODE=true` | `DEMO_MODE=True`, `simulated=True`, `/api/v1/meta/` 200 y depósito simulado **201** |
| Endpoints de budgets (runtime) | `curl` contra el `web` local | crear categoría 201, listar 200 paginado, crear presupuesto 201, duplicado 409, sin token 401, detalle de categoría 200/404/401 |
| Endpoints de reports (runtime) | `curl` contra el `web` local | los 4 reportes 200, sin moneda 400, sin token 401, CSV con `text/csv` y `Content-Disposition` |
| Endpoints de notifications (runtime) | `curl` contra el `web` local | listado 200, preferencias GET 200 y PUT 200, sin token 401 |
| Compose de producción | `docker compose -f docker-compose.prod.yml config` | válido (5 servicios); con `--profile proxy` agrega `caddy` (80/443) y `web` no publica puertos |
| Backups | `docker compose -f docker-compose.prod.yml --profile backup run --rm backup` | dump comprimido de 12K; con `BACKUP_KEEP=1` conserva solo el más nuevo |
| Restauración | `gunzip -c <backup>.sql.gz \| psql` en una base de prueba | 28 tablas y las transacciones del ledger restauradas |
| Estado del repo | `git status` | limpio |

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
| D34 | `reports` es una app **sin modelos** ni migraciones, como `matching` | Es de solo lectura: no hay nada que persistir y el ledger sigue siendo la única fuente de verdad |
| D35 | Cada reporte es de **una sola moneda** y `currency` es obligatorio | AGENTS §6: no se mezclan ni se convierten importes |
| D36 | El "saldo pendiente" de un préstamo es la suma de las **cuotas pendientes** (capital e interés) | Es lo que falta pagar y lo que el prestamista va a cobrar; el interés pagado va aparte |
| D37 | El CSV exporta como máximo **10.000 filas** y neutraliza la inyección de fórmulas con un apóstrofo | Un reporte enorme no se descarga: responde 400. El `csv` de la stdlib alcanza, sin dependencias |
| D38 | Se agregaron selectores de lectura en las apps dueñas (`ledger`, `loans`, `budgets`) | La app dueña es la que conoce sus datos: `reports` solo usa `services.py`/`selectors.py` (AGENTS §5.2) |
| D39 | Los avisos se idempotentan con la unicidad de `(usuario, evento, referencia)` | El mismo evento no genera dos avisos, aunque el receptor corra dos veces (AGENTS §5.3) |
| D40 | Las señales las define la app emisora y los receptores viven en `notifications` | Es el patrón de AGENTS §5.3: la app emisora define la señal, la app interesada tiene el receptor |
| D41 | El envío se encola con `transaction.on_commit` | El email nunca corre dentro de la transacción que originó el evento: un fallo de SMTP no rompe ni el ledger ni la app emisora |
| D42 | La alerta de presupuesto deriva su identificador del presupuesto y del mes (`uuid5`) | El mismo presupuesto avisa **una sola vez por mes**, sin guardar nada extra |
| D43 | El email del destinatario sale de `identity.selectors.get_user_email` | Ninguna app importa los modelos de otra (AGENTS §5.2): el selector es la única vía |
| D44 | El **modo demo** se activa con `DEMO_MODE=true` (por defecto apagado) | Convierte el stack en una demostración: habilita el dinero simulado, permite el `E001` en producción solo en ese caso y agrega la cabecera `X-Presto-Mode: demo` |
| D45 | `GET /api/v1/meta/` es público y no aplica throttling | El frontend y quien diagnostique necesitan saber si el dinero es real sin token |
| D46 | Los booleanos de entorno se leen **sin distinguir mayúsculas** | El compose pasa `true` en minúscula y la comparación con `'True'` apagaba el modo demo sin avisar |
| D47 | El proxy con TLS (Caddy) vive bajo el perfil `proxy` del compose de producción | Si la plataforma ya da HTTPS, el proxy sobra; con el perfil activo es el único que publica 80/443 y `web` queda en la red interna |
| D48 | El backup diario de PostgreSQL es un servicio con el perfil `backup` | Un `pg_dump` comprimido con rotación, con el procedimiento de restauración en el script |
| D49 | El **CORS lo responde la aplicación** con `django-cors-headers` | El front vive en otro origen (Vercel) y la API tiene que mandar los headers herself: `CORS_ALLOWED_ORIGINS` viene del entorno como lista separada por comas, **nunca `*`**, vacío significa "ningún origen", y **no se permiten credenciales** (la autenticación viaja en `Authorization: Bearer`, que sí está permitido en el preflight). El middleware va primero en la pila, antes de cualquier middleware que pueda generar una respuesta, para que el preflight `OPTIONS` se conteste |
| D50 | La **concurrencia de producción se ajusta por entorno** | `GUNICORN_WORKERS` (web) y `CELERY_WORKER_CONCURRENCY` (worker) con defaults bajos (3 y 2). La VM de Oracle tiene 1 o 2 OCPU y 6 o 12 GB: con 6 GB, 2 y 2; con 12 GB, 4 y 4. **No hay límites de memoria**: matan el proceso a mitad de una operación de dinero |
| D51 | El stack es **multi-arquitectura** (`linux/arm64` y `linux/amd64`) | Las imágenes de producción (`python:3.12-slim`, `postgres:16`, `redis:7-alpine`, `caddy:2-alpine`) publican arm64 y el build del proyecto para arm64 funciona sin compilar nada |
| D52 | El despliegue documentado apunta a **Oracle Cloud (Ubuntu 24.04 ARM) + DuckDNS + Vercel** | La guía de `docs/deploy-demo.md` §8 tiene el paso a paso: Docker en Ubuntu, el **firewall interno** de la VM (las imágenes de Oracle bloquean el tráfico con iptables aunque la Security List esté abierta), DuckDNS, el `DOMAIN` de Caddy, el `.env.prod`, los perfiles `proxy` y `backup`, el superusuario, los datos de demo, la verificación con `curl` (salud, meta, depósito y preflight CORS), la actualización y la restauración de backups |
| D53 | La **misma imagen** sirve para el web y para el worker, según el comando | El entrypoint de la imagen arma el comando: `web` (gunicorn en `$PORT`, con `RUN_MIGRATIONS` opcional) o `worker` (celery, con `-B` si `CELERY_EMBED_BEAT=true`). El compose de producción no cambia: su comando por defecto sigue siendo el de siempre |
| D54 | El **health check se contesta antes de validar el `Host`** | Las plataformas lo llaman con la IP interna del servicio y Django responde 400 si el `Host` no está en `ALLOWED_HOSTS` (que tiene que quedar cerrado con el dominio público). El endpoint es público y solo dice si la base contesta |
| D55 | Las **URLs de las bases administradas se parsean con la stdlib** | `DATABASE_URL` y `REDIS_URL` entran tal cual las da la plataforma (la clave percent-encoded se des-codifica) y `DB_SSLMODE` agrega o pisa el `sslmode`. Sin `DATABASE_URL` el comportamiento no cambia |
| D56 | Los **estáticos los sirve la aplicación** con whitenoise | El admin del Django salía sin estilos en producción (404): no hay servidor de estáticos delante. La imagen los recolecta y whitenoise los sirve |
| D57 | El **esquema se corrige con hooks** de drf-spectacular, sin tocar el comportamiento | La paginación real, los errores de cada operación, la respuesta CSV de los reportes, el KYC nullable y la cabecera `X-Presto-Mode` se declaran en `apps/core/hooks.py` y `apps/core/openapi.py`: el esquema describe lo que la API ya hace y ningún endpoint cambia. **Ojo**: definir `POSTPROCESSING_HOOKS` **reemplaza** la lista de drf-spectacular, así que la de por defecto (la de los enums) queda incluida a mano |
| D58 | El **esquema versionado** es `docs/openapi.yaml` | El front lo consume de ahí y un test comprueba que es el mismo que genera el código: si alguien cambia la API y no lo regenera, la build falla |
| D59 | El **importe del movimiento** es el de la pata del usuario, con su signo | Un movimiento tiene varias patas: la que toca la billetera del usuario dice cuánto entró o salió. El listado muestra ese número (con signo ✓) porque es el saldo de la billetera ✓; el reporte de movimientos sigue mostrando el total del movimiento (sin signo ✓). Son dos números distintos y no se mezclan (ADR 0008 ✓) |
| D60 | Los dos listados **suman campos de solo lectura** (importe, moneda) | Es aditivo y retrocompatible ✓: el front puede leerlos sin romper nada ✓ y el backend no renombra ni saca ningún campo ✓ |

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
| P24 | El `ruff` del hook de pre-commit (v0.6.0) marcó `UP038` en `apps/reports/export.py` (`isinstance` con tupla) y el del contenedor no | Se adoptó la forma `isinstance(value, datetime | date)` (Python 3.10+), que pasa en las dos versiones |
| P25 | Los tests de `reports` para el reporte de préstamos necesitaban un `Offer` y no hay service para crearlos (los productos y las ofertas los da staff) | Se usan `offers.services.create_offer` (una **service**, la interfaz autorizada) desde los tests. El contrato de `import-linter` de `reports` no incluye `offers`: queda anotado en el ADR 0003 |
| P27 | El modo demo no se activaba en el stack de producción: el compose pasa `DEMO_MODE=true` (minúscula) y los settings comparaban con `'True'` | Los booleanos de entorno se leen sin distinguir mayúsculas (D46). El bug apareció en el arranque real del stack, no en los tests |
| P28 | Los tests heredaban `DEMO_MODE` del entorno del contenedor y fallaban (3 tests) | Los settings de test fijan `DEMO_MODE=False`: los tests son herméticos y activan el modo demo explícitamente |
| P29 | El primer backup dejó un archivo vacío cuando el `pg_dump` falló (faltaba la contraseña) | El script vuelca a un archivo temporal y solo lo renombra cuando termina: un dump fallido no deja un backup roto |
| P26 | Los tests de `budgets` e `investments` importaban los modelos de `notifications` | El contrato nuevo de `import-linter` lo detectó: los tests end-to-end se movieron a la app de `notifications` (cada app prueba su propio código) |
| P27 | La API de notificaciones respondía 500 en el entorno local: `relation "notifications_notificationpreference" does not exist` | Las migraciones nuevas no estaban aplicadas en la base de desarrollo (el `web` corre `migrate` al arrancar): se aplicaron y el servicio se reinició |
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
- **Modo demo**: se activa con `DEMO_MODE=true` (el compose de desarrollo ya
  lo trae). Habilita el dinero simulado, permite el `E001` en producción solo en
  ese caso, y `GET /api/v1/meta/` responde `{"mode": "demo", "simulated_money":
  true}`; todas las respuestas llevan `X-Presto-Mode: demo`.
- **Email**: sin `EMAIL_HOST` definido, el backend por defecto es el de
  **consola**: los avisos de las notificaciones salen en los **logs del worker**.
  Con `EMAIL_HOST` definido, el backend por defecto pasa a ser SMTP; un
  `EMAIL_BACKEND` explícito manda siempre. Está documentado en
  `docs/deploy-demo.md` y en `.env.prod.example`.
- **Sin implementar todavía**: `payments`
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

Resultado esperado: **700 passed**. Con cobertura:

```sh
docker compose run --rm web python -m pytest -v --cov=apps --cov-report=term-missing
```

La suite end-to-end (el flujo completo, en ARS y USD) va en su propio paquete:

```sh
docker compose run --rm web python -m pytest tests/test_end_to_end.py -v
```

### Lint, formato y límites entre apps

```sh
make lint      # ruff check . + ruff format --check . + import-linter
```

Equivalentes sueltos:

```sh
docker compose run --rm web ruff check .
docker compose run --rm web ruff format --check .
docker compose run --rm web lint-imports --cache-dir /tmp/import-linter-cache
```

> El `--cache-dir` es necesario desde que el contenedor corre como usuario sin
> privilegios: el proyecto viene montado como volumen del host y ahí no se
> puede escribir (ver `docs/audit-final.md` B-8). La cache de ruff ya apunta a
> `/tmp` por variable de entorno en el `Dockerfile`.

Auditoría de vulnerabilidades conocidas y chequeo de producción:

```sh
make audit      # pip-audit sobre las dependencias del proyecto

docker compose run --rm web bash -c "
  export DJANGO_SETTINGS_MODULE=config.settings.production
  export DJANGO_SECRET_KEY=\"\$(python -c 'import secrets; print(secrets.token_urlsafe(50))')\"
  export DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
  export DJANGO_DEBUG=0
  export REDIS_URL=redis://localhost:6379/0
  python manage.py check --deploy --fail-level WARNING"
```

> Los dos comandos corren también en la CI (job *quality*). El
> `check --deploy` falla con cualquier aviso de seguridad; el único silenciado
> es el preload del HSTS (`security.W021`), que es irreversible y la decisión
> es del cliente.

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
| `apps.loans.tasks.notify_installments_due_soon` | todos los días a las 00:10 | avisa al prestatario de las cuotas que vencen en ≤3 días |
| `apps.loans.tasks.notify_overdue_installments` | todos los días a las 00:20 | avisa al prestatario y al prestamista de las cuotas vencidas |
| `apps.investments.tasks.settle_investments` | todos los días a las 00:15 | liquida las posiciones vencidas (capital + interés) |

El aviso de la inversión liquidada sale de la liquidación y el de la alerta de
presupuesto, de categorizar un movimiento: no son tareas del beat.

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

### Modo demo

```sh
curl -s http://127.0.0.1:8000/api/v1/meta/     # {"mode":"demo","simulated_money":true}
docker compose logs -f worker                    # los avisos salen acá
```

Con `DEMO_MODE=true` el dinero es simulado y el check `ledger.E001` lo permite.
Sin `EMAIL_HOST` el backend de email es el de consola; definiéndolo pasa a ser
SMTP. El detalle (incluido el despliegue en una plataforma con Docker Compose, el
proxy opcional y los backups) está en `docs/deploy-demo.md`.

### El esquema OpenAPI

```sh
# Regenerar el esquema versionado (el que consume el front)
docker compose run --rm web python manage.py spectacular \
  --file docs/openapi.yaml --validate --fail-on-warn

# Los tests de contrato (compara el esquema con la API real)
docker compose run --rm web python -m pytest tests/test_openapi_contract.py -v
```

### Los dos listados con los datos que faltaban

```sh
# El listado de movimientos: el importe (con signo) y la moneda
curl -s http://127.0.0.1:8000/api/v1/ledger/transactions/ -H "Authorization: Bearer $TOKEN"

# El listado de posiciones: la moneda del producto
curl -s http://127.0.0.1:8000/api/v1/investments/positions/ -H "Authorization: Bearer $TOKEN"
```

El criterio del importe (la pata de la billetera del usuario, con su signo) está
en [ADR 0008](docs/adr/0008-importe-del-movimiento-en-el-listado.md) ✓.

### Despliegue en plataformas administradas

La imagen es única: el **entrypoint** (`deploy/entrypoint.sh`) arma el comando
según el rol (`web` o `worker`) y las variables de entorno.

```sh
# El web
sh deploy/entrypoint.sh web          # gunicorn en $PORT (8000), workers de GUNICORN_WORKERS
# El worker (con el beat embebido)
sh deploy/entrypoint.sh worker       # celery con --concurrency y -B si CELERY_EMBED_BEAT=true
```

Las guías de despliegue están en:

- [docs/deploy-demo.md](docs/deploy-demo.md): modo demo, producción en general,
  **Oracle Cloud (Ubuntu 24.04 ARM) + DuckDNS + Vercel** y la compatibilidad
  arm64.
- [docs/deploy-northflank.md](docs/deploy-northflank.md): **Northflank (plan
  gratuito) + Vercel**: dos servicios, dos bases administradas y dos cron jobs.

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

### `budgets`

| Método | Ruta | Descripción |
|---|---|---|
| GET, POST | `/api/v1/budgets/` | Lista los presupuestos propios / crea uno por categoría, período y moneda |
| GET, PATCH | `/api/v1/budgets/{budget_id}/` | Detalle / actualiza el límite o el umbral de un presupuesto propio |
| GET | `/api/v1/budgets/{budget_id}/status/` | Gasto del período, restante y si la alerta se dispara |
| GET, POST | `/api/v1/budgets/categories/` | Lista las categorías propias / crea una categoría |
| GET, PATCH | `/api/v1/budgets/categories/{category_id}/` | Detalle / renombra una categoría propia (404 si es de otro) |
| GET, POST | `/api/v1/budgets/expenses/` | Lista los gastos categorizados / categoriza un movimiento del ledger |

El importe del gasto **no se guarda**: sale del ledger (ADR 0002).

### `reports`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/reports/spending/` | Gasto por categoría en el rango (parámetros: `currency`, `from`, `to`) |
| GET | `/api/v1/reports/loans/` | Préstamos como prestatario y como prestamista (parámetro: `currency`) |
| GET | `/api/v1/reports/investments/` | Posiciones, capital invertido e interés (parámetro: `currency`) |
| GET | `/api/v1/reports/movements/` | Movimientos del ledger paginados, con `is_reversed` (parámetros: `currency`, `from`, `to`) |

Los cuatro aceptan `?export=csv` para bajar el CSV (tope de 10.000 filas; las
celdas que empiezan por `=`, `+`, `-` o `@` se neutralizan). `currency` es
obligatorio (`ARS` o `USD`), `from`/`to` van en ISO y por defecto cubren el mes
calendario actual en UTC, con un máximo de 12 meses de rango.

### `notifications`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/notifications/` | Lista los avisos del usuario (paginado) |
| GET | `/api/v1/notifications/preferences/` | Preferencias de avisos (por defecto, todo habilitado) |
| PUT | `/api/v1/notifications/preferences/` | Activa o desactiva un tipo de aviso |

### Fuera de `/api/v1/`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/schema/` | Esquema OpenAPI (JSON) |
| GET | `/api/docs/` | Swagger UI |
| GET | `/health/` | Chequeo de estado (público; 503 si la base no responde) |
| GET | `/api/v1/meta/` | Modo de la instancia (`demo` o `normal`) y si el dinero es simulado |
| — | `/admin/` | Django admin (solo staff): usuarios, perfiles, KYC, cuentas, transacciones, asientos, productos y posiciones de inversión |

---

## 11. Próximos pasos

Orden real de lo que falta, de mayor a menor prioridad.

1. **Bloque 7 — `payments` con proveedor real**: es la tarea recomendada. Hoy
   los depósitos y retiros son **simulados** y están apagados en producción por
   el system check `ledger.E001` (salvo en modo demo). Depende de la decisión O1
   (qué proveedor), que sigue abierta (§11.1).
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
6. ✅ **Documentación**: `docs/architecture.md` escrito (apps, capas, invariantes
   del dinero, recorrido de un movimiento) y los ADR que faltaban ya están
   (0005 saldo desnormalizado, 0006 doble entrada con trigger diferido, 0007
   orden de las apps). El `README.md` quedó al día (estructura real, endpoints,
   tareas de beat, modo demo) y hay tests que impiden que vuelva a quedar viejo.
   Queda pendiente **aplicar** el texto propuesto para `AGENTS.md` (está en
   `docs/agents-changelog-proposal.md`; `AGENTS.md` no se toco).
7. ✅ **`IsKycApproved` en las vistas que mueven dinero**: aplicado a los
   movimientos del ledger, la publicación de ofertas, la aceptación de préstamos,
   el pago de cuotas y la apertura de posiciones de inversión. Los `GET` no cambian
   y los services siguen validando KYC.
8. **Cobertura de vistas por debajo de 100%**: `budgets/views.py` 87%,
   `loans/views.py` 93%, `investments/views.py` 93%. No es un bloqueo (los
   umbrales de AGENTS §10 son 90% en `ledger`/`budgets` y 80% general).
9. ✅ **Agregar `budgets` al umbral de cobertura del 90%** en la CI: ya está
   (gate de `apps.budgets.services`).
10. **Envío del esquema OpenAPI al frontend**: queda pendiente. El **CORS ya
    está resuelto** ✅: `django-cors-headers` es dependencia de producción, el
    middleware responde el preflight y `CORS_ALLOWED_ORIGINS` viene del entorno
    (sin `*`, vacío = ningún origen, sin credenciales).
11. **Decisiones técnicas que siguen abiertas** (ver `docs/audit-final.md` §5):
    `sentry-sdk` como dependencia, imágenes fijadas a digest y el reintento o el
    resumen de los avisos fallidos. **Ya resueltas**: `pip-audit` en la CI, el
    `check --deploy` en la CI y el `CheckConstraint` de moneda del ledger
    (2026-10-21), el **CORS real** con `django-cors-headers` y los **estáticos
    del admin** con `whitenoise` (2026-10-22).
12. **El contrato del frontend**: quedó todo resuelto ✓ (el esquema ✓ y los
    dos listados ✓). Queda **confirmar con el front** el criterio del importe
    con signo del listado de movimientos ✓ (ADR 0008 ✓) y que la moneda de las
    posiciones alcanza ✓.
13. **Northflank**: la guía está escrita y el entorno se simuló localmente ✓,
    pero **no se pudo comprobar la consola de la plataforma** (el plan, los
    límites, los backups del add-on, el panel de logs): todo eso está marcado
    como "verificar en la UI" en `docs/deploy-northflank.md` ✓. Falta además
    el **cron job** que reemplace al beat embebido si el plan no lo permite
    (hoy el worker lleva el beat ✓).

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

- `reports`: **resuelto** (Bloque 6c): el cliente aprobó los cuatro reportes,
  sus parámetros, el rango máximo, el formato CSV y el tope de filas (ADR 0003).
- `notifications`: **resuelto** (Bloque 6d): el cliente aprobó los cuatro
  eventos, el canal (email), la idempotencia, las preferencias y la API (ADR
  0004). Queda sin definir el reintento de los avisos fallidos y el resumen de
  varios avisos en un mismo email.

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
| 2026-10-21 | **Modo demo completo**: `DEMO_MODE` (nuevo setting, apagado por defecto) habilita el dinero simulado y el `E001` lo permite solo en ese caso; `GET /api/v1/meta/` es público y devuelve el modo y si el dinero es simulado; el middleware agrega `X-Presto-Mode: demo` a todas las respuestas; el compose de producción pasa `DEMO_MODE`, `LEDGER_SIMULATED_DEPOSITS_ENABLED` y `CORS_ALLOWED_ORIGINS` por entorno, suma el proxy Caddy con TLS automático bajo el perfil `proxy` (único con 80/443; `web` no publica puertos) y el backup diario de PostgreSQL con rotación bajo el perfil `backup`; `docs/deploy-demo.md` documenta el modo demo, el proxy, los backups y los pasos de despliegue. **620 tests pasan**. Verificado en runtime: el stack de desarrollo y el de producción responden `mode=demo` con la cabecera, el depósito simulado devuelve 201, el backup genera un dump de 12K con rotación y la restauración recupera las 28 tablas. Se corrigió un bug real: los booleanos de entorno se leían con comparación case-sensitive y el compose pasa `true` en minúscula. |
| 2026-10-21 | **Modo demo de email**: sin `EMAIL_HOST` definido el backend por defecto es el de consola, así que los avisos de las notificaciones salen en los logs del worker; con `EMAIL_HOST` definido pasa a ser SMTP y un `EMAIL_BACKEND` explícito manda siempre. Cubierto por `apps/core/tests/test_email_backend.py` (3 tests) y documentado en `docs/deploy-demo.md` y `.env.prod.example`. Además, `.env.prod` quedó ignorado por `.gitignore`. |
| 2026-10-21 | **Bloque 6d implementado: app `notifications`** en 7 commits: `cc1d359` app con los modelos `Notification` y `NotificationPreference` y los services idempotentes, `a9bb4a9` tarea de envío de email y configuración SMTP por entorno, `454fa87` señales y tareas diarias de cuota por vencer y vencida, `1ca99a3` aviso de la inversión liquidada, `0ae71d3` alerta de presupuesto con identificador derivado presupuesto+mes, `79d0a77` API de listado y preferencias, `a4e51d2` contratos de import-linter, gate de cobertura del 90% y ADR 0004. **608 tests pasan**, 28 contratos de import-linter y el 99% de cobertura de la app. Verificado en runtime real: los dos endpoints responden 200/401, el worker registra las 5 tasks y el beat tiene 4 entradas. El contrato nuevo detectó dos violaciones reales en tests de otras apps, corregidas. |
| 2026-10-21 | **Bloque 6c implementado: app `reports`** en 7 commits: `4bb5fe7` app y validación de parámetros, `b68975f` reporte de movimientos (+ selector de rango en `ledger`), `593a34b` reporte de spending (+ selector de gastos en `budgets`), `5fef54f` reporte de préstamos (+ selector de cuotas en `loans`), `2a75626` reporte de inversiones, `73b62f1` exportación CSV con neutralización de fórmulas y tope de 10.000 filas, `9599982` contratos de import-linter, umbral de cobertura del 90% en la CI y ADR 0003. **556 tests pasan**, 22 contratos de import-linter, cobertura de `reports` del 99%. Verificado en runtime real contra el `web` local: los cuatro reportes 200, sin moneda 400, sin token 401 y el CSV con `text/csv` y `Content-Disposition`. |
| 2026-10-21 | **Tres mejoras chicas**: `6efb50f` aplica `IsKycApproved` a las vistas que mueven dinero (movimientos del ledger, publicar oferta, aceptar préstamo, pagar cuota, abrir posición) con un mixin que solo afecta los métodos que no son de lectura; `89d6f49` agrega `GET /health/` (200 `{"status": "ok"}` / 503 `{"status": "unavailable"}`, público y fuera del esquema OpenAPI); `45eefa8` crea `docker-compose.prod.yml` (db, redis, web con gunicorn, worker y beat; sin puertos de db/redis, secretos por entorno, `restart: unless-stopped`, healthchecks y volúmenes persistentes) y ajusta `SECURE_PROXY_SSL_HEADER` en producción para que el chequeo de salud no reciba un 301. **504 tests pasan**, cobertura 98,81%. El stack de producción se levantó de verdad: `db`, `redis` y `web` healthy, `worker` y `beat` Up y `/health/` respondiendo 200. |
| 2026-10-21 | **Bloque 6b implementado: app `budgets`** en 7 commits: `29f9b96` selector de patas y reversión en el ledger, `82793c2` `ledger_transaction_id` en `Installment`/`Loan` + selector de desglose, `e18b0a7` app con `Category` y `Budget`, `91b3858` service de categorización, `9f1a546` cálculo del gasto acumulado por categoría y moneda, `9125429` API y OpenAPI sin warnings, `92f2e1a` contratos de import-linter, umbral de cobertura del 90% en la CI y ADR 0002. **491 tests pasan**, cobertura total 98,85% y `budgets/services.py` al 100%. Migraciones: `budgets.0001_initial`, `budgets.0002_expense` y `loans.0002_installment_ledger_transaction_id_and_more`. Los endpoints quedaron verificados en runtime real contra el `web` local (crear categoría 201, listar 200 paginado, crear presupuesto 201, duplicado 409, sin token 401). |
| 2026-10-21 | **Reescritura del documento** para traspaso a Claude: §2 con el stack real (Celery 5.6.3 en uso), §3 con el árbol real (celery.py, tasks.py, ADR 0001), §5 con las reglas de API/seguridad/testing, §6.3 con los módulos verificados, §6.4 con la tabla de verificaciones comprobadas hoy (407 tests, 99,07% de cobertura, 11 contratos, 5 servicios Up), §7 con D19-D24 (Celery), §8 con P15-P17, §9 corregido (una billetera por moneda; depósitos simulados apagados en local), §10 con los comandos reales (`docker compose ps` muestra 5 servicios), §11 con el bloque 6b como tarea recomendada y §11.3 con el contexto técnico de `budgets`, §11.4 con los huecos de especificación de `reports`/`notifications`, **§13 nueva con las reglas para Claude** y §14 el registro. Se eliminaron datos obsoletos (conteo de commits, "374 passed", "3 servicios Up", `docs/adr/` vacío) sin perder decisiones vigentes. |
| 2026-10-21 | **Auditoría final y pulido del backend** (14 commits): auditoría de solo lectura en `docs/audit-final.md` (0 críticos, 2 altos, 9 medios y 8 bajos, con la evidencia de cada uno y una sección "Requiere decisión" con recomendación) y corrección de todo lo crítico, alto y medio, con TDD: validadores de contraseña de Django activos (AGENTS §9.5), HSTS en producción (AGENTS §9.4), `update_offer`/`expire_offer` con `transaction.atomic()` y `select_for_update()`, contenedores de la aplicación corriendo como el usuario `presto` (uid 1000), health check de producción mandando un `Host` permitido, test del endpoint de detalle de categoría, test de concurrencia de la categorización de gastos, test de concurrencia de la actualización de ofertas, suite end-to-end del flujo completo (registro → login → KYC → depósito → oferta → préstamo → cuota → inversión → reportes → avisos, en ARS y USD, verificando que la suma de saldos por moneda sea 0), `docs/architecture.md`, ADR 0005 (saldo desnormalizado), 0006 (doble entrada con trigger diferido) y 0007 (orden de las apps), README al día y `.env.example` con todas las variables. **655 tests pasan**, 28 contratos de import-linter, cobertura del 99%, OpenAPI sin warnings y arranque real verificado de los stacks de desarrollo y de producción (este último con `DEMO_MODE=true` y luego bajado con `down -v`). `AGENTS.md` **no** se modificó: el texto propuesto para su §17 quedó en `docs/agents-changelog-proposal.md`. |
| 2026-10-21 | **Autorizaciones del desarrollador (4 commits)**: (1) `docs(agents)` aplicó el texto de `docs/agents-changelog-proposal.md` **solo en el registro de la §17** de `AGENTS.md` (bloque 6a, bloque 6b, modo demo, correcciones de la auditoría y documentación); las §§7, 15 y 4 no se tocaron. (2) `chore(deps)` agregó `pip-audit` como dependencia de desarrollo (pyproject, imagen y lista de la CI) con un paso en la CI que falla si hay vulnerabilidades conocidas, más el target `make audit`: **las dependencias del proyecto están limpias** (la auditoría previa solo mostró avisos en el propio `pip`, que la CI actualiza). El repo **no tiene lock file**, así que no había nada que fijar ahí. (3) `ci` agregó `manage.py check --deploy --fail-level WARNING` con los settings de producción (clave secreta aleatoria en el paso); el único aviso que quedaba, el preload del HSTS (`security.W021`), quedó silenciado en `production.py` con la razón escrita al lado, porque el preload es irreversible y la decisión es del cliente. (4) `feat(ledger)` agregó el `CheckConstraint` de moneda (`ARS`/`USD`) a `Account` y `LedgerEntry` con la migración `ledger.0003`: la base ya no acepta `EUR` ni `ars` en minúscula, y los triggers, la inmutabilidad y la idempotencia siguen funcionando. **662 tests pasan**. `docs/audit-final.md` §5 quedó con el estado de cada decisión. |
| 2026-10-22 | **CORS + despliegue en Oracle Cloud (4 commits)**: `feat(core)` habilitó el CORS real con `django-cors-headers` (dependencia de producción, middleware primero en la pila, `CORS_ALLOWED_ORIGINS` desde el entorno sin `*` y sin credenciales, 8 tests nuevos); `docs(deploy)` verificó y documentó la compatibilidad **arm64** (las cuatro imágenes de producción publican `linux/arm64` y la imagen del proyecto compila para arm64); `chore(infra)` hizo configurable la concurrencia de producción (`GUNICORN_WORKERS` y `CELERY_WORKER_CONCURRENCY`, defaults 3 y 2, recomendados 2/2 para 6 GB y 4/4 para 12 GB, sin límites de memoria); `docs(deploy)` escribió la guía **Oracle Cloud (Ubuntu 24.04 ARM) + DuckDNS + Vercel** (Docker, swap opcional, el firewall interno de la VM con iptables, DuckDNS y `DOMAIN`, `.env.prod`, perfiles `proxy` y `backup`, superusuario y datos de demo, verificación con `curl`, actualización y restauración de backups). **672 tests pasan**. Verificado en runtime con el stack de producción y `DEMO_MODE=true`: `/health/` 200, `/api/v1/meta/` 200 `mode=demo`, preflight CORS 200 con el origen permitido, depósito simulado con la suma por moneda en 0.00 y el worker con `concurrency: 2`. |
| 2026-10-22 | **Despliegue en Northflank (7 commits)**: `feat(core)` dejó el parseo de las URLs de conexión en la stdlib (`DATABASE_URL` y `REDIS_URL` con `DB_SSLMODE`, parseo propio y sin `dj-database-url`); `feat(deploy)` agregó el **entrypoint de la imagen** (roles `web` y `worker`, puerto `$PORT`, `RUN_MIGRATIONS`) y el **beat embebido** (`CELERY_EMBED_BEAT`, con la restricción de una sola réplica); `feat(core)` hizo que el **health check** se conteste antes de validar el `Host` (las plataformas lo llaman con la IP interna); `feat(core)` habilitó **whitenoise** para que el **admin cargue sus estilos** (antes 404, verificado con una petición real); `fix(deploy)` movió el archivo del schedule del beat al directorio que el contenedor puede escribir (lo encontró la simulación local); `chore`/`docs` actualizaron los recursos recomendados (1 y 1 para los planes gratuitos) y escribieron `docs/deploy-northflank.md`. **700 tests pasan**. Verificado con una simulación local del entorno (imagen única como web y como worker, base y redis de prueba, beat embebido): migraciones aplicadas, `/health/` 200 con el Host interno, el beat con el schedule del proyecto, el depósito simulado con la suma por moneda en 0.00 y el preflight CORS 200. **No verificado**: la consola de Northflank (el plan, los límites, los backups del add-on, los logs), marcado como "verificar en la UI" en la guía. |
| 2026-10-22 | **El esquema OpenAPI describe la API real (6 commits)**: el frontend mandó sus diferencias (`docs/backend-contract.md`, versionado en `49054e8`) y el esquema se corrigió por grupos: la **paginación real** de cada listado (`{count, next, previous, results}` y `{next, previous, results}` por cursor, con `investments/products/` que antes se declaraba como array), el header **`Idempotency-Key`** obligatorio de las tres operaciones que mueven dinero, el **body del refresh**, los **parámetros y la respuesta CSV de los cuatro reportes**, los **errores de cada operación** (401, 403 `permission_denied` del KYC, 404, 409 y 400, con el formato de AGENTS §8), el **KYC nullable** y la cabecera **`X-Presto-Mode`**. Todo con hooks de drf-spectacular y serializers de documentación: **ningún endpoint cambió de comportamiento** ✓. La suite de contrato (`tests/test_openapi_contract.py`) llama a la API real y compara cada respuesta con lo declarado ✓, y un test comprueba que el `docs/openapi.yaml` versionado es el que genera el código ✓. Los tres huecos de **comportamiento** (el importe de los movimientos, la moneda de las posiciones y la respuesta vacía del KYC) quedaron en `docs/audit-final.md` §5 con la recomendación ✓. **755 tests pasan** |
| 2026-10-22 | **Los dos listados con los datos que faltaban (3 commits)**: `feat(ledger)` agregó al listado de movimientos el **importe** (la pata de la billetera del usuario, con su signo: un crédito suma y un débito resta ✓) y la **moneda** ✓, y `feat(investments)` agregó al listado de posiciones la **moneda** del producto ✓. Los dos son **aditivos** (solo lectura ✓, sin quitar ni renombrar nada ✓), no tocan el schema, los triggers, la inmutabilidad ni la idempotencia del ledger ✓, y **no hacen N+1** ✓ (los movimientos usan los asientos que el listado ya precargaba ✓ y las posiciones el `select_related` del producto ✓; hay tests que comparan la cantidad de consultas ✓). El criterio del importe quedó documentado en el **ADR 0008** ✓. `fix(schema)` declaró en el esquema la respuesta **vacía** de `GET /api/v1/kyc/` (sin cambiar su comportamiento ✓). `docs/backend-contract.md` quedó actualizado para el front ✓ y `docs/audit-final.md` §5 marca D-10, D-11 y D-12 como resueltos ✓. **772 tests pasan** |
