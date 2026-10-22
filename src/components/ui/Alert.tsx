import type { ReactNode } from 'react'

import { Icon } from './Icon'
import type { IconName } from './Icon'

type Tone = 'info' | 'success' | 'warning' | 'danger'

const TONES: Record<Tone, { box: string; icon: IconName; iconClass: string }> = {
  info: {
    box: 'border-brand-200 bg-brand-50 text-brand-900',
    icon: 'info',
    iconClass: 'text-brand-600',
  },
  success: {
    box: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    icon: 'checkCircle',
    iconClass: 'text-emerald-600',
  },
  warning: {
    box: 'border-amber-200 bg-amber-50 text-amber-900',
    icon: 'alert',
    iconClass: 'text-amber-600',
  },
  danger: {
    box: 'border-rose-200 bg-rose-50 text-rose-900',
    icon: 'alert',
    iconClass: 'text-rose-600',
  },
}

export interface AlertProps {
  tone?: Tone
  title?: ReactNode
  children?: ReactNode
  onDismiss?: () => void
  className?: string
}

/** Aviso destacado. Los errores usan `role="alert"` para ser anunciados. */
export function Alert({ tone = 'info', title, children, onDismiss, className = '' }: AlertProps) {
  const palette = TONES[tone]
  const isDanger = tone === 'danger'

  return (
    <div
      role={isDanger ? 'alert' : 'status'}
      className={`flex items-start gap-3 rounded-[var(--radius-control)] border px-4 py-3 text-[13px] leading-5 ${palette.box} ${className}`}
    >
      <Icon name={palette.icon} size={17} className={`mt-px ${palette.iconClass}`} />

      <div className="min-w-0 flex-1">
        {title ? <p className="font-semibold">{title}</p> : null}
        {children ? <div className={title ? 'mt-0.5' : ''}>{children}</div> : null}
      </div>

      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Cerrar aviso"
          className="-mr-1 shrink-0 rounded p-1 opacity-60 transition-opacity hover:opacity-100"
        >
          <Icon name="x" size={15} />
        </button>
      ) : null}
    </div>
  )
}
