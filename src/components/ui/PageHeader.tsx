import type { ReactNode } from 'react'

export interface PageHeaderProps {
  title: string
  description?: ReactNode
  /** Acción principal de la pantalla (un solo botón). */
  action?: ReactNode
  /** Acciones secundarias. */
  secondaryActions?: ReactNode
}

/** Encabezado de página: título, bajada y la acción principal. */
export function PageHeader({ title, description, action, secondaryActions }: PageHeaderProps) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {description ? (
          <p className="mt-1 max-w-2xl text-[13px] leading-5 text-slate-500">{description}</p>
        ) : null}
      </div>

      {action || secondaryActions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {secondaryActions}
          {action}
        </div>
      ) : null}
    </header>
  )
}
