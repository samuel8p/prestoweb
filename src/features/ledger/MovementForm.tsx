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
import { createIdempotencyKey } from '../../lib/idempotency'
import { useAliasLookup } from './aliasLookup'
import { useCreateTransaction } from './api'

const AMOUNT_PATTERN = /^\d{1,16}(\.\d{1,2})?$/

const movementSchema = z.object({
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
  destination_alias: z.string().trim(),
  destination_currency: z.string(),
  description: z.string().trim().max(255, 'La descripción es demasiado larga.'),
})

type MovementValues = z.infer<typeof movementSchema>

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
  const [alias, setAlias] = useState('')
  const [searching, setSearching] = useState(false)

  const aliasQuery = useAliasLookup(alias, searching)

  const {
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
      destination_alias: '',
      destination_currency: '',
      description: '',
    },
  })

  async function onSubmit(values: MovementValues) {
    setFormError(null)

    let destinationAccountId: string | undefined

    if (values.type === 'transfer') {
      const target = aliasQuery.data?.wallets.find(
        (wallet) => wallet.currency === values.destination_currency,
      )
      if (!target) {
        setError('destination_alias', {
          message: 'Buscá el alias y elegí la moneda de destino.',
        })
        return
      }
      destinationAccountId = target.account_id
    }

    try {
      await createTransaction.mutateAsync({
        idempotencyKey,
        payload: {
          type: values.type,
          currency: values.currency,
          amount: values.amount,
          description: values.description || undefined,
          destination_account_id: destinationAccountId,
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
        options={[
          { value: 'deposit', label: 'Depósito' },
          { value: 'withdrawal', label: 'Retiro' },
          { value: 'transfer', label: 'Transferencia' },
        ]}
        error={errors.type?.message}
        {...register('type')}
      />

      <Select
        label="Moneda"
        options={[
          { value: 'ARS', label: 'Pesos (ARS)' },
          { value: 'USD', label: 'Dólares (USD)' },
        ]}
        error={errors.currency?.message}
        {...register('currency')}
      />

      <Input
        label="Importe"
        inputMode="decimal"
        placeholder="1500.50"
        icon="wallet"
        hint="Se puede escribir con hasta dos decimales."
        error={errors.amount?.message}
        {...register('amount')}
      />

      {initialType === 'transfer' ? (
        <div className="flex flex-col gap-3 rounded-[var(--radius-control)] bg-surface-muted p-4">
          <Input
            label="Alias del destinatario"
            placeholder="ana.presto"
            value={alias}
            error={errors.destination_alias?.message}
            onChange={(event) => {
              setAlias(event.target.value)
              setSearching(false)
            }}
          />

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="secondary"
              icon="search"
              loading={aliasQuery.isFetching}
              disabled={!alias.trim()}
              onClick={() => setSearching(true)}
            >
              Buscar
            </Button>
            {aliasQuery.isError ? (
              <span className="text-[13px] text-danger">
                {describeError(aliasQuery.error).message}
              </span>
            ) : null}
          </div>

          {aliasQuery.data ? (
            <div className="flex flex-col gap-3">
              <p className="text-[13px] text-ink-muted">
                {aliasQuery.data.name} · alias{' '}
                <span className="font-semibold text-ink">@{aliasQuery.data.alias}</span>
              </p>
              {aliasQuery.data.wallets.length === 0 ? (
                <Alert tone="warning">Esa persona todavía no tiene billeteras.</Alert>
              ) : (
                <Select
                  label="Moneda de destino"
                  options={aliasQuery.data.wallets.map((wallet) => ({
                    value: wallet.currency,
                    label: wallet.currency,
                  }))}
                  error={errors.destination_currency?.message}
                  {...register('destination_currency', {
                    value: aliasQuery.data.wallets[0]?.currency ?? '',
                  })}
                />
              )}
            </div>
          ) : null}
        </div>
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
