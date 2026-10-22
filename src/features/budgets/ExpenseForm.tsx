import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Select } from '../../components/ui/Select'
import { describeError } from '../../lib/api/errors'
import { formatDateTime } from '../../lib/money/format'
import type { Category, MovementReportRow } from '../../lib/api/types'
import { useCategorizeMovement } from './api'

const expenseSchema = z.object({
  category_id: z.string().min(1, 'Elegí una categoría.'),
  ledger_transaction_id: z.string().min(1, 'Elegí un movimiento.'),
})

type ExpenseValues = z.infer<typeof expenseSchema>

export interface ExpenseFormProps {
  categories: Category[]
  movements: MovementReportRow[]
  onDone: () => void
}

/** Formulario para categorizar un movimiento como gasto. */
export function ExpenseForm({ categories, movements, onDone }: ExpenseFormProps) {
  const categorize = useCategorizeMovement()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<ExpenseValues>({
    resolver: zodResolver(expenseSchema),
    defaultValues: {
      category_id: categories[0]?.id ?? '',
      ledger_transaction_id: movements[0]?.id ?? '',
    },
  })

  async function onSubmit(values: ExpenseValues) {
    setFormError(null)
    try {
      await categorize.mutateAsync({
        category_id: values.category_id,
        ledger_transaction_id: values.ledger_transaction_id,
      })
      onDone()
    } catch (error) {
      const described = describeError(error)
      setFormError(described.message)
      for (const [field, messages] of Object.entries(described.fieldErrors)) {
        if (field in values) {
          setError(field as keyof ExpenseValues, { message: messages[0] ?? 'Revisá este dato.' })
        }
      }
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      {formError ? <Alert tone="danger">{formError}</Alert> : null}

      <Select
        label="Movimiento"
        options={movements.map((movement) => ({
          value: movement.id,
          label: `${movement.type} · ${movement.description || 'sin descripción'} · ${formatDateTime(movement.occurred_at)}`,
        }))}
        hint={movements.length === 0 ? 'No hay movimientos para categorizar.' : undefined}
        error={errors.ledger_transaction_id?.message}
        {...register('ledger_transaction_id')}
      />

      <Select
        label="Categoría"
        options={categories.map((category) => ({ value: category.id, label: category.name }))}
        hint={categories.length === 0 ? 'Primero creá una categoría.' : undefined}
        error={errors.category_id?.message}
        {...register('category_id')}
      />

      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onDone}>
          Cancelar
        </Button>
        <Button type="submit" loading={categorize.isPending}>
          Categorizar
        </Button>
      </div>
    </form>
  )
}
