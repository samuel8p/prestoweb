# Auditoría final del backend de Presto

- **Fecha:** 2026-10-21
- **Alcance:** el backend completo (`apps/`, `config/`, `deploy/`, CI, docs y compose).
- **Método:** lectura del código, greps dirigidos sobre las reglas de AGENTS.md,
  `manage.py check --deploy` con los settings de producción, un mapeo automático
  de endpoints ↔ tests, y una **prueba desde cero** (§6).
- **Reglas de referencia:** `AGENTS.md` (fuente de verdad) y `HANDOFF.md`.

> Esta auditoría **no modificó código**. Los hallazgos se corrigen en commits
> aparte, cada uno con su test rojo previo. Lo que necesita una decisión del
> cliente está en §5.

## Resumen

| Severidad | Cantidad | Corregidos | En "requiere decisión" |
|---|---|---|---|
| Crítico | 0 | 0 | 0 |
| Alto | 2 | 2 | 0 |
| Medio | 9 | 9 | 0 |
| Bajo | 8 | 3 | 5 |

Categorías con hallazgos: **seguridad** (5), **tests** (6), **docs** (5),
**dinero** (1), **bug** (2), **incompleto** (3).

Lo que salió bien y no hay que tocar: no hay `float` en el código de dinero,
no hay redondeo fuera de `core/money.py`, no hay ForeignKey entre apps de
dominio, el ledger es inmutable con triggers en la base, todos los endpoints
tienen permisos, 29 de 33 endpoints tienen tests completos y el esquema
OpenAPI genera sin warnings.

---

## 1. Hallazgos

### 1.1 Críticos

**Ninguno.** No encontré una vía por la que se pueda mover dinero sin pasar
por el ledger, ni una fuga de datos entre usuarios, ni una corrupción del
invariante de saldos.

### 1.2 Altos

#### A-1 · seguridad · Los validadores de contraseña de Django están desactivados

- **Dónde:** `config/settings/base.py:140` → `AUTH_PASSWORD_VALIDATORS = []`
- **Viola:** AGENTS.md §9.5 ("Contraseñas con validadores de Django activos")
- **Qué pasa hoy:** el registro solo exige 10 caracteres
  (`RegisterSerializer.password` con `min_length=10`), así que se puede registrar
  con `1234567890` o `aaaaaaaaaa`. Faltan los validadores de contraseña común,
  numérica, longitud mínima y similitud con el email.
- **Corrección:** activar los cuatro validadores de Django
  (`UserAttributeSimilarityValidator`, `MinimumLengthValidator`,
  `CommonPasswordValidator`, `NumericPasswordValidator`) y bajar el
  `min_length` del serializer a 8 (el validador de Django pone el piso en 8),
  para no tener dos reglas distintas de longitud.

#### A-2 · seguridad · Falta HSTS en producción

- **Dónde:** `config/settings/production.py` (define `SECURE_SSL_REDIRECT`,
  `SESSION_COOKIE_SECURE` y `CSRF_COOKIE_SECURE`, pero no HSTS)
- **Viola:** AGENTS.md §9.4 ("HTTPS obligatorio en producción (SECURE_SSL_REDIRECT,
  cookies seguras, HSTS)")
- **Evidencia:** `manage.py check --deploy` con los settings de producción
  devuelve `security.W004` ("You have not set a value for the SECURE_HSTS_SECONDS
  setting").
- **Corrección:** `SECURE_HSTS_SECONDS` (un año) y
  `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`. **No** se activa `SECURE_HSTS_PRELOAD`:
  es irreversible y depende de que todos los subdominios sirvan HTTPS.

### 1.3 Medios

#### M-1 · tests · `GET /api/v1/budgets/categories/{id}/` sin ningún test

- **Dónde:** `apps/budgets/views.py::CategoryDetailView`
- **Qué pasa hoy:** es el único endpoint de la API sin cobertura: no hay test de
  200, ni de 404 para una categoría de otro usuario, ni de 401 sin token.
- **Corrección:** agregar los tres tests (propio 200, ajeno 404, sin token 401).

#### M-2 · bug · `update_offer` y `expire_offer` sin transacción ni bloqueo

- **Dónde:** `apps/offers/services.py:73` (`update_offer`) y `:125` (`expire_offer`)
- **Qué pasa hoy:** los dos leen la oferta y la guardan sin
  `transaction.atomic()` ni `select_for_update()`. Dos PATCH concurrentes sobre la
  misma oferta pueden pisarse (el último en guardar gana) y un PATCH concurrente
  con un `expire` puede dejar campos viejos con el estado nuevo. El resto de los
  services que escriben (ledger, loans, investments, identity, budgets) sí usan
  `transaction.atomic()` y `select_for_update()`.
- **Corrección:** envolver en `transaction.atomic()` y bloquear la oferta con
  `select_for_update()`, como ya hace `accept_offer` en la misma app.

#### M-3 · seguridad · Los contenedores corren como root

- **Dónde:** `Dockerfile` (no crea ningún usuario) y los compose (sin `user:`)
- **Viola:** el criterio de auditoría C.7 ("contenedores sin root")
- **Qué pasa hoy:** el proceso de gunicorn, el worker y el beat corren como root.
- **Corrección:** crear un usuario sin privilegios en el `Dockerfile` y ejecutarlo
  con `user:` en los servicios de producción. El compose de desarrollo mantiene
  root a propósito: el código va montado como volumen y el usuario del host
  debe poder escribir.

#### M-4 · docs · `.env.example` no documenta dos variables que sí se leen

- **Dónde:** `.env.example` (leídas por `config/settings/base.py` y por los
  compose)
- **Qué pasa hoy:** `DEMO_MODE` y `LEDGER_SIMULATED_DEPOSITS_ENABLED` no
  aparecen, así que alguien que copie el archivo no sabe que el compose las
  usa.
- **Corrección:** documentarlas en `.env.example` (y chequear que
  `.env.prod.example` las tenga también).

#### M-5 · docs · El README quedó desactualizado

- **Dónde:** `README.md`
- **Qué pasa hoy:** (a) la sección "Estructura" lista solo 4 de las 10 apps;
  (b) la sección de tareas de beat menciona 2 de las 4 tareas reales; (c) la
  lista de endpoints solo incluye `identity`; (d) el README usa `make` en todos
  los comandos pero "Requisitos" solo dice Docker + Docker Compose (en una
  máquina sin `make` los comandos no existen — pasó en la prueba desde cero, §6);
  (e) no menciona el modo demo, `/health/`, `/api/v1/meta/` ni el
  `docker-compose.prod.yml`.
- **Corrección:** actualizar el README con la estructura real, las cuatro
  tareas, los endpoints por app, el requisito de `make` (con la alternativa
  directa de Docker Compose), y una sección de modo demo y despliegue.

#### M-6 · docs · Falta `docs/architecture.md`

- **Dónde:** lo pide AGENTS.md §4 (el árbol del repo) y §13 (documentación).
- **Corrección:** escribirlo con la arquitectura real: monolito modular, capas,
  los ocho invariantes del dinero, el flujo de una operación de dinero y el
  mapa de apps.

#### M-7 · docs · Faltan tres ADRs que AGENTS.md §13 pide

- **Dónde:** `docs/adr/` tiene 4 ADRs (Celery, budgets, reports, notifications)
  y AGENTS.md §13 pide un ADR por decisión importante.
- **Corrección:** escribir tres ADRs: el saldo desnormalizado de las cuentas, el
  contrato diferido de doble entrada y el orden de las apps.

#### M-8 · docs · El HANDOFF quedó desactualizado

- **Dónde:** `HANDOFF.md` §6.1 (dice 82 commits) y §10 (no lista los endpoints
  de `budgets`).
- **Corrección:** actualizarlos al cerrar el bloque.

#### M-9 · bug · El health check de producción siempre fallaba

- **Dónde:** `docker-compose.prod.yml` (el `healthcheck` del servicio `web`).
- **Qué pasa hoy:** el chequeo pedía `http://127.0.0.1:8000/health/` sin header
  `Host`, y Django responde **400** cuando el `Host` no está en `ALLOWED_HOSTS`
  (en producción es `presto.example.com`). El contenedor de producción quedaba
  `unhealthy` para siempre, aunque la aplicación funcionara.
- **Cómo se encontró:** en el arranque real del stack de producción (FASE 2,
  cierre), no con una lectura del código.
- **Corrección:** el chequeo manda el primer host permitido. Con el stack de
  producción levantado, el contenedor queda `healthy`.

### 1.4 Bajos

#### B-1 · docs · El esquema OpenAPI no tiene ejemplos

- **Dónde:** todos los endpoints (las descripciones sí están: salen del docstring
  de la vista ✓).
- **Nota:** AGENTS.md §8 no pide ejemplos. Se deja como está y se listan
  como mejora candidata.

#### B-2 · dinero · El campo `currency` no tiene constraint en la base

- **Dónde:** `ledger.Account.currency`, `ledger.LedgerEntry.currency`,
  `loans.Loan.currency`, `investments.Position` (vía el producto),
  `budgets.Budget.currency` y `notifications` (vía el evento).
- **Qué pasa hoy:** el valor se valida en los serializers, pero la base acepta
  cualquier texto. Un bug futuro podría guardar `ars` en minúscula y los
  reportes (que comparan con `ARS`) no lo verían.
- **No se corrige:** es un cambio de schema y AGENTS.md §12 pide revisar cada
  migración. Va a §5.

#### B-3 · docs · Las variables de CORS no hacen nada

- **Dónde:** `CORS_ALLOWED_ORIGINS` está en `.env.example` y en
  `.env.prod.example` y se pasa al contenedor, pero los settings no la leen
  (no hay `django-cors-headers`).
- **Consecuencia:** sin ese paquete, un front en otro origen no puede llamar a
  la API. La variable está de adorno.
- **No se corrige:** corregirlo es agregar una dependencia (§5).

#### B-4 · seguridad · Las imágenes no están fijadas a un digest

- **Dónde:** `docker-compose.yml` y `docker-compose.prod.yml` usan
  `postgres:16`, `redis:7-alpine` y `caddy:2-alpine` (etiqueta mayor, no exacta).
- **Nota:** fijar el digest o el parche exacto es una decisión de operación
  (los digests cambian con cada parche de seguridad). Va a §5.

#### B-5 · seguridad · La CI no corre `manage.py check --deploy`

- **Dónde:** `.github/workflows/ci.yml` (corre ruff, import-linter, spectacular,
  makemigrations y los tests).
- **Qué pasa hoy:** un ajuste de producción que rompa una regla de seguridad
  (HSTS, cookies seguras, `ALLOWED_HOSTS`, `DEBUG`) llega a producción sin que
  nadie lo note.
- **No se corrige:** el check devuelve avisos (no errores) y el `SECRET_KEY`
  ficticio de la CI dispararía un aviso siempre: hacer que falle requiere
  decidir la política. Va a §5.

#### B-6 · tests · Falta un test de concurrencia para la categorización de gastos

- **Dónde:** `apps/budgets/services.py::categorize_movement` (crea un
  `Expense` con unicidad `(user_id, ledger_transaction_id)`).
- **Qué pasa hoy:** la carrera se maneja por la constraint (una segunda
  categorización concurrente recibe `AlreadyCategorized` ✓) pero no está
  probada con hilos, como sí están las del ledger, loans e investments.
- **Corrección:** agregar el test de concurrencia.

#### B-7 · bug · Faltaban los `__init__.py` de tres paquetes

- **Dónde:** `apps/`, `apps/core/` y `apps/identity/` (AGENTS §4 pide un
  `__init__.py` en cada app ✓).
- **Qué pasa hoy:** sin el marcador, pytest importaba `apps/core/tests` como el
  paquete de nivel superior `tests` y cualquier otro paquete llamado `tests`
  (el de la suite end-to-end) no se podía collecting. Con `apps/` sin
  `__init__.py` además, `apps` era un *namespace package* implícito.
- **Corrección:** agregar los tres archivos.

#### B-8 · bug · Los linters escribían su cache en el directorio del proyecto

- **Dónde:** `ruff` (`.ruff_cache/`) e `import-linter` (su cache) escriben en
  el directorio del proyecto.
- **Qué pasa hoy:** con el usuario sin privilegios de la imagen (M-3) y el
  código montado como volumen del host, esas escrituras fallan con
  `Permission denied` y `make lint` deja de funcionar dentro del contenedor.
- **Corrección:** la imagen apunta la cache de ruff a `/tmp` y el target
  `make lint` le pasa a import-linter un directorio de cache escribible.

### 1.5 Lo que está bien (y no hay que tocar)

- **Sin `float`** en el código de dinero (AGENTS §6.1) ✓.
- **Un solo redondeo**: `round()` solo aparece en `apps/core/money.py` ✓.
- **Sin ForeignKey entre apps de dominio**: todas las FK son intra-app
  (`Budget.category → Category`, `Installment.loan → Loan`,
  `LedgerEntry.account → Account`, `Position.product → Product`) ✓.
- **El ledger es inmutable**: los triggers de PostgreSQL bloquean `UPDATE` y
  `DELETE` sobre `ledger_ledgertransaction` y `ledger_ledgerentry` ✓, y la
  doble entrada se valida con un constraint trigger diferido ✓.
- **Idempotencia** en todos los services que mueven dinero (`deposit`,
  `withdraw`, `transfer`, `transfer_between_users`, `accept_offer`,
  `open_position`) ✓, con `request_hash` para distinguir reintentos de payloads
  distintos ✓.
- **Permisos en los 33 endpoints** ✓ (los públicos son `register`, `login` y
  `meta` ✓) y throttles en login (5/min) y register (5/hora) ✓.
- **Aislamiento por usuario** con test en cada endpoint que muestra datos
  (404 para un tercero) ✓.
- **Sin secretos** en el código ni en el historial de git ✓.
- **Sin datos sensibles en los logs** (los logs llevan ids y conteos, nunca
  emails, contraseñas, tokens ni saldos) ✓; los emails de las notificaciones
  tampoco incluyen saldos completos ni datos de KYC ✓.
- **El formato de error de AGENTS §8** es uniforme en todos los endpoints ✓.
- **Paginación** en todos los listados ✓ (cursor para los movimientos, que es lo
  que pide AGENTS §8 ✓).
- **El esquema OpenAPI** genera con 0 errores y 0 warnings ✓, con descripciones
  en todos los endpoints ✓.
- **Sin N+1** en los selectores: los listados usan `select_related` /
  `prefetch_related` y los reportes resuelven en lote
  (`list_movement_details`, `list_installments_for_loans`,
  `list_spending_movements`) ✓.
- **Sin lógica de negocio** en vistas, serializers, signals ni `save()` ✓
  (las signals solo llevan identificadores ✓).

---

## 2. Lo que se va a corregir (FASE 2)

| # | Hallazgo | Tipo de commit |
|---|---|---|
| A-1 | validadores de contraseña | fix(security) |
| A-2 | HSTS en producción | fix(security) |
| M-1 | test del detalle de categoría | test(budgets) |
| M-2 | atomic + select_for_update en offers | fix(offers) |
| M-3 | contenedores sin root | chore(infra) |
| M-4 | variables en `.env.example` | docs(config) |
| M-5 | README desactualizado | docs(readme) |
| M-6 | `docs/architecture.md` | docs(architecture) |
| M-7 | tres ADRs pendientes | docs(adr) |
| M-8 | HANDOFF desactualizado | docs(handoff) |
| M-9 | health check de producción | fix(deploy) |
| B-6 | test de concurrencia de budgets | test(budgets) |
| B-7 | `__init__.py` que faltaban | fix(structure) |
| B-8 | cache de los linters | fix(infra) |

Además, por pedido explícito:

- **Test end-to-end** del flujo completo (registro → login → KYC → depósito
  simulado → oferta → préstamo → pago de cuota → inversión → reportes →
  notificaciones), con **ARS y USD por separado**, verificando que la **suma de
  saldos por moneda sea 0**.
- **Tests de concurrencia** para las operaciones de dinero que no los tenían.

## 3. Lo que NO se va a tocar (decisiones del cliente)

> Actualizado el 2026-10-21: el desarrollador autorizó el `CheckConstraint` de
> moneda del ledger (D-3), que es la **única** parte de esta lista que cambió.

- El **schema del ledger**: solo el `CheckConstraint` de moneda, ya aplicado
  (D-3). Los **triggers** y la **inmutabilidad** quedan intocables.
- Los **management commands**.
- Los **contratos de import-linter** existentes.
- **`AGENTS.md`**: el registro de la §17 quedó aplicado (D-1); el resto de las
  secciones sigue sin tocarse.
- **Dependencias nuevas**: `pip-audit` ya está (D-2); `sentry-sdk` y
  `django-cors-headers` siguen esperando.
- El **reintento** de avisos fallidos y el **resumen** de avisos.
- Todo lo que dependa de **negocio**: `payments` (O1), el marco regulatorio de la
  custodia (O2), el rendimiento de los plazos fijos (O3), PLA/FT (O5) y el CFT
  (O6).

## 4. Detalle de la prueba desde cero (§6)

- Clon: `git clone <repo> /tmp/presto-clone` ✓
- `docker compose up --build -d` → 5 servicios arriba ✓
- `docker compose run --rm web pytest -q` → **620 passed** ✓
- Smoke: `/api/schema/` 200 ✓, `/api/v1/meta/` 200 con `mode=demo` ✓,
  `/health/` 200 `{"status":"ok"}` ✓
- **Falla:** `make` no está instalado en la máquina → los comandos `make up`,
  `make test`, etc. del README no se pueden ejecutar (M-5) ✓
- Se bajó el clon con `down -v` y se restauró el stack de desarrollo ✓

## 5. Requiere decisión (con recomendación)

**Estado a 2026-10-21:** el desarrollador autorizó tres de los nueve temas (D-1,
la parte de `pip-audit` de D-2 y D-3) y quedaron resueltos ✓. Los demás siguen
abiertos ✗.

**Estado a 2026-10-22 (contrato del frontend):** el frontend mandó sus
desviaciones del esquema (`docs/backend-contract.md`). Todas las que eran del
**esquema** se corrigieron (paginación real, el header `Idempotency-Key`, los
parámetros y el CSV de los reportes, los errores y el KYC nullable ✓). Las que
son de **comportamiento** quedaron sin implementar (D-10, D-11 y D-12 ✗) y son
las que el frontend tiene que confirmar.

| # | Tema | Qué hay que decidir | Recomendación | Estado |
|---|---|---|---|---|
| D-1 | **AGENTS.md** | Registrar en §17 las decisiones D19-D48 y el modo demo, y actualizar §7 (modelos de `budgets`, `reports`, `notifications`) y §15 (numeración de bloques) | Adoptar el texto propuesto de `docs/agents-changelog-proposal.md` tal cual: es un registro de lo ya implementado y probado, sin cambiar reglas | ✅ **Resuelto**: el registro de la §17 quedó aplicado (commit `301beca`). Las §§7, 15 y 4 **no** se tocaron: no fueron autorizadas (siguen propuestas en `docs/agents-changelog-proposal.md`) |
| D-2 | **Dependencias nuevas** | `sentry-sdk` (errores en producción), `pip-audit` (vulnerabilidades en la CI) y `django-cors-headers` (CORS real para el front) | Agregar `sentry-sdk` y `pip-audit` (son de bajo riesgo y cierran dos huecos de §9 y de la CI). `django-cors-headers` solo cuando exista el front que consuma la API | ◐ **Parcial**: `pip-audit` ya es dependencia de desarrollo y la CI lo corre (commit `307e2a6`); las dependencias del proyecto están limpias. `sentry-sdk` y `django-cors-headers` siguen abiertos |
| D-3 | **Schema del ledger** | Agregar `CheckConstraint` de moneda (`ARS`/`USD`) a `Account` y `LedgerEntry` (B-2) | Sí: es una migración pequeña, reversible y protege el invariante de los reportes. Requiere una migración nueva y revisada (AGENTS §12) | ✅ **Resuelto**: los dos constraints están, con la migración `ledger.0003` y sus tests (commit `b875471`) |
| D-4 | **Management commands** | Ningún cambio propuesto: hoy son correctos y el usuario los pidió intocables | No tocar | ⬜ Sin cambios |
| D-5 | **Contratos de import-linter** | Ningún cambio propuesto: los 28 contratos cubren el estado actual | No tocar | ⬜ Sin cambios |
| D-6 | **Avisos fallidos** | Si un envío falla, ¿se reintenta? ¿con qué backoff? ¿y se agrupan varios avisos en un mismo email? | Reintentar con backoff exponencial (3 intentos) y **no** agrupar: un aviso por email es más simple de auditar. Es una decisión de producto | ⬜ Abierto |
| D-7 | **Negocio** | `payments` (O1: proveedor), custodia (O2), rendimiento de plazos fijos (O3), PLA/FT (O5) y CFT (O6) | Depende del cliente: sin O1 no se puede empezar el Bloque 7 | ⬜ Abierto |
| D-8 | **CORS real** | Instalar `django-cors-headers` o resolver el CORS en el proxy inverso | Resolverlo en el proxy: menos dependencias y el front igual necesita el dominio configurado | ✅ **Resuelto** (2026-10-21): `django-cors-headers` es dependencia de producción, el middleware responde el preflight, `CORS_ALLOWED_ORIGINS` viene del entorno (sin `*`, vacío = ninguno) y no se permiten credenciales (la autenticación va en `Authorization`) |
| D-9 | **Fijar imágenes a digest** | Fijar `postgres`, `redis` y `caddy` a un digest o a un parche exacto | Fijar a digest: el tag mayor deja entrar parches de seguridad sin control | ⬜ Abierto |
| D-10 | **Los movimientos del ledger no traen importe ni moneda** | `GET /api/v1/ledger/transactions/` devuelve el tipo, la fecha, la descripción y la cuenta de destino, pero no el **importe** ni la **moneda** (el frontend los tiene que pedir en `GET /api/v1/reports/movements/`, que además pagina). ¿Se suman el importe y la moneda al listado de movimientos? | **Sí**: el historial de una billetera sin el importe es inservible y obliga al front a saltar a otro endpoint. El cambio es de **comportamiento** (agregar dos campos al serializer del listado) y no se hizo porque el frontend tiene que confirmar que no le rompe la paginación por cursor ni el formato de los importes (string decimal) |
| D-11 | **Las posiciones de inversión no traen la moneda** | `GET /api/v1/investments/positions/` solo devuelve el `id` del producto: para saber la moneda hay que pedir el detalle (`product_detail`). ¿Se suma la moneda (y quizá el plazo y la tasa) al listado? | **Sí**, por el mismo motivo: el listado de posiciones es una pantalla del front y sin la moneda no se puede mostrar el importe. El detalle ya trae `product_detail` ✓, así que la opción menos invasiva es sumar `currency` (y no más) al listado |
| D-12 | **`GET /api/v1/kyc/` responde el body vacío, no `null`** | Sin verificación el endpoint responde 200 con el body **vacío** (no la cadena `null`). El esquema ya lo declara nullable ✓ y el frontend lo lee como null ✓, así que no hay nada roto: alcanza con corregir la tabla del contrato | **Ninguna decisión**: es una aclaración del contrato (`docs/backend-contract.md` dice `null`; la API responde vacío). Lo que sí se puede decidir es si la API debería responder `null` explícito para que los dos clientes coincidan: **cambiarlo sería tocar el comportamiento** ✗, así que quedó como está |

Además, el desarrollador autorizó el **`check --deploy` en la CI** (B-5): la CI
corre `manage.py check --deploy --fail-level WARNING` con los settings de
producción y falla con cualquier aviso (commit `caac920`). El único aviso que
queda (el preload del HSTS, `security.W021`) está silenciado en los settings de
producción con la razón escrita al lado, porque el preload es irreversible y la
decisión es del cliente.

**Aclaraciones del contrato del frontend** (no son decisiones, son diferencias
entre la tabla del contrato y lo que la API responde de verdad):

- El **409** no se responde con el código genérico `conflict` ✗: la API responde
  el código del dominio (`duplicate_category` para un presupuesto o una
  categoría repetidos ✓, `idempotency_conflict` para la misma clave de
  idempotencia con otro payload ✓). La tabla del contrato dice `conflict` ✗ →
  hay que corregirla ✓.
- `GET /api/v1/kyc/` responde el **body vacío** (no `null`) cuando el usuario
  no pidió la verificación ✗ → ver D-12 ✓.
- Los **importes** viajan como string decimal ✓ (`"1500.50"`) ✓ → el esquema
  ya lo dice ✓ (no hubo que tocarlo ✓).
