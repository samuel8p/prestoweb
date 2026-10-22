import { Link } from 'react-router-dom'

export interface LogoProps {
  /** Variante compacta para el encabezado en pantallas chicas. */
  compact?: boolean
  className?: string
}

/**
 * Marca de Presto: un símbolo geométrico y el nombre.
 *
 * El símbolo evoca una cartera abierta con una línea de saldo: azul marino,
 * sin degradados.
 */
export function Logo({ compact = false, className = '' }: LogoProps) {
  return (
    <Link
      to="/panel"
      aria-label="Presto, ir al panel"
      className={`flex items-center gap-2.5 ${className}`}
    >
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-900 text-white shadow-xs">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M4 8.5A2.5 2.5 0 0 1 6.5 6H18a2 2 0 0 1 2 2v1.5"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <path
            d="M4 8.5V17a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5a2 2 0 0 0-2-2H6"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="16" cy="13" r="1.4" fill="currentColor" />
        </svg>
      </span>

      {!compact ? (
        <span className="text-[17px] font-semibold tracking-tight text-brand-950">Presto</span>
      ) : null}
    </Link>
  )
}
