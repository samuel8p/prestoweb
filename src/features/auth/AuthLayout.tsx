import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'

import { DemoBanner } from '../meta/DemoBanner'
import { useMeta } from '../meta/useMeta'

export interface AuthLayoutProps {
  title: string
  description?: string
  children: ReactNode
  footer?: ReactNode
}

/** Estructura de las pantallas de acceso (login y registro). */
export function AuthLayout({ title, description, children, footer }: AuthLayoutProps) {
  const { data: meta } = useMeta()
  const isDemo = meta?.mode === 'demo'

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-canvas px-4 py-10">
      <DemoBanner />

      <div className={`w-full max-w-md ${isDemo ? 'mt-8' : ''}`}>
        <Link
          to="/"
          className="mb-6 block text-center text-2xl font-bold tracking-tight text-brand-700"
        >
          Presto
        </Link>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
          {description ? <p className="mt-1 text-sm text-slate-500">{description}</p> : null}
          <div className="mt-5">{children}</div>
        </div>

        {footer ? <div className="mt-4 text-center text-sm text-slate-600">{footer}</div> : null}
      </div>
    </div>
  )
}
