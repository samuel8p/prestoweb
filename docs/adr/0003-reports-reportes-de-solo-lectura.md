# ADR 0003 — App `reports`: reportes de solo lectura con una moneda por reporte

- **Estado:** aceptado
- **Fecha:** 2026-10-21
- **Ámbito:** app `reports` (Bloque 6c del plan de Presto)

## Contexto

El cliente aprobó cuatro reportes de solo lectura, todos del usuario
autenticado:

1. `GET /api/v1/reports/spending/`: gasto por categoría en el rango.
2. `GET /api/v1/reports/loans/`: préstamos como prestatario y como prestamista.
3. `GET /api/v1/reports/investments/`: posiciones, capital invertido e interés.
4. `GET /api/v1/reports/movements/`: movimientos del ledger con `is_reversed`.

Reglas fijadas: la moneda es obligatoria (un reporte = una moneda, nunca se
mezcla ni se convierte), el rango `from`/`to` va por defecto en el mes
calendario actual (UTC) y no puede superar 12 meses calendario, la exportación
a CSV se hace con `?export=csv` usando el módulo `csv` de la stdlib
neutralizando la inyección de fórmulas, y cada usuario ve solo sus datos.

Restricciones que condicionan el diseño:

- AGENTS §4/§5: la app sigue la estructura de `matching` (app de solo lectura):
  sin modelos, sin escrituras, sin migraciones.
- AGENTS §5.2: entre apps solo se usan `services.py` y `selectors.py`; sin
  ForeignKey y sin importar los modelos de otra app.
- AGENTS §6: los importes son `Decimal`, el redondeo solo vía `core/money.py`
  y no se mezclan monedas.
- AGENTS §10: 90% de cobertura para la app `reports` en la CI.

## Decisión

1. **Sin modelos ni escrituras.** `reports` no tiene `models.py`: no hay
   migraciones y no se toca el schema de ninguna app.
2. **Una moneda por reporte.** `currency` es obligatorio y tiene que ser `ARS`
   o `USD`. Los agregadores filtran por la moneda **antes** de sumar, así que
   nunca se mezclan importes ni se convierten.
3. **El rango es un mes calendario en UTC por defecto.** `from` y `to` se leen
   en ISO (`AAAA-MM-DD`); si falta uno, se usa el primer o el último día del
   mes actual. El rango no puede ser invertido ni cubrir más de 12 meses
   calendario: ambos casos son 400 con el formato de AGENTS §8.
4. **El importe se deriva, no se recalcula.** El reporte de spending reutiliza
   el selector de `budgets` (`list_spending_movements`), que ya deriva el
   importe del ledger aplicando las reglas de gasto (interés de una cuota de
   préstamo, inversiones, reversos). El reporte de movimientos reutiliza
   `ledger.selectors.list_movement_details`.
5. **Se agregaron selectores de lectura en las apps dueñas** (solo lectura,
   con tests, sin tocar el schema ni la integridad del ledger):
   - `ledger.selectors.list_transactions_in_period`: movimientos del usuario en
     un rango y una moneda.
   - `loans.selectors.list_installments_for_loans`: cuotas de varios
     préstamos en una sola consulta.
   - `budgets.selectors.list_spending_movements`: movimientos categorizados con
     el importe derivado del ledger.
6. **Sin N+1.** Los movimientos se resuelven en un lote (`list_movement_details`
   con `prefetch_related` y una subconsulta `Exists`) y las cuotas de todos los
   préstamos del usuario se resuelven en una consulta.
7. **El "saldo pendiente" de un préstamo es la suma de las cuotas pendientes**
   (capital e interés): es lo que falta pagar y lo que el prestamista va a
   cobrar. El "interés pagado/cobrado" es el interés de las cuotas ya pagadas.
8. **CSV con el módulo `csv` de la stdlib.** Las celdas que empiezan por `=`,
   `+`, `-` o `@` se exportan con un apóstrofo adelante para que la planilla no
   las ejecute. El `Content-Type` es `text/csv; charset=utf-8` y el
   `Content-Disposition` es `attachment`.
9. **Tope de 10.000 filas por exportación.** Un reporte más grande responde
   400 en vez de bajar un archivo enorme. El JSON de movimientos va paginado con
   `StandardPagination` (100 por página, máximo 1.000). El tope está en
   `apps/reports/export.py::MAX_EXPORT_ROWS`.
10. **Los reportes no exigen KYC**: son lecturas.

## Consecuencias

**Positivas**

- El ledger sigue siendo la única fuente de verdad: los reportes no guardan ni
  recalculan importes.
- Cada usuario ve solo sus datos y cada reporte es de una sola moneda.
- El CSV es seguro contra la inyección de fórmulas y tiene un tamaño acotado.

**Negativas / riesgos asumidos**

- El reporte de spending carga en memoria los movimientos categorizados del
  usuario antes de agregar: con muchísimos movimientos categorizados el costo
  crece (el rango de 12 meses acota el período, pero el filtro por categoría y
  moneda se aplica después de resolver los movimientos).
- `outstanding_amount` incluye el interés de las cuotas pendientes: es la
  lectura de "cuánto falta pagar", no el capital pendiente.
- El CSV de préstamos no incluye el detalle de las próximas cuotas (queda en el
  JSON): el CSV trae el resumen por rol y la cantidad de cuotas próximas.
- El contrato de `import-linter` para `reports` cubre `ledger`, `loans`,
  `investments`, `budgets` e `identity`. Los tests de `reports` usan
  `offers.services` (una **service**, la interfaz autorizada) para armar un
  préstamo; si en el futuro hace falta, esa app también debería entrar al
  contrato.
- No hay paginación en el JSON de spending, loans e investments: el tope de
  filas solo aplica a la exportación CSV.

**Pendiente**

- `notifications` (Bloque 6d) sigue sin especificación.
- El envío del esquema OpenAPI al frontend y el CORS real siguen pendientes.
