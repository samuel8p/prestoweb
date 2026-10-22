import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardHeader } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Modal } from '../../components/ui/Modal'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import { SkeletonRows } from '../../components/ui/Skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/Table'
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

const STATUS_TONE = {
  active: 'success',
  accepted: 'info',
  expired: 'neutral',
} as const

const STATUS_LABEL = {
  active: 'Activa',
  accepted: 'Aceptada',
  expired: 'Expirada',
} as const

/**
 * Marketplace de ofertas.
 *
 * Arranca con las ofertas propias; la búsqueda se revela al apretar el botón
 * principal y, recién ahí, aparece el formulario con los resultados debajo.
 */
export function MarketplacePage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const searching = searchParams.get('buscar') === '1'

  const [filters, setFilters] = useState<Filters>({ currency: 'ARS', ordering: 'rate' })
  const [selected, setSelected] = useState<string[]>([])
  const [offerFormOpen, setOfferFormOpen] = useState(false)
  const [accepting, setAccepting] = useState<OfferMatch | null>(null)
  const [comparisonOpen, setComparisonOpen] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [idempotencyKey, setIdempotencyKey] = useState(() => createIdempotencyKey())

  const offers = useMatchingOffers(filters, searching)
  const myOffers = useMyOffers()
  const compare = useCompareOffers()
  const acceptOffer = useAcceptOffer()

  const results = searching ? (offers.data?.results ?? []) : []

  function openSearch() {
    const next = new URLSearchParams(searchParams)
    next.set('buscar', '1')
    setSearchParams(next)
  }

  function toggleSelection(id: string) {
    setSelected((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    )
  }

  async function handleCompare() {
    setActionError(null)
    try {
      await compare.mutateAsync({ offer_ids: selected })
      setComparisonOpen(true)
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
      {actionError ? <Alert tone="danger">{actionError}</Alert> : null}

      {/* Búsqueda: el botón principal revela el formulario */}
      <Card>
        <CardHeader
          title="Buscar ofertas"
          description="El préstamo toma el importe completo de la oferta."
          icon="search"
          action={
            searching ? (
              <Button
                variant="secondary"
                icon="x"
                onClick={() => {
                  const next = new URLSearchParams(searchParams)
                  next.delete('buscar')
                  setSearchParams(next)
                }}
              >
                Cerrar búsqueda
              </Button>
            ) : null
          }
        />

        {!searching ? (
          <EmptyState
            title="Buscá la oferta que mejor te sirva"
            description="Filtrá por moneda, importe, tasa y plazo, y compará las que te interesen."
            illustration="empty"
            action={
              <Button icon="search" onClick={openSearch}>
                Buscar ofertas
              </Button>
            }
          />
        ) : (
          <>
            <div className="px-5 py-4">
              <OfferFiltersForm onFiltersChange={setFilters} />
            </div>

            {offers.isLoading ? <SkeletonRows rows={4} columns={3} /> : null}

            {offers.isError ? (
              <div className="px-5 py-4">
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
                illustration="empty"
              />
            ) : null}

            {results.length > 0 ? (
              <>
                <ul className="divide-y divide-line border-t border-line">
                  {results.map((offer) => {
                    const currency = offer.currency === 'USD' ? 'USD' : 'ARS'

                    return (
                      <li key={offer.id} className="animate-fade-up px-5 py-4">
                        <div className="flex flex-wrap items-start justify-between gap-4">
                          <div className="min-w-0 flex-1">
                            <p className="text-lg font-semibold tracking-tight text-ink tabular">
                              <MoneyAmount value={offer.amount} currency={currency} />
                            </p>
                            <p className="mt-1 text-[13px] text-ink-muted">
                              {formatRate(offer.interest_rate)} anual · {offer.term_months} meses
                            </p>
                            {offer.requirements ? (
                              <p className="mt-1.5 max-w-xl truncate-1 text-[13px] text-ink-muted">
                                {offer.requirements}
                              </p>
                            ) : null}
                          </div>

                          <div className="flex shrink-0 items-center gap-3">
                            <label className="flex cursor-pointer items-center gap-2 text-[13px] text-ink-muted">
                              <input
                                type="checkbox"
                                checked={selected.includes(offer.id)}
                                onChange={() => toggleSelection(offer.id)}
                                className="h-4 w-4 rounded border-line-strong text-primary focus:ring-primary/30"
                              />
                              Comparar
                            </label>
                            <Button size="sm" onClick={() => setAccepting(offer)}>
                              Aceptar
                            </Button>
                          </div>
                        </div>
                      </li>
                    )
                  })}
                </ul>

                {selected.length >= 2 ? (
                  <div className="flex justify-end border-t border-line px-5 py-3">
                    <Button icon="sliders" onClick={() => void handleCompare()}>
                      Comparar ({selected.length})
                    </Button>
                  </div>
                ) : null}
              </>
            ) : null}
          </>
        )}
      </Card>

      {/* Mis ofertas */}
      <Card>
        <CardHeader
          title="Mis ofertas"
          description="Las ofertas que publicaste vos."
          icon="wallet"
          action={
            <Button variant="secondary" icon="plus" onClick={() => setOfferFormOpen(true)}>
              Publicar oferta
            </Button>
          }
        />

        {myOffers.isLoading ? <SkeletonRows rows={3} columns={3} /> : null}

        {myOffers.isError ? (
          <div className="px-5 py-4">
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
            illustration="empty"
            action={
              <Button icon="plus" onClick={() => setOfferFormOpen(true)}>
                Publicar oferta
              </Button>
            }
          />
        ) : null}

        <ul className="divide-y divide-line">
          {(myOffers.data?.results ?? []).map((offer) => {
            const currency = offer.currency === 'USD' ? 'USD' : 'ARS'

            return (
              <li
                key={offer.id}
                className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5"
              >
                <div>
                  <p className="text-sm font-medium text-ink tabular">
                    <MoneyAmount value={offer.amount} currency={currency} />
                  </p>
                  <p className="mt-0.5 text-xs text-ink-muted">
                    {formatRate(offer.interest_rate)} anual · {offer.term_months} meses · publicada
                    el {formatDate(offer.created_at)}
                  </p>
                </div>
                <Badge tone={STATUS_TONE[offer.status] ?? 'neutral'} dot>
                  {STATUS_LABEL[offer.status] ?? offer.status}
                </Badge>
              </li>
            )
          })}
        </ul>
      </Card>

      {/* Publicar oferta */}
      <Modal
        open={offerFormOpen}
        title="Publicar oferta"
        description="El prestatario recibe el importe completo de la oferta."
        onClose={() => setOfferFormOpen(false)}
      >
        <OfferForm onDone={() => setOfferFormOpen(false)} />
      </Modal>

      {/* Aceptar oferta */}
      <Modal
        open={accepting !== null}
        title="Aceptar la oferta"
        description="Se crea un préstamo a tu nombre con su cronograma de cuotas."
        onClose={() => setAccepting(null)}
      >
        {accepting ? (
          <div className="flex flex-col gap-4">
            <div className="rounded-[var(--radius-control)] bg-surface-muted p-4">
              <p className="text-lg font-semibold text-ink tabular">
                <MoneyAmount
                  value={accepting.amount}
                  currency={accepting.currency === 'USD' ? 'USD' : 'ARS'}
                />
              </p>
              <p className="mt-1 text-[13px] text-ink-muted">
                {formatRate(accepting.interest_rate)} anual a {accepting.term_months} meses
              </p>
            </div>

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

      {/* Comparación */}
      <Modal
        open={comparisonOpen}
        title="Comparación de ofertas"
        description="Cuota, interés total y costo total de cada oferta."
        size="lg"
        onClose={() => setComparisonOpen(false)}
      >
        {comparison && comparison.length > 0 ? (
          <Table>
            <TableHead>
              <TableHeader>Importe</TableHeader>
              <TableHeader>Tasa</TableHeader>
              <TableHeader>Plazo</TableHeader>
              <TableHeader align="right">Cuota</TableHeader>
              <TableHeader align="right">Interés total</TableHeader>
              <TableHeader align="right">Costo total</TableHeader>
            </TableHead>
            <TableBody>
              {comparison.map((item) => {
                const currency = item.currency === 'USD' ? 'USD' : 'ARS'

                return (
                  <TableRow key={item.id}>
                    <TableCell className="font-medium text-ink">
                      <MoneyAmount value={item.amount} currency={currency} />
                    </TableCell>
                    <TableCell>{formatRate(item.interest_rate)}</TableCell>
                    <TableCell>{item.term_months} meses</TableCell>
                    <TableCell align="right">
                      <MoneyAmount value={item.installment} currency={currency} />
                    </TableCell>
                    <TableCell align="right">
                      <MoneyAmount value={item.total_interest} currency={currency} />
                    </TableCell>
                    <TableCell align="right" className="font-medium text-ink">
                      <MoneyAmount value={item.total_cost} currency={currency} />
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        ) : (
          <EmptyState title="No hay nada para comparar todavía" illustration="empty" />
        )}
      </Modal>
    </div>
  )
}
