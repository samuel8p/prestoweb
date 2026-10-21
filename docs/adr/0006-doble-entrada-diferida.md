# ADR 0006 — La doble entrada se valida con un trigger diferido

- **Estado:** aceptado
- **Fecha:** 2026-10-21
- **Ámbito:** app `ledger`

## Contexto

Un movimiento del ledger es una `LedgerTransaction` con varios `LedgerEntry`
(asientos). La regla de la doble entrada es que **por cada transacción, la suma
de los débitos es igual a la suma de los créditos**: el dinero no se crea ni se
destruye.

La regla se puede verificar en tres lugares distintos, y cada uno tiene un
problema distinto:

1. **Solo en el código** (`services.py` valida antes de escribir). Un `INSERT`
   directo en SQL, un `bulk_create` o un error de concurrencia pueden dejar una
   transacción desbalanceada sin que nadie se entere.
2. **Con un `CheckConstraint`**. No sirve: un constraint de fila se evalúa
   **por fila**, y el balance es una propiedad **del grupo** de asientos de una
   transacción. En el momento de insertar el segundo asiento de un movimiento de
   tres, la transacción todavía está desbalanceada, y el constraint la
   rechazaría.
3. **Con un trigger de fila**. El mismo problema: se evalúa asiento por
   asiento, cuando el grupo todavía está incompleto.

Además, los movimientos **no se editan ni se borran**: una corrección se hace
con un movimiento compensatorio (AGENTS §6, regla 4). Esa inmutabilidad tiene
que estar garantizada en la base, no por convención.

## Decisión

1. **La doble entrada se valida en la base con un _constraint trigger
   diferido_**: `ledger_entry_balanced`, sobre `ledger_ledgerentry`, con la
   función `ledger_assert_balanced(target_transaction_id)`. Un *constraint
   trigger* diferido se ejecuta **al commit** de la transacción, cuando todos
   los asientos de la transacción ya están escritos: ahí sí se puede comparar
   la suma de débitos con la suma de créditos de la transacción completa.
2. **Si la transacción queda desbalanceada, el commit falla** y todo lo escrito
   dentro de la transacción se revierte. No queda un movimiento a medias.
3. **La inmutabilidad la garantizan triggers de fila**:
   `ledger_transaction_immutable` y `ledger_entry_immutable` bloquean `UPDATE` y
   `DELETE` sobre `ledger_ledgertransaction` y `ledger_ledgerentry`. No hay
   ninguna forma de editar o borrar un movimiento, ni desde el admin ni desde
   SQL.
4. **Los tres objetos viven en una migración propia** (`ledger.0002_ledger_triggers`)
   que los crea y los borra: el estado del schema en la base es explícito y
   reversible.
5. **El código sigue validando antes de escribir.** La base es la red de
   seguridad, no el mecanismo principal: `ledger.services` calcula las piernas
   del movimiento y llama a `_assert_sufficient_funds` antes de escribir. El
   trigger no reemplaza la lógica de negocio, la vuelve verificable.
6. **Los tests corren contra PostgreSQL real.** Con SQLite los triggers no
   existen y el test pasaría sin comprobar nada.

## Consecuencias

**Positivas**

- Un movimiento desbalanceado no puede quedar en la base, aunque se escriba por
  una vía que no pase por los services.
- La inmutabilidad de los movimientos es una propiedad del schema, no una
  convención del equipo.
- El fallo es ruidoso y temprano: el commit falla, no el reporte de mañana.

**Negativas / riesgos asumidos**

- La doble entrada se valida **al commit**, no al escribir: dentro de la
  transacción hay un instante en que los débitos y los créditos no coinciden.
  Nadie ve ese estado porque la transacción es atómica, pero cualquier código
  que lea el ledger desde **otra** conexión durante esa ventana vería el
  movimiento a medias. Es el precio de la atomicidad.
- Los triggers son código de PostgreSQL embebido en una migración: hay que
  mantenerlos a mano cuando cambie el schema, y su sintaxis no la valida Django.
- Un `UPDATE` o un `DELETE` que un administrador intente hacer sobre un
  movimiento falla con un error de PostgreSQL, no con un mensaje de la
  aplicación: hay que documentarlo (el admin de Presto no ofrece esas
  acciones).

**Pendiente**

- No hay un mecanismo para **auditar** quién intentó editar un movimiento: el
  trigger corta la operación, no la registra.
- La lista de cuentas `custody` y `system` no tiene una comprobación de que
  el total por moneda cuadre con el exterior más allá de los tests: la
  conciliación diaria con el proveedor de pagos es el Bloque 7.
