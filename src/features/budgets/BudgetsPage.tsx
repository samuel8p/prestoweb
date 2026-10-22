import { useState } from 'react'

import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardHeader } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Modal } from '../../components/ui/Modal'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import { PageHeader } from '../../components/ui/PageHeader'
import { ProgressBar } from '../../components/ui/ProgressBar'
import { Segmented } from '../../components/ui/Segmented'
import { SkeletonRows } from '../../components/ui/Skeleton'
import { describeError } from '../../lib/api/errors'
import { percentOf } from '../../lib/money/decimal'
import { formatDateTime } from '../../lib/money/format'
import type { Currency } from '../../lib/money/format'
import { useMovements } from '../ledger/useMovements'
import { useBudgets, useBudgetStatuses, useCategories, useExpenses, useRenameCategory } from './api'
import { BudgetForm } from './BudgetForm'
import { CategoryForm } from './CategoryForm'
import { ExpenseForm } from './ExpenseForm'

const CURRENCY_OPTIONS = [
  { value: 'ARS' as const, label: 'Pesos (ARS)' },
  { value: 'USD' as const, label: 'Dólares (USD)' },
]

/** Presupuestos: categorías, límites mensuales, estado y gastos categorizados. */
export function BudgetsPage() {
  const [currency, setCurrency] = useState<Currency>('ARS')
  const [categoryOpen, setCategoryOpen] = useState(false)
  const [budgetOpen, setBudgetOpen] = useState(false)
  const [expenseOpen, setExpenseOpen] = useState(false)
  const [renaming, setRenaming] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)

  const categories = useCategories()
  const budgets = useBudgets()
  const expenses = useExpenses()
  const renameCategory = useRenameCategory()

  const categoryList = categories.data?.results ?? []
  const budgetList = (budgets.data?.results ?? []).filter((budget) => budget.currency === currency)
  const statuses = useBudgetStatuses(budgetList.map((budget) => budget.id))
  const expenseList = expenses.data?.results ?? []

  const movements = useMovements({ currency })
  const movementList = movements.data?.pages.flatMap((page) => page.results) ?? []

  async function handleRename(categoryId: string) {
    setActionError(null)
    try {
      await renameCategory.mutateAsync({ id: categoryId, name: renameValue })
      setRenaming(null)
    } catch (error) {
      setActionError(describeError(error).message)
    }
  }

  return (
    <div className="flex animate-fade-up flex-col gap-6">
      <PageHeader
        title="Presupuestos"
        description="Categorizá tus gastos y controlá cuánto gastás por categoría."
        action={
          <Button
            icon="plus"
            onClick={() => setBudgetOpen(true)}
            disabled={categoryList.length === 0}
          >
            Nuevo presupuesto
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <span className="text-[13px] font-medium text-ink">Moneda</span>
        <Segmented
          label="Moneda"
          value={currency}
          options={CURRENCY_OPTIONS}
          onChange={setCurrency}
        />
      </div>

      {actionError ? <Alert tone="danger">{actionError}</Alert> : null}

      {/* Presupuestos del mes */}
      <Card>
        <CardHeader
          title="Presupuestos del mes"
          description={`Cuánto gastaste de cada límite en ${currency}.`}
          icon="budget"
        />

        {budgets.isLoading ? <SkeletonRows rows={2} columns={4} /> : null}

        {budgets.isError ? (
          <div className="px-5 py-4">
            <ErrorState
              message={describeError(budgets.error).message}
              onRetry={() => void budgets.refetch()}
            />
          </div>
        ) : null}

        {!budgets.isLoading && !budgets.isError && budgetList.length === 0 ? (
          <EmptyState
            title={`No tenés presupuestos en ${currency}`}
            description="Creá un presupuesto mensual por categoría."
            action={
              <Button size="sm" onClick={() => setBudgetOpen(true)}>
                Crear presupuesto
              </Button>
            }
          />
        ) : null}

        <ul className="stagger divide-y divide-line">
          {budgetList.map((budget) => {
            const status = statuses.byBudget.get(budget.id)
            const spent = status?.spent_amount ?? '0.00'
            const percent = status ? percentOf(spent, status.limit_amount) : 0
            const tone = status?.alert_triggered
              ? 'danger'
              : percent >= budget.alert_threshold
                ? 'warning'
                : 'ok'

            return (
              <li key={budget.id} className="px-5 py-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-[15px] font-semibold text-ink">{budget.category.name}</p>
                    <p className="mt-0.5 text-[13px] text-ink-muted">
                      Límite <MoneyAmount value={budget.limit_amount} currency={budget.currency} />{' '}
                      · aviso al {budget.alert_threshold}%
                    </p>
                  </div>
                  {status?.alert_triggered ? (
                    <Badge tone="danger" dot>
                      Alerta
                    </Badge>
                  ) : null}
                </div>

                {status ? (
                  <>
                    <dl className="mt-4 grid gap-4 sm:grid-cols-3">
                      <div>
                        <dt className="label-caps text-ink-subtle">Gastado</dt>
                        <dd className="mt-0.5 text-sm font-semibold text-ink tabular">
                          <MoneyAmount value={status.spent_amount} currency={currency} />
                        </dd>
                      </div>
                      <div>
                        <dt className="label-caps text-ink-subtle">Disponible</dt>
                        <dd className="mt-0.5 text-sm font-semibold text-ink tabular">
                          <MoneyAmount value={status.remaining_amount} currency={currency} />
                        </dd>
                      </div>
                      <div>
                        <dt className="label-caps text-ink-subtle">Umbral</dt>
                        <dd className="mt-0.5 text-sm font-semibold text-ink tabular">
                          <MoneyAmount value={status.threshold_amount} currency={currency} />
                        </dd>
                      </div>
                    </dl>

                    <div className="mt-3 max-w-sm">
                      <ProgressBar
                        percent={percent}
                        label={`Gastado de ${budget.category.name}`}
                        tone={tone}
                      />
                    </div>
                  </>
                ) : statuses.isLoading ? (
                  <div className="mt-4">
                    <SkeletonRows rows={1} columns={3} />
                  </div>
                ) : null}
              </li>
            )
          })}
        </ul>
      </Card>

      {/* Categorías */}
      <Card>
        <CardHeader
          title="Categorías"
          description="Las etiquetas que usás para ordenar tus gastos."
          icon="offer"
          action={
            <Button size="sm" variant="secondary" onClick={() => setCategoryOpen(true)}>
              Nueva categoría
            </Button>
          }
        />

        {categories.isLoading ? <SkeletonRows rows={2} columns={2} /> : null}

        {categories.isError ? (
          <div className="px-5 py-4">
            <ErrorState
              message={describeError(categories.error).message}
              onRetry={() => void categories.refetch()}
            />
          </div>
        ) : null}

        {!categories.isLoading && !categories.isError && categoryList.length === 0 ? (
          <EmptyState
            title="Todavía no creaste categorías"
            description="Las categorías son las etiquetas de tus gastos."
            action={
              <Button size="sm" onClick={() => setCategoryOpen(true)}>
                Crear categoría
              </Button>
            }
          />
        ) : null}

        <ul className="stagger divide-y divide-line">
          {categoryList.map((category) => (
            <li
              key={category.id}
              className="flex flex-wrap items-center justify-between gap-3 px-5 py-3"
            >
              {renaming === category.id ? (
                <form
                  className="flex flex-1 items-end gap-2"
                  onSubmit={(event) => {
                    event.preventDefault()
                    void handleRename(category.id)
                  }}
                >
                  <div className="flex-1">
                    <label
                      htmlFor={`rename-${category.id}`}
                      className="text-xs font-medium text-ink-muted"
                    >
                      Nuevo nombre
                    </label>
                    <input
                      id={`rename-${category.id}`}
                      value={renameValue}
                      onChange={(event) => setRenameValue(event.target.value)}
                      className="mt-1 w-full rounded-[var(--radius-control)] border border-line-strong px-3 py-2 text-sm focus:border-teal focus:outline-none focus:ring-2 focus:ring-teal/20"
                    />
                  </div>
                  <Button size="sm" type="submit" loading={renameCategory.isPending}>
                    Guardar
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setRenaming(null)}>
                    Cancelar
                  </Button>
                </form>
              ) : (
                <>
                  <p className="text-sm font-medium text-ink">{category.name}</p>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setRenaming(category.id)
                      setRenameValue(category.name)
                    }}
                  >
                    Renombrar
                  </Button>
                </>
              )}
            </li>
          ))}
        </ul>
      </Card>

      {/* Gastos categorizados */}
      <Card>
        <CardHeader
          title="Gastos categorizados"
          description="Los movimientos que asignaste a una categoría."
          icon="swap"
          action={
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setExpenseOpen(true)}
              disabled={movementList.length === 0}
            >
              Categorizar movimiento
            </Button>
          }
        />

        {expenses.isLoading ? <SkeletonRows rows={2} columns={2} /> : null}

        {expenses.isError ? (
          <div className="px-5 py-4">
            <ErrorState
              message={describeError(expenses.error).message}
              onRetry={() => void expenses.refetch()}
            />
          </div>
        ) : null}

        {!expenses.isLoading && !expenses.isError && expenseList.length === 0 ? (
          <EmptyState
            title="Todavía no categorizaste ningún gasto"
            description="Elegí un movimiento del ledger y asignale una categoría."
          />
        ) : null}

        <ul className="stagger divide-y divide-line">
          {expenseList.map((expense) => (
            <li
              key={expense.id}
              className="flex flex-wrap items-center justify-between gap-3 px-5 py-3"
            >
              <p className="text-sm font-medium text-ink">{expense.category.name}</p>
              <p className="text-xs text-ink-subtle tabular">
                Movimiento {expense.ledger_transaction_id.slice(0, 8)}… ·{' '}
                {formatDateTime(expense.created_at)}
              </p>
            </li>
          ))}
        </ul>
      </Card>

      <Modal
        open={categoryOpen}
        title="Nueva categoría"
        description="La etiqueta con la que vas a agrupar tus gastos."
        onClose={() => setCategoryOpen(false)}
      >
        <CategoryForm onDone={() => setCategoryOpen(false)} />
      </Modal>

      <Modal
        open={budgetOpen}
        title="Nuevo presupuesto"
        description="Un límite mensual para una categoría y una moneda."
        onClose={() => setBudgetOpen(false)}
      >
        <BudgetForm
          categories={categoryList}
          defaultCurrency={currency}
          onDone={() => setBudgetOpen(false)}
        />
      </Modal>

      <Modal
        open={expenseOpen}
        title="Categorizar movimiento"
        description="El importe sale del ledger: nunca se guarda una copia."
        onClose={() => setExpenseOpen(false)}
      >
        <ExpenseForm
          categories={categoryList}
          movements={movementList}
          onDone={() => setExpenseOpen(false)}
        />
      </Modal>
    </div>
  )
}
