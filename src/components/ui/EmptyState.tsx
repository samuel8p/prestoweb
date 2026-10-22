import type { ReactNode } from 'react'

import { Icon } from './Icon'
import type { IconName } from './Icon'

export interface EmptyStateProps {
  title: string
  description?: ReactNode
  action?: ReactNode
  icon?: IconName
}

/** Estado vacío: cuando no hay nada para mostrar. */
export function EmptyState({ title, description, action, icon = 'search' }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-500">
        <Icon name={icon} size={20} />
      </span>
      <div className="max-w-sm space-y-1">
        <p className="text-sm font-medium text-slate-800">{title}</p>
        {description ? <p className="text-[13px] leading-5 text-slate-500">{description}</p> : null}
      </div>
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  )
}
