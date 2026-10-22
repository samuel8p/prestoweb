import { useState } from 'react'

import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardHeader } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Modal } from '../../components/ui/Modal'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import { PageHeader } from '../../components/ui/PageHeader'
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

      {/* Productos */}
      <Card>
        <CardHeader
          title="Productos de plazo fijo"
          description="Plazos fijos ofrecidos por la plataforma."
          icon="trending"
        />

        {products.isLoading ? <SkeletonRows rows={2} columns={3} /> : null}

        {products.isError ? (
          <div className="px-5 py-4">
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
            icon="trending"
          />
        ) : null}

        <ul className="grid gap-px bg-line sm:grid-cols-2">
          {productList.map((product) => {
            const currency = product.currency === 'USD' ? 'USD' : 'ARS'

            return (
              <li key={product.id} className="flex flex-col justify-between gap-4 bg-surface p-5">
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-[15px] font-semibold text-slate-900">
                      Plazo fijo de {product.term_days} días
                    </p>
                    <Badge tone="info" dot>
                      {product.annual_rate_tna}% anual
                    </Badge>
                  </div>
                  <p className="mt-1.5 text-[13px] text-slate-500">
                    Inversión mínima: <MoneyAmount value={product.min_amount} currency={currency} />
                  </p>
                </div>

                <Button size="sm" icon="arrowUpRight" onClick={() => setSelectedProduct(product)}>
                  Invertir
                </Button>
              </li>
            )
          })}
        </ul>
      </Card>

      {/* Posiciones */}
      <Card>
        <CardHeader
          title="Mis posiciones"
          description="El capital invertido y el interés."
          icon="coins"
        />

        {positions.isLoading ? <SkeletonRows rows={3} columns={4} /> : null}

        {positions.isError ? (
          <div className="px-5 py-4">
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
            icon="coins"
          />
        ) : null}

        {positionList.length > 0 ? (
          <Table>
            <TableHead>
              <TableHeader>Capital invertido</TableHeader>
              <TableHeader>Interés</TableHeader>
              <TableHeader>Vencimiento</TableHeader>
              <TableHeader align="right">Estado</TableHeader>
            </TableHead>
            <TableBody>
              {positionList.map(({ position, detail }) => {
                const currency = detail?.product_detail.currency === 'USD' ? 'USD' : 'ARS'
                const matured = position.status === 'matured'

                return (
                  <TableRow key={position.id}>
                    <TableCell>
                      <span className="font-medium text-slate-900 tabular">
                        <MoneyAmount value={position.amount} currency={currency} />
                      </span>
                      <span className="block text-xs text-slate-400">
                        Abierta el {formatDate(position.opened_at)}
                        {detail
                          ? ` · ${detail.product_detail.term_days} días al ${detail.product_detail.annual_rate_tna}%`
                          : ''}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="block text-xs text-slate-500">
                        {matured ? 'Interés ganado' : 'Interés esperado'}
                      </span>
                      <span className="font-medium text-slate-900 tabular">
                        <MoneyAmount value={position.interest_amount} currency={currency} />
                      </span>
                    </TableCell>
                    <TableCell className="tabular">{formatDate(position.maturity_date)}</TableCell>
                    <TableCell align="right">
                      <Badge tone={matured ? 'success' : 'info'} dot>
                        {matured ? 'Liquidada' : 'Vigente'}
                      </Badge>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        ) : null}
      </Card>

      <Modal
        open={selectedProduct !== null}
        title="Abrir inversión"
        description="El capital se mueve a la cuenta del sistema hasta el vencimiento."
        onClose={() => setSelectedProduct(null)}
      >
        {selectedProduct ? (
          <OpenPositionForm product={selectedProduct} onDone={() => setSelectedProduct(null)} />
        ) : null}
      </Modal>
    </div>
  )
}
