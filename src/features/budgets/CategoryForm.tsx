import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { describeError } from '../../lib/api/errors'
import { useCreateCategory } from './api'

const categorySchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, 'Ingresá el nombre de la categoría.')
    .max(100, 'El nombre es demasiado largo.'),
})

type CategoryValues = z.infer<typeof categorySchema>

export interface CategoryFormProps {
  onDone: () => void
}

/** Formulario para crear una categoría de gasto. */
export function CategoryForm({ onDone }: CategoryFormProps) {
  const createCategory = useCreateCategory()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<CategoryValues>({
    resolver: zodResolver(categorySchema),
    defaultValues: { name: '' },
  })

  async function onSubmit(values: CategoryValues) {
    setFormError(null)
    try {
      await createCategory.mutateAsync({ name: values.name })
      onDone()
    } catch (error) {
      const described = describeError(error)
      setFormError(described.message)
      for (const [field, messages] of Object.entries(described.fieldErrors)) {
        if (field === 'name') {
          setError('name', { message: messages[0] ?? 'Revisá este dato.' })
        }
      }
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      {formError ? <Alert tone="danger">{formError}</Alert> : null}

      <Input
        label="Nombre de la categoría"
        placeholder="Almacenamiento"
        error={errors.name?.message}
        {...register('name')}
      />

      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onDone}>
          Cancelar
        </Button>
        <Button type="submit" loading={createCategory.isPending}>
          Crear categoría
        </Button>
      </div>
    </form>
  )
}
