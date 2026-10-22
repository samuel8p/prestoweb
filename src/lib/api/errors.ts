/**
 * Manejador único de errores de la API.
 *
 * El backend responde siempre con el mismo formato (AGENTS §8 del backend):
 *
 * ```json
 * { "error": { "code": "validation_error", "message": "…", "details": {} } }
 * ```
 *
 * Este módulo traduce ese formato a mensajes en español y a errores por
 * campo. Nunca se expone la traza ni los detalles internos del backend.
 */

const SESSION_EXPIRED_MESSAGE = 'Tu sesión expiró. Volvé a iniciar sesión.'
const NETWORK_MESSAGE = 'No pudimos conectar con el servidor. Revisá tu conexión.'
const UNEXPECTED_MESSAGE = 'Ocurrió un error inesperado. Intentá de nuevo.'
const KYC_MESSAGE = 'Tu cuenta aún no fue verificada (KYC)'

export interface ErrorDescription {
  /** Título corto para mostrar arriba del mensaje. */
  title: string
  /** Mensaje en español para la persona usuaria. */
  message: string
  /** Errores de validación por campo. */
  fieldErrors: Record<string, string[]>
}

const FIELD_ERROR_LABELS: Record<string, string> = {
  email: 'El email',
  password: 'La contraseña',
  currency: 'La moneda',
  amount: 'El importe',
  type: 'El tipo de movimiento',
  description: 'La descripción',
  destination_account_id: 'La cuenta de destino',
  idempotency_key: 'La clave de idempotencia',
  category_id: 'La categoría',
  categories: 'La categoría',
  limit_amount: 'El límite',
  alert_threshold: 'El umbral de alerta',
  ledger_transaction_id: 'El movimiento',
  product_id: 'El producto',
  offer_id: 'La oferta',
  offer_ids: 'Las ofertas',
  term_months: 'El plazo',
  interest_rate: 'La tasa',
  documents: 'Los documentos',
  phone_number: 'El teléfono',
  date_of_birth: 'La fecha de nacimiento',
  country: 'El país',
}

/** Traducciones de los mensajes de validación que el backend deja en inglés. */
const MESSAGE_TRANSLATIONS: Array<[RegExp, string]> = [
  [/^A valid number is required\.$/i, 'Ingresá un número válido.'],
  [/^This field is required\.$/i, 'Este campo es obligatorio.'],
  [/^This field may not be blank\.$/i, 'Este campo es obligatorio.'],
  [/^Enter a valid email address\.$/i, 'Ingresá un email válido.'],
  [/^No email provided\.$/i, 'Ingresá tu email.'],
  [/^No password provided\.$/i, 'Ingresá tu contraseña.'],
  [/^Invalid credentials\.$/i, 'Email o contraseña incorrectos.'],
  [/^Unable to log in with provided credentials\.$/i, 'Email o contraseña incorrectos.'],
  [/^No active account found with the given credentials\.$/i, 'Email o contraseña incorrectos.'],
  [/^Authentication credentials were not provided\.$/i, SESSION_EXPIRED_MESSAGE],
  [/^Email already registered\.$/i, 'Ese email ya está registrado.'],
  [/^Invalid token\.$/i, SESSION_EXPIRED_MESSAGE],
  [/^Token is invalid or expired\.$/i, SESSION_EXPIRED_MESSAGE],
  [/^Given token not valid for any token type\.$/i, SESSION_EXPIRED_MESSAGE],
  [/^This password is too short/i, 'La contraseña es demasiado corta (mínimo 8 caracteres).'],
  [/^This password is too common\./i, 'La contraseña es demasiado común.'],
  [/^This password is entirely numeric\./i, 'La contraseña no puede ser solo números.'],
  [
    /^This password is too similar to the email address\./i,
    'La contraseña es demasiado similar al email.',
  ],
]

const DEFAULT_MESSAGES: Record<number, { title: string; message: string }> = {
  400: { title: 'Revisá los datos', message: 'Hay datos que no son válidos.' },
  401: { title: 'Sesión expirada', message: SESSION_EXPIRED_MESSAGE },
  403: { title: 'Sin permisos', message: 'No tenés permisos para realizar esta acción.' },
  404: { title: 'No encontrado', message: 'No encontramos lo que estabas buscando.' },
  405: { title: 'Método no permitido', message: 'Esta acción no está disponible.' },
  409: { title: 'Conflicto', message: 'Esta acción entra en conflicto con el estado actual.' },
  429: {
    title: 'Demasiados intentos',
    message: 'Demasiadas solicitudes. Intentá de nuevo más tarde.',
  },
}

/** Error de la API con el código, el estado y los errores por campo. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fieldErrors: Record<string, string[]>

  constructor(
    status: number,
    code: string,
    message: string,
    fieldErrors: Record<string, string[]> = {},
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fieldErrors = fieldErrors
  }

  /** `true` cuando el backend responde que falta la verificación KYC. */
  get isKycRequired(): boolean {
    return this.status === 403 && /\bkyc\b|verificaci/i.test(this.message)
  }

  /** `true` cuando la sesión no está autenticada o venció. */
  get isUnauthorized(): boolean {
    return this.status === 401
  }
}

function translateMessage(message: string): string {
  const trimmed = message.trim()
  if (!trimmed) {
    return trimmed
  }

  for (const [pattern, translation] of MESSAGE_TRANSLATIONS) {
    if (pattern.test(trimmed)) {
      return translation
    }
  }
  return trimmed
}

/** Saca el texto de los mensajes que el backend manda envueltos en `ErrorDetail`. */
export function unwrapMessage(message: string): string {
  const match = /string='([^']*)'/.exec(message)
  return match?.[1] ?? message
}

/**
 * Normaliza los detalles del backend en errores por campo.
 *
 * @param details - el `details` del formato de error del backend.
 * @returns los errores por campo, con los mensajes ya traducidos.
 */
export function toFieldErrors(details: unknown): Record<string, string[]> {
  if (!details || typeof details !== 'object' || Array.isArray(details)) {
    return {}
  }

  const fieldErrors: Record<string, string[]> = {}
  for (const [field, value] of Object.entries(details as Record<string, unknown>)) {
    const messages = Array.isArray(value) ? value : [value]
    const translated = messages
      .filter((item): item is string => typeof item === 'string')
      .map(translateMessage)
    if (translated.length > 0) {
      fieldErrors[field] = translated
    }
  }
  return fieldErrors
}

/**
 * Arma un `ApiError` a partir de una respuesta de la API.
 *
 * @param status - código de estado HTTP.
 * @param body - cuerpo de la respuesta ya parseado (o texto plano).
 * @returns el error con el código y los detalles del backend.
 */
export function apiErrorFromResponse(status: number, body: unknown): ApiError {
  const payload = body as {
    error?: { code?: unknown; message?: unknown; details?: unknown }
  } | null
  const error = payload?.error

  const code = typeof error?.code === 'string' ? error.code : defaultCodeFor(status)
  const rawMessage = typeof error?.message === 'string' ? error.message : ''
  const message = translateMessage(unwrapMessage(rawMessage))
  const fieldErrors = toFieldErrors(error?.details)

  return new ApiError(status, code, message, fieldErrors)
}

function defaultCodeFor(status: number): string {
  switch (status) {
    case 400:
      return 'validation_error'
    case 401:
      return 'not_authenticated'
    case 403:
      return 'permission_denied'
    case 404:
      return 'not_found'
    case 409:
      return 'conflict'
    case 429:
      return 'throttled'
    default:
      return 'api_error'
  }
}

/**
 * Traduce cualquier error a un mensaje en español para la interfaz.
 *
 * @param error - el error que se quiere mostrar.
 * @returns el título, el mensaje y los errores por campo.
 */
export function describeError(error: unknown): ErrorDescription {
  if (error instanceof ApiError) {
    if (error.isKycRequired) {
      return { title: 'Verificación pendiente', message: KYC_MESSAGE, fieldErrors: {} }
    }

    if (error.isUnauthorized) {
      const message = error.message.trim() || SESSION_EXPIRED_MESSAGE
      return {
        title:
          message === SESSION_EXPIRED_MESSAGE ? 'Sesión expirada' : 'No pudimos iniciar sesión',
        message,
        fieldErrors: {},
      }
    }

    const fallback = DEFAULT_MESSAGES[error.status]
    const message = error.message.trim()
    const generic = fallback?.message ?? UNEXPECTED_MESSAGE

    return {
      title: fallback?.title ?? 'Algo salió mal',
      message: message || generic,
      fieldErrors: error.fieldErrors,
    }
  }

  if (error instanceof TypeError) {
    return { title: 'Sin conexión', message: NETWORK_MESSAGE, fieldErrors: {} }
  }

  return { title: 'Algo salió mal', message: UNEXPECTED_MESSAGE, fieldErrors: {} }
}

/**
 * Devuelve el texto de un campo para los mensajes de error.
 *
 * @param field - nombre del campo en snake_case.
 * @returns la etiqueta en español del campo.
 */
export function fieldLabel(field: string): string {
  return FIELD_ERROR_LABELS[field] ?? 'El dato'
}
