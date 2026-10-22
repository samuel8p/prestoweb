import type { ReactNode } from 'react'

type Tone = 'neutral' | 'info' | 'success' | 'warning' | 'danger'

const TONES: Record<Tone, string> = {
  neutral: 'bg-surface-muted text-ink-muted ring-line',
  info: 'bg-teal-tint text-teal-deep ring-teal/25',
  success: 'bg-success-bg text-success ring-success/25',
  warning: 'bg-warning-bg text-warning ring-warning/25',
  danger: 'bg-danger-bg text-danger ring-danger/25',
}

const DOT_TONES: Record<Tone, string> = {
  neutral: 'bg-ink-subtle',
  info: 'bg-teal',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger',
}

export interface BadgeProps {
  children: ReactNode
  tone?: Tone
  /** Muestra un punto de color antes del texto. */
  dot?: boolean
  className?: string
}

/**
 * Etiqueta de estado.
 *
 * El color nunca es la única señal: siempre acompaña al texto, y el punto
 * refuerza (nunca reemplaza) el significado.
 */
export function Badge({ children, tone = 'neutral', dot = false, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${TONES[tone]} ${className}`}
    >
      {dot ? <span className={`h-1.5 w-1.5 rounded-full ${DOT_TONES[tone]}`} /> : null}
      {children}
    </span>
  )
}
