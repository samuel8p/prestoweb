# Arquitectura de Presto

Este documento describe cómo está armado el backend: qué piezas existen, cómo
se comunican y por qué. Las **reglas** del proyecto (qué está permitido y qué
no) viven en [AGENTS.md](../AGENTS.md); las **decisiones** con su contexto y sus
consecuencias viven en [adr/](adr/). Este documento es el mapa.

## 1. Panorama

Presto es un **monolito modular**: un solo proyecto Django, una sola base de
datos PostgreSQL, un solo despliegue.

```
                    ┌───────────────────────────────┐
   cliente HTTP ───▶│  Django + DRF  (/api/v1/)     │
                    │  auth JWT · drf-spectacular   │
                    └───────────────┬───────────────┘
                                    │
        ┌───────────┬───────────┬───┴────┬───────────┬────────────┐
        ▼           ▼           ▼        ▼           ▼            ▼
    identity     ledger     offers   matching     loans     investments
        │           │           │        │           │            │
        │           │           │        │           │            │
        └───────────┴─────┬─────┴────────┴───────────┴────────────┘
                          ▼
              budgets · reports · notifications
                          │
                          ▼
                 PostgreSQL 16 · Redis (Celery)
```

No hay microservicios, ni API gateway, ni broker de mensajes, ni más de una base
de datos. El motivo está en el ADR del orden de las apps y en `AGENTS.md` §2.

## 2. Mapa de apps

| App | Responsabilidad | Models | Interfaz pública |
|---|---|---|---|
| `core` | Utilidades transversales: `BaseModel`, `money.py`, excepciones, paginación, health, meta | `BaseModel` (abstracto) | `core.money`, `core.exceptions` |
| `identity` | Usuarios, login JWT, perfil, KYC | `User`, `Profile`, `KYCVerification` | `identity.services`, `identity.selectors` |
| `ledger` | Libro mayor de doble entrada: cuentas, movimientos, reversos, transferencias | `Account`, `LedgerTransaction`, `LedgerEntry` | `ledger.services`, `ledger.selectors` |
| `offers` | Ofertas de préstamo del prestamista | `Offer` | `offers.services`, `offers.selectors` |
| `matching` | Búsqueda, comparación y recomendación (solo lectura) | — | `matching.selectors` |
| `loans` | Préstamos tomados, cronograma de cuotas, estados | `Loan`, `OfferTermsSnapshot`, `Installment` | `loans.services`, `loans.selectors` |
| `investments` | Plazos fijos | `InvestmentProduct`, `Position` | `investments.services`, `investments.selectors` |
| `budgets` | Presupuestos, categorías y gastos (el importe se deriva del ledger) | `Budget`, `Category`, `Expense` | `budgets.services`, `budgets.selectors` |
| `reports` | Reportes de solo lectura y exportación a CSV | — | `reports.selectors` |
| `notifications` | Avisos por email | `Notification`, `NotificationPreference` | `notifications.services`, `notifications.selectors` |

### Cómo se comunican

- Una app **solo entra a otra por su `services.py` y su `selectors.py`**. Nunca
  se importan modelos, vistas ni serializers de otra app.
- **No hay ForeignKey entre apps de dominio.** Las referencias cruzadas son
  `UUIDField` (`user_id`, `offer_id`, `ledger_transaction_id`…) y se resuelven
  por el selector de la app dueña. La excepción es `core`, que no importa
  ninguna otra app.
- Los límites se verifican con `import-linter`: hay **28 contratos** y la CI
  falla si alguno se rompe.

## 3. Capas dentro de una app

```
urls.py ──▶ views.py ──▶ serializers.py   (validan la entrada y el formato)
                 │
                 ├──▶ services.py          (escriben: reglas de negocio, atomic)
                 └──▶ selectors.py         (leen: consultas, filtros, agregados)
                          │
                          ▼
                      models.py             (campos, constraints, métodos triviales)
```

- `views.py` no tiene lógica de negocio: autentica, valida, llama a un service o
  a un selector y responde.
- `services.py` tiene todo lo que **escribe**: usa `transaction.atomic()` y
  `select_for_update()` cuando hay riesgo de carrera.
- `selectors.py` tiene todo lo que **lee**: sin N+1 (los listados usan
  `select_related` / `prefetch_related` y los reportes resuelven en lote).
- `signals.py` es la excepción documentada: puede importar modelos de otra app,
  pero la lógica vive en el service de la app dueña y los receptores son
  idempotentes.

## 4. El dinero

Ocho invariantes, verificados en código, en constraints y en tests:

1. **`Decimal` siempre**, nunca `float`. Los importes son
   `DecimalField(max_digits=18, decimal_places=2)`.
2. **Un solo redondeo**: `round_two` en `core/money.py`. Ningún otro módulo
   redondea.
3. **Una moneda por importe**: `ARS` o `USD`, código ISO 4217. No se suman ni
   comparan importes de monedas distintas sin conversión explícita.
4. **El ledger es inmutable**: los triggers de PostgreSQL bloquean `UPDATE` y
   `DELETE` sobre `ledger_ledgertransaction` y `ledger_ledgerentry`. Un error se
   corrige con una transacción compensatoria (`reverses`).
5. **Doble entrada**: por cada `LedgerTransaction`, la suma de los débitos es
   igual a la suma de los créditos. Lo garantiza un *constraint trigger
   diferido* en la base, que evalúa el saldo al commit.
6. **Saldo no negativo** para las cuentas `user_wallet` (`CheckConstraint` en la
   base). Las cuentas de contrapartida (`custody`, `system`) reflejan el mundo
   exterior y pueden quedar negativas.
7. **Idempotencia**: todo service que mueve dinero recibe una
   `idempotency_key` única por `(usuario, clave)` y guarda el `request_hash` del
   payload. Misma clave y mismo hash devuelven la operación original; misma
   clave y hash distinto devuelven `409`.
8. **KYC obligatorio**: depósito, retiro, transferencia, inversión y aceptación
   de un préstamo exigen `identity.selectors.is_kyc_approved(user_id)`.

### Cómo se mueve el dinero

Todo movimiento pasa por el ledger, incluso los de inversiones:

```
        deposit / withdraw / transfer        loans (desembolso)     investments
                 │                                   │                     │
                 ▼                                   ▼                     ▼
     ledger.services ───────────────▶  LedgerTransaction + LedgerEntry (debit/credit)
                                              │
                                              ▼
                                   Account.balance  (materializado)
```

El saldo de una cuenta está **materializado** en `Account.balance` y se mantiene
igual a `sum(créditos) - sum(débitos)` de sus asientos. Solo se modifica dentro
de `services.py`, bajo `select_for_update()`, bloqueando las cuentas en orden
ascendente por `id` (evita deadlocks). Hay un test de invariante que lo
verifica para toda cuenta.

El invariante global del ledger es `Σ(custody) + Σ(system) = -Σ(user_wallet)`
por moneda: la suma de todos los saldos es cero.

Detalle de cada decisión:

- [ADR 0005 — el saldo desnormalizado de las cuentas](adr/0005-saldo-desnormalizado.md)
- [ADR 0006 — el contrato diferido de doble entrada](adr/0006-doble-entrada-diferida.md)
- [ADR 0002 — el gasto de los presupuestos se deriva del ledger](adr/0002-budgets-derivacion-del-gasto.md)

## 5. Un movimiento de punta a punta

Ejemplo: un prestatario paga la primera cuota de un préstamo.

1. `POST /api/v1/loans/{id}/installments/{n}/pay/` → `loans.views`
2. El view valida el cuerpo y llama a `loans.services.pay_installment`
3. El service, dentro de `transaction.atomic()`:
   - bloquea la cuota y el préstamo (`select_for_update`);
   - verifica que el prestatario sea quien paga, que las cuotas anteriores estén
     pagadas y que se pague la cuota **completa**;
   - llama a `ledger.services.transfer_between_users` (origen: el prestatario,
     destino: el prestamista) con una `idempotency_key` derivada del préstamo;
   - marca la cuota como pagada y, si era la última, el préstamo como `paid`.
4. El ledger bloquea las dos cuentas, escribe la transacción y sus asientos y
   actualiza los saldos.
5. Una señal notifica el pago; el aviso por email sale de la cola de Celery.

## 6. Tareas asíncronas

Celery con Redis como broker. Las tareas reales (emails, Liquidación de plazos
fijos, avisos de vencimientos) corren en el worker; el beat las dispara:

| Hora (UTC) | Tarea | Qué hace |
|---|---|---|
| 00:05 | `apps.loans.tasks.mark_overdue_loans` | Vence las cuotas atrasadas y deja el préstamo en default |
| 00:10 | `apps.loans.tasks.notify_installments_due_soon` | Avisa las cuotas que vencen en los próximos días |
| 00:15 | `apps.investments.tasks.settle_investments` | Liquida los plazos fijos vencidos |
| 00:20 | `apps.loans.tasks.notify_overdue_installments` | Avisa las cuotas atrasadas |

## 7. Entornos

| | Desarrollo | Producción |
|---|---|---|
| Settings | `config.settings.local` | `config.settings.production` |
| Compose | `docker-compose.yml` (5 servicios) | `docker-compose.prod.yml` (+ perfiles `proxy` y `backup`) |
| Dinero | simulado | bloqueado salvo `DEMO_MODE=true` |
| Email | consola | SMTP (o consola en demo) |
| Seguridad | `DEBUG=True` | `DEBUG=False`, SSL, HSTS, cookies seguras, `ALLOWED_HOSTS` explícito |

El compose de producción levanta Django + Gunicorn, PostgreSQL, Redis, el worker
y el beat. Opcionalmente, el perfil `proxy` agrega Caddy (TLS automático) y el
perfil `backup` agrega el backup diario de PostgreSQL. Los contenedores de la
aplicación corren como el usuario sin privilegios `presto`.

Modo demo (`DEMO_MODE=true`): el dinero es simulado, los avisos salen por
consola y el system check `ledger.E001` no bloquea el dinero simulado. La guía
está en [deploy-demo.md](deploy-demo.md).

## 8. Frontend

El backend es **API only**: no hay templates ni front. El contrato es el
esquema OpenAPI que genera `drf-spectacular` en `/api/schema/` (Swagger UI en
`/api/docs/`). Los importes viajan como **string** decimal (`"1250.50"`) y las
fechas en ISO 8601 UTC. Los errores usan siempre el mismo formato:

```json
{ "error": { "code": "insufficient_funds", "message": "…", "details": {} } }
```

## 9. Decisiones documentadas

| ADR | Decisión |
|---|---|
| [0001](adr/0001-celery-redis-cola-y-scheduler.md) | Celery + Redis como cola y scheduler |
| [0002](adr/0002-budgets-derivacion-del-gasto.md) | El gasto de los presupuestos se deriva del ledger |
| [0003](adr/0003-reports-reportes-de-solo-lectura.md) | Los reportes son de solo lectura |
| [0004](adr/0004-notifications-avisos-por-email.md) | Los avisos se mandan por email desde una cola |
| [0005](adr/0005-saldo-desnormalizado.md) | El saldo de las cuentas está desnormalizado |
| [0006](adr/0006-doble-entrada-diferida.md) | La doble entrada se valida con un trigger diferido |
| [0007](adr/0007-orden-de-las-apps.md) | El orden de las apps y por qué |
