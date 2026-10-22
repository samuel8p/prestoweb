import type { ReactNode } from 'react'

import { Icon } from './Icon'
import type { IconName } from './Icon'

export interface CardProps {
  children: ReactNode
  className?: string
  as?: 'div' | 'section' | 'article'
  /** Superficie oscura (bloque de saldo). */
  tone?: 'light' | 'dark'
}

/**
 * Superficie de la aplicación.
 *
 * Blanca con borde cálido y sombra mínima; la variante oscura se usa para el
 * bloque de saldo.
 */
export function Card({ children, className = '', as: Tag = 'div', tone = 'light' }: CardProps) {
  const dark = tone === 'dark'

  return (
    <Tag
      className={`rounded-[var(--radius-card)] ${
        dark ? 'bg-ocean text-white shadow-raised' : 'border border-line bg-surface shadow-card'
      } ${className}`}
    >
      {children}
    </Tag>
  )
}

export interface CardHeaderProps {
  title: ReactNode
  description?: ReactNode
  /** Acción a la derecha del encabezado (un botón, un link, un filtro). */
  action?: ReactNode
  /** Ícono del encabezado. */
  icon?: IconName
  /** Encabezado sobre fondo oscuro. */
  tone?: 'light' | 'dark'
}

export function CardHeader({ title, description, action, icon, tone = 'light' }: CardHeaderProps) {
  const dark = tone === 'dark'

  return (
    <div
      className={`flex items-start justify-between gap-4 border-b px-5 py-4 ${
        dark ? 'border-white/10' : 'border-line'
      }`}
    >
      <div className="flex min-w-0 items-start gap-3">
        {icon ? (
          <span
            className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
              dark ? 'bg-white/10 text-turquoise' : 'bg-teal-tint text-teal'
            }`}
          >
            <Icon name={icon} size={17} />
          </span>
        ) : null}
        <div className="min-w-0">
          <h2 className={`text-[15px] font-semibold leading-6 ${dark ? 'text-white' : 'text-ink'}`}>
            {title}
          </h2>
          {description ? (
            <p
              className={`mt-0.5 text-[13px] leading-5 ${
                dark ? 'text-white/70' : 'text-ink-muted'
              }`}
            >
              {description}
            </p>
          ) : null}
        </div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}

export interface CardBodyProps {
  children: ReactNode
  className?: string
  /** Espaciado interno reducido. */
  tight?: boolean
}

export function CardBody({ children, className = '', tight = false }: CardBodyProps) {
  return <div className={`${tight ? 'px-5 py-3' : 'px-5 py-4'} ${className}`}>{children}</div>
}
