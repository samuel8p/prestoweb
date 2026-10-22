import { useQuery } from '@tanstack/react-query'

import { apiPaths } from '../../lib/config'
import { useApiClient } from '../auth/auth-context'

/** Una billetera del usuario buscado: la moneda y el id de la cuenta. */
export interface AliasWallet {
  currency: string
  account_id: string
}

/** Lo mínimo para poder pagarle a un usuario por su alias. */
export interface AliasLookup {
  alias: string
  name: string
  wallets: AliasWallet[]
}

/**
 * Busca un usuario por su alias público.
 *
 * Solo se consulta cuando hay un alias escrito y el lookup está habilitado.
 *
 * @param alias - el alias a buscar.
 * @param enabled - si se permite disparar la consulta.
 */
export function useAliasLookup(alias: string, enabled: boolean) {
  const client = useApiClient()
  const trimmed = alias.trim()

  return useQuery({
    queryKey: ['ledger', 'alias', trimmed],
    queryFn: () => client.get<AliasLookup>(apiPaths.accountByAlias(trimmed)),
    enabled: enabled && trimmed.length > 0,
    retry: false,
  })
}
