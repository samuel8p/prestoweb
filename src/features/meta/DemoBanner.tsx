import { Icon } from '../../components/ui/Icon'
import { useMeta } from './useMeta'

/**
 * Aviso de modo demo.
 *
 * Aparece cuando la instancia corre en modo demo (`mode: "demo"`). Si el
 * endpoint no responde, no se muestra nada: la app sigue funcionando.
 */
export function DemoBanner() {
  const { data } = useMeta()

  if (data?.mode !== 'demo') {
    return null
  }

  return (
    <div
      role="status"
      className="flex items-center justify-center gap-2 border-b border-warning/20 bg-warning-bg px-4 py-1.5 text-center text-[12px] font-semibold text-warning"
    >
      <Icon name="info" size={14} />
      <span>
        Demo: el dinero es simulado
        <span className="hidden font-normal sm:inline">
          {' '}
          · los saldos y los movimientos son de prueba
        </span>
      </span>
    </div>
  )
}
