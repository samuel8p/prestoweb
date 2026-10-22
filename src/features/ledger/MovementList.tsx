import { Button } from '../../components/ui/Button'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Spinner } from '../../components/ui/Spinner'
import { describeError } from '../../lib/api/errors'
import type { MovementReportRow } from '../../lib/api/types'
import { MovementRow } from './MovementRow'

export interface MovementListProps {
  movements: MovementReportRow[]
  isLoading: boolean
  error: unknown
  hasNextPage: boolean
  isFetchingMore: boolean
  onRetry: () => void
  onLoadMore: () => void
}

/** Historial de movimientos, con estados de carga, vacío y error. */
export function MovementList({
  movements,
  isLoading,
  error,
  hasNextPage,
  isFetchingMore,
  onRetry,
  onLoadMore,
}: MovementListProps) {
  if (isLoading) {
    return (
      <div className="flex justify-center px-4 py-10">
        <Spinner label="Cargando los movimientos" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-4 py-4">
        <ErrorState message={describeError(error).message} onRetry={onRetry} />
      </div>
    )
  }

  if (movements.length === 0) {
    return (
      <EmptyState
        title="Todavía no hay movimientos"
        description="Cuando deposites, retires o transfieras dinero, los movimientos aparecen acá."
      />
    )
  }

  return (
    <div>
      <ul className="divide-y divide-slate-100">
        {movements.map((movement) => (
          <MovementRow key={movement.id} movement={movement} reversed={movement.is_reversed} />
        ))}
      </ul>

      {hasNextPage ? (
        <div className="flex justify-center border-t border-slate-100 px-4 py-3">
          <Button variant="secondary" size="sm" loading={isFetchingMore} onClick={onLoadMore}>
            Cargar más
          </Button>
        </div>
      ) : null}
    </div>
  )
}
