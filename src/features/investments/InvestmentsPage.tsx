import { useState } from 'react'

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
import { formatDate } from '../../lib/money/format'
import type { InvestmentProduct } from '../../lib/api/types'
import { useInvestmentProducts, usePositionsWithDetails } from './api'
import { OpenPositionForm } from './OpenPositionForm'

/** Inversiones a plazo fijo: productos, apertura y posiciones. */
export function InvestmentsPage() {
  const products = useInvestmentProducts()
  const positions = usePositionsWithDetails()
  const [selectedProduct, setSelectedProduct] = useState<InvestmentProduct | null>(null)

  const productList = products.data?.results ?? []
  const positionList = positions.items

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Inversiones"
        description="Invertí tu saldo a plazo fijo y seguí cuánto rendiste."
      />

      <Card>
        <CardHeader
          title="Productos disponibles"
          description="Plazos fijos ofrecidos por la plataforma."
        />

        {products.isLoading ? (
          <div className="flex justify-center px-4 py-10">
            <Spinner label="Cargando los productos" />
          </div>
        ) : null}

        {products.isError ? (
          <div className="px-4 py-4">
            <ErrorState
              message={describeError(products.error).message}
              onRetry={() => void products.refetch()}
            />
          </div>
        ) : null}

        {!products.isLoading && !products.isError && productList.length === 0 ? (
          <EmptyState
            title="No hay productos disponibles"
            description="Cuando haya productos de plazo fijo, los vas a ver acá."
          />
        ) : null}

        <ul className="divide-y divide-slate-100">
          {productList.map((product) => {
            const currency = product.currency === 'USD' ? 'USD' : 'ARS'
            return (
              <li
                key={product.id}
                className="flex flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-5"
              >
                <div>
                  <p className="text-sm font-semibold text-slate-900">
                    Plazo fijo de {product.term_days} días
                  </p>
                  <p className="mt-1 text-sm text-slate-600">
                    {product.annual_rate_tna}% anual · mínimo{' '}
                    <MoneyAmount value={product.min_amount} currency={currency} />
                  </p>
                </div>
                <Button size="sm" onClick={() => setSelectedProduct(product)}>
                  Invertir
                </Button>
              </li>
            )
          })}
        </ul>
      </Card>

      <Card>
        <CardHeader title="Mis posiciones" description="El capital invertido y el interés." />

        {positions.isLoading ? (
          <div className="flex justify-center px-4 py-10">
            <Spinner label="Cargando las posiciones" />
          </div>
        ) : null}

        {positions.isError ? (
          <div className="px-4 py-4">
            <ErrorState
              message={describeError(positions.error).message}
              onRetry={() => void positions.refetch()}
            />
          </div>
        ) : null}

        {!positions.isLoading && !positions.isError && positionList.length === 0 ? (
          <EmptyState
            title="Todavía no tenés inversiones"
            description="Elegí un producto y abrí tu primera posición."
          />
        ) : null}

        <ul className="divide-y divide-slate-100">
          {positionList.map(({ position, detail }) => {
            const currency = detail?.product_detail.currency === 'USD' ? 'USD' : 'ARS'
            const matured = position.status === 'matured'
            return (
              <li
                key={position.id}
                className="flex flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-5"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-slate-900">
                      <MoneyAmount value={position.amount} currency={currency} />
                    </p>
                    <Badge tone={matured ? 'success' : 'info'}>
                      {matured ? 'Liquidada' : 'Vigente'}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    Vence el {formatDate(position.maturity_date)} · abierta el{' '}
                    {formatDate(position.opened_at)}
                    {detail
                      ? ` · ${detail.product_detail.term_days} días al ${detail.product_detail.annual_rate_tna}%`
                      : ''}
                  </p>
                </div>

                <div className="text-right">
                  <p className="text-xs text-slate-500">
                    {matured ? 'Interés ganado' : 'Interés esperado'}
                  </p>
                  <p className="text-sm font-semibold text-slate-900">
                    <MoneyAmount value={position.interest_amount} currency={currency} />
                  </p>
                </div>
              </li>
            )
          })}
        </ul>
      </Card>

      <Modal
        open={selectedProduct !== null}
        title="Abrir inversión"
        onClose={() => setSelectedProduct(null)}
      >
        {selectedProduct ? (
          <OpenPositionForm product={selectedProduct} onDone={() => setSelectedProduct(null)} />
        ) : null}
      </Modal>
    </div>
  )
}
