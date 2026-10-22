# Presto — Frontend

Frontend de **Presto**, la app de finanzas e inversiones con marketplace de
préstamos. Es una SPA que consume la API del backend Django (API-only, JWT).

- Interfaz en español rioplatense.
- React + Vite + TypeScript (strict), React Router, TanStack Query, Tailwind CSS,
  react-hook-form + zod.
- Tests con Vitest + Testing Library + MSW (nunca pegan al backend real).

## Pantallas

| Ruta                           | Qué hace                                                                                             |
| ------------------------------ | ---------------------------------------------------------------------------------------------------- |
| `/ingresar`, `/registro`       | Acceso y alta de cuenta (JWT con refresh rotativo)                                                   |
| `/panel`                       | Saldos por moneda, últimos movimientos y avisos                                                      |
| `/billetera`                   | Billeteras, depósito/retiro/transferencia simulados e historial paginado con los revertidos marcados |
| `/ofertas`                     | Marketplace: buscar, filtrar, comparar, publicar oferta y ver las propias                            |
| `/prestamos`, `/prestamos/:id` | Préstamos como prestatario y como prestamista, detalle con cuotas y pago de cuota                    |
| `/inversiones`                 | Productos a plazo fijo, apertura de posición e interés esperado/ganado                               |
| `/presupuestos`                | Categorías, presupuestos mensuales, estado (gastado, límite, alerta) y categorización de movimientos |
| `/reportes`                    | Movimientos, gasto por categoría, préstamos e inversiones, con moneda, rango y descarga CSV          |
| `/avisos`                      | Avisos paginados y preferencias por tipo de aviso                                                    |
| `/perfil`                      | Datos de la cuenta, perfil y estado del KYC                                                          |

## Requisitos

- Node.js 20 o superior.
- El backend de Presto corriendo (por defecto en `http://127.0.0.1:8000`).

## Puesta en marcha

```sh
npm install
cp .env.example .env        # ajustá VITE_API_URL si el backend está en otro lado
npm run dev
```

La app queda en `http://localhost:5173`.

## Variables de entorno

| Variable       | Para qué                            | Por defecto             |
| -------------- | ----------------------------------- | ----------------------- |
| `VITE_API_URL` | URL base de la API, sin barra final | `http://127.0.0.1:8000` |

No hay ni un secreto en el repo: los tokens nunca se escriben en el código ni
en los logs. La URL de la API es lo único configurable.

## Comandos

```sh
npm run dev          # servidor de desarrollo
npm run build        # build de producción (tsc -b + vite build)
npm run preview      # sirve el build
npm run typecheck    # tsc --noEmit
npm run lint         # eslint
npm run format       # prettier --write
npm run format:check # prettier --check
npm run test         # vitest run
npm run check        # typecheck + lint + format:check + test + build
npm run types:api    # regenera los tipos desde docs/openapi.yaml
```

Los tipos de la API se generan con `openapi-typescript` (dependencia de
desarrollo) desde [`docs/openapi.yaml`](./docs/openapi.yaml). El archivo
generado (`src/lib/api/schema.d.ts`) no se commitea: se regenera con
`npm run types:api`.

## Estructura

```
src/
├── app/            # router, providers y layout de la aplicación
├── components/     # componentes de UI reutilizables
├── features/       # una carpeta por dominio (auth, ledger, offers, ...)
├── lib/            # cliente de API, errores, dinero, tipos generados
└── test/           # setup de tests, MSW y fixtures
```

## Contrato con el backend

[`docs/backend-contract.md`](./docs/backend-contract.md) documenta el contrato
verificado contra la API real: paginación, formato de errores, el header
`Idempotency-Key`, los parámetros de los reportes y el endpoint de modo demo.
El esquema OpenAPI es la fuente de verdad de los endpoints y las formas de los
datos.

## Autenticación

La API usa JWT: `POST /api/v1/auth/login/` devuelve un access token y un
refresh token, y `POST /api/v1/auth/token/refresh/` los renueva **rotando** el
refresh token (el anterior queda en blacklist).

Dónde vive cada token y por qué:

| Token   | Dónde                | Por qué                                                                                                                         |
| ------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Access  | **solo en memoria**  | no se escribe en disco ni queda expuesto a otras pestañas ni a un script de la extensión. Vive hasta que se recarga la página   |
| Refresh | **`sessionStorage`** | es el único almacenamiento del navegador que se borra al cerrar la pestaña. `localStorage` persistiría el token indefinidamente |

El backend es una API JSON pura: no emite cookies `httpOnly`, así que no hay
una vía más segura que ésta para guardar el refresh token. El criterio
documentado es, entonces, **el refresh token más aislado disponible**:
`sessionStorage` en lugar de `localStorage`.

Además:

- Al arrancar, si hay un refresh token en la pestaña, la app renueva el
  access token y recupera el usuario; si la renovación falla, la sesión se
  descarta y se vuelve al login.
- Ante un `401`, el cliente renueva **una sola vez** y reintenta la petición.
  Si la renovación falla, se limpia la sesión y se vuelve al login.
- El logout borra los dos tokens de la sesión local. El backend no expone un
  endpoint de revocación: el refresh token queda en blacklist cuando rota.

## Despliegue en Vercel

El repo ya viene con `vercel.json`: build de Vite (`npm run build`), salida en
`dist` y la reescritura de SPA (todo lo que no sea un archivo existente cae en
`index.html`, para que las rutas profundas como `/prestamos/{id}` funcionen con
recarga directa).

### Pasos

1. **Importar el repo en Vercel** (Framework preset: _Vite_). Vercel detecta el
   `vercel.json` y usa el build y el directorio de salida de ahí.

2. **Definir la variable de entorno** `VITE_API_URL` en _Settings → Environment
   Variables_, para **Production** (y Preview si querés probar los previews):

   ```
   VITE_API_URL=https://api.presto.example.com
   ```

   Sin barra final. Vite la compila dentro del bundle: si la cambiás, hay que
   volver a desplegar.

3. **Permitir el origen del front en el backend (CORS).** Es el paso que más se
   olvida: sin esto, el navegador bloquea todas las peticiones.

   En el backend (Django + `django-cors-headers`), la variable
   `CORS_ALLOWED_ORIGINS` lleva los orígenes permitidos, separados por comas y
   **sin `*`**:

   ```sh
   CORS_ALLOWED_ORIGINS=https://presto-front.vercel.app,https://tu-prueba.vercel.app
   ```

   En producción (`config/settings/production.py`) el CORS se configura con esa
   variable; la lista vacía significa "ningún origen permitido". También
   conviene agregar el dominio de Vercel al `CSRF_TRUSTED_ORIGINS` del backend.

4. **Desplegar** y verificar:

   - `https://<tu-deploy>.vercel.app/health/` no aplica (el backend tiene
     `/health/`): probá `https://<tu-deploy>.vercel.app/` y que cargue la app.
   - `GET https://<backend>/api/v1/meta/` tiene que responder `200` desde el
     navegador (si el navegador lo bloquea, es el CORS).

### La prueba de humo

[`docs/smoke-test.md`](./docs/smoke-test.md) tiene el recorrido completo, paso
por paso, para verificar el flujo contra el backend real: registro, KYC,
billeteras, movimientos, ofertas, préstamos, inversiones, presupuestos, reportes
con CSV, avisos y cierre de sesión.

## Reglas de la casa

- **El dinero nunca pasa por `Number`.** Los importes llegan como string
  decimal y se formatean y comparan como string (`src/lib/money`).
- **Una moneda por vista.** Nunca se suman ni se convierten importes de ARS y
  USD.
- **Un solo manejador de errores** (`src/lib/api/errors.ts`) traduce el
  formato del backend a mensajes en español. No se muestran trazas.
- **Estados de carga, vacío y error** en todas las pantallas.
- **TDD**: primero el test, después la implementación.
