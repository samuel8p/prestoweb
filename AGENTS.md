# PROYECTO: Presto (Django + PostgreSQL)

> **Para la IA que lea este documento:** este archivo es la fuente de verdad del proyecto. Seguí estas reglas al pie de la letra. Si una instrucción del usuario contradice este documento, **avisá del conflicto antes de actuar** y esperá confirmación. Si algo no está definido acá, **preguntá en lugar de inventar**. Nunca tomes decisiones de arquitectura por tu cuenta.

---

## 1. Contexto

- **Producto:** Presto. App de finanzas e inversiones con marketplace de préstamos. Se crean ofertas de préstamo y quien busca préstamo las compara y elige la que mejor se adapta.
- **Presto CUSTODIA los fondos de los usuarios y mueve dinero entre ellos.**
- **Monedas:** ARS y USD. Cada usuario tiene una cuenta por moneda, sin conversión implícita.
- **Usuarios:** personas que buscan préstamos y personas que prestan o invierten.
- **Frontend:** solo backend (API-only). **Fecha de entrega:** sin definir.
- **TODO:** proveedor de pagos y bancos, KYC, marco regulatorio (custodia de fondos, bonos y fondos), método de amortización (francés por defecto).

---

## 2. Decisión de arquitectura (NO modificar)

**Monolito modular.** Un solo proyecto Django, una sola base de datos PostgreSQL, un solo despliegue.

- **Prohibido:** microservicios, API gateway, brokers de mensajes (RabbitMQ, Kafka), múltiples bases de datos, múltiples repositorios, Kubernetes.
- **Motivo:** un solo desarrollador, proyecto de cliente, dominio financiero donde las transacciones ACID de una única base son más seguras que la consistencia distribuida.
- Si en el futuro hace falta extraer un módulo, las reglas de la sección 5 garantizan que sea posible. **No anticipes esa extracción.**

---

## 3. Stack tecnológico

| Área | Tecnología |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework | Django 5.x |
| API | Django REST Framework |
| Base de datos | PostgreSQL 16 |
| Tareas asíncronas | Celery + Redis (solo para tareas reales: emails, reportes pesados, importaciones) |
| Autenticación | JWT con `djangorestframework-simplejwt` |
| Documentación API | `drf-spectacular` (OpenAPI) |
| Tests | `pytest`, `pytest-django`, `factory_boy` |
| Calidad | `ruff` (lint + formato), `pre-commit`, `import-linter` |
| Gestión de dependencias | `uv` o `poetry` (usar el que ya esté en el repo; no mezclar) |
| Contenedores | Docker + Docker Compose |
| CI | GitHub Actions |
| Errores en producción | Sentry |

**Regla de dependencias:** no agregues librerías nuevas sin justificarlas y pedir confirmación. Preferí la librería estándar y Django antes que un paquete externo.

---

## 4. Estructura del repositorio

```
finanzas/
├── AGENTS.md                 # Este documento
├── README.md
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
├── .env.example                # Todas las variables, sin valores secretos
├── pyproject.toml
├── .pre-commit-config.yaml
├── .importlinter               # Contratos de límites entre apps
├── manage.py
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── test.py
│   │   └── production.py
│   ├── urls.py
│   ├── celery.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── core/                   # Utilidades transversales, SIN lógica de negocio
│   │   ├── models.py           # BaseModel abstracto (UUID, timestamps)
│   │   ├── money.py            # Helpers de dinero
│   │   ├── exceptions.py
│   │   └── pagination.py
│   ├── identity/               # Usuarios, autenticación, perfiles
│   ├── ledger/                 # Libro mayor de doble entrada (núcleo)
│   ├── payments/               # Depósitos y retiros vía proveedor externo, webhooks, conciliación
│   ├── offers/                 # Ofertas de préstamo (monto, moneda, tasa, plazo, requisitos, estado)
│   ├── matching/               # Búsqueda, comparación y recomendación (solo lectura, vía selectors)
│   ├── loans/                  # Préstamos tomados, cuotas, estados
│   ├── investments/            # Productos: plazo fijo, bono, fondo
│   ├── budgets/                # Presupuestos, metas, alertas
│   ├── reports/                # Resúmenes y exportaciones
│   └── notifications/          # Emails y avisos
├── docs/
│   ├── architecture.md
│   └── adr/                    # Un archivo por decisión importante
└── .github/workflows/ci.yml
```

### Estructura obligatoria dentro de cada app de dominio

```
apps/<nombre>/
├── __init__.py
├── apps.py
├── models.py
├── services.py        # Lógica de ESCRITURA y reglas de negocio (interfaz pública)
├── selectors.py       # Lógica de LECTURA / consultas (interfaz pública)
├── serializers.py
├── views.py           # Finas: validan, llaman a services/selectors, responden
├── urls.py
├── permissions.py
├── signals.py         # Eventos internos (si aplica)
├── tasks.py           # Tareas Celery (si aplica)
├── admin.py
├── migrations/
└── tests/
    ├── test_models.py
    ├── test_services.py
    ├── test_selectors.py
    ├── test_api.py
    └── factories.py
```

---

## 5. Reglas de diseño (OBLIGATORIAS)

### 5.1 Capas y responsabilidades

- **`views.py`:** sin lógica de negocio. Solo: autenticar, validar entrada con serializers, llamar a un service o selector, devolver respuesta.
- **`services.py`:** toda la lógica que **modifica** estado. Funciones con argumentos explícitos y tipados. Usan `transaction.atomic` cuando corresponde.
- **`selectors.py`:** toda la lógica que **lee** datos y arma consultas (filtros, agregaciones, `select_related`/`prefetch_related`).
- **`models.py`:** campos, constraints, métodos triviales. **Sin** lógica de negocio compleja y **sin** llamadas a servicios.
- **Prohibido** poner lógica de negocio en serializers, signals, `save()` sobreescritos o templates.

### 5.2 Límites entre apps

1. Una app **solo puede usar a otra mediante su `services.py` y `selectors.py`**. Nunca importar modelos de otra app para consultarlos o modificarlos directamente. **Excepción documentada:** `signals.py` puede importar modelos de otra app para implementar la comunicación por señales (§5.3); los receptores resuelven la lógica de negocio llamando a `services.py` de la app dueña.
2. **Prohibidas las `ForeignKey` entre apps de dominios distintos.** Referenciar con un campo `UUIDField` (ej. `user_id`) y resolver mediante el selector de la app dueña. Excepción única: `ledger` puede apuntar a `settings.AUTH_USER_MODEL`.
3. `core` no puede importar de ninguna otra app. Las demás apps pueden importar de `core`.
4. Estos límites se verifican con `import-linter` en CI. **Si el chequeo falla, el cambio no se acepta.**

### 5.3 Comunicación entre apps

- Para efectos secundarios (ej. "se creó una transacción → recalcular presupuesto"), usar **señales personalizadas de Django** definidas en la app emisora (`signals.py`) y receptores en la app interesada.
- Los receptores que hagan trabajo pesado o con I/O externo deben delegar a una **tarea Celery**.
- Los receptores deben ser **idempotentes** (ejecutarlos dos veces no debe romper nada).

---

## 6. Reglas de dinero (CRÍTICAS)

1. **Nunca usar `float`** para montos. Usar `DecimalField(max_digits=18, decimal_places=2)` o enteros en la unidad mínima. **Elegir uno y usarlo en todo el proyecto**: `DecimalField` por defecto.
2. Usar `Decimal` de Python en toda la lógica. Construir siempre desde `str`, nunca desde `float` (`Decimal("10.50")`, no `Decimal(10.5)`).
3. Cada monto está asociado a una **moneda** (código ISO 4217, ej. `ARS`, `USD`). No sumar ni comparar montos de monedas distintas sin conversión explícita.
4. **Las transacciones son inmutables.** No se editan ni se borran físicamente. Para corregir un error se crea una **transacción compensatoria (reverso)** que referencia la original.
5. Todo endpoint o service que cree dinero/transacciones debe soportar una **`idempotency_key`** única para evitar duplicados por reintentos.
6. Toda operación que afecte varios registros (ej. transferencia entre cuentas) va dentro de `transaction.atomic()` y debe bloquear filas con `select_for_update()` cuando haya riesgo de condición de carrera.
7. El saldo de una cuenta se **deriva de las transacciones** (o se mantiene como campo denormalizado verificable contra ellas). Nunca editar un saldo "a mano".
8. Redondeo: definir una única función en `core/money.py` y usarla en todo el proyecto. No redondear en otros lugares.

## Reglas adicionales de dinero

1. **Doble entrada:** cada movimiento genera asientos; débitos = créditos, validado en DB y en tests.
2. **Custodia:** los fondos de usuarios se registran en cuentas de custodia del ledger. El total de saldos de usuarios debe coincidir con el saldo real en el banco o proveedor (conciliación diaria automática con alerta si hay diferencia).
3. **Saldo nunca negativo:** un saldo nunca puede quedar negativo. Reservas (holds) para operaciones en curso.
4. **Depósito con confirmación del proveedor:** un depósito se acredita solo con confirmación del proveedor (webhook firmado, idempotente). Nunca por confirmación del cliente.
5. **Retiros:** verificación, límites y registro de auditoría completo.
6. **Snapshot de oferta al aceptar:** al aceptar una oferta se guarda un snapshot inmutable de sus términos (tasa, plazo, reglas), con fecha y usuario. El cronograma de cuotas se calcula una sola vez, en core/money.py con Decimal, y se persiste. Editar una oferta nunca modifica préstamos ya creados.
7. **Estados de préstamo como máquina de estados:** transiciones válidas entre estados, en inglés: `active` | `pending` | `paid` | `defaulted`.
8. **Todo movimiento por ledger:** todo movimiento de dinero, incluidos investments, pasa por ledger.

---

## 7. Modelos base (punto de partida)

Todos los modelos heredan de `core.models.BaseModel`:

```python
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

### `identity`

- **User:** `AbstractUser` con email como login y **sin `username`** (migración que lo elimina). `UserManager` propio: `create_user(email, password)`. Clave primaria `UUID`.
- **Profile:** `user` (1:1 con User), `phone_number`, `date_of_birth`, `country` (ISO 3166-1 alpha-2).
- **KYCVerification:** `user` (FK, historial de solicitudes), `status` (`pending` | `approved` | `rejected`), `requested_at`, `resolved_at` (nullable), `resolved_by_user_id` (`UUIDField` nullable), `documents` (JSON, **solo metadata**, sin datos sensibles). **Una sola verificación `pending` por usuario** (`UniqueConstraint` condicional).

### `ledger`

- **Account:** `user_id`, `currency` (`ARS` | `USD`), `kind` (`user_wallet` | `custody` | `system`). **Uno solo por user_id y currency.** **Sin campo `amount`:** el saldo se deriva de los asientos (§6 regla 7).
- **LedgerTransaction:** `type` (`deposit` | `withdrawal` | `transfer` | `interest` | `fee` | `reversal`), `idempotency_key` (único), `occurred_at`, `description`, `reverses` (FK a sí misma, opcional). **Regla DB:** por cada transacción, suma de débitos = suma de créditos.
- **LedgerEntry:** `ledger_transaction`, `account`, `direction` (`debit` | `credit`), `amount` (`Decimal`, `> 0`), `currency`. **Por cada LedgerTransaction, sum(debits) = sum(credits).**

### `payments`

- **Payment:** `user_id`, `direction` (`deposit` | `withdrawal`), `amount` (`Decimal`, `> 0`), `currency`, `provider` (código proveedor externo), `provider_reference` (único), `status` (`pending` | `confirmed` | `failed` | `reversed`), `idempotency_key` (único).

### `offers`

- **Offer:** `lender_user_id`, `amount` (`Decimal`, `> 0`), `currency`, `interest_rate` (`Decimal`), `term_months`, `requirements` (texto), `status` (`active` | `expired` | `accepted`).

### `loans`

- **Loan:** `borrower_user_id`, `lender_user_id`, `offer_id` (UUID), `principal` (`Decimal`, `> 0`), `currency`, `status` (`active` | `pending` | `paid` | `defaulted`).
- **OfferTermsSnapshot:** `loan` (único por loan), `accepted_at`, `accepted_by_user_id`, `snapshot_data` (JSON con tasa, plazo, reglas), `is_immutable` (siempre `True`).
- **Installment:** `loan`, `number`, `due_date`, `principal_amount` (`Decimal`, `> 0`), `interest_amount` (`Decimal`, `>= 0`), `status` (`pending` | `paid` | `overdue`), `paid_at` (nullable).

### `investments`

- **InvestmentProduct:** `type` (`fixed_term` | `bond` | `fund`), `currency`, `conditions` (JSON con tasas, fechas, reglas), `status` (`active` | `matured` | `cancelled`).
- **Position:** `user_id`, `product`, `amount` (`Decimal`, `> 0`), `status` (`active` | `matured` | `cancelled`), `opened_at`, `maturity_date`.

### `budgets`

- **Budget:** `user_id`, `category_id` (UUID, sin FK), `period` (`monthly`), `limit_amount` (`Decimal`, `> 0`), `currency`, `alert_threshold` (`Integer`, porcentaje).
- **Goal:** `user_id`, `name`, `target_amount` (`Decimal`, `> 0`), `current_amount` (`Decimal`, `>= 0`), `deadline`.
- **TODO (Fase 6):** categorías de gasto personal.

**Regla de dinero:** todos los montos son `Decimal` con `constraint amount > 0` donde corresponda. Ninguna app de dominio distinto puede tener ForeignKey a models de otra app; usar `UUIDField` para referencias.

---

## 8. Convenciones de API

- Prefijo y versión: `/api/v1/`.
- Recursos en plural y en inglés: `/api/v1/accounts/`, `/api/v1/transactions/`.
- Formato: JSON. Fechas en ISO 8601 (UTC). Montos como **string** decimal en las respuestas (`"1250.50"`) para evitar errores de coma flotante en el cliente.
- Identificadores públicos: UUID. Nunca exponer IDs autoincrementales.
- Paginación obligatoria en listados (por cursor para transacciones; límite máximo por página).
- Filtros y ordenamiento mediante `django-filter` o parámetros explícitos documentados.
- Errores con un formato uniforme:

```json
{
  "error": {
    "code": "insufficient_funds",
    "message": "Mensaje legible en español.",
    "details": {}
  }
}
```

- Códigos HTTP correctos: `201` crear, `400` validación, `401` sin autenticar, `403` sin permiso, `404` no encontrado, `409` conflicto (ej. idempotency key repetida con distinto payload).
- Toda vista debe estar documentada con `drf-spectacular` (`extend_schema`).

---

## 9. Seguridad (OBLIGATORIO)

1. **Aislamiento por usuario:** cada consulta filtra por el usuario autenticado. Un usuario nunca debe poder leer ni modificar datos de otro. **Cada endpoint debe tener un test que lo verifique** (intento de acceso cruzado → 404 o 403).
2. Secretos solo en variables de entorno. **Nunca** commitear claves, tokens ni contraseñas. Mantener `.env.example` actualizado.
3. `DEBUG=False` en producción. `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `CORS_ALLOWED_ORIGINS` configurados explícitamente (nada de `*`).
4. HTTPS obligatorio en producción (`SECURE_SSL_REDIRECT`, cookies seguras, HSTS).
5. Contraseñas con los validadores de Django activos; hasher Argon2 preferido.
6. Rate limiting (throttling de DRF) en login, registro y recuperación de contraseña.
7. Nunca registrar en logs: contraseñas, tokens, números de tarjeta ni datos personales sensibles.
8. **No almacenar datos de tarjetas.** Si hace falta cobrar, se delega a un proveedor de pagos.
9. **KYC obligatorio:** la verificación KYC es obligatoria antes de operar con dinero. No se permiten depósitos, retiros ni operaciones de inversión sin KYC completado.
10. Auditoría: registrar quién hizo qué y cuándo en operaciones financieras.
11. Usar siempre el ORM o consultas parametrizadas. **Prohibido** construir SQL concatenando strings.

---

## 10. Testing

- **Cobertura mínima:** 90% en `services.py` de `ledger` y `budgets`; 80% general.
- Tests obligatorios para:
  - Toda regla de dinero (redondeo, saldos, reversos, transferencias, idempotencia).
  - Permisos y aislamiento entre usuarios.
  - Condiciones de borde (montos cero, negativos, muy grandes, monedas distintas).
  - Concurrencia en operaciones que modifican saldos.
- Usar `factory_boy` para datos de prueba. No usar fixtures JSON gigantes.
- Los tests deben correr contra **PostgreSQL real** (no SQLite).
- **Todo bug corregido debe incluir un test que lo reproduzca.**
- No se da por terminada una tarea si los tests no pasan.

---

## 11. Estilo de código

- Formato y lint con `ruff`. Línea máxima: 100 caracteres.
- **Type hints** en todas las funciones de `services.py` y `selectors.py`.
- Nombres descriptivos en inglés; funciones en `snake_case`, clases en `PascalCase`.
- Funciones cortas con una sola responsabilidad. Si una función supera ~40 líneas, evaluar dividirla.
- Docstrings en español para services y selectors públicos (qué hace, argumentos, excepciones).
- Excepciones de dominio propias (en `core/exceptions.py` o por app); no usar `Exception` genérica.
- Nada de `print()` para depurar: usar `logging`.
- Sin código comentado, sin `TODO` sin explicación, sin "magia" innecesaria.

---

## 11.b Metodología: TDD y código limpio

### TDD (Test-Driven Development)

1. **Prohibido escribir código de producción sin antes tener un test que falle.**
   El flujo comienza siempre con un test; sin test, no hay producción.
2. **Red: escribí UN test, ejecutálo y confirmá que falla por la razón correcta.**
   El test debe fallar por una razón esperada (módulo inexistente, función sin implementar, etc.). Si el test ya pasa, no estás escribiendo un test Rojo nuevo.
3. **Green: escribí el mínimo código para que pase. Nada más.**
   Implementá solo lo necesario para que el test pase. Sin funcionalidad extra, sin optimización prematura.
4. **Refactor: limpiá el código con todos los tests en verde.**
   Una vez que el test pasa, mejorá la estructura, nombres y diseño del código, asegurándote de que todos los tests sigan verdes.
5. **Repetí en ciclos pequeños, un comportamiento por vez.**
   Un test pequeño por cada comportamiento nuevo. No intentes cubrir todo el sistema de una sola vez.
6. **Mostrá la salida real de pytest en cada paso (rojo y verde). Sin evidencia, el paso no cuenta.**
   Los logs de los tests deben mostrarse y guardarse. Un paso "Rojo" o "Verde" sin salida registrada no es válido.
7. **Nunca modifiques ni borres un test para hacerlo pasar.**
   Si el test falla, el código está mal o falta implementar. Si el requisito cambió, avisá y esperá confirmación antes de modificar tests.
8. **Bug: primero un test que lo reproduce, después el arreglo.**
   Todo bug debe tener un test que lo reproduzca antes de implementar la corrección. El test reproduce el bug, luego se corrige el código.
9. **Empezá siempre por los tests de las reglas de dinero (ledger, cuotas, redondeo, idempotencia).**
   El manejo de dinero es crítico; la cobertura mínima es 90% en services.py de ledger y budgets.

### CÓDIGO LIMPIO

1. **Nombres que revelen la intención; sin abreviaturas crípticas.**
   Variable y función nombres deben decir "qué hacen", no "cómo lo hacen".
2. **Funciones cortas con una sola responsabilidad.**
   Si una función supera ~40 líneas, evaluar dividirla. Cada función debe hacer una cosa bien.
3. **Sin duplicación, pero sin abstracciones prematuras.**
   Elimina la duplicación que ya existen; no construyas lo que no se pidió aún (YAGNI).
4. **Si el código necesita un comentario para entenderse, reescribilo más claro.**
   Código autoexplicativo es preferible a comentarios enredados.
5. **Errores con excepciones de dominio, nunca silenciados.**
   Usá excepciones propias de la aplicación (en `core/exceptions.py` o por app); no usar `Exception` genérica ni `try/except` vacíos.
6. **Sin código muerto ni comentado.**
   Todo código debe estar activo y justificado. Remover código que ya no se usa.
7. **Dejá el código mejor de como lo encontraste, dentro del alcance de la tarea.**
   Cada cambio debe mejorar la calidad del proyecto, aunque sea un pequeño paso.

### PROFESIONALISMO

1. **No declares una tarea terminada sin tests en verde, ruff e import-linter sin errores.**
   El "Done" incluye la evidencia de tests, linting y límites de importación.
2. **Si algo es ambiguo o riesgoso, avisame antes de implementar.**
   Dudas o riesgos deben comunicarse antes de escribir código, no después.
3. **Si una instrucción mía contradice AGENTS.md, advertilo antes de actuar.**
   Las contradicciones al documento fuente deben señalarse antes de proceder.
4. **Cambios pequeños y commits pequeños.**
   Commits atómicos con mensajes claros (Conventional Commits). Un cambio por commit.

---

## 12. Base de datos y migraciones

- Una sola base: PostgreSQL. Configuración por `DATABASE_URL`.
- **Toda migración se revisa antes de aplicarse.** Nunca editar una migración ya aplicada en producción: crear una nueva.
- Migraciones destructivas (borrar columnas/tablas) se hacen en dos pasos: primero dejar de usar el campo, después eliminarlo en un release posterior.
- Definir constraints e índices **en la base de datos** (`CheckConstraint`, `UniqueConstraint`, `Index`), no solo en el código.
- Evitar consultas N+1: usar `select_related` / `prefetch_related` y revisarlo en los selectors.
- Backups automáticos diarios de PostgreSQL en producción, con prueba periódica de restauración.

---

## 13. Flujo de trabajo (Git)

- Rama principal: `main` (siempre desplegable). Trabajo en ramas `feature/<descripcion>`, `fix/<descripcion>`.
- Commits pequeños con mensajes en inglés siguiendo **Conventional Commits** (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- Antes de cada commit deben pasar: `ruff`, `import-linter` y los tests.
- CI en cada push: lint, límites de importación, tests, chequeo de migraciones faltantes (`makemigrations --check`).
- Decisiones de arquitectura importantes se documentan en `docs/adr/` (un archivo corto por decisión: contexto, decisión, consecuencias).

---

## 14. Entorno y despliegue

- **Desarrollo:** `docker compose up` debe levantar todo (Django, PostgreSQL, Redis, worker de Celery). Un `Makefile` con comandos comunes: `make up`, `make test`, `make lint`, `make migrate`, `make shell`.
- **Producción:** un VPS con Docker Compose: Django + Gunicorn, PostgreSQL, Redis, worker de Celery, proxy inverso (Nginx o Caddy) con HTTPS.
- Variables de entorno documentadas en `.env.example`. Settings separados por entorno.
- Logs estructurados; Sentry para errores; endpoint `/health/` para chequeo de estado.

---

## 15. Plan de desarrollo por fases

Trabajar **una fase a la vez** y no avanzar sin confirmación del desarrollador.

**Fase 0: Cimientos**
Estructura del repo, Docker Compose, settings por entorno, `pre-commit`, CI, `import-linter`, `BaseModel`, modelo de usuario personalizado, `core/money.py`.

**Fase 1: identity y ledger**
`identity` (registro, login JWT, perfil) y `ledger` (cuentas, categorías, transacciones, reversos, transferencias, idempotencia) con depósitos simulados. Tests completos de dinero y permisos.

**Fase 2: payments**
`payments` (proveedor real, sandbox primero; depósitos y retiros vía webhooks, conciliación).

**Fase 3: offers y matching**
`offers` (ofertas de préstamo) y `matching` (búsqueda, comparación y recomendación vía selectors).

**Fase 4: loans y cuotas**
`loans` (préstamos tomados, cuotas, estados). Máquina de estados con transiciones válidas.

**Fase 5: investments**
`investments` (plazo fijo primero; bonos y fondos después, requieren precios externos).

**Fase 6: budgets, reports y notifications**
budgets, reports (resúmenes y exportaciones) y notifications (emails).

**Fase 7: producción**
Hardening de seguridad, backups, monitoreo, documentación final y despliegue.

---

## 16. Cómo debe trabajar la IA (instrucciones directas)

**Antes de escribir código:**
1. Leé este documento completo.
2. Confirmá en qué fase estamos y qué se pide.
3. Si la tarea es ambigua o toca una decisión no definida, **hacé preguntas concretas antes de implementar**.

**Al escribir código:**
1. Respetá la estructura de carpetas y las capas (sección 4 y 5) sin excepciones.
2. Entregá cambios **pequeños y completos**: código + tests + migración (si aplica) en el mismo paso.
3. Explicá brevemente **qué hiciste y por qué**, y señalá cualquier decisión que hayas tenido que tomar.
4. Si encontrás un error, riesgo o una mejor alternativa, **decilo**, aunque contradiga lo pedido.

**Prohibiciones explícitas:**
- No introducir microservicios, brokers, ni nuevas bases de datos.
- No usar `float` para dinero.
- No editar ni borrar transacciones: se compensan.
- No crear `ForeignKey` entre apps de dominios distintos.
- No poner lógica de negocio en views, serializers, signals ni modelos.
- No agregar dependencias sin pedir confirmación.
- No omitir tests ni "dejarlos para después".
- No commitear secretos.
- No inventar requisitos, campos o endpoints que no estén definidos: preguntar.

**Definición de "terminado" (checklist):**
- [ ] Cumple la estructura y reglas de este documento.
- [ ] Tests nuevos escritos y toda la suite pasa.
- [ ] `ruff` e `import-linter` sin errores.
- [ ] Migraciones generadas y revisadas.
- [ ] Endpoints documentados en OpenAPI.
- [ ] Permisos y aislamiento entre usuarios verificados con tests.
- [ ] Sin secretos ni datos sensibles en el código o los logs.
- [ ] Documentación actualizada si cambió algo relevante (README / ADR).
- [ ] **Ciclo Red-Green-Refactor evidenciado con la salida de pytest.**

---

## 17. Registro de cambios de este documento

Todo cambio a este archivo debe ser aprobado por el desarrollador y anotarse aquí.

| Fecha | Cambio |
|---|---|
| 2026-10-20 | Versión inicial: arquitectura de monolito modular. |
| 2026-10-20 | Actualización de contexto, apps, reglas de dinero, modelos, seguridad y plan de fases para Presto con marketplace de préstamos, custodia, KYC, y nuevas apps (payments, offers, matching, loans, investments). |
| 2026-10-20 | Sección 11.b añadida: Metodología TDD y código limpio. Sección 16 actualizada: item "Ciclo Red-Green-Refactor evidenciado con la salida de pytest". |
| 2026-10-20 | Sección 7 actualizada: modelos de identidad, ledger (custodia doble entrada), payments, offers, loans, investments, budgets, con constraints de dinero y referencias UUID entre apps. |
| 2026-10-20 | **Fase 1A (identity) — decisiones registradas.** (a) `User` sin `username` con `UserManager` por email; (b) `Profile` 1:1 con `User` y campos `phone_number`, `date_of_birth`, `country`; (c) `KYCVerification` con FK a `User` e historial, `UniqueConstraint` condicional de una sola verificación `pending` por usuario, campos `status`/`requested_at`/`resolved_at`/`resolved_by_user_id`/`documents`; (d) la resolución de KYC la hace una acción del Django admin que invoca `services.resolve_kyc`; (e) throttling con scope: login `5/min`, register `5/hour`; (f) log de decisiones de KYC con `logging`, sin datos sensibles. Extras: `selectors.is_kyc_approved(user_id)`, refresh de JWT con rotación y blacklist, `EXCEPTION_HANDLER` con el formato de error de §8, `drf-spectacular` en todas las vistas. |
| 2026-10-20 | **Correcciones de nomenclatura y constraints.** Estados de préstamo en inglés: `active` \| `pending` \| `paid` \| `defaulted` (§6 regla 7 y §7 `loans`). `Account` **sin** campo `amount` ni constraint `amount >= 0`: el saldo se deriva de los asientos (§6 regla 7). `KYCVerification` con campos en inglés (`status`, `requested_at`, `resolved_at`, `resolved_by_user_id`, `documents`) (§7 `identity`). `signals.py` como **excepción documentada** a la regla de imports entre apps (§5.2 regla 1), con la lógica de negocio delegada a `services.py` de la app dueña. |
