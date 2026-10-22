import { Link } from 'react-router-dom'

export interface LogoProps {
  /** `dark` para usarlo sobre el fondo océano. */
  variant?: 'light' | 'dark'
  /** Versión compacta, sin el nombre. */
  compact?: boolean
  className?: string
}

/**
 * Marca de Presto.
 *
 * Símbolo geométrico: una cartera abierta con el saldo en turquesa sobre
 * azul marino. Sin degradados ni recursos externos.
 */
export function Logo({ variant = 'light', compact = false, className = '' }: LogoProps) {
  const dark = variant === 'dark'

  return (
    <Link
      to="/panel"
      aria-label="Presto, ir al panel"
      className={`flex items-center gap-2.5 ${className}`}
    >
      <span className="flex h-9 w-9 items-center justify-center rounded-[0.65rem] bg-chrome">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path
            d="M4 8.2A3.2 3.2 0 0 1 7.2 5H14a1 1 0 0 1 1 1v1.4"
            stroke="#2DD4BF"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
          <path
            d="M4 8.2V14a3 3 0 0 0 3 3h6.2a3 3 0 0 0 3-3v-3.4a1.6 1.6 0 0 0-1.6-1.6H7"
            stroke="#FFFFFF"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="12.8" cy="11.6" r="1.15" fill="#0E7C86" />
        </svg>
      </span>

      {!compact ? (
        <span
          className={`text-[17px] font-bold tracking-tight ${dark ? 'text-white' : 'text-chrome'}`}
        >
          Presto
        </span>
      ) : null}
    </Link>
  )
}
