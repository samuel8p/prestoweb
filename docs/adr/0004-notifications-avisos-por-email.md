# ADR 0004 — App `notifications`: avisos por email con señales y tareas

- **Estado:** aceptado
- **Fecha:** 2026-10-21
- **Ámbito:** app `notifications` (Bloque 6d del plan de Presto)

## Contexto

El cliente aprobó una especificación cerrada para la app `notifications`: cuatro
eventos (cuota por vencer, cuota vencida, inversión liquidada y alerta de
presupuesto), un solo canal (email), idempotencia por evento, preferencias por
usuario, API de lectura y sin FK a otras apps.

Restricciones del proyecto:

- AGENTS §5.3: los efectos secundarios se comunican con **señales** definidas
  en la app emisora; los receptores llaman al `services.py` de la app
  interesada y delegan el trabajo pesado a una tarea Celery; los receptores
  deben ser idempotentes.
- AGENTS §5.2: entre apps solo se usan `services.py` y `selectors.py`.
- AGENTS §6: los importes son `Decimal` y el redondeo solo vía
  `core/money.py`.
- AGENTS §9: nada de datos sensibles en los emails (sin saldos completos ni
  datos de KYC).

## Decisión

1. **Dos modelos propios.** `Notification` (usuario, tipo de evento,
   referencia, estado `pending|sent|failed`, fecha de envío y error) y
   `NotificationPreference` (usuario, tipo de evento, habilitado). Sin FK a
   otras apps: las referencias son `UUIDField`.
2. **Idempotencia por evento.** La unicidad de
   `(user_id, event_type, reference_id)` hace que el mismo evento no genere
   dos avisos: el receptor puede correr dos veces sin duplicar nada.
3. **Preferencias con valor por defecto.** Si no hay fila de preferencia, el
   evento está **habilitado**: el usuario solo crea la fila cuando lo
   desactiva.
4. **Las señales las define la app emisora** (`loans`, `investments`,
   `budgets`) y llevan solo identificadores. Los receptores viven en
   `notifications/receivers.py`: crean el aviso con `notifications.services` y
   **encolan** la tarea de envío con `transaction.on_commit`, así el email
   nunca corre dentro de la transacción que originó el evento.
5. **El envío es una tarea.** `send_notification_email` es idempotente (un
   aviso enviado no se manda de nuevo), marca `sent` con la fecha o `failed`
   con el motivo. Un fallo de SMTP **no rompe** la transacción de la app
   emisora ni el ledger: la tarea corre aparte.
6. **Los importes de las cuotas por vencer y vencidas salen de dos tareas
   diarias de beat** (`notify_installments_due_soon` a las 00:10 y
   `notify_overdue_installments` a las 00:20 UTC, después de
   `mark_overdue_loans` a las 00:05). Se apoyan en selectores de lectura de
   `loans`.
7. **La alerta de presupuesto se dispara al categorizar.** `categorize_movement`
   revisa los presupuestos de la categoría y, si cruzaron el umbral, emite la
   señal. El identificador de la alerta se **deriva** del presupuesto y del mes
   (`uuid5`), así que el mismo presupuesto avisa **una sola vez por mes**.
8. **Emails en español, texto plano y sin datos sensibles**: se incluye lo del
   evento (importe de la cuota, interés de la inversión, gastado y límite del
   presupuesto) y nunca saldos completos ni datos de KYC.
9. **SMTP por variables de entorno** (`EMAIL_BACKEND`, `EMAIL_HOST`,
   `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`,
   `DEFAULT_FROM_EMAIL`). En desarrollo el backend es de consola y en los tests
   es el de memoria: no hay secretos en el repo.
10. **El email del destinatario sale de `identity.selectors`**
    (`get_user_email`, un selector de lectura nuevo): ninguna app importa los
    modelos de otra.

## Consecuencias

**Positivas**

- Los avisos no se duplican aunque el mismo evento se dispare dos veces.
- Un fallo de SMTP no afecta el ledger ni la transacción de la app emisora.
- El usuario puede desactivar cada tipo de aviso por separado.
- El beat corre los avisos de cuotas sin que nadie se acuerde.

**Negativas / riesgos asumidos**

- La app `notifications` importa las **señales** de las apps emisoras: es la
  excepción documentada de AGENTS §5.3 y el patrón estándar de Django. El
  contrato de `import-linter` lo refleja (prohíbe los modelos, las vistas, los
  serializers, el admin y las urls de las otras apps, no las señales).
- `categorize_movement` recalcula el estado de los presupuestos de la categoría
  para ver si cruzaron el umbral: son consultas extra por categorización.
- El identificador de la alerta de presupuesto es **derivado**: para armar el
  email hay que buscar el presupuesto entre los del usuario comparando el
  identificador (`find_budget_by_alert_reference`).
- Los correos no se reintentan: un aviso fallido queda en `failed` y no vuelve
  a encolarse solo.
- `notify_overdue_installments` incluye las cuotas `pending` y `overdue` para
  no depender del orden de las tareas del beat.

**Pendiente**

- El reintento de los avisos fallidos y el resumen de las notificaciones
  (agregar varios avisos en un solo email) no están especificados.
- El envío del esquema OpenAPI al frontend y el CORS real siguen pendientes.
