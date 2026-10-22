import { Link } from 'react-router-dom'
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

      <div className="flex flex-1 items-center justify-center px-4 py-10 sm:py-14">
        <div className="w-full max-w-[26rem]">
          <div className="mb-7 flex justify-center">
            <Logo />
          </div>

          <div className="rounded-[var(--radius-card)] border border-line bg-surface p-6 shadow-card sm:p-7">
            <h1 className="text-lg font-semibold tracking-tight text-slate-900">{title}</h1>
            {description ? (
              <p className="mt-1.5 text-[13px] leading-5 text-slate-500">{description}</p>
            ) : null}

            <div className="mt-6">{children}</div>
          </div>

          {footer ? (
            <p className="mt-5 text-center text-[13px] text-slate-600">
              {footer}{' '}
              <Link to="/" className="sr-only">
                Volver al inicio
              </Link>
            </p>
          ) : null}
        </div>
      </div>
    </div>
  )
}
