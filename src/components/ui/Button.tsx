import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { Icon } from './Icon'
import type { IconName } from './Icon'
import { Spinner } from './Spinner'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'dark' | 'onDark'
type Size = 'sm' | 'md' | 'lg'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-teal text-white hover:bg-teal-dark active:bg-teal-deep',
  secondary:
    'bg-surface text-ink hover:bg-surface-muted border border-line-strong hover:border-teal/50',
  ghost: 'text-ink-muted hover:bg-surface-muted hover:text-ink',
  danger: 'bg-danger text-white hover:bg-danger/90 active:bg-danger/95',
  dark: 'bg-ocean text-white hover:bg-ocean-800',
  onDark: 'bg-white/10 text-white hover:bg-white/20',
}

const SIZES: Record<Size, string> = {
  sm: 'h-8 gap-1.5 px-3 text-[13px]',
  md: 'h-10 gap-2 px-4 text-sm',
  lg: 'h-12 gap-2 px-6 text-[15px]',
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
 * Jerarquía: `primary` es la única acción principal de la pantalla (teal
 * sólido), `secondary` acompaña, `ghost` es terciario.
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
      className={`inline-flex select-none items-center justify-center rounded-[var(--radius-control)] font-semibold transition-[transform,background-color,border-color,color] duration-200 ease-out active:scale-[0.98] disabled:pointer-events-none disabled:opacity-55 ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...rest}
    >
      {loading ? <Spinner size="sm" /> : icon ? <Icon name={icon} size={ICON_SIZES[size]} /> : null}
      {children}
      {iconRight && !loading ? <Icon name={iconRight} size={ICON_SIZES[size]} /> : null}
    </button>
  )
}
