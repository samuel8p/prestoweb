import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'
import { describeError } from '../../lib/api/errors'
import { compareDecimals } from '../../lib/money/decimal'
import type { Category } from '../../lib/api/types'
import { useCreateBudget } from './api'

const AMOUNT_PATTERN = /^\d{1,16}(\.\d{1,2})?$/

const budgetSchema = z.object({
  category_id: z.string().min(1, 'Elegí una categoría.'),
  limit_amount: z
    .string()
    .trim()
    .regex(AMOUNT_PATTERN, 'Ingresá un importe válido, con hasta 2 decimales.')
    .refine(
      (value) => compareDecimals(value, '0.00') > 0,
      'El límite tiene que ser mayor que cero.',
    ),
  currency: z.enum(['ARS', 'USD']),
  alert_threshold: z
    .string()
    .trim()
    .regex(/^\d{1,3}$/, 'Ingresá un porcentaje entre 0 y 100.')
    .refine((value) => Number(value) >= 0 && Number(value) <= 100, 'El umbral va entre 0 y 100.'),
})

type BudgetValues = z.infer<typeof budgetSchema>

const CURRENCY_OPTIONS = [
  { value: 'ARS', label: 'Pesos (ARS)' },
  { value: 'USD', label: 'Dólares (USD)' },
]

export interface BudgetFormProps {
  categories: Category[]
  defaultCurrency: 'ARS' | 'USD'
  onDone: () => void
}

/** Formulario para crear un presupuesto mensual. */
export function BudgetForm({ categories, defaultCurrency, onDone }: BudgetFormProps) {
  const createBudget = useCreateBudget()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<BudgetValues>({
    resolver: zodResolver(budgetSchema),
    defaultValues: {
      category_id: categories[0]?.id ?? '',
      limit_amount: '',
      currency: defaultCurrency,
      alert_threshold: '80',
    },
  })

  async function onSubmit(values: BudgetValues) {
    setFormError(null)
    try {
      await createBudget.mutateAsync({
        category_id: values.category_id,
        limit_amount: values.limit_amount,
        currency: values.currency,
        alert_threshold: Number(values.alert_threshold),
      })
      onDone()
    } catch (error) {
      const described = describeError(error)
      setFormError(described.message)
      for (const [field, messages] of Object.entries(described.fieldErrors)) {
        if (field in values) {
          setError(field as keyof BudgetValues, { message: messages[0] ?? 'Revisá este dato.' })
        }
      }
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      {formError ? <Alert tone="danger">{formError}</Alert> : null}

      <Select
        label="Categoría"
        options={categories.map((category) => ({ value: category.id, label: category.name }))}
        hint={categories.length === 0 ? 'Primero creá una categoría.' : undefined}
        error={errors.category_id?.message}
        {...register('category_id')}
      />

      <Input
        label="Límite mensual"
        inputMode="decimal"
        placeholder="200000.00"
        error={errors.limit_amount?.message}
        {...register('limit_amount')}
      />

      <Select
        label="Moneda"
        options={CURRENCY_OPTIONS}
        error={errors.currency?.message}
        {...register('currency')}
      />

      <Input
        label="Umbral de alerta (%)"
        inputMode="numeric"
        hint="Se avisa cuando el gasto llega a este porcentaje del límite."
        error={errors.alert_threshold?.message}
        {...register('alert_threshold')}
      />

      <div className="flex justify-end gap-2 border-t border-line pt-4">
        <Button variant="secondary" onClick={onDone}>
          Cancelar
        </Button>
        <Button type="submit" loading={createBudget.isPending}>
          Crear presupuesto
        </Button>
      </div>
    </form>
  )
}
