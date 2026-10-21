# ADR 0007 — El orden de las apps y por qué

- **Estado:** aceptado
- **Fecha:** 2026-10-21
- **Ámbito:** proyecto

## Contexto

Presto tiene nueve apps de dominio (`identity`, `ledger`, `offers`, `matching`,
`loans`, `investments`, `budgets`, `reports`, `notifications`) y una transversal
(`core`). El orden en el que se construyen no es un detalle de calendario: cada
app depende de las anteriores y algunas dependencias no se pueden invertir.

AGENTS §15 define un plan por fases, pero el orden real de los bloques fue
cambiando a medida que aparecieron requisitos del cliente (el modo demo, el
proveedor de pagos al final, las inversiones antes que los presupuestos). Este
ADR deja el orden **explícito y justificado**, para que no se vuelva a mover
por intuición.

Además hay una restricción fuerte: AGENTS §5.2 prohíbe las ForeignKey entre
apps de dominio y obliga a que una app entre a otra solo por sus `services.py` y
`selectors.py`. Eso convierte el orden de construcción en algo casi secuencial:
una app que se construye antes no puede importar de una que se construye
después.

## Decisión

1. **`core` primero, y sin dependencias.** `core` no importa ninguna otra app
   (AGENTS §5.2, regla 3). Tiene `BaseModel`, `core.money` (la única función de
   redondeo del proyecto), las excepciones compartidas y la paginación.
2. **`identity` antes que `ledger`.** El ledger guarda `user_id` (un `UUIDField`,
   sin ForeignKey) y valida el KYC con `identity.selectors.is_kyc_approved`.
   Sin `identity` no hay usuarios ni KYC, y sin KYC no se puede mover dinero.
3. **`ledger` antes que todo lo que mueve dinero.** Es la fuente de verdad de
   los saldos: `loans` (desembolso y pago de cuotas), `investments` (apertura y
   liquidación) y `budgets` (el gasto se deriva de los movimientos) dependen de
   él. El `ledger` no depende de ninguna otra app de dominio.
4. **`offers` antes que `loans`.** Un préstamo nace de una oferta: `loans`
   toma un snapshot inmutable de sus términos. `offers` no conoce `loans`
   (una app no importa hacia atrás).
5. **`matching` después de `offers`, y solo de lectura.** `matching` se apoya
   en `offers.selectors` y nunca importa `offers.models`; `offers` no importa
   `matching` en ningún sentido. Es la única app sin models.
6. **`loans` después de `offers` y `ledger`.** El desembolso lo ejecuta un
   service interno del ledger y el cronograma de cuotas se calcula en
   `core.money` (método francés).
7. **`investments` después de `ledger`.** La apertura mueve el saldo a la cuenta
   `system` y la liquidación lo devuelve con el interés. No depende de
   `loans`.
8. **`budgets`, `reports` y `notifications` al final.** Los tres leen o anotan
   sobre datos que ya existen: `budgets` deriva el gasto del ledger, `reports`
   agrega y exporta, `notifications` observa lo que pasó. Los tres son, además,
   *de solo lectura o de efecto secundario*: ninguno escribe estado financiero.
9. **`payments` al final de todo.** El proveedor real de pagos y la
   conciliación con el banco son el último bloque, porque el dinero simulado
   del ledger ya está modelado y probado: el proveedor externo es una
   **fuente** de eventos (un webhook firmado que confirma un depósito), no una
   pieza que cambie el modelo del ledger.

El orden de los bloques que se está trabajando:

```
core → identity → ledger → offers → matching → loans → investments
     → budgets → reports → notifications → payments
```

10. **La arquitectura es un monolito modular, y va a seguir siéndolo.** No hay
    microservicios, ni API gateway, ni broker de mensajes, ni más de una base
    de datos. La razón está en AGENTS §2: un solo desarrollador, un proyecto de
    cliente y un dominio financiero donde las transacciones ACID de una única
    base son más seguras que la consistencia distribuida. Las reglas de
    capas y de límites son las que garantizan que una eventual extracción sea
    posible **si algún día hace falta**; anticiparla sería construir algo que
    nadie pidió.

## Consecuencias

**Positivas**

- El orden de construcción es determinista: cada app se puede empezar cuando
  sus dependencias existen y probadas.
- Las dependencias entre apps son explícitas y verificables (`import-linter`,
  28 contratos) en lugar de implícitas.
- La regla de "cada app entra a otra por sus services y selectors" evita que
  el grafo de dependencias se vuelva un grafo de modelos.

**Negativas / riesgos asumidos**

- El plan es **secuencial**: una app que necesita otra que todavía no existe
  no se puede empezar. Es el precio de no acoplar las apps por los modelos.
- Cambiar el orden después de empezar un bloque implica trabajo de rehacer
  (por ejemplo, `budgets` se diseñó después que `ledger` justamente para poder
  derivar el gasto de los movimientos).
- `payments` queda bloqueado por decisiones de negocio que no son técnicas
  (qué proveedor, qué regulación, qué hay que hacer con la custodia).

**Pendiente**

- El orden de los **bloques de trabajo** (que no es exactamente el orden de
  las apps: `budgets`, `reports` y `notifications` se pueden hacer en
  cualquier orden entre sí) debería quedar anotado en `HANDOFF.md` §15.
- Cuando exista el proveedor de pagos, habrá que decidir si `payments` es una
  app más del monolito o un módulo con su propio despliegue. La decisión
  depende del proveedor y de la regulación, no de la arquitectura.
