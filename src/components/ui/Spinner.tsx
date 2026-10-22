export interface SpinnerProps {
  size?: 'sm' | 'md'
  label?: string
}

/** Indicador de carga con texto para lectores de pantalla. */
export function Spinner({ size = 'md', label = 'Cargando' }: SpinnerProps) {
  const dimension = size === 'sm' ? 'h-4 w-4' : 'h-6 w-6'

  return (
    <span className="inline-flex items-center gap-2" role="status">
      <span
        className={`${dimension} animate-spin rounded-full border-2 border-current border-r-transparent`}
        aria-hidden="true"
      />
      <span className="sr-only">{label}</span>
    </span>
  )
}
