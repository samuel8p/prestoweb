import { Button } from '../../components/ui/Button'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { SkeletonRows } from '../../components/ui/Skeleton'
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
  /** Mensaje del estado vacío. */
  emptyTitle?: string
  emptyDescription?: string
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
  emptyTitle = 'Todavía no hay movimientos',
  emptyDescription = 'Cuando deposites, retires o transfieras dinero, los movimientos aparecen acá.',
}: MovementListProps) {
  if (isLoading) {
    return <SkeletonRows rows={5} columns={3} />
  }

  if (error) {
    return (
      <div className="px-5 py-4">
        <ErrorState message={describeError(error).message} onRetry={onRetry} />
      </div>
    )
  }

  if (movements.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} icon="swap" />
  }

  return (
    <div>
      <ul className="divide-y divide-line">
        {movements.map((movement) => (
          <MovementRow key={movement.id} movement={movement} reversed={movement.is_reversed} />
        ))}
      </ul>

      {hasNextPage ? (
        <div className="flex justify-center border-t border-line px-5 py-3">
          <Button variant="secondary" size="sm" loading={isFetchingMore} onClick={onLoadMore}>
            Cargar más movimientos
          </Button>
        </div>
      ) : null}
    </div>
  )
}
