import type { ReactNode } from 'react'

import { Icon } from './Icon'
import type { IconName } from './Icon'

export interface CardProps {
  children: ReactNode
  className?: string
  as?: 'div' | 'section' | 'article'
}

/**
 * Superficie base de la aplicación.
 *
 * Blanco con borde sutil y sombra mínima: separa del fondo sin pasos de color.
 */
export function Card({ children, className = '', as: Tag = 'div' }: CardProps) {
  return (
    <Tag
      className={`rounded-[var(--radius-card)] border border-line bg-surface shadow-card ${className}`}
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
}

export function CardHeader({ title, description, action, icon }: CardHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
      <div className="flex min-w-0 items-start gap-3">
        {icon ? (
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
            <Icon name={icon} size={17} />
          </span>
        ) : null}
        <div className="min-w-0">
          <h2 className="text-[15px] font-semibold leading-6 text-slate-900">{title}</h2>
          {description ? (
            <p className="mt-0.5 text-[13px] leading-5 text-slate-500">{description}</p>
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
