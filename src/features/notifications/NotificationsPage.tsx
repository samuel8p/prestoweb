import { useState } from 'react'

import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Card, CardHeader } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { PageHeader } from '../../components/ui/PageHeader'
import { SkeletonRows } from '../../components/ui/Skeleton'
import { describeError } from '../../lib/api/errors'
import { formatDateTime } from '../../lib/money/format'
import type { EventType } from '../../lib/api/types'
import {
  useNotificationPreferences,
  useNotifications,
  useUpdateNotificationPreference,
} from './api'

const EVENT_LABEL: Record<EventType, string> = {
  installment_due_soon: 'Cuota por vencer',
  installment_overdue: 'Cuota vencida',
  investment_settled: 'Inversión liquidada',
  budget_alert: 'Alerta de presupuesto',
}

const EVENT_DESCRIPTION: Record<EventType, string> = {
  installment_due_soon: 'Te avisamos cuando una cuota vence en los próximos días.',
  installment_overdue: 'Te avisamos cuando una cuota queda vencida.',
  investment_settled: 'Te avisamos cuando una inversión se liquida.',
  budget_alert: 'Te avisamos cuando un presupuesto llega a su umbral de alerta.',
}

const STATUS_LABEL = {
  pending: 'Pendiente',
  sent: 'Enviado',
  failed: 'Fallido',
} as const

/** Avisos del usuario y preferencias por tipo de aviso. */
export function NotificationsPage() {
  const notifications = useNotifications(50)
  const preferences = useNotificationPreferences()
  const updatePreference = useUpdateNotificationPreference()
  const [actionError, setActionError] = useState<string | null>(null)

  const items = notifications.data?.results ?? []

  async function toggle(eventType: EventType, enabled: boolean) {
    setActionError(null)
    try {
      await updatePreference.mutateAsync({ event_type: eventType, enabled })
    } catch (error) {
      setActionError(describeError(error).message)
    }
  }

  return (
    <div className="flex animate-fade-up flex-col gap-6">
      <PageHeader
        title="Avisos"
        description="Las novedades de tu cuenta y los correos que querés recibir."
      />

      {actionError ? <Alert tone="danger">{actionError}</Alert> : null}

      {/* Preferencias */}
      <Card>
        <CardHeader
          title="Preferencias de avisos"
          description="Elegí qué avisos querés recibir por email."
          icon="sliders"
        />

        {preferences.isLoading ? <SkeletonRows rows={4} columns={2} /> : null}

        {preferences.isError ? (
          <div className="px-5 py-4">
            <ErrorState
              message={describeError(preferences.error).message}
              onRetry={() => void preferences.refetch()}
            />
          </div>
        ) : null}

        <ul className="stagger divide-y divide-line">
          {(preferences.data?.preferences ?? []).map((preference) => (
            <li
              key={preference.event_type}
              className="flex items-center justify-between gap-4 px-5 py-3.5"
            >
              <div className="min-w-0 flex-1">
                <label
                  htmlFor={`preference-${preference.event_type}`}
                  className="block text-sm font-medium text-ink"
                >
                  {EVENT_LABEL[preference.event_type] ?? preference.event_type}
                </label>
                <p className="mt-0.5 text-[13px] text-ink-muted">
                  {EVENT_DESCRIPTION[preference.event_type]}
                </p>
              </div>

              <input
                id={`preference-${preference.event_type}`}
                type="checkbox"
                checked={preference.enabled}
                disabled={updatePreference.isPending}
                onChange={(event) => void toggle(preference.event_type, event.target.checked)}
                className="peer sr-only"
              />
              <span
                aria-hidden="true"
                className="relative h-6 w-10 shrink-0 cursor-pointer rounded-full bg-line transition-colors after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:shadow-sm after:transition-transform peer-checked:bg-primary peer-checked:after:translate-x-4 peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-primary"
              />
            </li>
          ))}
        </ul>
      </Card>

      {/* Avisos */}
      <Card>
        <CardHeader title="Mis avisos" description="Del más nuevo al más viejo." icon="bell" />

        {notifications.isLoading ? <SkeletonRows rows={4} columns={2} /> : null}

        {notifications.isError ? (
          <div className="px-5 py-4">
            <ErrorState
              message={describeError(notifications.error).message}
              onRetry={() => void notifications.refetch()}
            />
          </div>
        ) : null}

        {!notifications.isLoading && !notifications.isError && items.length === 0 ? (
          <EmptyState
            title="No tenés avisos"
            description="Acá vas a ver las cuotas por vencer, las vencidas y las liquidaciones."
          />
        ) : null}

        <ul className="stagger divide-y divide-line">
          {items.map((notification) => (
            <li
              key={notification.id}
              className="flex flex-wrap items-start justify-between gap-3 px-5 py-3.5"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-ink">
                  {EVENT_LABEL[notification.event_type] ?? notification.event_type}
                </p>
                <p className="mt-0.5 text-xs text-ink-subtle tabular">
                  {formatDateTime(notification.created_at)} · referencia{' '}
                  {notification.reference_id.slice(0, 8)}…
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
                {STATUS_LABEL[notification.status] ?? notification.status}
              </Badge>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
