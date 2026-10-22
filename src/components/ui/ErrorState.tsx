import { Alert } from './Alert'
import { Button } from './Button'

export interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
}

/** Estado de error de una pantalla, con la opción de reintentar. */
export function ErrorState({
  title = 'No pudimos cargar esto',
  message,
  onRetry,
}: ErrorStateProps) {
  return (
    <Alert tone="danger" title={title}>
      <p>{message}</p>
      {onRetry ? (
        <div className="mt-3">
          <Button variant="secondary" size="sm" onClick={onRetry}>
            Reintentar
          </Button>
        </div>
      ) : null}
    </Alert>
  )
}
