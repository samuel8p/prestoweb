import { useMutation, useQuery } from '@tanstack/react-query'

import { apiPaths } from '../../lib/config'
import { queryKeys } from '../../lib/query/keys'
import type {
  InvestmentsReport,
  LoansReport,
  MovementReportRow,
  Paginated,
  SpendingReport,
} from '../../lib/api/types'
import type { Currency } from '../../lib/money/format'
import { useApiClient } from '../auth/auth-context'

export interface ReportRange {
  currency: Currency
  from?: string
  to?: string
}

/** Gasto acumulado por categoría en el período. */
export function useSpendingReport(range: ReportRange) {
  const client = useApiClient()
  const { currency, from, to } = range

  return useQuery({
    queryKey: queryKeys.reportSpending({ currency, from, to }),
    queryFn: () =>
      client.get<SpendingReport>(apiPaths.reportSpending, {
        query: { currency, from, to },
      }),
  })
}

/** Préstamos del usuario en la moneda pedida. */
export function useLoansReport(currency: Currency) {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.reportLoans({ currency }),
    queryFn: () => client.get<LoansReport>(apiPaths.reportLoans, { query: { currency } }),
  })
}

/** Inversiones del usuario en la moneda pedida. */
export function useInvestmentsReport(currency: Currency) {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.reportInvestments({ currency }),
    queryFn: () =>
      client.get<InvestmentsReport>(apiPaths.reportInvestments, { query: { currency } }),
  })
}

/** Movimientos del usuario en el período. */
export function useMovementsReport(range: ReportRange) {
  const client = useApiClient()
  const { currency, from, to } = range

  return useQuery({
    queryKey: queryKeys.reportMovements({ currency, from, to }),
    queryFn: () =>
      client.get<Paginated<MovementReportRow>>(apiPaths.reportMovements, {
        query: { currency, from, to, page_size: 25 },
      }),
  })
}

/** Rutas de los cuatro reportes, para la descarga en CSV. */
export const reportPaths = {
  spending: apiPaths.reportSpending,
  loans: apiPaths.reportLoans,
  investments: apiPaths.reportInvestments,
  movements: apiPaths.reportMovements,
} as const

export type ReportKey = keyof typeof reportPaths

/**
 * Baja el reporte en CSV.
 *
 * La descarga va autenticada: el `Authorization` viaja en la misma petición,
 * así que el archivo no queda expuesto en una URL.
 */
export function useReportCsv() {
  const client = useApiClient()

  return useMutation({
    mutationFn: async ({ report, range }: { report: ReportKey; range: ReportRange }) => {
      const file = await client.downloadCsv(reportPaths[report], {
        query: {
          currency: range.currency,
          from: range.from,
          to: range.to,
          export: 'csv',
        },
      })
      triggerDownload(file.blob, file.filename)
      return file
    },
  })
}

/**
 * Descarga un archivo al navegador.
 *
 * @param blob - el contenido del archivo.
 * @param filename - el nombre sugerido.
 */
export function triggerDownload(blob: Blob, filename: string): void {
  if (typeof URL.createObjectURL !== 'function') {
    return
  }

  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
