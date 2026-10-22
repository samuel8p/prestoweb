import { useEffect } from 'react'

/**
 * Cierra un panel flotante al hacer clic afuera o al presionar Escape.
 *
 * @param open - si el panel está abierto.
 * @param onClose - se llama cuando hay que cerrarlo.
 */
export function useDismissable(open: boolean, onClose: () => void): void {
  useEffect(() => {
    if (!open) {
      return undefined
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])
}
