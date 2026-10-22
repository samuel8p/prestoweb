import { useQuery } from '@tanstack/react-query'

import { apiPaths } from '../../lib/config'
import { queryKeys } from '../../lib/query/keys'
import type { Notification, Paginated } from '../../lib/api/types'
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
