import { useState } from 'react'

import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Card, CardHeader } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
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
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Avisos"
        description="Las novedades de tu cuenta y los correos que querés recibir."
      />

      {actionError ? <Alert tone="danger">{actionError}</Alert> : null}

      <Card>
        <CardHeader
          title="Preferencias de avisos"
          description="Elegí qué avisos querés recibir por email."
        />

        {preferences.isLoading ? (
          <div className="flex justify-center px-4 py-10">
            <Spinner label="Cargando las preferencias" />
          </div>
        ) : null}

        {preferences.isError ? (
          <div className="px-4 py-4">
            <ErrorState
              message={describeError(preferences.error).message}
              onRetry={() => void preferences.refetch()}
            />
          </div>
        ) : null}

        <ul className="divide-y divide-slate-100">
          {(preferences.data?.preferences ?? []).map((preference) => (
            <li
              key={preference.event_type}
              className="flex items-center justify-between gap-3 px-4 py-3 sm:px-5"
            >
              <label
                htmlFor={`preference-${preference.event_type}`}
                className="text-sm font-medium text-slate-900"
              >
                {EVENT_LABEL[preference.event_type] ?? preference.event_type}
              </label>
              <input
                id={`preference-${preference.event_type}`}
                type="checkbox"
                checked={preference.enabled}
                disabled={updatePreference.isPending}
                onChange={(event) => void toggle(preference.event_type, event.target.checked)}
                className="h-5 w-5 rounded border-slate-300 text-brand-600 focus:ring-brand-400"
              />
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <CardHeader title="Mis avisos" description="Del más nuevo al más viejo." />

        {notifications.isLoading ? (
          <div className="flex justify-center px-4 py-10">
            <Spinner label="Cargando los avisos" />
          </div>
        ) : null}

        {notifications.isError ? (
          <div className="px-4 py-4">
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

        <ul className="divide-y divide-slate-100">
          {items.map((notification) => (
            <li
              key={notification.id}
              className="flex flex-wrap items-start justify-between gap-3 px-4 py-3 sm:px-5"
            >
              <div>
                <p className="text-sm font-medium text-slate-900">
                  {EVENT_LABEL[notification.event_type] ?? notification.event_type}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
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
