import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiPaths } from '../../lib/config'
import { queryKeys } from '../../lib/query/keys'
import type {
  Notification,
  NotificationPreference,
  NotificationPreferenceList,
  Paginated,
} from '../../lib/api/types'
import { useApiClient } from '../auth/auth-context'

/** Avisos del usuario, del más nuevo al más viejo. */
export function useNotifications(pageSize = 20) {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.notifications,
    queryFn: () =>
      client.get<Paginated<Notification>>(apiPaths.notifications, {
        query: { page_size: pageSize },
      }),
  })
}

/** Preferencias de avisos por tipo de evento. */
export function useNotificationPreferences() {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.notificationPreferences,
    queryFn: () => client.get<NotificationPreferenceList>(apiPaths.notificationPreferences),
  })
}

/** Activa o desactiva un tipo de aviso. */
export function useUpdateNotificationPreference() {
  const client = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: NotificationPreference) =>
      client.put<NotificationPreference>(apiPaths.notificationPreferences, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.notificationPreferences })
    },
  })
}
