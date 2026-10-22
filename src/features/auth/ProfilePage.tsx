import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { z } from 'zod'

import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardHeader } from '../../components/ui/Card'
import { Input } from '../../components/ui/Input'
import { PageHeader } from '../../components/ui/PageHeader'
import { Select } from '../../components/ui/Select'
import { Spinner } from '../../components/ui/Spinner'
import { apiPaths } from '../../lib/config'
import { describeError } from '../../lib/api/errors'
import { queryKeys } from '../../lib/query/keys'
import type { User } from '../../lib/api/types'
import { useApiClient, useAuth } from './auth-context'
import { useKyc, useSubmitKyc } from './useKyc'

const profileSchema = z.object({
  phone_number: z.string().max(32, 'El teléfono es demasiado largo.').optional(),
  date_of_birth: z.string().optional(),
  country: z
    .string()
    .regex(/^[A-Z]{2}$/, 'El país se escribe con dos letras, por ejemplo AR.')
    .optional()
    .or(z.literal('')),
})

type ProfileValues = z.infer<typeof profileSchema>

const KYC_TONE = {
  approved: 'success',
  pending: 'warning',
  rejected: 'danger',
} as const

const KYC_LABEL = {
  approved: 'Aprobada',
  pending: 'Pendiente',
  rejected: 'Rechazada',
} as const

/** Pantalla de perfil: datos de la cuenta, perfil y estado del KYC. */
export function ProfilePage() {
  const { user } = useAuth()
  const client = useApiClient()
  const queryClient = useQueryClient()
  const { data: kyc, isLoading: kycLoading } = useKyc()
  const submitKyc = useSubmitKyc()
  const [formError, setFormError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [documentType, setDocumentType] = useState('DNI')
  const [documentNumber, setDocumentNumber] = useState('')

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { phone_number: '', date_of_birth: '', country: '' },
  })

  const updateProfile = useMutation({
    mutationFn: (values: ProfileValues) =>
      client.patch<User>(apiPaths.me, {
        phone_number: values.phone_number || undefined,
        date_of_birth: values.date_of_birth || null,
        country: values.country || undefined,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.me })
      setSaved(true)
    },
    onError: (error) => {
      const described = describeError(error)
      setFormError(described.message)
      for (const [field, messages] of Object.entries(described.fieldErrors)) {
        if (field === 'phone_number' || field === 'date_of_birth' || field === 'country') {
          setError(field, { message: messages[0] ?? 'Revisá este dato.' })
        }
      }
    },
  })

  useEffect(() => {
    if (saved) {
      const timer = window.setTimeout(() => setSaved(false), 3000)
      return () => window.clearTimeout(timer)
    }
    return undefined
  }, [saved])

  function onSubmit(values: ProfileValues) {
    setFormError(null)
    setSaved(false)
    updateProfile.mutate(values)
  }

  async function onSubmitKyc(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError(null)
    try {
      await submitKyc.mutateAsync({
        document_type: documentType,
        document_number: documentNumber.trim(),
      })
      setDocumentNumber('')
    } catch (error) {
      setFormError(describeError(error).message)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Mi perfil" description="Tus datos y el estado de tu cuenta." />

      {/* Datos de la cuenta */}
      <Card>
        <CardHeader title="Datos de la cuenta" icon="user" />
        <dl className="grid gap-5 px-5 py-4 sm:grid-cols-2">
          <div>
            <dt className="text-[13px] text-slate-500">Email</dt>
            <dd className="mt-0.5 text-sm font-medium text-slate-900">{user?.email ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-[13px] text-slate-500">Nombre</dt>
            <dd className="mt-0.5 text-sm font-medium text-slate-900">
              {[user?.first_name, user?.last_name].filter(Boolean).join(' ') || '—'}
            </dd>
          </div>
        </dl>
      </Card>

      {/* KYC */}
      <Card>
        <CardHeader
          title="Verificación KYC"
          description="Necesitás estar verificado para mover dinero."
          icon="shield"
          action={
            kycLoading ? null : (
              <Badge tone={kyc ? (KYC_TONE[kyc.status] ?? 'neutral') : 'neutral'} dot>
                {kyc ? (KYC_LABEL[kyc.status] ?? kyc.status) : 'Sin verificar'}
              </Badge>
            )
          }
        />

        <div className="flex flex-col gap-4 px-5 py-4">
          {kycLoading ? <Spinner label="Cargando el estado de la verificación" /> : null}

          {kyc?.status === 'approved' ? (
            <Alert tone="success">Tu cuenta está verificada. Ya podés mover dinero.</Alert>
          ) : null}

          {kyc?.status === 'pending' ? (
            <Alert tone="info">
              Tu verificación está en proceso. Te avisamos por email cuando esté resuelta.
            </Alert>
          ) : null}

          {kyc?.status === 'rejected' ? (
            <Alert tone="danger">
              Tu verificación fue rechazada. Revisá tus datos y pedí una nueva verificación.
            </Alert>
          ) : null}

          {!kyc || kyc.status === 'rejected' ? (
            <form className="flex flex-col gap-4 sm:flex-row sm:items-end" onSubmit={onSubmitKyc}>
              <div className="flex-1">
                <Select
                  label="Tipo de documento"
                  value={documentType}
                  onChange={(event) => setDocumentType(event.target.value)}
                  options={['DNI', 'Pasaporte', 'Cédula'].map((value) => ({
                    value,
                    label: value,
                  }))}
                />
              </div>
              <div className="flex-[2]">
                <Input
                  label="Número de documento"
                  value={documentNumber}
                  onChange={(event) => setDocumentNumber(event.target.value)}
                  placeholder="12345678"
                />
              </div>
              <Button type="submit" loading={submitKyc.isPending}>
                Pedir verificación
              </Button>
            </form>
          ) : null}

          <p className="text-xs text-slate-500">
            Solo se envía la metadata del documento. La app no sube archivos ni guarda datos
            sensibles.
          </p>
        </div>
      </Card>

      {/* Datos de contacto */}
      <Card>
        <CardHeader
          title="Datos de contacto"
          description="Opcionales, nos ayudan a contactarte."
          icon="mail"
        />
        <form
          className="flex flex-col gap-4 px-5 py-4"
          onSubmit={handleSubmit(onSubmit)}
          noValidate
        >
          {formError ? <Alert tone="danger">{formError}</Alert> : null}
          {saved ? <Alert tone="success">Guardamos tus datos.</Alert> : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Teléfono"
              type="tel"
              autoComplete="tel"
              placeholder="+54 9 11 1234 5678"
              icon="phone"
              error={errors.phone_number?.message}
              {...register('phone_number')}
            />
            <Input
              label="Fecha de nacimiento"
              type="date"
              icon="calendar"
              error={errors.date_of_birth?.message}
              {...register('date_of_birth')}
            />
          </div>

          <Input
            label="País"
            placeholder="AR"
            hint="Código de dos letras (ISO 3166-1)."
            error={errors.country?.message}
            {...register('country')}
          />

          <div className="border-t border-line pt-4">
            <Button type="submit" loading={isSubmitting || updateProfile.isPending}>
              Guardar cambios
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
