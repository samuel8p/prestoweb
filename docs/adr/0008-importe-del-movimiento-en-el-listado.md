# ADR 0008 — El importe del movimiento en el listado del ledger

- **Estado:** aceptado
- **Fecha:** 2026-10-22
- **Ámbito:** app `ledger` (listado de movimientos)

## Contexto

`GET /api/v1/ledger/transactions/` devolvía el tipo, la fecha, la descripción y
la cuenta de destino, pero **no el importe ni la moneda**. El frontend (que
consume el esquema) tenía que pedir `GET /api/v1/reports/movements/` para
saber cuánto dinero entró o salió: un salto extra (y otro endpoint) para pintar
el historial de una billetera.

El movimiento, en cambio, sí tiene importe: son sus **patas** (los asientos). Un
movimiento toca la billetera del usuario (crédito → entró dinero, débito →
salió) y las cuentas de contrapartida (`custody`, `system`).

## Decisión

1. **El importe del listado es el de la pata que toca la cuenta del usuario,
   con su signo**: un crédito suma y un débito resta. Un depósito de 1000 ARS
   aparece como `1000.00` y un retiro de 250,50 ARS como `-250.50`.
2. **La moneda es la de esa pata**. Un movimiento del ledger nunca mezcla
   monedas (la transferencia exige la misma moneda en origen y destino), así que
   el criterio es inequívoco.
3. **Cada movimiento toca, como mucho, una billetera del usuario**: hay una
   sola `user_wallet` por moneda. Un movimiento nunca toca dos cuentas del
   mismo usuario, así que no hay ambigüedad al sumar las patas propias.
4. **Los campos son de solo lectura y aditivos**: el listado suma `amount` y
   `currency`; no se saca ni se renombra nada. El detalle del movimiento
   (`GET /api/v1/ledger/transactions/{id}/`) no cambia.
5. **Sin N+1**: el importe sale de los asientos que el selector del listado ya
   precarga (`entries__account`), con la función pura
   `ledger.selectors.list_user_movement_amounts`. La cantidad de consultas no
   crece con la cantidad de movimientos (hay un test que lo comprueba).
6. **El importe viaja como string decimal** (`"1000.00"`), igual que todos los
   importes de la API (AGENTS §6).

## Consecuencias

**Positivas**

- El historial de la billetera se puede pintar con una sola llamada.
- El signo lo dice todo: no hay que interpretar el tipo del movimiento.
- Es el mismo número que ve el usuario en su cuenta (el saldo es la suma de
  estos importes con signo).

**Negativas / riesgos asumidos**

- El signo es relativo **al usuario que pregunta**: el emisor de una
  transferencia ve `-700.00` y el receptor `700.00`. Es lo correcto (cada uno
  ve su billetera), pero el mismo movimiento tiene dos importes.
- El importe del listado **no es** el total del movimiento (la suma de los
  débitos, que es lo que publica el reporte de movimientos): es el saldo de la
  billetera. Los dos números conviven y no deben mezclarse.
- El listado y el reporte de movimientos cuentan cosas distintas: el listado es
  el historial de la billetera (con signo) y el reporte es el movimiento en sí
  (sin signo, con `is_reversed`).

**Pendiente**

- El reporte de movimientos (`GET /api/v1/reports/movements/`) sigue mostrando
  el total del movimiento sin signo: es lo que usa el front para el detalle.
  Unificar los dos criterios sería un cambio de comportamiento del reporte ✗
  (decisión del cliente).
- El listado no trae `is_reversed` (el movimiento revertido sí aparece, con su
  importe original). Sumarlo al listado es el mismo tipo de cambio aditivo ✓,
  a la espera de que el front lo pida.
