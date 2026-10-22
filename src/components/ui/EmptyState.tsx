import type { ReactNode } from 'react'

import { Illustration } from './Illustration'
import type { IllustrationName } from './Illustration'

export interface EmptyStateProps {
  title: string
  description?: ReactNode
  action?: ReactNode
  /** Ilustración geométrica del estado. */
  illustration?: IllustrationName
}

/** Estado vacío: cuando no hay nada para mostrar. */
export function EmptyState({
  title,
  description,
  action,
  illustration = 'empty',
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <Illustration name={illustration} className="animate-fade-in" />
      <div className="max-w-sm space-y-1">
        <p className="text-sm font-semibold text-ink">{title}</p>
        {description ? <p className="text-[13px] leading-5 text-ink-muted">{description}</p> : null}
      </div>
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  )
}
