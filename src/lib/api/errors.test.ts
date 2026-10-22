import { describe, expect, it } from 'vitest'

import { ApiError, apiErrorFromResponse, describeError, toFieldErrors } from './errors'

describe('toFieldErrors', () => {
  it('normaliza los errores por campo del backend', () => {
    expect(toFieldErrors({ amount: ['A valid number is required.'] })).toEqual({
      amount: ['Ingresá un número válido.'],
    })
  })

  it('acepta un mensaje suelto como si fuera una lista', () => {
    expect(toFieldErrors({ currency: 'Es obligatorio.' })).toEqual({
      currency: ['Es obligatorio.'],
    })
  })

  it('traduce los mensajes de validación en inglés del backend', () => {
    expect(toFieldErrors({ email: ['Enter a valid email address.'] })).toEqual({
      email: ['Ingresá un email válido.'],
    })
    expect(toFieldErrors({ password: ['This field is required.'] })).toEqual({
      password: ['Este campo es obligatorio.'],
    })
  })

  it('deja los errores que no son de campo en un grupo aparte', () => {
    expect(toFieldErrors({ non_field_errors: ['Ya existe uno con ese nombre.'] })).toEqual({
      non_field_errors: ['Ya existe uno con ese nombre.'],
    })
  })

  it('devuelve un objeto vacío si no hay detalles', () => {
    expect(toFieldErrors(undefined)).toEqual({})
    expect(toFieldErrors('texto')).toEqual({})
  })
})

describe('apiErrorFromResponse', () => {
  it('arma el error con el código, el mensaje y los detalles del backend', () => {
    const error = apiErrorFromResponse(400, {
      error: {
        code: 'validation_error',
        message: 'Los datos enviados no son válidos.',
        details: { amount: ['A valid number is required.'] },
      },
    })

    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(400)
    expect(error.code).toBe('validation_error')
    expect(error.fieldErrors.amount).toEqual(['Ingresá un número válido.'])
  })

  it('no rompe cuando la respuesta no es JSON', () => {
    const error = apiErrorFromResponse(500, '<html>Internal Server Error</html>')

    expect(error.status).toBe(500)
    expect(error.code).toBe('api_error')
    expect(error.fieldErrors).toEqual({})
  })

  it('detecta que el KYC no está aprobado', () => {
    const error = apiErrorFromResponse(403, {
      error: {
        code: 'permission_denied',
        message: 'Necesitás completar la verificación KYC para realizar esta operación.',
        details: {},
      },
    })

    expect(error.isKycRequired).toBe(true)
  })

  it('no confunde un 403 común con el KYC', () => {
    const error = apiErrorFromResponse(403, {
      error: { code: 'permission_denied', message: 'No tenés permisos.', details: {} },
    })

    expect(error.isKycRequired).toBe(false)
  })
})

describe('describeError', () => {
  it('explica que la sesión expiró', () => {
    const error = apiErrorFromResponse(401, {
      error: {
        code: 'not_authenticated',
        message: 'Authentication credentials were not provided.',
      },
    })

    const described = describeError(error)

    expect(described.title).toBe('Sesión expirada')
    expect(described.message).toBe('Tu sesión expiró. Volvé a iniciar sesión.')
  })

  it('avisa que falta la verificación KYC', () => {
    const error = apiErrorFromResponse(403, {
      error: {
        code: 'permission_denied',
        message: 'Necesitás completar la verificación KYC para realizar esta operación.',
      },
    })

    expect(describeError(error).message).toBe('Tu cuenta aún no fue verificada (KYC)')
  })

  it('muestra los errores de validación por campo', () => {
    const error = apiErrorFromResponse(400, {
      error: {
        code: 'validation_error',
        message: 'Los datos enviados no son válidos.',
        details: { amount: ['A valid number is required.'] },
      },
    })

    const described = describeError(error)

    expect(described.fieldErrors.amount).toEqual(['Ingresá un número válido.'])
  })

  it('traduce el mensaje de los reportes que viene envuelto', () => {
    const error = apiErrorFromResponse(400, {
      error: {
        code: 'validation_error',
        message:
          "[ErrorDetail(string='El parámetro currency es obligatorio (ARS o USD).', code='invalid')]",
      },
    })

    expect(describeError(error).message).toBe('El parámetro currency es obligatorio (ARS o USD).')
  })

  it('explica los errores de red sin mostrar detalles internos', () => {
    const described = describeError(new TypeError('Failed to fetch'))

    expect(described.message).toBe('No pudimos conectar con el servidor. Revisá tu conexión.')
    expect(described.message).not.toContain('fetch')
  })

  it('explica un error inesperado sin mostrar la traza', () => {
    const described = describeError(new Error('boom'))

    expect(described.message).toBe('Ocurrió un error inesperado. Intentá de nuevo.')
    expect(described.message).not.toContain('boom')
  })
})
