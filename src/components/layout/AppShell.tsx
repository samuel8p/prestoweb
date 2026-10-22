import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { Button } from '../ui/Button'
import { DemoBanner } from '../../features/meta/DemoBanner'
import { useMeta } from '../../features/meta/useMeta'
import { useAuth } from '../../features/auth/auth-context'

interface NavItem {
  to: string
  label: string
}

const NAV_ITEMS: NavItem[] = [
  { to: '/panel', label: 'Panel' },
  { to: '/billetera', label: 'Billetera' },
  { to: '/ofertas', label: 'Ofertas' },
  { to: '/prestamos', label: 'Préstamos' },
  { to: '/inversiones', label: 'Inversiones' },
  { to: '/presupuestos', label: 'Presupuestos' },
  { to: '/reportes', label: 'Reportes' },
  { to: '/avisos', label: 'Avisos' },
]

const linkClasses = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
    isActive ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
  }`

/** Estructura de la aplicación: encabezado, navegación y contenido. */
export function AppShell() {
  const { user, logout } = useAuth()
  const { data: meta } = useMeta()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const isDemo = meta?.mode === 'demo'

  function handleLogout() {
    logout()
    navigate('/ingresar', { replace: true })
  }

  return (
    <div className="min-h-screen bg-canvas">
      <DemoBanner />

      <header
        className={`sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur ${
          isDemo ? 'mt-8' : ''
        }`}
      >
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <NavLink to="/panel" className="text-lg font-bold tracking-tight text-brand-700">
              Presto
            </NavLink>
            <span className="hidden text-xs text-slate-400 sm:inline">
              Finanzas, inversiones y préstamos
            </span>
          </div>

          <div className="flex items-center gap-2">
            <NavLink
              to="/perfil"
              className="hidden max-w-[14rem] truncate text-sm text-slate-600 hover:text-slate-900 sm:block"
            >
              {user?.email ?? 'Mi perfil'}
            </NavLink>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              Salir
            </Button>
            <Button
              variant="secondary"
              size="sm"
              className="sm:hidden"
              aria-expanded={menuOpen}
              aria-controls="nav-principal"
              onClick={() => setMenuOpen((open) => !open)}
            >
              {menuOpen ? 'Cerrar' : 'Menú'}
            </Button>
          </div>
        </div>

        <nav
          id="nav-principal"
          aria-label="Principal"
          className={`${menuOpen ? 'block' : 'hidden'} border-t border-slate-100 px-4 pb-3 sm:block sm:border-0 sm:pb-0`}
        >
          <ul className="mx-auto flex max-w-6xl flex-col gap-1 sm:flex-row sm:flex-wrap sm:items-center sm:gap-1 sm:px-6">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink to={item.to} className={linkClasses} onClick={() => setMenuOpen(false)}>
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        <Outlet />
      </main>
    </div>
  )
}
