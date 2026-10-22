import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { describeError } from '../../lib/api/errors'
import { compareDecimals } from '../../lib/money/decimal'
import { createIdempotencyKey } from '../../lib/idempotency'
import type { InvestmentProduct } from '../../lib/api/types'
import { useOpenPosition } from './api'

const AMOUNT_PATTERN = /^\d{1,16}(\.\d{1,2})?$/

const positionSchema = z.object({
  amount: z
    .string()
    .trim()
    .regex(AMOUNT_PATTERN, 'Ingresá un importe válido, con hasta 2 decimales.')
    .refine(
      (value) => compareDecimals(value, '0.00') > 0,
      'El importe tiene que ser mayor que cero.',
    ),
})

type PositionValues = z.infer<typeof positionSchema>

export interface OpenPositionFormProps {
  product: InvestmentProduct
  onDone: () => void
}

/** Formulario para abrir una posición de inversión a plazo fijo. */
export function OpenPositionForm({ product, onDone }: OpenPositionFormProps) {
  const openPosition = useOpenPosition()
  const [idempotencyKey] = useState(() => createIdempotencyKey())
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<PositionValues>({
    resolver: zodResolver(positionSchema),
    defaultValues: { amount: '' },
  })

  const currency = product.currency === 'USD' ? 'USD' : 'ARS'

  async function onSubmit(values: PositionValues) {
    setFormError(null)

    if (compareDecimals(values.amount, product.min_amount) < 0) {
      setError('amount', {
        message: `El importe mínimo de este producto es ${product.min_amount} ${currency}.`,
      })
      return
    }

    try {
      await openPosition.mutateAsync({
        idempotencyKey,
        payload: {
          product_id: product.id,
          amount: values.amount,
          currency: product.currency,
        },
      })
      onDone()
    } catch (error) {
      const described = describeError(error)
      setFormError(described.message)
      for (const [field, messages] of Object.entries(described.fieldErrors)) {
        if (field === 'amount') {
          setError('amount', { message: messages[0] ?? 'Revisá este dato.' })
        }
      }
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      {formError ? <Alert tone="danger">{formError}</Alert> : null}

      <dl className="grid grid-cols-2 gap-3 rounded-[--radius-control] bg-surface-muted p-4 text-[13px]">
        <div>
          <dt className="text-slate-500">Plazo</dt>
          <dd className="font-medium text-slate-900">{product.term_days} días</dd>
        </div>
        <div>
          <dt className="text-slate-500">Tasa anual</dt>
          <dd className="font-medium text-slate-900">{product.annual_rate_tna}%</dd>
        </div>
        <div>
          <dt className="text-slate-500">Inversión mínima</dt>
          <dd className="font-medium text-slate-900 tabular">
            {product.min_amount} {currency}
          </dd>
        </div>
      </dl>

      <Input
        label="Importe a invertir"
        inputMode="decimal"
        placeholder="50000.00"
        icon="wallet"
        error={errors.amount?.message}
        {...register('amount')}
      />

      <div className="flex justify-end gap-2 border-t border-line pt-4">
        <Button variant="secondary" onClick={onDone}>
          Cancelar
        </Button>
        <Button type="submit" loading={openPosition.isPending}>
          Invertir
        </Button>
      </div>
    </form>
  )
}
