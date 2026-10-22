import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Select } from '../../components/ui/Select'
import { describeError } from '../../lib/api/errors'
import { useCreateAccount } from './api'

const accountSchema = z.object({
  currency: z.enum(['ARS', 'USD']),
})

type AccountValues = z.infer<typeof accountSchema>

const CURRENCY_OPTIONS = [
  { value: 'ARS', label: 'Pesos (ARS)' },
  { value: 'USD', label: 'Dólares (USD)' },
]

export interface CreateWalletFormProps {
  onDone: () => void
  /** Moneda que ya existe y no se puede volver a crear. */
  existingCurrency?: 'ARS' | 'USD'
}

/** Formulario para abrir una billetera en una moneda. */
export function CreateWalletForm({ onDone, existingCurrency }: CreateWalletFormProps) {
  const createAccount = useCreateAccount()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AccountValues>({
    resolver: zodResolver(accountSchema),
    defaultValues: {
      currency: existingCurrency === 'ARS' ? 'USD' : 'ARS',
    },
  })

  async function onSubmit(values: AccountValues) {
    setFormError(null)
    try {
      await createAccount.mutateAsync({ currency: values.currency })
      onDone()
    } catch (error) {
      setFormError(describeError(error).message)
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      {formError ? <Alert tone="danger">{formError}</Alert> : null}

      <Select
        label="Moneda de la billetera"
        options={CURRENCY_OPTIONS}
        error={errors.currency?.message}
        {...register('currency')}
      />

      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onDone}>
          Cancelar
        </Button>
        <Button type="submit" loading={createAccount.isPending}>
          Abrir billetera
        </Button>
      </div>
    </form>
  )
}
