import { useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { Button } from '../ui/Button'
import { Icon } from '../ui/Icon'
import type { IconName } from '../ui/Icon'
import { Logo } from '../ui/Logo'
import { DemoBanner } from '../../features/meta/DemoBanner'
import { useAuth } from '../../features/auth/auth-context'

interface NavItem {
  to: string
  label: string
  icon: IconName
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Dinero',
    items: [
      { to: '/panel', label: 'Panel', icon: 'dashboard' },
      { to: '/billetera', label: 'Billetera', icon: 'wallet' },
    ],
  },
  {
    label: 'Préstamos',
    items: [
      { to: '/ofertas', label: 'Ofertas', icon: 'offer' },
      { to: '/prestamos', label: 'Préstamos', icon: 'loan' },
    ],
  },
  {
    label: 'Planificación',
    items: [
      { to: '/inversiones', label: 'Inversiones', icon: 'trending' },
      { to: '/presupuestos', label: 'Presupuestos', icon: 'budget' },
      { to: '/reportes', label: 'Reportes', icon: 'report' },
    ],
  },
  {
    label: 'Cuenta',
    items: [
      { to: '/avisos', label: 'Avisos', icon: 'bell' },
      { to: '/perfil', label: 'Perfil', icon: 'user' },
    ],
  },
]

const itemClasses = ({ isActive }: { isActive: boolean }) =>
  `group flex items-center gap-2.5 rounded-[var(--radius-control)] px-2.5 py-2 text-[13.5px] font-medium transition-colors ${
    isActive
      ? 'bg-brand-50 text-brand-800'
      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
  }`

/** Navegación lateral agrupada por categorías. */
function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav aria-label="Principal" className="flex flex-1 flex-col gap-6 overflow-y-auto px-3 py-4">
      {NAV_GROUPS.map((group) => (
        <div key={group.label}>
          <p className="px-2.5 pb-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400">
            {group.label}
          </p>
          <ul className="space-y-0.5">
            {group.items.map((item) => (
              <li key={item.to}>
                <NavLink to={item.to} className={itemClasses} onClick={onNavigate}>
                  {({ isActive }) => (
                    <>
                      <Icon
                        name={item.icon}
                        size={17}
                        className={isActive ? 'text-brand-600' : 'text-slate-400'}
                      />
                      {item.label}
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  )
}

/** Pie de la barra lateral: la cuenta y la salida. */
function AccountFooter({ onNavigate }: { onNavigate?: () => void }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/ingresar', { replace: true })
    onNavigate?.()
  }

  return (
    <div className="border-t border-line px-3 py-3">
      <NavLink
        to="/perfil"
        onClick={onNavigate}
        className="flex items-center gap-2.5 rounded-[var(--radius-control)] px-2.5 py-2 transition-colors hover:bg-slate-100"
      >
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100 text-[12px] font-semibold text-brand-800">
          {(user?.first_name?.[0] ?? user?.email?.[0] ?? '?').toUpperCase()}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[13px] font-medium text-slate-800">
            {[user?.first_name, user?.last_name].filter(Boolean).join(' ') || 'Mi cuenta'}
          </span>
          <span className="block truncate text-xs text-slate-500">{user?.email}</span>
        </span>
      </NavLink>

      <Button
        variant="ghost"
        size="sm"
        icon="logout"
        className="mt-1 w-full justify-start"
        onClick={handleLogout}
      >
        Cerrar sesión
      </Button>
    </div>
  )
}

/**
 * Estructura de la aplicación.
 *
 * En pantallas grandes hay una barra lateral fija con la navegación agrupada;
 * en las chicas, un encabezado con menú lateral desplegable.
 */
export function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  const section = NAV_GROUPS.find((group) =>
    group.items.some((item) => location.pathname.startsWith(item.to)),
  )?.label

  return (
    <div className="min-h-screen bg-canvas">
      {/* Barra lateral (pantallas grandes) */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-line bg-surface lg:flex">
        <div className="flex h-14 items-center px-5">
          <Logo />
        </div>
        <Navigation />
        <AccountFooter />
      </aside>

      <div className="lg:pl-64">
        {/* Encabezado fijo */}
        <header className="sticky top-0 z-20 border-b border-line bg-surface/95 backdrop-blur">
          <DemoBanner />

          <div className="flex h-14 items-center justify-between gap-3 px-4 sm:px-6">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                icon="menu"
                className="lg:hidden"
                aria-expanded={menuOpen}
                aria-controls="menu-lateral"
                onClick={() => setMenuOpen((open) => !open)}
              >
                <span className="sr-only">Abrir el menú</span>
              </Button>

              <span className="hidden text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400 lg:inline">
                {section ?? 'Presto'}
              </span>

              <span className="lg:hidden">
                <Logo compact />
              </span>
            </div>

            <p className="hidden text-[13px] text-slate-500 sm:block">
              {section ? `Finanzas entre personas · ${section}` : 'Finanzas entre personas'}
            </p>
          </div>
        </header>

        <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
          <Outlet />
        </main>
      </div>

      {/* Menú lateral (pantallas chicas) */}
      {menuOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Cerrar el menú"
            onClick={() => setMenuOpen(false)}
            className="absolute inset-0 cursor-default bg-slate-950/40"
          />

          <div
            id="menu-lateral"
            className="absolute inset-y-0 left-0 flex w-72 max-w-[85%] flex-col border-r border-line bg-surface shadow-raised"
          >
            <div className="flex h-14 items-center justify-between px-5">
              <div onClick={() => setMenuOpen(false)}>
                <Logo />
              </div>
              <Button
                variant="ghost"
                size="sm"
                icon="x"
                aria-label="Cerrar el menú"
                onClick={() => setMenuOpen(false)}
              />
            </div>

            <Navigation onNavigate={() => setMenuOpen(false)} />
            <AccountFooter onNavigate={() => setMenuOpen(false)} />
          </div>
        </div>
      ) : null}
    </div>
  )
}
