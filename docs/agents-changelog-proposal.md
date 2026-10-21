# Propuesta de cambios en AGENTS.md (sin aplicarlos)

Este documento **no** modifica `AGENTS.md`: es el texto propuesto para que el
desarrollor lo apruebe y lo aplique. Está escrito en el mismo formato del
registro de la §17 (una fila por decisión) y con el mismo tono del resto del
documento.

Cada bloque dice **qué se propone**, **dónde** va y **por qué**. Nada de esto
está aplicado: `AGENTS.md` sigue como estaba.

---

## 1. §17 — filas nuevas del registro de cambios

Agregar al final de la tabla de la §17 (después de la fila del **Bloque 5
(investments, plazo fijo)**) estas filas, con la fecha de aprobación:

```markdown
| 2026-10-21 | **Bloque 6a (reports + notifications) — decisiones registradas.** Nueva sección §Reglas adicionales de reports y notifications. `reports` es **de solo lectura**: expone selectores que agregan sobre `ledger`, `loans` e `investments` y **nunca escribe**; los endpoints aceptan `currency` y un rango de fechas (máximo 12 meses) y la exportación a CSV neutraliza la inyección de fórmulas. `notifications` **observa** lo que pasa: recibe señales de las demás apps y crea `Notification` + `NotificationPreference` por usuario y tipo de evento (`installment_due_soon`, `installment_overdue`, `investment_settled`, `budget_alert`); el envío es una **tarea Celery** y el receptor es idempotente. Las preferencias se guardan por `(usuario, tipo de evento)` y una preferencia apagada impide crear el aviso. Los avisos **no incluyen saldos completos ni datos de KYC**. |
| 2026-10-21 | **Bloque 6b (budgets) — decisiones registradas.** Nueva sección §Reglas adicionales de budgets. El **importe del gasto no se guarda**: `Expense` solo apunta al `ledger_transaction_id` y el monto se **deriva del ledger al leer**, en lote (`ledger.selectors.list_movement_details` + `loans.selectors.list_loan_movement_breakdowns`), de modo que `budgets` no puede mostrar un importe que contradiga al ledger. `Category` es un modelo propio con FK **interna** a la app (AGENTS §5.2 solo prohíbe las FK *entre* apps de dominio). El gasto cuenta solo si el movimiento sale de la billetera del usuario y el crédito no va a otra cuenta del propio usuario ni a la cuenta `system`; el **desembolso** de un préstamo no cuenta (el dinero se convierte en un activo) y el **pago de una cuota** cuenta solo por el **interés** (el capital es amortización). Un presupuesto es único por `(usuario, categoría, período, moneda)` y el gasto se filtra por la moneda: nunca se suman ARS y USD. El `alert_threshold` es un porcentaje entre 0 y 100, con `CheckConstraint` en la base. Cobertura mínima del 90% en `budgets/services.py`. |
| 2026-10-21 | **Modo demo (`DEMO_MODE`).** Con `DEMO_MODE=true` la aplicación corre como demostración: el dinero simulado queda permitido (el system check `ledger.E001` no lo bloquea) y el backend de email pasa a la **consola** (los avisos salen en los logs del worker). El modo demo **nunca** habilita `LEDGER_SIMULATED_DEPOSITS_ENABLED` por sí solo: las dos variables se controlan por separado y `production.py` sigue exigiendo que el dinero simulado esté apagado salvo que `DEMO_MODE` esté activo. El endpoint `GET /api/v1/meta/` informa el modo y si el dinero es simulado, y `GET /health/` es público. |
| 2026-10-21 | **Auditoría final del backend — correcciones registradas.** (a) **Validadores de contraseña de Django activos** (§9.5): los cuatro validadores están en `AUTH_PASSWORD_VALIDATORS`, el service `identity.register_user` valida la contraseña y la vista responde `400` con el formato de error de §8; el `min_length` del serializer queda en 8, alineado con el validador de Django. (b) **HSTS en producción** (§9.4): `SECURE_HSTS_SECONDS` (un año) y `SECURE_HSTS_INCLUDE_SUBDOMAINS` en `production.py`; el **preload queda apagado** porque es irreversible. (c) `update_offer` y `expire_offer` corren dentro de `transaction.atomic()` y leen la oferta con `select_for_update()` (AGENTS §6 regla 6): sin el bloqueo, dos escrituras simultáneas se pisan. (d) **Los contenedores de la aplicación no corren como root**: la imagen crea el usuario `presto` (uid 1000) y los servicios `web`, `worker` y `beat` lo usan. (e) El **health check de producción** manda un `Host` permitido: Django responde `400` cuando el `Host` no está en `ALLOWED_HOSTS` y el chequeo interno usa `127.0.0.1`. (f) `apps/`, `apps/core/` y `apps/identity/` tienen su `__init__.py` (§4). (g) `.env.example` documenta `DEMO_MODE` y `LEDGER_SIMULATED_DEPOSITS_ENABLED`, y `.env.prod.example` documenta `SECURE_HSTS_SECONDS`. |
| 2026-10-21 | **Documentación del proyecto.** `docs/architecture.md` describe la arquitectura real (apps, capas, invariantes del dinero, recorrido de un movimiento) y los ADR 0005 (saldo desnormalizado), 0006 (doble entrada con constraint trigger diferido) y 0007 (orden de las apps) documentan las decisiones que faltaban. El `README.md` lista la estructura real, los endpoints, las tareas de beat y el modo demo. |
```

---

## 2. §7 — modelos que faltan

La §7 documenta los modelos de `identity`, `ledger`, `payments`, `offers`,
`loans`, `investments` y `budgets`, pero **no** los de `reports` ni
`notifications` (que sí existen) y la entrada de `budgets` quedó anterior a la
implementación (no menciona `Category` ni `Expense`).

Agregar al final de la §7:

```markdown
### `reports`

- Sin modelos: la app es de **solo lectura**. Agrega sobre `ledger`, `loans` e
  `investments` y devuelve primitivos (no modelos de otra app).

### `notifications`

- **Notification:** `user_id` (`UUIDField`), `event_type` (`installment_due_soon` | `installment_overdue` | `investment_settled` | `budget_alert`), `status` (`pending` | `sent` | `failed`), `subject`, `body`, `sent_at` (nullable), `error_message` (nullable). **Un aviso por `(usuario, tipo de evento, movimiento o referencia)`**: el `UniqueConstraint` evita el duplicado cuando el receptor corre dos veces.
- **NotificationPreference:** `user_id` (`UUIDField`), `event_type` (los mismos cuatro), `enabled` (booleano). **Una preferencia por `(usuario, tipo de evento)`**. Una preferencia apagada impide que se cree el aviso.
```

Y reemplazar la entrada de `budgets` por esta:

```markdown
### `budgets`

- **Category:** `user_id` (`UUIDField`), `name`. **Único por `(user_id, name)`**.
- **Budget:** `user_id` (`UUIDField`), `category` (FK **interna** a la app), `period` (`monthly`), `limit_amount` (`Decimal`, `> 0`), `currency` (`ARS` | `USD`), `alert_threshold` (`Integer`, porcentaje entre 0 y 100). **Único por `(user_id, category, período, moneda)`**.
- **Expense:** `user_id` (`UUIDField`), `category` (FK **interna** a la app), `ledger_transaction_id` (`UUIDField`). **No guarda importe**: el monto se deriva del ledger al leer. **Único por `(user_id, ledger_transaction_id)`**: un movimiento se categoriza una sola vez.
- **Regla de dinero:** el gasto se **deriva** del ledger, no se duplica (ver §Reglas adicionales de budgets).
```

## 3. §15 — fases

La §15 ya refleja el orden real (`payments` al final ✓). La única diferencia
es que el **Bloque 6** (budgets, reports y notifications) se terminó en tres
bloques y que el **modo demo** no figura en el plan. Agregar al final de la
§15:

```markdown
**Fase 5 (detalle):** el bloque se implementó en tres partes, en este orden:
`reports` + `notifications` (Bloque 6a) y `budgets` (Bloque 6b). El modo demo
(`DEMO_MODE`) se agregó en el Bloque 6c, como forma de poder demostrar el
producto sin proveedor de pagos ni SMTP.
```

## 4. §4 — estructura del repositorio

La §4 ya lista `apps/budgets`, `apps/reports` y `apps/notifications` ✓. La
única diferencia con el código real es que **faltan** las apps `matching` y
`payments` en el árbol (la `payments` todavía no existe ✓ y `matching` sí ✓).
Reemplazar la línea de `payments` por:

```
│   ├── matching/                # búsqueda, comparación y recomendación (solo lectura, vía selectors)
```

y dejar `payments` fuera del árbol hasta que exista.

---

## 5. Lo que **no** se propone

- **No** se cambian las reglas de dinero, de capas ni de seguridad: la auditoría
  no encontró ninguna que estuviera mal, solo implementaciones que faltaban.
- **No** se agrega `payments` (el proveedor de pagos es una decisión de
  negocio, no de documentación).
- **No** se registran las decisiones que siguen esperando al cliente
  (Sentry, `pip-audit`, CORS real, constraints de moneda en la base,
  reintento de avisos, resumen de avisos): están en `docs/audit-final.md` §5.
