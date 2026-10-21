# ADR 0005 — El saldo de las cuentas está desnormalizado

- **Estado:** aceptado
- **Fecha:** 2026-10-21
- **Ámbito:** app `ledger`

## Contexto

Cada cuenta del ledger tiene un saldo que se muestra en pantalla, se usa para
validar operaciones y aparece en los reportes. Hay dos formas de obtenerlo:

1. **Derivado**: `sum(créditos) - sum(débitos)` de los asientos de la cuenta.
   Es la verdad por definición, pero cada consulta de saldo recorre la tabla
   de asientos.
2. **Materializado**: una columna `Account.balance` que se actualiza en cada
   movimiento.

Con la opción 1, cada validación de saldo (¿alcanza el dinero?, ¿la billetera
queda negativa?) y cada reporte paga el costo de agregar los asientos de la
cuenta, y el cálculo se repite en cada lectura con la posibilidad de que dos
lecturas concurrentes vean estados distintos del mismo agregado.

AGENTS §6 (regla 7) deja las dos abiertas: "el saldo de una cuenta se deriva de
las transacciones (o se mantiene como campo denormalizado verificable contra
ellas)". AGENTS §Reglas del ledger 1 pide un campo denormalizado **verificable**:
la materializedización tiene que poder contrastarse contra los asientos.

## Decisión

1. **`Account.balance` es un campo desnormalizado** (`DecimalField`, misma
   escala que los importes) que materializa el saldo de la cuenta.
2. **La regla de oro es una sola**: `balance == sum(créditos) - sum(débitos)`.
   Hay un test de invariante que lo verifica para **toda** cuenta de la base,
   no solo para las que tocaron una prueba.
3. **El saldo nunca se edita a mano.** Solo se modifica dentro de
   `ledger.services`, dentro de un `transaction.atomic()` y con
   `select_for_update()` sobre las cuentas involucradas, **bloqueadas en orden
   ascendente por `id`** (el orden estable evita deadlocks entre transferencias
   en sentidos contrarios).
4. **El saldo nunca queda negativo en una `user_wallet`.** Hay un
   `CheckConstraint` en la base (`ledger_account_user_wallet_balance_non_negative`)
   que lo garantiza aunque el código tuviera un error. Las cuentas de
   contrapartida (`custody`, `system`) reflejan el mundo exterior y **sí**
   pueden quedar negativas: la restricción no aplica a ellas.
5. **La unicidad de las cuentas** la define la base, no el código: una
   `user_wallet` por `(user_id, currency)` y una cuenta por `(kind, currency)`
   para `custody` y `system` (`UniqueConstraint` condicional).
6. **Los asientos mandan.** Si el saldo materializado y el derivado no coinciden,
   es un bug del código, no un dato válido: por eso el test de invariante corre
   contra PostgreSQL real y no contra SQLite.

## Consecuencias

**Positivas**

- El saldo se lee en O(1) y las validaciones de fondos no agregan el costo de
  recorrer los asientos.
- La restricción de saldo no negativo queda garantizada por la base, no por la
  disciplina del código.
- El deadlock entre transferencias en sentidos contrarios se evita con el orden
  de bloqueo por `id`.

**Negativas / riesgos asumidos**

- El saldo es un dato duplicado: hay que mantenerlo. La mitigación es que solo
  `ledger.services` lo escribe, siempre bajo bloqueo, y que el test de
  invariante lo contraste con los asientos en cada corrida.
- Un `UPDATE` manual sobre `ledger_account.balance` desde el admin o desde SQL
  rompería la invariante. Hoy el admin no expone la edición de saldos y los
  triggers de inmutabilidad cubren transacciones y asientos, pero **no** el saldo:
  queda como riesgo asumido y como punto de control futuro (un trigger que
  prohíba cambiar `balance` fuera de los services no es posible sin distinguir
  el origen de la escritura).
- La reversión de un movimiento **no recalcula** el saldo: escribe los asientos
  de sentido contrario y mueve el `balance` con el delta de cada cuenta, dentro
  de la misma transacción y con las cuentas bloqueadas. Es más barato que
  recalcular, pero depende de que la transacción original y su reverso se
  escriban siempre en la misma operación.

**Pendiente**

- No hay reconciliación periódica entre el saldo materializado y el derivado
  fuera de los tests. Con un solo desarrollador y un solo despliegue, el test de
  invariante alcanza; si el sistema creciera, la reconciliación diaria sería
  lo natural.
- La moneda no tiene `CheckConstraint` en la base (solo `choices`): es un
  cambio de schema y está a la espera de una decisión (ver `docs/audit-final.md`
  §5, D-3).
