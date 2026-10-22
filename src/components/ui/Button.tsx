import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { Icon } from './Icon'
import type { IconName } from './Icon'
import { Spinner } from './Spinner'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-brand-600 text-white shadow-xs hover:bg-brand-700 active:bg-brand-800 disabled:hover:bg-brand-600',
  secondary:
    'bg-white text-slate-700 ring-1 ring-inset ring-line-strong shadow-xs hover:bg-slate-50 active:bg-slate-100 disabled:hover:bg-white',
  ghost: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 disabled:hover:bg-transparent',
  danger:
    'bg-rose-600 text-white shadow-xs hover:bg-rose-700 active:bg-rose-800 disabled:hover:bg-rose-600',
}

const SIZES: Record<Size, string> = {
  sm: 'h-8 gap-1.5 px-2.5 text-[13px]',
  md: 'h-9.5 gap-2 px-3.5 text-sm',
  lg: 'h-11 gap-2 px-5 text-sm',
}

const ICON_SIZES: Record<Size, number> = { sm: 15, md: 17, lg: 18 }

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  /** Ícono a la izquierda del texto. */
  icon?: IconName
  /** Ícono a la derecha del texto. */
  iconRight?: IconName
  children?: ReactNode
}

/**
 * Botón de la aplicación.
 *
 * Jerarquía: `primary` es la acción principal de la pantalla (una sola por
 * vista), `secondary` acompaña, `ghost` es terciario.
 */
export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  iconRight,
  disabled,
  className = '',
  children,
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`inline-flex select-none items-center justify-center rounded-[var(--radius-control)] font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-55 ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...rest}
    >
      {loading ? <Spinner size="sm" /> : icon ? <Icon name={icon} size={ICON_SIZES[size]} /> : null}
      {children}
      {iconRight && !loading ? <Icon name={iconRight} size={ICON_SIZES[size]} /> : null}
    </button>
  )
}
