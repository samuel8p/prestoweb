import { useSearchParams } from 'react-router-dom'

import { PageHeader } from '../../components/ui/PageHeader'
import { SectionTabs } from '../../components/ui/SectionTabs'
import { LoansPage } from '../loans/LoansPage'
import { MarketplacePage } from '../offers/MarketplacePage'

/**
 * Sección de préstamos: mis préstamos y las ofertas del marketplace.
 *
 * La pestaña activa se guarda en el query param (`?vista=`), así que la URL
 * es compartible.
 */
export function PrestamosPage() {
  const [searchParams] = useSearchParams()
  const vista = searchParams.get('vista') === 'ofertas' ? 'ofertas' : 'prestamos'

  return (
    <div className="flex animate-fade-up flex-col gap-6">
      <PageHeader
        title="Préstamos"
        description="Los préstamos que tomaste, los que prestaste y las ofertas del marketplace."
      />

      <SectionTabs
        value={vista}
        tabs={[
          { id: 'prestamos', label: 'Mis préstamos', content: <LoansPage /> },
          { id: 'ofertas', label: 'Ofertas', content: <MarketplacePage /> },
        ]}
      />
    </div>
  )
}
