import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardHeader } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Modal } from '../../components/ui/Modal'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
import { describeError } from '../../lib/api/errors'
import { formatDate, formatRate } from '../../lib/money/format'
import type { OfferMatch } from '../../lib/api/types'
import { createIdempotencyKey } from '../../lib/idempotency'
import { useAcceptOffer } from '../loans/api'
import { useCompareOffers, useMatchingOffers, useMyOffers } from './api'
import { OfferFiltersForm } from './OfferFiltersForm'
import { OfferForm } from './OfferForm'

interface Filters {
  currency: string
  amount_min?: string
  amount_max?: string
  max_rate?: string
  term_months?: number
  ordering?: string
}

/** Marketplace de ofertas: buscar, comparar, publicar y ver las propias. */
export function MarketplacePage() {
  const navigate = useNavigate()
  const [filters, setFilters] = useState<Filters>({ currency: 'ARS', ordering: 'rate' })
  const [selected, setSelected] = useState<string[]>([])
  const [offerFormOpen, setOfferFormOpen] = useState(false)
  const [accepting, setAccepting] = useState<OfferMatch | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const offers = useMatchingOffers(filters)
  const myOffers = useMyOffers()
  const compare = useCompareOffers()
  const acceptOffer = useAcceptOffer()
  const [idempotencyKey, setIdempotencyKey] = useState(() => createIdempotencyKey())

  const results = offers.data?.results ?? []

  function toggleSelection(id: string) {
    setSelected((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    )
  }

  async function handleCompare() {
    setActionError(null)
    try {
      await compare.mutateAsync({ offer_ids: selected })
    } catch (error) {
      setActionError(describeError(error).message)
    }
  }

  async function handleAccept() {
    if (!accepting) {
      return
    }
    setActionError(null)
    try {
      const loan = await acceptOffer.mutateAsync({
        offerId: accepting.id,
        idempotencyKey,
      })
      setAccepting(null)
      setIdempotencyKey(createIdempotencyKey())
      navigate(`/prestamos/${loan.id}`)
    } catch (error) {
      setActionError(describeError(error).message)
    }
  }

  const comparison = compare.data

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Ofertas de préstamo"
        description="Buscá, compará y elegí la oferta que mejor te sirve."
        action={<Button onClick={() => setOfferFormOpen(true)}>Publicar oferta</Button>}
      />

      <Card>
        <CardHeader
          title="Buscar"
          description="El préstamo toma el importe completo de la oferta."
        />
        <div className="px-4 py-4 sm:px-5">
          <OfferFiltersForm onFiltersChange={setFilters} />
        </div>
      </Card>

      {actionError ? <Alert tone="danger">{actionError}</Alert> : null}

      <Card>
        <CardHeader
          title="Ofertas disponibles"
          description={`${results.length} ${results.length === 1 ? 'oferta' : 'ofertas'} en ${filters.currency}.`}
          action={
            selected.length >= 2 ? (
              <Button size="sm" loading={compare.isPending} onClick={() => void handleCompare()}>
                Comparar ({selected.length})
              </Button>
            ) : null
          }
        />

        {offers.isLoading ? (
          <div className="flex justify-center px-4 py-10">
            <Spinner label="Buscando ofertas" />
          </div>
        ) : null}

        {offers.isError ? (
          <div className="px-4 py-4">
            <ErrorState
              message={describeError(offers.error).message}
              onRetry={() => void offers.refetch()}
            />
          </div>
        ) : null}

        {!offers.isLoading && !offers.isError && results.length === 0 ? (
          <EmptyState
            title="No hay ofertas con esos filtros"
            description="Probá con otro rango de importes o con otra tasa."
          />
        ) : null}

        {results.length > 0 ? (
          <ul className="divide-y divide-slate-100">
            {results.map((offer) => (
              <li key={offer.id} className="px-4 py-4 sm:px-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold text-slate-900">
                      <MoneyAmount
                        value={offer.amount}
                        currency={offer.currency === 'USD' ? 'USD' : 'ARS'}
                      />
                    </p>
                    <p className="mt-1 text-sm text-slate-600">
                      {formatRate(offer.interest_rate)} anual · {offer.term_months} meses
                    </p>
                    {offer.requirements ? (
                      <p className="mt-1 max-w-xl text-sm text-slate-500">{offer.requirements}</p>
                    ) : null}
                  </div>

                  <div className="flex items-center gap-2">
                    <label className="flex items-center gap-1.5 text-xs text-slate-600">
                      <input
                        type="checkbox"
                        checked={selected.includes(offer.id)}
                        onChange={() => toggleSelection(offer.id)}
                        className="h-4 w-4 rounded border-slate-300"
                      />
                      Comparar
                    </label>
                    <Button size="sm" onClick={() => setAccepting(offer)}>
                      Aceptar
                    </Button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </Card>

      {comparison && comparison.length > 0 ? (
        <Card>
          <CardHeader title="Comparación" description="Cuota, interés total y costo total." />
          <div className="overflow-x-auto px-4 py-4 sm:px-5">
            <table className="w-full min-w-[34rem] text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                  <th scope="col" className="py-2 pr-3">
                    Importe
                  </th>
                  <th scope="col" className="py-2 pr-3">
                    Tasa
                  </th>
                  <th scope="col" className="py-2 pr-3">
                    Plazo
                  </th>
                  <th scope="col" className="py-2 pr-3">
                    Cuota
                  </th>
                  <th scope="col" className="py-2 pr-3">
                    Interés total
                  </th>
                  <th scope="col" className="py-2">
                    Costo total
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {comparison.map((item) => (
                  <tr key={item.id}>
                    <td className="py-2 pr-3">
                      <MoneyAmount
                        value={item.amount}
                        currency={item.currency === 'USD' ? 'USD' : 'ARS'}
                      />
                    </td>
                    <td className="py-2 pr-3">{formatRate(item.interest_rate)}</td>
                    <td className="py-2 pr-3">{item.term_months} meses</td>
                    <td className="py-2 pr-3">
                      <MoneyAmount
                        value={item.installment}
                        currency={item.currency === 'USD' ? 'USD' : 'ARS'}
                      />
                    </td>
                    <td className="py-2 pr-3">
                      <MoneyAmount
                        value={item.total_interest}
                        currency={item.currency === 'USD' ? 'USD' : 'ARS'}
                      />
                    </td>
                    <td className="py-2">
                      <MoneyAmount
                        value={item.total_cost}
                        currency={item.currency === 'USD' ? 'USD' : 'ARS'}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}

      <Card>
        <CardHeader title="Mis ofertas" description="Las ofertas que publicaste vos." />
        {myOffers.isLoading ? (
          <div className="flex justify-center px-4 py-10">
            <Spinner label="Cargando tus ofertas" />
          </div>
        ) : null}

        {myOffers.isError ? (
          <div className="px-4 py-4">
            <ErrorState
              message={describeError(myOffers.error).message}
              onRetry={() => void myOffers.refetch()}
            />
          </div>
        ) : null}

        {!myOffers.isLoading && !myOffers.isError && (myOffers.data?.results.length ?? 0) === 0 ? (
          <EmptyState
            title="Todavía no publicaste ofertas"
            description="Publicá una oferta para prestar tu dinero."
            action={
              <Button size="sm" onClick={() => setOfferFormOpen(true)}>
                Publicar oferta
              </Button>
            }
          />
        ) : null}

        <ul className="divide-y divide-slate-100">
          {(myOffers.data?.results ?? []).map((offer) => (
            <li
              key={offer.id}
              className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-5"
            >
              <div>
                <p className="text-sm font-medium text-slate-900">
                  <MoneyAmount
                    value={offer.amount}
                    currency={offer.currency === 'USD' ? 'USD' : 'ARS'}
                  />
                </p>
                <p className="text-xs text-slate-500">
                  {formatRate(offer.interest_rate)} anual · {offer.term_months} meses ·{' '}
                  {formatDate(offer.created_at)}
                </p>
              </div>
              <Badge
                tone={
                  offer.status === 'active'
                    ? 'success'
                    : offer.status === 'accepted'
                      ? 'info'
                      : 'neutral'
                }
              >
                {offer.status === 'active'
                  ? 'Activa'
                  : offer.status === 'accepted'
                    ? 'Aceptada'
                    : 'Expirada'}
              </Badge>
            </li>
          ))}
        </ul>
      </Card>

      <Modal open={offerFormOpen} title="Publicar oferta" onClose={() => setOfferFormOpen(false)}>
        <OfferForm onDone={() => setOfferFormOpen(false)} />
      </Modal>

      <Modal open={accepting !== null} title="Aceptar la oferta" onClose={() => setAccepting(null)}>
        {accepting ? (
          <div className="flex flex-col gap-4">
            <div className="rounded-lg bg-slate-50 p-3 text-sm">
              <p className="font-medium text-slate-900">
                <MoneyAmount
                  value={accepting.amount}
                  currency={accepting.currency === 'USD' ? 'USD' : 'ARS'}
                />
              </p>
              <p className="mt-1 text-slate-600">
                {formatRate(accepting.interest_rate)} anual a {accepting.term_months} meses
              </p>
            </div>

            <p className="text-sm text-slate-600">
              Al aceptar, el prestamista te transfiere el importe y queda registrado un préstamo con
              su cronograma de cuotas.
            </p>

            {actionError ? <Alert tone="danger">{actionError}</Alert> : null}

            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setAccepting(null)}>
                Cancelar
              </Button>
              <Button loading={acceptOffer.isPending} onClick={() => void handleAccept()}>
                Aceptar y recibir
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  )
}
