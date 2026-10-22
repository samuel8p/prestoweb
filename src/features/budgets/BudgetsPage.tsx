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
import { Select } from '../../components/ui/Select'
import { Spinner } from '../../components/ui/Spinner'
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
  { value: 'ARS', label: 'Pesos (ARS)' },
  { value: 'USD', label: 'Dólares (USD)' },
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
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Presupuestos"
        description="Categorizá tus gastos y controlá cuánto gastás por categoría."
        action={
          <>
            <Button variant="secondary" onClick={() => setCategoryOpen(true)}>
              Nueva categoría
            </Button>
            <Button onClick={() => setBudgetOpen(true)} disabled={categoryList.length === 0}>
              Nuevo presupuesto
            </Button>
          </>
        }
      />

      <div className="max-w-xs">
        <Select
          label="Moneda"
          value={currency}
          options={CURRENCY_OPTIONS}
          onChange={(event) => setCurrency(event.target.value as Currency)}
        />
      </div>

      {actionError ? <Alert tone="danger">{actionError}</Alert> : null}

      <Card>
        <CardHeader
          title="Categorías"
          description="Las etiquetas que usás para ordenar tus gastos."
        />

        {categories.isLoading ? (
          <div className="flex justify-center px-4 py-10">
            <Spinner label="Cargando las categorías" />
          </div>
        ) : null}

        {categories.isError ? (
          <div className="px-4 py-4">
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

        <ul className="divide-y divide-slate-100">
          {categoryList.map((category) => (
            <li
              key={category.id}
              className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-5"
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
                      className="text-xs font-medium text-slate-600"
                    >
                      Nuevo nombre
                    </label>
                    <input
                      id={`rename-${category.id}`}
                      value={renameValue}
                      onChange={(event) => setRenameValue(event.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-200"
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
                  <p className="text-sm font-medium text-slate-900">{category.name}</p>
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

      <Card>
        <CardHeader
          title="Presupuestos del mes"
          description={`Cuánto gastaste de cada límite en ${currency}.`}
        />

        {budgets.isLoading ? (
          <div className="flex justify-center px-4 py-10">
            <Spinner label="Cargando los presupuestos" />
          </div>
        ) : null}

        {budgets.isError ? (
          <div className="px-4 py-4">
            <ErrorState
              message={describeError(budgets.error).message}
              onRetry={() => void budgets.refetch()}
            />
          </div>
        ) : null}

        {!budgets.isLoading && !budgets.isError && budgetList.length === 0 ? (
          <EmptyState
            title="No tenés presupuestos en esta moneda"
            description="Creá un presupuesto mensual por categoría."
            action={
              <Button size="sm" onClick={() => setBudgetOpen(true)}>
                Crear presupuesto
              </Button>
            }
          />
        ) : null}

        <ul className="divide-y divide-slate-100">
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
              <li key={budget.id} className="px-4 py-4 sm:px-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-slate-900">{budget.category.name}</p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      Límite <MoneyAmount value={budget.limit_amount} currency={budget.currency} />{' '}
                      · aviso al {budget.alert_threshold}%
                    </p>
                  </div>
                  {status?.alert_triggered ? <Badge tone="danger">Alerta</Badge> : null}
                </div>

                {status ? (
                  <div className="mt-3 grid gap-3 sm:grid-cols-3">
                    <div>
                      <p className="text-xs text-slate-500">Gastado</p>
                      <p className="text-sm font-semibold text-slate-900">
                        <MoneyAmount value={status.spent_amount} currency={currency} />
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Disponible</p>
                      <p className="text-sm font-semibold text-slate-900">
                        <MoneyAmount value={status.remaining_amount} currency={currency} />
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Umbral</p>
                      <p className="text-sm font-semibold text-slate-900">
                        <MoneyAmount value={status.threshold_amount} currency={currency} />
                      </p>
                    </div>
                    <div className="sm:col-span-3">
                      <ProgressBar
                        percent={percent}
                        label={`Gastado de ${budget.category.name}`}
                        tone={tone}
                      />
                    </div>
                  </div>
                ) : statuses.isLoading ? (
                  <div className="mt-3">
                    <Spinner label="Cargando el estado del presupuesto" />
                  </div>
                ) : null}
              </li>
            )
          })}
        </ul>
      </Card>

      <Card>
        <CardHeader
          title="Gastos categorizados"
          description="Los movimientos que asignaste a una categoría."
          action={
            <Button
              size="sm"
              onClick={() => setExpenseOpen(true)}
              disabled={movementList.length === 0}
            >
              Categorizar movimiento
            </Button>
          }
        />

        {expenses.isLoading ? (
          <div className="flex justify-center px-4 py-10">
            <Spinner label="Cargando los gastos" />
          </div>
        ) : null}

        {expenses.isError ? (
          <div className="px-4 py-4">
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

        <ul className="divide-y divide-slate-100">
          {expenseList.map((expense) => (
            <li
              key={expense.id}
              className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-5"
            >
              <div>
                <p className="text-sm font-medium text-slate-900">{expense.category.name}</p>
                <p className="mt-0.5 text-xs text-slate-400">
                  Movimiento {expense.ledger_transaction_id.slice(0, 8)}… ·{' '}
                  {formatDateTime(expense.created_at)}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </Card>

      <Modal open={categoryOpen} title="Nueva categoría" onClose={() => setCategoryOpen(false)}>
        <CategoryForm onDone={() => setCategoryOpen(false)} />
      </Modal>

      <Modal open={budgetOpen} title="Nuevo presupuesto" onClose={() => setBudgetOpen(false)}>
        <BudgetForm
          categories={categoryList}
          defaultCurrency={currency}
          onDone={() => setBudgetOpen(false)}
        />
      </Modal>

      <Modal
        open={expenseOpen}
        title="Categorizar movimiento"
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
