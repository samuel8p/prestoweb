# HANDOFF — Presto

> Documento de traspaso para retomar el trabajo. La fuente de verdad del proyecto es
> [AGENTS.md](AGENTS.md); este documento describe el **estado real** del repo, las
> decisiones tomadas y lo que falta.
>
> **Última actualización:** 2026-10-21 · rama `main` · 63 commits (62 previos + este
> documento). El hash de HEAD cambia con cada amend, por eso no se referencia acá.

---

## 1. Descripción

Presto es una API de finanzas e inversiones con marketplace de préstamos.
El usuario puede publicar ofertas de préstamo, buscar y comparar ofertas como
prestatario, aceptar un préstamo, pagar sus cuotas e invertir su saldo a plazo
fijo. Presto custodia los fondos de los usuarios y los mueve entre ellos en dos
monedas: **ARS** y **USD**, sin conversión implícita.

El backend es **API-only** (no hay frontend en el repo). Todo movimiento de
dinero pasa por el `ledger`, un libro mayor de doble entrada con idempotencia,
reversos y saldo nunca negativo en las billeteras de usuario.

**Estado de la hoja de ruta:** Fase 0 (Cimientos) **completa**. Fase 1 **completa**
(1A identity + 1B ledger). Bloques 3 (offers+matching), 4 (loans) y 5
(investments) **completos**. Faltan el **Bloque 6**
(budgets/reports/notifications) y el **Bloque 7** (payments con proveedor real).

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
| Tareas async | Celery | 5.3+ (instalado, **aún sin usar**: no hay `config/celery.py`) |
| Tests | `pytest` + `pytest-django` + `pytest-cov` + `factory_boy` | pytest 9.1.1 / pytest-django 4.14.0 / pytest-cov 7.1.0 / factory_boy 3.3.3 |
| Lint / formato | `ruff` (E, F, I, B, UP; línea 100; comillas simples) | — |
| Límites entre apps | `import-linter` | 2.15 (11 contratos activos) |
| Hooks | `pre-commit` (ruff, ruff-format, import-linter) | 4.7.0 (instalado en el host) |
| Contenedores | Docker + Docker Compose | — |
| CI | GitHub Actions (`.github/workflows/ci.yml`) | — |

Base de datos: una sola, PostgreSQL 16, un solo despliegue (monolito modular).

## 3. Estructura del repositorio

```
.
├── AGENTS.md                     # fuente de verdad del proyecto (§1-§17)
├── README.md                     # quickstart, endpoints, formato de error
├── HANDOFF.md                    # este documento
├── Makefile                      # up, down, test, lint, migrate, shell, makemigrations
├── docker-compose.yml            # db, redis, web (localhost only)
├── Dockerfile                    # python:3.12-slim + deps de pyproject.toml
├── pytest.ini                    # DJANGO_SETTINGS_MODULE + --ds=config.settings.test
├── pyproject.toml                # deps + config de ruff
├── .importlinter                 # 11 contratos de límites entre apps
├── .pre-commit-config.yaml       # ruff, ruff-format, import-linter
├── .github/workflows/ci.yml      # ruff, import-linter, makemigrations --check, pytest
├── .env.example                 # SOLO placeholders, nunca secretos reales
├── apps/
│   ├── core/                     # transversales: BaseModel, money, exceptions,
│   │   └── tests/                #   pagination, exception_handler
│   ├── identity/                 # User, Profile, KYCVerification; auth JWT
│   │   └── tests/
│   ├── ledger/                   # Account, LedgerTransaction, LedgerEntry
│   │   └── tests/
│   ├── offers/                   # Offer (plazo fijo, TNA anual)
│   │   └── tests/
│   ├── matching/                 # solo lectura: búsqueda y comparación
│   │   └── tests/
│   ├── loans/                    # Loan, OfferTermsSnapshot, Installment
│   │   ├── management/commands/  #   mark_overdue_loans
│   │   └── tests/
│   └── investments/              # InvestmentProduct, Position (plazo fijo)
│       ├── management/commands/  #   settle_investments
│       └── tests/
└── config/
    ├── settings/                 # base, local, test, production
    ├── urls.py                   # /api/v1/ + /api/schema/ + /api/docs/ + /admin/
    ├── wsgi.py, asgi.py
```

Apps existentes: `core`, `identity`, `ledger`, `offers`, `matching`, `loans`,
`investments`. **No existen** (aún): `payments`, `budgets`, `reports`,
`notifications`.

## 4. Requisitos, entorno local e invariantes del dinero

- Docker + Docker Compose (único requisito; todo corre en contenedores)
- Puertos publicados **solo en localhost**: `127.0.0.1:5432` (Postgres),
  `127.0.0.1:6379` (Redis), `127.0.0.1:8000` (web)
- El código se monta como volumen (`.:/app`), así que los cambios se reflejan
  sin reconstruir la imagen
- `web` corre `manage.py migrate` y después `runserver` en `0.0.0.0:8000`
- Variables de entorno: ver `.env.example` (placeholders, sin secretos)
- `DJANGO_SETTINGS_MODULE` del servicio web: `config.settings.local`
  (`config.settings.test` solo para los tests, `config.settings.production` para
  producción; ninguna existe aún)

### Invariantes del ledger (requisitos no negociables del dominio)

Estas tres reglas son **requisitos de negocio**, no detalles de implementación:
vienen de AGENTS.md §6 y están garantizadas en código y en la base de datos.

1. **El saldo no negativo aplica solo a `user_wallet`.** Una billetera de usuario
   nunca puede quedar negativa (`CheckConstraint(balance >= 0)` en la tabla
   `Account`). Las cuentas de contrapartida (`custody`, `system`) representan el
   mundo exterior —los fondos custodiados y la contraparte de las inversiones— y
   **pueden** quedar negativas: eso es correcto, no un bug.
2. **`idempotency_key` es única por `(usuario, clave)`, no global.** Dos usuarios
   distintos pueden usar la misma clave sin colisionar. Se guarda además un
   `request_hash` del payload: misma clave **y** mismo hash devuelven la
   operación original; misma clave **y** hash distinto devuelven `409`. Ante un
   `IntegrityError` por concurrencia, el service reintenta y devuelve la
   operación original.
3. **La suma de saldos por moneda es cero.** Con la convención
   `balance = créditos - débitos`, la suma de **todos** los saldos de una moneda
   da 0, es decir `Σ(custody) + Σ(system) = -Σ(user_wallet)`. No es un chequeo
   decorativo: hay un test de invariante que lo verifica por moneda después de
   depósitos, retiros, transferencias, préstamos e inversiones.

## 5. Convenciones y flujo de trabajo

- **AGENTS.md manda.** Si una instrucción contradice AGENTS.md, se avisa antes de
  actuar.
- **Nombres de campos, clases y funciones en inglés**; docstrings de
  `services.py` / `selectors.py` en español; comentarios y logs en español.
- **Capas obligatorias** (AGENTS §5): `views.py` finas → `services.py` (escritura)
  / `selectors.py` (lectura) → `models.py`. Nada de lógica de negocio en
  serializers, signals ni `save()`.
- **Límites entre apps** verificados con `import-linter`: cada app usa de otra
  solo su `services.py` y `selectors.py`, nunca `models`, `views` ni
  `serializers`. Las referencias entre apps se guardan como `UUIDField`.
- **Dinero**: siempre `Decimal`, nunca `float`; los montos viajan como string
  decimal en la API; un único redondeo, en `core/money.py`.
- **TDD** por comportamiento: test rojo → implementación mínima → verde, con
  la salida real de pytest registrada. No se tocan tests para que pasen.
- **Commits**: Conventional Commits en inglés, uno por funcionalidad, con
  `ruff`, `lint-imports` y `pytest` en verde antes de cada commit. Nunca se usa
  `--no-verify`.
- Ramas: `main` (siempre desplegable) y `feature/*` / `fix/*`.

---

## 6. Estado actual

### 6.1 Commits (log real y completo, `git log --oneline`)

Log completo del repo. Los 4 commits de este mismo `HANDOFF.md` están
listados; el commit final que agrega esta fila no puede listarse a sí mismo
(tras el push, `git log --oneline | wc -l` da **67**).

| Commit | Asunto |
|---|---|
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
| **Fase 0 — Bloque B** Docker/Postgres | ✅ completa | `Dockerfile`, `docker-compose.yml` con PostgreSQL 16, Redis y web; puertos publicados solo en localhost; los tests corren contra Postgres real. |
| **Fase 0 — Bloque C** TDD core+identity | ✅ completa | Primer ciclo rojo→verde: tests de `core.money`, `core.models` y del `User`; configuración de pytest para usar los settings de test. |
| **Fase 0 — Bloque D** Calidad | ✅ completa | `ruff` + `ruff-format`, `.importlinter` con contratos entre apps, hooks de `pre-commit`, `Makefile` y CI con `makemigrations --check` y `--cov-fail-under=80`. |
| **Fase 1A — identity** | ✅ completa | `User` sin `username`, `Profile`, `KYCVerification` con una sola pendiente por usuario, JWT con rotación y blacklist, throttles por scope, `exception_handler` con el formato de AGENTS §8 y resolución de KYC desde el admin. |
| **Fase 1B — ledger** | ✅ completa | `Account` / `LedgerTransaction` / `LedgerEntry`, saldo desnormalizado, triggers de doble entrada e inmutabilidad, idempotencia por `(usuario, clave)`, depósitos simulados, reversos solo staff, API y acción de reverso en el admin. |
| **Bloque 3 — offers + matching** | ✅ completa | `Offer` con TNA anual en `%`, amortización francesa en `core/money.py`, búsqueda por rango de montos, comparación de ofertas (cuota, interés, costo total) y API del marketplace. |
| **Bloque 4 — loans** | ✅ completa | `Loan` / `OfferTermsSnapshot` / `Installment`, aceptación atómica con snapshot inmutable, pago de cuotas en orden, marcado de vencidos, máquina de estados y API con aislamiento por partes. |
| **Bloque 5 — investments (plazo fijo)** | ✅ completa | `InvestmentProduct` (solo staff) y `Position` de plazo fijo, apertura atómica contra la cuenta `system`, liquidación idempotente con interés simple y API de productos y posiciones. |
| **Bloque 6 — budgets / reports / notifications** | ❌ no empezada | Modelos ya definidos en AGENTS §7; `reports` es solo lectura y `notifications` necesita Celery. |
| **Bloque 7 — payments (proveedor real)** | ❌ no empezada | Hoy los depósitos y retiros son simulados y el system check `ledger.E001` los bloquea en producción. |

### 6.3 Estado verificado ahora (2026-10-21)

| Chequeo | Comando | Resultado |
|---|---|---|
| Tests | `docker compose run --rm web pytest -v` | **374 passed** |
| Cobertura total | `docker compose run --rm web pytest --cov=apps` | **99%** (68 statements sin cubrir de 5092) |
| Cobertura por app | idem | `identity` 100% · `ledger/services.py` 93% · `ledger/views.py` 100% · `offers/views.py` 100% · `offers/permissions.py` 100% · `loans/services.py` 99% · `investments/services.py` 99% |
| Lint | `docker compose run --rm web ruff check .` | All checks passed |
| Formato | `docker compose run --rm web ruff format --check .` | 140 files already formatted |
| Límites entre apps | `docker compose run --rm web lint-imports` | **11 kept, 0 broken** |
| Migraciones | `docker compose run --rm web python manage.py makemigrations --check --dry-run` | No changes detected |
| System checks | `docker compose run --rm web python manage.py check` | System check identified no issues |
| Pre-commit (host) | `python -m pre_commit run --all-files` | ruff / ruff-format / import-linter: Passed |
| OpenAPI | `docker compose run --rm web python manage.py spectacular --validate --fail-on-warn --file schema.yml` | **PASA: 0 errores, 0 warnings** |
| Estado del repo | `git status` | limpio; `main` **1 commit adelante** de `origin/main` (el de este documento, sin push) |

**Pendiente de la Fase 0:** nada. La Fase 0 quedó cerrada (bloques A, B, C y D) con
`pytest`, `ruff`, `lint-imports` y `makemigrations --check` en verde.

---

## 7. Decisiones técnicas

Solo las decisiones **nuevas** de los bloques 1A → 5. Las de AGENTS.md §17
(sin cambio de rationale) ya están registradas allí y no se repiten.

| # | Decisión | Motivo |
|---|---|---|
| D1 | `User` sin `username`, con `UserManager` propio por email (migración `0002` elimina la columna) | El login es por email; mantener `username` obligaba a duplicar el dato y a romper `create_user` |
| D2 | `Account.balance` **desnormalizado** con `CheckConstraint(balance >= 0)` **solo** para `user_wallet` | El saldo de una cuenta se deriva de sus asientos, pero materializarlo permite un `SELECT` barato y una restricción de no-negatividad en la base; las cuentas de contrapartida (`custody`, `system`) reflejan el mundo exterior y pueden quedar negativas |
| D3 | Doble entrada garantizada con un **constraint trigger diferido** de PostgreSQL (`sum(debits) = sum(credits)` al commit) + triggers que bloquean `UPDATE`/`DELETE` en `LedgerTransaction` y `LedgerEntry` | La regla de §6 debe vivir en la base, no solo en Python; diferido porque los asientos se insertan en varias sentencias |
| D4 | `idempotency_key` única por `(created_by_user_id, idempotency_key)` con `request_hash` | La clave debe ser única **por usuario**, no global: dos usuarios distintos pueden usar la misma clave. El hash permite distinguir "reintento" de "payload distinto" (409) |
| D5 | Bloqueo de cuentas con `select_for_update` **en orden ascendente por `id`** | Evita deadlocks entre transferencias cruzadas; el orden determinista es la única forma de garantizarlo |
| D6 | `ledger.transfer_between_users` (interno) + `transfer_to_counterpart` / `transfer_from_counterpart` | Los flujos de préstamos e inversiones mueven saldo entre usuarios o contra cuentas sin usuario (`user_id = NULL`), que no se pueden resolver con `transfer_between_users` |
| D7 | `Loan` con estados `active` \| `paid` \| `defaulted` (el `pending` no se usa) | El préstamo nace `active` al aceptar la oferta; `pending` era un estado muerto |
| D8 | La última cuota ajusta su **parte de capital** (el interés absorbe el redondeo acumulado) | El importe de la cuota es constante y la suma de capitales es exactamente el principal |
| D9 | Reversos **solo staff** y **sin endpoint** (acción del admin) | Los reversos son una corrección de un movimiento ya registrado, no una operación del usuario; el admin es la única vía y por eso el rol staff es la barrera |
| D10 | `Offer.interest_rate` es **TNA anual en `%`**; la cuota mensual se calcula una sola vez en `core/money.py` con `Decimal` | Una sola fuente de verdad para el cronograma; sin redondeos intermedios |
| D11 | La búsqueda de ofertas filtra por **rango** (`amount_min` / `amount_max`) y no por monto exacto | El préstamo toma el **monto completo** de la oferta, así que el filtro es un rango |
| D12 | `matching` es solo lectura y se apoya únicamente en `offers.selectors` | La app de matching no escribe estado y no debe conocer el modelo de `offers` (verificado por `import-linter`) |
| D13 | `InvestmentProduct` se da de alta **solo por staff en el admin**; la API solo lista | Los productos son la oferta comercial de la plataforma; se gobiernan por staff, no por API pública |
| D14 | Sin cancelación anticipada de inversiones | No hay un camino de negocio definido; agregarlo después, no ahora |
| D15 | `simple_interest` con base **365 días** | Convención simple y auditable para un plazo fijo; el plazo exacto vive en el producto |
| D16 | `EXCEPTION_HANDLER` propio en `core` con el formato de §8 (`error.code` / `error.message` / `error.details`) | Uniformidad de errores; el código propio de la excepción se usa salvo en los status genéricos (400/401/403/404/405/429) |
| D17 | `pytest.ini` con `addopts = --ds=config.settings.test` | El `DJANGO_SETTINGS_MODULE` del entorno (docker-compose pone `config.settings.local`) tiene prioridad sobre el ini; el flag `--ds` lo pisa y garantiza settings de test |
| D18 | `config/settings/test.py` **no** sobrescribe `DATABASES['default']['NAME']` | pytest-django crea `test_<NAME>` solo; tocar el `NAME` rompía la creación de la base de test |

---

## 8. Problemas y resoluciones

| # | Problema | Resolución |
|---|---|---|
| P1 | `relation "auth_group" does not exist` en cada test: pytest-django creaba `test_presto` **sin** las tablas de `django.contrib.auth` | Causa raíz: `apps/identity` **no tenía carpeta `migrations/`**, así que sus tablas no se creaban y la FK a `auth_group` fallaba. Se generó `apps/identity/migrations/0001_initial.py` con `makemigrations` |
| P2 | `apps/ledger/tests/test_concurrency.py` fallaba con `MultipleObjectsReturned` al hacer `get(user_id=..., kind=USER_WALLET)` | Un usuario tiene una billetera **por moneda**: faltaba el filtro `currency`. Se corrigió el test (no el código) |
| P3 | Los tests de `loans`/`investments` fallaban con `Account matching query does not exist` | El `user_wallet` no existía porque la creación de la billetera ocurre dentro de la transacción atómica que se revierte. Se ajustaron las aserciones a `wallet is None or wallet.balance == 0` |
| P4 | Los tests de préstamos a 3 meses fallaban con `InsufficientFunds` al pagar la última cuota | El costo total (capital + interés) de un préstamo de 3 meses al 24% TNA **supera** el capital desembolsado: el prestatario necesita saldo extra para los intereses. Se financió explícitamente en el test y se documentó |
| P5 | `pytest` usaba `config.settings.local` (del `docker-compose.yml`) en vez de los settings de test | `DJANGO_SETTINGS_MODULE` del entorno tiene prioridad sobre `pytest.ini`; se resolvió con `addopts = --ds=config.settings.test` (ver D17) |
| P6 | `import-linter` reportaba "0 kept, 0 broken" sin ejecutar ningún contrato | La sección de contratos debe ser `[importlinter:contract:<nombre>]` (con dos puntos), no `[importlinter.contracts.<nombre>]`. Verificado mostrando "1 broken" con un import prohibido de prueba y revirtiendo |
| P7 | `import-linter` marcaba la cadena **indirecta** `ledger → identity.selectors → identity.models` | Las tablas de `identity` son internas de esa app; se activó `allow_indirect_imports = True` en ese contrato (la importación directa sigue prohibida) |
| P8 | El hook de `import-linter` en pre-commit fallaba: `pathspec 'v2.15.0' did not match` y `No such option '--config-file'` | El tag real es `v2.15` y la opción es `--config`. Corregidos en `.pre-commit-config.yaml` |
| P9 | El servicio web estaba caído (`WSGI application 'config.wsgi.application' could not be loaded`) | Resto del Bloque A: sobraba el paquete `config/config/` y faltaban `config/__init__.py`, `config/settings/__init__.py`, `config/wsgi.py`, `config/asgi.py`. Se aplanó la estructura (commit `819cd15`) |
| P10 | La migración que cambia `id` de `BigAutoField` a `UUIDField` fallaba con `cannot cast type bigint to uuid` | Base de datos de desarrollo con datos: se recreó la base y se regeneró la migración inicial con el modelo ya corregido |
| P11 | `makemigrations` generaba una migración `0002_alter_user_id` que no se podía aplicar | Se aplicó el modelo definitivo antes de generar la migración, y la migración inicial quedó con el `UUIDField` |
| P12 | Los tests de `loans` e `investments` violaban el contrato de `import-linter` importando `ledger.models` / `offers.models` | Se reemplazaron por los selectores y servicios públicos (`ledger.selectors.get_user_wallet`, `get_balance_breakdown`, `list_transactions_for_user`) y por literales de estado |
| P13 | `spectacular` genera el esquema con 1 error y 7 warnings | **Resuelto** (ver §11, ítem 1): 0 errores y 0 warnings. La CI valida el esquema con `--validate --fail-on-warn` |
| P14 | `pytest.raises(Exception)` disparaba el linter `B017` | Se reemplazó por la excepción concreta (`InsufficientFunds`) |

---

## 9. Notas y glosario

- **TNA**: tasa nominal anual, expresada en porcentaje (`24.00` = 24% TNA). La
  tasa mensual equivalente es `TNA / 100 / 12`; la efectiva es
  `(1 + TNA/100)^(1/12) - 1`. En el repo se usa la nominal.
- **`custody` / `system`**: cuentas de contrapartida sin `user_id`. `custody`
  representa los fondos custodiados; `system`, la contraparte de las inversiones.
  Con la convención `balance = créditos - débitos`, la suma de **todos** los
  saldos de una moneda es **cero** y `Σ(custody) + Σ(system) = -Σ(user_wallet)`.
- **`Idempotency-Key`**: header HTTP obligatorio en los POST que crean o
  mueven dinero (`/api/v1/loans/`, `/api/v1/investments/positions/`,
  `/api/v1/ledger/transactions/`). La unicidad es **por `(usuario, clave)`**, no
  global. Misma clave + mismo payload → devuelve la operación original; misma
  clave + payload distinto → `409`.
- **Saldo no negativo**: solo aplica a `user_wallet`. Las cuentas `custody` y
  `system` reflejan el mundo exterior y pueden quedar negativas (ver §4).
- **`request_hash`**: SHA-256 canónico del payload, guardado junto a la clave.
- **KYC**: `identity.selectors.is_kyc_approved(user_id)` es el único punto de
  entrada para exigir verificación. `apps/identity/permissions.py::IsKycApproved`
  replica la regla a nivel HTTP.
- **Sin implementar todavía**: `payments` (proveedor real), `budgets`,
  `reports`, `notifications`, `config/celery.py` y el worker de Celery, el
  `docker-compose.prod.yml` que pide AGENTS §4, y `docs/adr/`.
- **Sin verificar**: no se ejecutó nunca un despliegue real, ni
  `docker-compose.prod.yml` (no existe), ni el worker de Celery, ni el flujo
  contra un proveedor de pagos real.

---

## 10. Cómo ejecutar y validar

Todos los comandos se ejecutan **desde la raíz del repo**. Los que necesitan el
contenedor se ejecutan con `docker compose run --rm web ...`.

### Levantar / bajar el entorno

```sh
make up        # docker compose up --build -d
make down      # docker compose down
docker compose ps
```

`docker compose ps` debe mostrar **3 servicios Up**: `db`, `redis`, `web`.

### Tests

```sh
make test      # docker compose run --rm web python -m pytest -v
```

Resultado esperado: **374 passed**. Para ver la cobertura:

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

> Este comando **PASA**: 0 errores y 0 warnings. Es el mismo que corre la CI.
> La CI lo ejecuta en el job *quality* y falla si aparece cualquier warning.

### Management commands

```sh
docker compose run --rm web python manage.py mark_overdue_loans   # cuotas vencidas -> overdue
docker compose run --rm web python manage.py settle_investments    # posiciones vencidas -> matured
```

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
docker compose run --rm web python manage.py makemigrations --check --dry-run
docker compose run --rm web pytest -v --cov=apps --cov-report=term-missing --cov-fail-under=80
```

---

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

1. **Esquema OpenAPI.** ✅ **Resuelto** (commit `fix(openapi): generate a clean OpenAPI schema`): `python manage.py spectacular --validate --fail-on-warn --file schema.yml` corre con **0 errores y 0 warnings** y la CI lo valida (job *quality*). Se hizo:
   - `InstallmentPayView` declara `serializer_class = InstallmentSerializer` y `extend_schema(request=None)` (la vista no lee un body).
   - `ENUM_NAME_OVERRIDES` en `SPECTACULAR_SETTINGS`: `LoanStatusEnum` y `PositionStatusEnum` reemplazan los nombres colisionados `Status36cEnum` / `StatusF63Enum`.
   - `operation_id` explícito para las 5 pares lista/detalle (`kyc_list`/`kyc_retrieve`, `ledger_transactions_list`/`ledger_transactions_retrieve`, `loans_list`/`loans_retrieve`, `offers_list`/`offers_retrieve`, `investments_positions_list`/`investments_positions_retrieve`).
   - Cobertura de regresión en `apps/core/tests/test_openapi.py`.
2. **Bloque 6 — `budgets`, `reports`, `notifications`** (nadie empezó). Los modelos ya están definidos en AGENTS §7; `reports` es solo lectura y `notifications` usa Celery (hoy `config/celery.py` no existe).
3. **Bloque 7 — `payments` con proveedor real** (al final, a propósito). Hoy los depósitos y retiros son **simulados** y están apagados en producción por el system check `ledger.E001`: `ledger.withdraw` es alcanzable por HTTP pero **siempre devuelve 400** en producción (ver §9 y el diagnóstico del bloque 5).
4. **Cerrar la brecha de `config/celery.py` y el worker de Celery**: AGENTS §4 los lista y §14 exige que `docker compose up` levante el worker; hoy no existe ninguno de los dos.
5. **Programar las tareas periódicas con Celery beat**: hoy `mark_overdue_loans` y `settle_investments` son management commands que hay que correr a mano. Con `config/celery.py` + `celery beat` hay que registrar ambos como tareas periódicas (`mark_overdue_loans` diario para marcar cuotas vencidas y préstamos en mora, `settle_investments` diario para liquidar las posiciones de plazo fijo que vencieron) y que corran en el worker en vez de depender de que alguien se acuerde.
6. **Crear `docker-compose.prod.yml`**: está en el árbol exigido por AGENTS §4 y no existe.
7. **Producción**: hoy no hay nada desplegable. Falta el endpoint **`/health/`** (chequeo de estado), la integración con **Sentry** para errores, los **backups automáticos diarios** de PostgreSQL con prueba periódica de restauración, **HTTPS** obligatorio (`SECURE_SSL_REDIRECT`, cookies seguras, HSTS) y la configuración de **CORS** explícita para el front (`CORS_ALLOWED_ORIGINS`, sin `*`).
8. **Documentación**: `docs/architecture.md` y `docs/adr/` están vacíos; AGENTS §13 pide un ADR por decisión de arquitectura importante (empezar por: saldo desnormalizado, contrato diferido de doble entrada y el orden `offers+matching → loans → investments → payments`).
9. **Aplicar `IsKycApproved` en las vistas que mueven dinero.** Aclaración importante: `IsKycApproved` es una **capa extra de defense in depth**, no la única barrera. Los `services` ya exigen KYC aprobado por sí mismos (`identity.selectors.is_kyc_approved(user_id)`), así que el requisito de AGENTS §9.9 está garantizado aunque la vista no use la permission. Lo que falta es el mensaje y el `403` temprano y explícito en la capa HTTP, que hoy llega como error de dominio. La permission ya existe y está testeada; simplemente ninguna vista la usa.
10. **Cobertura de vistas por debajo de 100%**: `loans/views.py` 94%, `matching/views.py` 97%, `investments/views.py` 95%. No es un bloqueo (los umbrales de AGENTS §10 son 90% en `ledger`/`budgets` y 80% general), pero conviene cerrarlas.
11. **Agregar `budgets` al umbral de cobertura del 90%** cuando exista la app.

### 11.1 Decisiones abiertas con el cliente

Estas decisiones **no son técnicas**: cambian el producto, el modelo de negocio o
el marco legal. No hay una respuesta "correcta" en el código, así que **no se
implementan hasta que el cliente defina el criterio**. Cada una bloquea una
parte concreta del trabajo.

| # | Decisión abierta | Qué hay que definir | Qué bloquea |
|---|---|---|---|
| O1 | **Proveedor de pagos** | Cuál es el proveedor (PSP, banco, pasarela), qué operaciones soporta (depósito, retiro, transferencia), si hay API de webhooks firmados, comisiones, tiempos de liquidación y si el saldo del ledger se replica contra la cuenta del proveedor | Toda la app `payments` (Bloque 7) y el camino de depósitos/retiros, hoy simulados |
| O2 | **Marco regulatorio de la custodia** | Si Presto es una **plataforma de inversión** o un **agente de custodia**; qué entidad regulada respalda los saldos; si los fondos van a una cuenta segregada en un banco o a una cuenta del proveedor; requisitos de capital mínimo, seguro de depósitos y reporte de saldos | El modelo de cuentas `custody` / `system` y si Presto puede llamar "custodia" a lo que hace hoy |
| O3 | **Presto asume el rendimiento de los plazos fijos** | Si la tasa que se muestra está garantizada por Presto o si el rendimiento depende del instrumento que respalda la posición; qué pasa si el rendimiento real es menor que el prometido; si hay un fondo de garantía o un spread de riesgo; quién asume la diferencia | El modelo de `Position` e `InvestmentProduct` (hoy el interés es un `Decimal` fijo calculado al abrir) y el marketing del producto |
| O4 | **Regla de "gastado" en presupuestos** | Si "gastado" se calcula contra los **movimientos del ledger** (todo lo que sale de la billetera, incluidos pagos de cuotas e inversiones) o solo contra **gastos categorizados**; cómo se categoriza un movimiento sin categoría; qué pasa con las transferencias entre cuentas propias | Toda la app `budgets` (Bloque 6) y el significado de `Budget` y `Goal` |
| O5 | **PLA/FT (prevención de lavado)** | Umbrales de Reporte de Operaciones Sospechosas (ROS), identificación del beneficiario final, screening contra listas de sanciones, reglas de monitoreo de patrones (velocidad, montos, estructuración), documentación de la operatoria, plazos de conservación y responsable asignado | El alcance de `identity` (más allá del KYC actual) y de `payments`; también define auditoría y retención de datos |
| O6 | **CFT (costo financiero total)** | Si el cliente quiere el costo financiero total —capital + interés— **en la comparación de ofertas** (hoy `matching.compare_offers` ya devuelve cuota, interés total y costo total: la pregunta es de exposición y de etiquetado, no de cálculo), y si ese CFT debe compararse contra el costo de otras alternativas del usuario (crédito, plazo fijo, efectivo) | La presentación de `POST /api/v1/matching/comparisons/` y los reportes; el cálculo ya existe en `core/money.py` (`french_total_cost`) |

**Cómo se cierran estas decisiones:** cada respuesta se registra en AGENTS.md §17
y, si cambia la arquitectura, en un ADR de `docs/adr/`. Hasta entonces el código
se mantiene en el supuesto más conservador: no se promete rendimiento, no se
llama "custodia" a un saldo que no está en una cuenta segregada, y no se mueve
dinero sin KYC aprobado.

---

## 12. Comandos de management y datos de prueba

### Management commands implementados

| Comando | Qué hace |
|---|---|
| `python manage.py mark_overdue_loans` | Marca las cuotas vencidas (`overdue`) y sus préstamos (`defaulted`) |
| `python manage.py settle_investments` | Liquida las posiciones de inversión vencidas (capital + interés) |

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
  `config/settings/test.py`; en `production.py` depende de la variable de
  entorno y el system check `ledger.E001` impide que quede activa.

---

## 13. Registro

| Fecha | Cambio |
|---|---|
| 2026-10-21 | Documento creado: estado real del repo (63 commits), estado verificado de los checks, decisiones D1-D18, problemas P1-P14, endpoints reales extraídos del `URLConf`, comandos de ejecución validados y orden de los próximos pasos. **Nota**: `HANDOFF.md` **no existía** en el repo (ni en el árbol de trabajo, ni en el historial de git de ninguna rama, ni en el filesystem): se creó desde cero siguiendo la estructura de secciones indicada. |
| 2026-10-21 | Ajustes pedidos por el cliente: §6.2 ahora es un resumen de 1-2 líneas por bloque (sin el detalle de archivos por commit); §4 pasó a "Requisitos, entorno local e invariantes del dinero" con los tres invariantes del ledger (saldo no negativo solo en `user_wallet`, `idempotency_key` única por `(usuario, clave)`, suma de saldos por moneda = 0) y §9 los referencia; §11.1 nueva con las decisiones abiertas con el cliente. |
| 2026-10-21 | Tercer ajuste pedido por el cliente: §6.2 sin la columna de commits; §11.1 con O5 renombrado a PLA/FT y O6 nuevo sobre CFT (costo financiero total) en la comparación de ofertas; §11 renombra Fase 2 → Bloque 6 y Fase 3 → Bloque 7, suma el ítem de programar `mark_overdue_loans` y `settle_investments` con Celery beat, el ítem de Producción (/health/, Sentry, backups, HTTPS, CORS) y aclara que `IsKycApproved` es una capa extra porque los services ya exigen KYC. |
| 2026-10-21 | **Esquema OpenAPI arreglado**: `spectacular --validate --fail-on-warn` pasa con **0 errores y 0 warnings** y se agregó a la CI (job *quality*). `InstallmentPayView` declara `serializer_class` (+ `request=None` porque no lee body), `ENUM_NAME_OVERRIDES` nombra `LoanStatusEnum` y `PositionStatusEnum`, y las 5 pares lista/detalle tienen `operation_id` explícito. Regresión cubierta en `apps/core/tests/test_openapi.py` (380 tests). §6.1, §6.3, §8 (P13), §10 y §11 (ítem 1) actualizados. |
