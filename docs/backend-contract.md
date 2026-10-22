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
