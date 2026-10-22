import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { describeError } from '../../lib/api/errors'
import { AuthLayout } from './AuthLayout'
import { useAuth } from './auth-context'

const registerSchema = z
  .object({
    email: z.string().min(1, 'Ingresá tu email.').email('Ingresá un email válido.'),
    password: z
      .string()
      .min(8, 'La contraseña tiene que tener al menos 8 caracteres.')
      .regex(/[A-Za-z]/, 'La contraseña tiene que tener al menos una letra.')
      .regex(/\d/, 'La contraseña tiene que tener al menos un número.'),
    confirmPassword: z.string().min(1, 'Repetí la contraseña.'),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: 'Las contraseñas no coinciden.',
    path: ['confirmPassword'],
  })

type RegisterValues = z.infer<typeof registerSchema>

/** Pantalla de registro de cuenta. */
export function RegisterPage() {
  const { register: registerUser } = useAuth()
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: '', password: '', confirmPassword: '' },
  })

  async function onSubmit(values: RegisterValues) {
    setFormError(null)
    try {
      await registerUser(values.email, values.password)
      navigate('/panel', { replace: true })
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
      title="Creá tu cuenta"
      description="Con una cuenta podés pedir préstamos, invertir y hacer presupuestos."
      footer={
        <>
          ¿Ya tenés cuenta?{' '}
          <Link to="/ingresar" className="font-medium text-brand-700 hover:underline">
            Ingresá
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
          autoComplete="new-password"
          icon="lock"
          hint="Mínimo 8 caracteres, con al menos una letra y un número."
          error={errors.password?.message}
          {...register('password')}
        />

        <Input
          label="Repetí la contraseña"
          type="password"
          autoComplete="new-password"
          icon="lock"
          error={errors.confirmPassword?.message}
          {...register('confirmPassword')}
        />

        <Button type="submit" loading={isSubmitting} className="mt-1 w-full">
          Crear cuenta
        </Button>
      </form>
    </AuthLayout>
  )
}
