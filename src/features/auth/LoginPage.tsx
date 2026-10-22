import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { z } from 'zod'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { describeError } from '../../lib/api/errors'
import { AuthLayout } from './AuthLayout'
import { useAuth } from './auth-context'

const loginSchema = z.object({
  email: z.string().min(1, 'Ingresá tu email.').email('Ingresá un email válido.'),
  password: z.string().min(1, 'Ingresá tu contraseña.'),
})

type LoginValues = z.infer<typeof loginSchema>

/** Pantalla de inicio de sesión. */
export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  const from = (location.state as { from?: string } | null)?.from ?? '/panel'

  async function onSubmit(values: LoginValues) {
    setFormError(null)
    try {
      await login(values.email, values.password)
      navigate(from, { replace: true })
    } catch (error) {
      const described = describeError(error)
      setFormError(described.message)
      for (const [field, messages] of Object.entries(described.fieldErrors)) {
        if (field === 'email' || field === 'password') {
          setError(field, { message: messages[0] ?? 'Revisá este dato.' })
        }
      }
    }
  }

  return (
    <AuthLayout
      title="Iniciá sesión"
      description="Entrá con tu email y contraseña."
      footer={
        <>
          ¿No tenés cuenta?{' '}
          <Link to="/registro" className="font-medium text-primary hover:underline">
            Registrate
          </Link>
        </>
      }
    >
      <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        {formError ? <Alert tone="danger">{formError}</Alert> : null}

        <Input
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="ana@example.com"
          icon="mail"
          error={errors.email?.message}
          {...register('email')}
        />

        <Input
          label="Contraseña"
          type="password"
          autoComplete="current-password"
          icon="lock"
          error={errors.password?.message}
          {...register('password')}
        />

        <Button type="submit" loading={isSubmitting} className="mt-1 w-full">
          Ingresar
        </Button>
      </form>
    </AuthLayout>
  )
}
