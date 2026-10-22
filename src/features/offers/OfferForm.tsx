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
import { useCreateOffer } from './api'

const DECIMAL_PATTERN = /^\d{1,16}(\.\d{1,2})?$/

const offerSchema = z
  .object({
    amount: z
      .string()
      .trim()
      .regex(DECIMAL_PATTERN, 'Ingresá un importe válido, con hasta 2 decimales.')
      .refine(
        (value) => compareDecimals(value, '0.00') > 0,
        'El importe tiene que ser mayor que cero.',
      ),
    currency: z.enum(['ARS', 'USD']),
    interest_rate: z
      .string()
      .trim()
      .regex(DECIMAL_PATTERN, 'Ingresá una tasa válida, con hasta 2 decimales.')
      .refine(
        (value) => compareDecimals(value, '0.00') > 0,
        'La tasa tiene que ser mayor que cero.',
      ),
    term_months: z
      .string()
      .trim()
      .regex(/^\d{1,3}$/, 'Ingresá el plazo en meses.')
      .refine((value) => Number(value) > 0, 'El plazo tiene que ser mayor que cero.'),
    requirements: z.string().trim().max(2000, 'Los requisitos son demasiado largos.'),
  })
  .refine(
    (values) => compareDecimals(values.interest_rate, '100.00') <= 0,
    'La tasa no puede ser mayor al 100%.',
  )

type OfferValues = z.infer<typeof offerSchema>

const CURRENCY_OPTIONS = [
  { value: 'ARS', label: 'Pesos (ARS)' },
  { value: 'USD', label: 'Dólares (USD)' },
]

export interface OfferFormProps {
  onDone: () => void
}

/** Formulario para publicar una oferta de préstamo. */
export function OfferForm({ onDone }: OfferFormProps) {
  const createOffer = useCreateOffer()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<OfferValues>({
    resolver: zodResolver(offerSchema),
    defaultValues: {
      amount: '',
      currency: 'ARS',
      interest_rate: '',
      term_months: '',
      requirements: '',
    },
  })

  async function onSubmit(values: OfferValues) {
    setFormError(null)
    try {
      await createOffer.mutateAsync({
        amount: values.amount,
        currency: values.currency,
        interest_rate: values.interest_rate,
        term_months: Number(values.term_months),
        requirements: values.requirements || undefined,
      })
      onDone()
    } catch (error) {
      const described = describeError(error)
      setFormError(described.message)
      for (const [field, messages] of Object.entries(described.fieldErrors)) {
        if (field in values) {
          setError(field as keyof OfferValues, { message: messages[0] ?? 'Revisá este dato.' })
        }
      }
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      {formError ? <Alert tone="danger">{formError}</Alert> : null}

      <Input
        label="Importe"
        inputMode="decimal"
        placeholder="100000.00"
        hint="El prestatario recibe el importe completo de la oferta."
        error={errors.amount?.message}
        {...register('amount')}
      />

      <Select
        label="Moneda"
        options={CURRENCY_OPTIONS}
        error={errors.currency?.message}
        {...register('currency')}
      />

      <Input
        label="Tasa anual (TNA)"
        inputMode="decimal"
        placeholder="24.00"
        hint="Porcentaje anual: 24.00 significa 24% TNA."
        error={errors.interest_rate?.message}
        {...register('interest_rate')}
      />

      <Input
        label="Plazo en meses"
        inputMode="numeric"
        placeholder="12"
        error={errors.term_months?.message}
        {...register('term_months')}
      />

      <Input
        label="Requisitos"
        placeholder="Opcional: condiciones para el prestatario"
        error={errors.requirements?.message}
        {...register('requirements')}
      />

      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onDone}>
          Cancelar
        </Button>
        <Button type="submit" loading={createOffer.isPending}>
          Publicar oferta
        </Button>
      </div>
    </form>
  )
}
