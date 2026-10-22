import type { ReactNode } from 'react'

type Tone = 'info' | 'success' | 'warning' | 'danger'

const TONES: Record<Tone, string> = {
  info: 'border-brand-200 bg-brand-50 text-brand-800',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  warning: 'border-amber-200 bg-amber-50 text-amber-900',
  danger: 'border-rose-200 bg-rose-50 text-rose-800',
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
  const isDanger = tone === 'danger'

  return (
    <div
      role={isDanger ? 'alert' : 'status'}
      className={`flex items-start justify-between gap-3 rounded-lg border px-4 py-3 text-sm ${TONES[tone]} ${className}`}
    >
      <div className="flex flex-col gap-1">
        {title ? <p className="font-semibold">{title}</p> : null}
        {children ? <div className="leading-relaxed">{children}</div> : null}
      </div>
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Cerrar aviso"
          className="shrink-0 rounded p-1 text-current opacity-70 hover:opacity-100"
        >
          <span aria-hidden="true">×</span>
        </button>
      ) : null}
    </div>
  )
}
