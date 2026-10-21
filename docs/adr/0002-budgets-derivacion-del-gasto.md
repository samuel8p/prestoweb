# ADR 0002 — Gastos categorizados y presupuestos: el importe se deriva del ledger

- **Estado:** aceptado
- **Fecha:** 2026-10-21
- **Ámbito:** app `budgets` (Bloque 6b del plan de Presto)

## Contexto

El cliente resolvió la decisión O4 (HANDOFF §11.2): el **ledger es la fuente de
verdad** del dinero y de los saldos, y los presupuestos mensuales calculan el
gasto acumulado **por categoría y moneda**. Hay un registro de gastos personales
con categorías, vinculado a los movimientos del ledger cuando corresponda, **sin
duplicar movimientos ni mantener registros financieros contradictorios**.

Restricciones que condicionan el diseño:

- AGENTS §5.1: `views.py` finas, `services.py` para la escritura,
  `selectors.py` para la lectura; la lógica de negocio no va en serializers,
  signals ni `save()`.
- AGENTS §5.2: entre apps solo se usan `services.py` y `selectors.py`; sin
  ForeignKey entre apps de dominio; `core` no importa ninguna otra app.
- AGENTS §6: `Decimal` siempre, un solo redondeo en `core/money.py`, no se
  mezclan monedas, el ledger es inmutable y sus movimientos no se editan.
- AGENTS §7: el modelo de `budgets` preveía `Budget` con
  `category_id` "(UUID, sin FK)" y dejaba las categorías como TODO, porque el
  modelo de categorías todavía no existía.
- AGENTS §10: 90% de cobertura en `services.py` de `budgets`.

## Decisión

1. **El gasto no guarda importe.** La tabla `Expense` guarda solo el usuario, la
   categoría y el `ledger_transaction_id` del movimiento. El monto que suma al
   presupuesto se **deriva del ledger al leer**, en un lote. Así la app no
   guarda una segunda copia de los importes y no puede contradecir al ledger.
2. **`Category` es un modelo propio con FK interna.** `Budget.category` es una
   ForeignKey **dentro de la misma app** (como `investments.Position.product`).
   AGENTS §5.2 solo prohíbe las ForeignKey *entre apps de dominio*; el "(UUID,
   sin FK)" de AGENTS §7 respondía a que la categoría no existía, y ahora sí.
   La columna en la base sigue siendo `category_id`.
3. **Las reglas de gasto son una función pura.** `budgets.selectors` deriva,
   para cada movimiento, si es gasto del usuario y cuánto suma:
   - tiene que salir de la billetera del usuario (débito);
   - el crédito no puede ir a otra cuenta del **propio** usuario;
   - el crédito no puede ir a la cuenta `system` (movimiento de inversión);
   - el **desembolso** de un préstamo no cuenta: el dinero se convierte en un
     activo;
   - el **pago de una cuota** cuenta solo por el **interés**: el capital es
     amortización de deuda, no consumo;
   - un movimiento **revertido** no cuenta;
   - un movimiento **sin categoría** no se asigna a ningún presupuesto.
   La función es pura (no consulta la base) para que las reglas defensivas se
   puedan probar sin construir movimientos imposibles con los datos reales.
4. **Enlace con los préstamos.** `Installment` y `Loan` guardan el
   `ledger_transaction_id` del movimiento que pagó la cuota o desembolsó el
   préstamo. `loans.selectors` expone el desglose en **primitivos** (tipo,
   capital, interés, moneda), nunca modelos de otra app.
5. **Lectura en lote, sin N+1.** El detalle de los movimientos se resuelve con
   `ledger.selectors.list_movement_details` (un `prefetch_related` y una
   subconsulta `Exists` para el estado de reversión) y el desglose de préstamos
   con `loans.selectors.list_loan_movement_breakdowns`. Hay un test que
   comprueba que el número de consultas no crece con la cantidad de movimientos.
6. **Un presupuesto, una moneda.** `Budget` es único por
   `(usuario, categoría, período, moneda)` y el gasto se filtra por la moneda
   del presupuesto: nunca se suman ARS y USD. El período es el mes calendario
   en UTC (`TIME_ZONE` del proyecto).
7. **El umbral de alerta es un porcentaje entre 0 y 100**, con
   `CheckConstraint` en la base. El importe que dispara la alerta se calcula con
   `core.money.round_two`.

## Consecuencias

**Positivas**

- El ledger sigue siendo la única fuente de verdad: `budgets` no puede mostrar
  un importe que contradiga al ledger.
- El presupuesto nunca mezcla monedas y cada categoría puede tener su propio
  límite en ARS y en USD.
- Las reglas de gasto quedan en un solo lugar y se prueban de punta a punta
  (tests de integración con movimientos reales y tests unitarios de las reglas
  defensivas).

**Negativas / riesgos asumidos**

- El cálculo de un presupuesto lee del ledger: es más pesado que un `SUM` sobre
  una tabla de gastos. Se compensa con el lote; si el volumen de movimientos
  creciera, habría que materializar el importe (y cambiaría esta decisión).
- La clasificación depende de que el movimiento exista en el ledger: un gasto
  sin movimiento no se puede registrar (decisión del cliente: no hay gastos
  manuales).
- El enlace `Installment.ledger_transaction_id` /
  `Loan.ledger_transaction_id` es un dato que se agrega en la app de préstamos
  para que otra app pueda consultar el desglose. Si mañana el desglose cambia,
  hay que actualizar esos campos.
- La categoría es una etiqueta del usuario: si el usuario renombra la categoría,
  el histórico de gastos conserva el mismo `category_id` (el nombre no se
  congela).

**Pendiente**

- `Goal` (AGENTS §7) no se implementó: no estaba en el alcance pedido.
- La categoría no tiene color, ícono ni presupuesto por defecto: no hay
  requisito definido para eso.
- `reports` y `notifications` siguen sin especificación (HANDOFF §11.4).
