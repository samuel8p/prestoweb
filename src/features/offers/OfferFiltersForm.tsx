import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'
import { compareDecimals } from '../../lib/money/decimal'

const DECIMAL_PATTERN = /^\d{1,16}(\.\d{1,2})?$/

const filtersSchema = z
  .object({
    currency: z.enum(['ARS', 'USD']),
    amount_min: z.string().trim(),
    amount_max: z.string().trim(),
    max_rate: z.string().trim(),
    term_months: z.string().trim(),
    ordering: z.enum(['rate', 'term', 'amount']),
  })
  .superRefine((values, ctx) => {
    if (
      values.amount_min &&
      values.amount_max &&
      compareDecimals(values.amount_min, values.amount_max) > 0
    ) {
      ctx.addIssue({
        code: 'custom',
        path: ['amount_max'],
        message: 'El importe máximo tiene que ser mayor al mínimo.',
      })
    }

    for (const field of ['amount_min', 'amount_max', 'max_rate'] as const) {
      const value = values[field]
      if (value && !DECIMAL_PATTERN.test(value)) {
        ctx.addIssue({
          code: 'custom',
          path: [field],
          message: 'Ingresá un número válido, con hasta 2 decimales.',
        })
      }
    }
  })

type FiltersValues = z.infer<typeof filtersSchema>

const CURRENCY_OPTIONS = [
  { value: 'ARS', label: 'Pesos (ARS)' },
  { value: 'USD', label: 'Dólares (USD)' },
]

const ORDERING_OPTIONS = [
  { value: 'rate', label: 'Primero las de menor tasa' },
  { value: 'term', label: 'Primero las de menor plazo' },
  { value: 'amount', label: 'Primero las de menor importe' },
]

export interface OfferFiltersFormProps {
  onFiltersChange: (filters: {
    currency: string
    amount_min?: string
    amount_max?: string
    max_rate?: string
    term_months?: number
    ordering?: string
  }) => void
}

/** Formulario de búsqueda de ofertas del marketplace. */
export function OfferFiltersForm({ onFiltersChange }: OfferFiltersFormProps) {
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FiltersValues>({
    resolver: zodResolver(filtersSchema),
    defaultValues: {
      currency: 'ARS',
      amount_min: '',
      amount_max: '',
      max_rate: '',
      term_months: '',
      ordering: 'rate',
    },
  })

  function onSubmit(values: FiltersValues) {
    setFormError(null)
    onFiltersChange({
      currency: values.currency,
      amount_min: values.amount_min || undefined,
      amount_max: values.amount_max || undefined,
      max_rate: values.max_rate || undefined,
      term_months: values.term_months ? Number(values.term_months) : undefined,
      ordering: values.ordering,
    })
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      {formError ? (
        <div className="mb-4">
          <Alert tone="danger">{formError}</Alert>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Select
          label="Moneda"
          options={CURRENCY_OPTIONS}
          error={errors.currency?.message}
          {...register('currency')}
        />

        <Input
          label="Importe mínimo"
          inputMode="decimal"
          placeholder="10000.00"
          icon="wallet"
          error={errors.amount_min?.message}
          {...register('amount_min')}
        />

        <Input
          label="Importe máximo"
          inputMode="decimal"
          placeholder="500000.00"
          icon="wallet"
          error={errors.amount_max?.message}
          {...register('amount_max')}
        />

        <Input
          label="Tasa máxima (TNA)"
          inputMode="decimal"
          placeholder="30.00"
          icon="trending"
          hint="Porcentaje anual."
          error={errors.max_rate?.message}
          {...register('max_rate')}
        />

        <Input
          label="Plazo en meses"
          inputMode="numeric"
          placeholder="12"
          icon="calendar"
          error={errors.term_months?.message}
          {...register('term_months')}
        />

        <Select
          label="Ordenar por"
          options={ORDERING_OPTIONS}
          error={errors.ordering?.message}
          {...register('ordering')}
        />
      </div>

      <div className="mt-4 flex justify-end border-t border-line pt-4">
        <Button type="submit" icon="search">
          Buscar ofertas
        </Button>
      </div>
    </form>
  )
}
