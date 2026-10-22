import { Link } from 'react-router-dom'

import { Badge } from '../ui/Badge'
import { Icon } from '../ui/Icon'
import type { IconName } from '../ui/Icon'
import { Spinner } from '../ui/Spinner'
import { formatDateTime } from '../../lib/money/format'
import type { EventType } from '../../lib/api/types'
import { useNotifications } from '../../features/notifications/api'

const EVENT_META: Record<EventType, { label: string; icon: IconName }> = {
  installment_due_soon: { label: 'Cuota por vencer', icon: 'clock' },
  installment_overdue: { label: 'Cuota vencida', icon: 'alert' },
  investment_settled: { label: 'Inversión liquidada', icon: 'trending' },
  budget_alert: { label: 'Alerta de presupuesto', icon: 'budget' },
}

export interface NotificationsPanelProps {
  open: boolean
  onClose: () => void
}

/**
 * Panel de avisos del encabezado.
 *
 * Sin insignia con contador: el esquema no trae estado de lectura, así que no
 * hay forma honesta de saber cuántos avisos son nuevos.
 */
export function NotificationsPanel({ open, onClose }: NotificationsPanelProps) {
  const notifications = useNotifications(5)
  const items = notifications.data?.results?.slice(0, 5) ?? []

  if (!open) {
    return null
  }

  return (
    <div className="absolute right-0 top-full z-40 mt-2 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-[var(--radius-card)] border border-line bg-surface shadow-raised animate-scale-in">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <p className="text-sm font-semibold text-ink">Avisos</p>
        {notifications.isLoading ? <Spinner size="sm" /> : null}
      </div>

      {notifications.isError ? (
        <p className="px-4 py-6 text-center text-[13px] text-danger">
          No pudimos cargar los avisos.
        </p>
      ) : null}

      {!notifications.isLoading && !notifications.isError && items.length === 0 ? (
        <p className="px-4 py-8 text-center text-[13px] text-ink-muted">
          No tenés avisos por ahora.
        </p>
      ) : null}

      <ul className="max-h-80 divide-y divide-line overflow-y-auto">
        {items.map((notification) => {
          const meta = EVENT_META[notification.event_type]

          return (
            <li key={notification.id} className="flex items-start gap-3 px-4 py-3">
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary-tint text-primary">
                <Icon name={meta?.icon ?? 'bell'} size={16} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-semibold text-ink">
                  {meta?.label ?? notification.event_type}
                </p>
                <p className="mt-0.5 text-[11px] text-ink-subtle tabular">
                  {formatDateTime(notification.created_at)}
                </p>
              </div>
              <Badge
                tone={
                  notification.status === 'failed'
                    ? 'danger'
                    : notification.status === 'sent'
                      ? 'success'
                      : 'warning'
                }
                dot
              >
                {notification.status === 'sent'
                  ? 'Enviado'
                  : notification.status === 'failed'
                    ? 'Fallido'
                    : 'Pendiente'}
              </Badge>
            </li>
          )
        })}
      </ul>

      <div className="flex items-center justify-between gap-2 border-t border-line bg-surface-muted px-4 py-3">
        <Link
          to="/avisos"
          onClick={onClose}
          className="text-[13px] font-semibold text-primary hover:underline"
        >
          Ver todos
        </Link>
        <Link
          to="/avisos#preferencias"
          onClick={onClose}
          className="text-[13px] font-semibold text-primary hover:underline"
        >
          Configurar
        </Link>
      </div>
    </div>
  )
}
