import { useMeta } from './useMeta'

/**
 * Cartel fijo de modo demo.
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
      className="fixed inset-x-0 top-0 z-50 bg-amber-400 px-4 py-2 text-center text-sm font-semibold text-amber-950"
    >
      Demo: el dinero es simulado
    </div>
  )
}
