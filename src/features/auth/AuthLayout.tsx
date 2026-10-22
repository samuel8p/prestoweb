import type { ReactNode } from 'react'

import { Logo } from '../../components/ui/Logo'
import { DemoBanner } from '../meta/DemoBanner'

export interface AuthLayoutProps {
  title: string
  description?: string
  children: ReactNode
  footer?: ReactNode
}

/** Estructura de las pantallas de acceso (login y registro). */
export function AuthLayout({ title, description, children, footer }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <DemoBanner />

      <div className="relative flex flex-1 items-center justify-center overflow-hidden px-4 py-12">
        {/* Patrón de olas, muy sutil, detrás de la tarjeta */}
        <div
          aria-hidden="true"
          className="wave-pattern pointer-events-none absolute inset-0 opacity-70"
        />

        <div className="relative w-full max-w-[26rem]">
          <div className="mb-7 flex justify-center">
            <Logo />
          </div>

          <div className="rounded-[var(--radius-card)] border border-line bg-surface p-6 shadow-raised animate-fade-up sm:p-7">
            <h1 className="text-xl font-bold tracking-tight text-ink">{title}</h1>
            {description ? (
              <p className="mt-1.5 text-[13px] leading-5 text-ink-muted">{description}</p>
            ) : null}

            <div className="mt-6">{children}</div>
          </div>

          {footer ? <p className="mt-5 text-center text-[13px] text-ink-muted">{footer}</p> : null}
        </div>
      </div>
    </div>
  )
}
