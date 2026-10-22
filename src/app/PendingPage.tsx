import { Link } from 'react-router-dom'

export interface PendingPageProps {
  title: string
}

/** Pantalla provisoria de una sección que todavía no está construida. */
export function PendingPage({ title }: PendingPageProps) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
      <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
      <p className="mt-2 text-sm text-slate-500">Esta sección todavía no está disponible.</p>
      <Link
        to="/panel"
        className="mt-4 inline-block text-sm font-medium text-brand-700 hover:underline"
      >
        Volver al panel
      </Link>
    </div>
  )
}
