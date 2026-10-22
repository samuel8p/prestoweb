# Contrato de la API de Presto (verificado)

Este documento describe **cómo responde realmente** la API de Presto. La fuente
primaria es [`openapi.yaml`](./openapi.yaml), generado en el repo del backend con
`python manage.py spectacular --file openapi.yaml`.

El esquema y la API real coinciden en las formas de los datos, pero el esquema
**no declara** todo lo que la API exige o devuelve. Acá está la lista de esas
diferencias, verificada contra el backend corriendo (`http://127.0.0.1:8000`).
El frontend está construido contra esta realidad, no contra una suposición.

## 1. Autenticación

|          |                                                                                                |
| -------- | ---------------------------------------------------------------------------------------------- |
| Login    | `POST /api/v1/auth/login/` → `{ access, refresh, user }`                                       |
| Refresh  | `POST /api/v1/auth/token/refresh/` con body `{ "refresh": "<token>" }` → `{ access, refresh }` |
| Registro | `POST /api/v1/auth/register/` con `{ email, password }` → `201` con el usuario                 |
| Header   | `Authorization: Bearer <access>`                                                               |

- El refresh **rota** el token: el anterior queda en blacklist y no sirve más.
  Hay que guardar siempre el refresh más reciente.
- El login y el registro tienen **throttle**: 5/min y 5/hora respectivamente
  (`429` con `code: "throttled"`).
- El refresh **no** está declarado en el esquema (no declara `requestBody`).

## 2. Header `Idempotency-Key`

Es obligatorio en los tres endpoints que mueven dinero o crean un préstamo:

- `POST /api/v1/ledger/transactions/`
- `POST /api/v1/loans/`
- `POST /api/v1/investments/positions/`

Si falta, la API responde `400` con:

```json
{
  "error": {
    "code": "validation_error",
    "message": "…",
    "details": { "idempotency_key": ["El header Idempotency-Key es obligatorio."] }
  }
}
```

La clave es única **por usuario**. Con la misma clave y el mismo payload la API
devuelve la operación original; con la misma clave y otro payload responde
`409` con `code: "idempotency_conflict"`.

## 3. Paginación

La API usa dos paginaciones distintas y el esquema declara los listados como
si fueran un objeto suelto (no es así):

| Endpoint                           | Forma de la respuesta                                                                                    |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `GET /api/v1/ledger/transactions/` | `{ next, previous, results }` — **por cursor**, sin `count` (página de 50, máximo 200)                   |
| Todos los demás listados           | `{ count, next, previous, results }` — por página (página de 100, `page_size` configurable, máximo 1000) |

`next` y `previous` son URLs completas: para pedir la página siguiente hay que
seguir la URL, no armar el query string a mano.

**Ojo con los productos de inversión:** el esquema declara
`GET /api/v1/investments/products/` como un array plano, pero el backend lo
pags igual que a los demás y devuelve `{ count, next, previous, results }`. El
frontend lo trata como una lista paginada.

### 3.b Lo que el esquema no dice de los datos

Verificado contra la API corriendo:

- `GET /api/v1/ledger/transactions/` **no devuelve el importe ni la moneda**:
  solo el tipo, la fecha, la descripción y la cuenta de destino. El importe y
  la marca de revertido están en `GET /api/v1/reports/movements/` (que además
  pagina y filtra por moneda y rango). Por eso el historial de movimientos de
  la app usa ese endpoint.
- `GET /api/v1/investments/positions/` **no devuelve la moneda** de la posición:
  solo el `id` del producto. Para saber en qué moneda está hay que pedir
  `GET /api/v1/investments/positions/{id}/`, que trae `product_detail` con la
  moneda, el plazo y la tasa.
- `GET /api/v1/kyc/` devuelve **`null`** cuando el usuario todavía no pidió la
  verificación (el esquema no lo declara nullable).

## 4. Errores

Formato único (AGENTS §8 del backend):

```json
{
  "error": {
    "code": "validation_error",
    "message": "Los datos enviados no son válidos.",
    "details": { "amount": ["A valid number is required."] }
  }
}
```

- `details` es un objeto con **el nombre del campo** y una lista de mensajes.
  Los errores de validación se muestran por campo.
- Códigos que devuelve la API:

| Código                 | HTTP  | Cuándo                                                     |
| ---------------------- | ----- | ---------------------------------------------------------- |
| `validation_error`     | 400   | datos inválidos (el `details` dice el campo)               |
| `not_authenticated`    | 401   | falta o venció el token                                    |
| `permission_denied`    | 403   | sin permiso; **también** es el código del KYC no aprobado  |
| `not_found`            | 404   | el recurso no existe o no es del usuario                   |
| `method_not_allowed`   | 405   | método HTTP incorrecto                                     |
| `conflict`             | 409   | conflicto genérico (por ejemplo, un presupuesto duplicado) |
| `idempotency_conflict` | 409   | misma clave de idempotencia con otro payload               |
| `throttled`            | 429   | demasiados intentos                                        |
| `api_error`            | otros | error no clasificado                                       |

El KYC se distingue por el mensaje: `"Necesitás completar la verificación KYC
para realizar esta operación."`.

## 5. Modo demo

`GET /api/v1/meta/` es público y **no** pide token:

```json
{ "mode": "demo", "simulated_money": true }
```

Cuando `mode` es `demo` la API responde además con el header
`X-Presto-Mode: demo`. Si el endpoint falla, la app sigue funcionando sin
cartel.

## 6. Reportes

Los cuatro reportes aceptan query params que **el esquema no declara**:

| Param      | Obligatorio | Detalle                                                             |
| ---------- | ----------- | ------------------------------------------------------------------- |
| `currency` | sí          | `ARS` o `USD`. Sin él: `400`                                        |
| `from`     | no          | fecha ISO (`YYYY-MM-DD`). Por defecto, el primer día del mes actual |
| `to`       | no          | fecha ISO. Por defecto, el último día del mes actual                |
| `export`   | no          | `csv` para bajar el CSV. Cualquier otro valor: `400`                |

- El rango no puede superar **12 meses calendario**.
- `from` posterior a `to` → `400`.
- El CSV responde `text/csv` con `Content-Disposition: attachment`.
- `GET /api/v1/reports/movements/` devuelve el formato paginado
  `{ count, next, previous, results }`.

## 7. Búsqueda de ofertas

`GET /api/v1/matching/offers/` acepta (según el esquema):

`currency`, `amount_min`, `amount_max`, `max_rate`, `term_months` y
`ordering` (`rate` | `term` | `amount`).

Los importes del filtro van como **string decimal** (`"10000.00"`), no como
número.

## 8. Importes

Todos los importes llegan como **string decimal** con dos decimales
(`"1500.50"`), incluso los negativos. Nunca se convierten a `Number`: el
frontend los formatea y compara como strings (ver `src/lib/money`).

---

## 9. Qué hay que corregir en el esquema

Checklist exacto para que `docs/openapi.yaml` describa la API real. Cada punto
está verificado contra la API corriendo. Los ejemplos de YAML son los que
genera `drf-spectacular` con la misma convención del archivo actual.

### 9.1 Header `Idempotency-Key` (falta en 3 endpoints)

Es **obligatorio** y sin él la API responde `400` con
`details: { "idempotency_key": [...] }`. Hay que declararlo como parámetro de
header:

```yaml
parameters:
  - in: header
    name: Idempotency-Key
    required: true
    schema:
      type: string
```

Endpoints:

- `POST /api/v1/ledger/transactions/`
- `POST /api/v1/loans/`
- `POST /api/v1/investments/positions/`

### 9.2 Parámetros de los reportes (hoy no hay ninguno declarado)

Los cuatro reportes aceptan `currency` y, dos de ellos, un rango de fechas.
Ninguno está declarado en el esquema.

```yaml
parameters:
  - in: query
    name: currency
    required: true
    schema:
      enum: [ARS, USD]
      type: string
  - in: query
    name: from
    required: false
    schema:
      type: string
      format: date
  - in: query
    name: to
    required: false
    schema:
      type: string
      format: date
  - in: query
    name: export
    required: false
    schema:
      enum: [csv]
      type: string
```

| Endpoint                           | `currency`  | `from` / `to` | `export` |
| ---------------------------------- | ----------- | ------------- | -------- |
| `GET /api/v1/reports/spending/`    | obligatorio | opcional      | opcional |
| `GET /api/v1/reports/movements/`   | obligatorio | opcional      | opcional |
| `GET /api/v1/reports/loans/`       | obligatorio | —             | opcional |
| `GET /api/v1/reports/investments/` | obligatorio | —             | opcional |

Los defaults: sin `from`/`to` el reporte va del primer al último día del mes
calendario actual (UTC). El rango no puede pasar de **12 meses calendario** y
`from` posterior a `to` se rechaza.

### 9.3 La paginación: los listados devuelven un sobre, no el objeto suelto

El esquema declara la respuesta de cada listado como el esquema del ítem
(`Account`, `Offer`, ...), pero la API devuelve un sobre. Hay que agregar dos
componentes y usarlos en las respuestas.

```yaml
PaginatedAccount:
  type: object
  properties:
    count: { type: integer }
    next: { type: string, format: uri, nullable: true }
    previous: { type: string, format: uri, nullable: true }
    results:
      type: array
      items: { $ref: '#/components/schemas/Account' }
  required: [count, next, previous, results]
```

El de cursor (sin `count`):

```yaml
CursorPaginatedLedgerTransaction:
  type: object
  properties:
    next: { type: string, format: uri, nullable: true }
    previous: { type: string, format: uri, nullable: true }
    results:
      type: array
      items: { $ref: '#/components/schemas/LedgerTransaction' }
  required: [next, previous, results]
```

**Lista completa de los listados** (todos devuelven el sobre `Paginated*`):

| Endpoint                             | Envoltorio a usar                  |
| ------------------------------------ | ---------------------------------- |
| `GET /api/v1/ledger/accounts/`       | `PaginatedAccount`                 |
| `GET /api/v1/ledger/transactions/`   | `CursorPaginatedLedgerTransaction` |
| `GET /api/v1/offers/`                | `PaginatedOffer`                   |
| `GET /api/v1/matching/offers/`       | `PaginatedOfferMatch`              |
| `GET /api/v1/loans/`                 | `PaginatedLoan`                    |
| `GET /api/v1/investments/products/`  | `PaginatedInvestmentProduct` ⚠️    |
| `GET /api/v1/investments/positions/` | `PaginatedPosition`                |
| `GET /api/v1/budgets/`               | `PaginatedBudget`                  |
| `GET /api/v1/budgets/categories/`    | `PaginatedCategory`                |
| `GET /api/v1/budgets/expenses/`      | `PaginatedExpense`                 |
| `GET /api/v1/notifications/`         | `PaginatedNotification`            |
| `GET /api/v1/reports/movements/`     | `PaginatedMovementReportRow`       |

⚠️ **`GET /api/v1/investments/products/`** es el que más confunde: el esquema lo
declara como un array plano de `InvestmentProduct`, pero la API lo pagina
igual que a los demás y devuelve `{ count, next, previous, results }`.

`POST /api/v1/matching/comparisons/` **sí** devuelve un array suelto (no está
paginado): eso está bien como está.

Además, `GET /api/v1/ledger/transactions/` usa paginación por cursor: el cursor
viaja en el query param `cursor` (el default de DRF `CursorPagination`) y la
página siguiente viene completa en `next`. La página va de 50 (máximo 200).

### 9.4 `GET /api/v1/kyc/` puede devolver `null`

Hoy el esquema declara `KYCVerification`, pero si el usuario nunca pidió la
verificación la API responde `null`. Hay que marcarlo nullable:

```yaml
KYCVerificationNullable:
  nullable: true
  allOf:
    - $ref: '#/components/schemas/KYCVerification'
```

### 9.5 `POST /api/v1/auth/token/refresh/` no declara el body

La petición es `{"refresh": "<token>"}` y la respuesta es
`{ "access": "...", "refresh": "..." }` (sin `user`):

```yaml
TokenRefreshRequest:
  type: object
  properties:
    refresh: { type: string }
  required: [refresh]
```

### 9.6 Respuestas de error: falta el sobre de error

Todas las vistas declaran solo el `200`. La API responde con el formato
uniforme de AGENTS §8, así que conviene un componente y referenciarlo en las
respuestas `400`, `401`, `403`, `404`, `409` y `429`:

```yaml
ApiError:
  type: object
  properties:
    error:
      type: object
      properties:
        code: { type: string }
        message: { type: string }
        details: { type: object, additionalProperties: true }
      required: [code, message, details]
  required: [error]
```

Los `details` de un error de validación son `{ "<campo>": ["<mensaje>", ...] }`;
el de los errores sin campo es `{}`.

Códigos que usa la API: `validation_error` (400), `not_authenticated` (401),
`permission_denied` (403), `not_found` (404), `method_not_allowed` (405),
`conflict` (409), `idempotency_conflict` (409), `throttled` (429) y `api_error`
(otros). El 403 del **KYC no aprobado** usa el código genérico
`permission_denied` y el mensaje "Necesitás completar la verificación KYC para
realizar esta operación."

### 9.7 Qué implica para el frontend

- El front ya funciona contra la API real: estas diferencias están
  contempladas y documentadas en `src/lib/api/types.ts` (`Paginated<T>` y
  `CursorPaginated<T>` escritos a mano) y en `src/lib/config.ts` (las rutas).
- Cuando el esquema esté corregido hay que **volver a copiar**
  `docs/openapi.yaml` del backend al front y correr `npm run types:api`: los
  tipos generados pasan a describir los sobres y se pueden borrar los alias
  manuales de `src/lib/api/types.ts`.
- Mientras tanto, el front sigue funcionando igual: los tipos del esquema y
  los sobres conviven sin romper nada.
