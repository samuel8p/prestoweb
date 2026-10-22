import type { ReactNode } from 'react'

type Tone = 'neutral' | 'info' | 'success' | 'warning' | 'danger'

const TONES: Record<Tone, string> = {
  neutral: 'bg-slate-100 text-slate-700 ring-slate-200',
  info: 'bg-brand-50 text-brand-700 ring-brand-200',
  success: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  warning: 'bg-amber-50 text-amber-800 ring-amber-200',
  danger: 'bg-rose-50 text-rose-700 ring-rose-200',
}

const DOT_TONES: Record<Tone, string> = {
  neutral: 'bg-slate-400',
  info: 'bg-brand-500',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-rose-500',
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
 * Los colores se usan con moderación: fondo tenue, texto de buen contraste y
 * un anillo del mismo tono.
 */
export function Badge({ children, tone = 'neutral', dot = false, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${TONES[tone]} ${className}`}
    >
      {dot ? <span className={`h-1.5 w-1.5 rounded-full ${DOT_TONES[tone]}`} /> : null}
      {children}
    </span>
  )
}
