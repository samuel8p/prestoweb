import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'
import { describeError } from '../../lib/api/errors'
import { compareDecimals } from '../../lib/money/decimal'
import { createIdempotencyKey } from '../../lib/idempotency'
import { useCreateTransaction } from './api'

const AMOUNT_PATTERN = /^\d{1,16}(\.\d{1,2})?$/
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const movementSchema = z
  .object({
    type: z.enum(['deposit', 'withdrawal', 'transfer']),
    currency: z.enum(['ARS', 'USD']),
    amount: z
      .string()
      .trim()
      .regex(AMOUNT_PATTERN, 'Ingresá un importe válido, con hasta 2 decimales.')
      .refine(
        (value) => compareDecimals(value, '0.00') > 0,
        'El importe tiene que ser mayor que cero.',
      ),
    destination_account_id: z.string().trim(),
    description: z.string().trim().max(255, 'La descripción es demasiado larga.'),
  })
  .superRefine((values, ctx) => {
    if (values.type === 'transfer' && !UUID_PATTERN.test(values.destination_account_id)) {
      ctx.addIssue({
        code: 'custom',
        path: ['destination_account_id'],
        message: 'Ingresá el ID de la cuenta de destino (un UUID).',
      })
    }
  })

type MovementValues = z.infer<typeof movementSchema>

const TYPE_OPTIONS = [
  { value: 'deposit', label: 'Depósito' },
  { value: 'withdrawal', label: 'Retiro' },
  { value: 'transfer', label: 'Transferencia' },
]

const CURRENCY_OPTIONS = [
  { value: 'ARS', label: 'Pesos (ARS)' },
  { value: 'USD', label: 'Dólares (USD)' },
]

export interface MovementFormProps {
  onDone: () => void
  /** Moneda inicial del formulario. */
  defaultCurrency?: 'ARS' | 'USD'
  /** Tipo de movimiento preseleccionado (lo usan las acciones rápidas). */
  initialType?: 'deposit' | 'withdrawal' | 'transfer'
}

/**
 * Formulario para crear un movimiento de dinero.
 *
 * La clave de idempotencia se genera al abrir el formulario y se reutiliza en
 * los reintentos: la API no duplica la operación.
 */
export function MovementForm({
  onDone,
  defaultCurrency = 'ARS',
  initialType = 'deposit',
}: MovementFormProps) {
  const createTransaction = useCreateTransaction()
  const [idempotencyKey] = useState(() => createIdempotencyKey())
  const [formError, setFormError] = useState<string | null>(null)

  const {
    control,
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<MovementValues>({
    resolver: zodResolver(movementSchema),
    defaultValues: {
      type: initialType,
      currency: defaultCurrency,
      amount: '',
      destination_account_id: '',
      description: '',
    },
  })

  const type = useWatch({ control, name: 'type' })

  async function onSubmit(values: MovementValues) {
    setFormError(null)
    try {
      await createTransaction.mutateAsync({
        idempotencyKey,
        payload: {
          type: values.type,
          currency: values.currency,
          amount: values.amount,
          description: values.description || undefined,
          destination_account_id:
            values.type === 'transfer' ? values.destination_account_id : undefined,
        },
      })
      onDone()
    } catch (error) {
      const described = describeError(error)
      setFormError(described.message)
      for (const [field, messages] of Object.entries(described.fieldErrors)) {
        if (field in values) {
          setError(field as keyof MovementValues, { message: messages[0] ?? 'Revisá este dato.' })
        }
      }
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      {formError ? <Alert tone="danger">{formError}</Alert> : null}

      <Select
        label="Tipo de movimiento"
        options={TYPE_OPTIONS}
        error={errors.type?.message}
        {...register('type')}
      />

      <Select
        label="Moneda"
        options={CURRENCY_OPTIONS}
        error={errors.currency?.message}
        {...register('currency')}
      />

      <Input
        label="Importe"
        inputMode="decimal"
        placeholder="1500.50"
        hint="Se puede escribir con hasta dos decimales."
        error={errors.amount?.message}
        {...register('amount')}
      />

      {type === 'transfer' ? (
        <Input
          label="ID de la cuenta de destino"
          placeholder="11111111-1111-4111-8111-111111111111"
          hint="El UUID de la billetera de la otra persona."
          error={errors.destination_account_id?.message}
          {...register('destination_account_id')}
        />
      ) : null}

      <Input
        label="Descripción"
        placeholder="Opcional"
        error={errors.description?.message}
        {...register('description')}
      />

      <div className="flex justify-end gap-2 border-t border-line pt-4">
        <Button variant="secondary" onClick={onDone}>
          Cancelar
        </Button>
        <Button type="submit" loading={createTransaction.isPending}>
          Confirmar
        </Button>
      </div>
    </form>
  )
}
