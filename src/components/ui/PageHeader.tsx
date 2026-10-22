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
    <header className="flex flex-wrap items-end justify-between gap-4 animate-fade-up">
      <div className="min-w-0">
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-[28px]">{title}</h1>
        {description ? (
          <p className="mt-1 max-w-2xl text-[13px] leading-5 text-ink-muted">{description}</p>
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
