import { useLayoutEffect, useRef, useState } from 'react'
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

/** Rutas que tienen una entrada en la navegación. */
const NAV_ITEMS = NAV_GROUPS.flatMap((group) => group.items)

/** Navegación del océano, con el indicador de ruta activa que se desliza. */
function Navigation({
  onNavigate,
  itemRefs,
}: {
  onNavigate?: () => void
  itemRefs: React.MutableRefObject<Record<string, HTMLLIElement | null>>
}) {
  const { pathname } = useLocation()
  const listRef = useRef<HTMLUListElement>(null)
  const [indicatorTop, setIndicatorTop] = useState<number | null>(null)

  const activePath = NAV_ITEMS.find((item) => pathname.startsWith(item.to))?.to ?? null

  useLayoutEffect(() => {
    function update() {
      if (!activePath) {
        setIndicatorTop(null)
        return
      }
      const element = itemRefs.current[activePath]
      if (element) {
        setIndicatorTop(element.offsetTop)
      }
    }

    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [activePath, itemRefs])

  return (
    <nav aria-label="Principal" className="flex flex-1 flex-col gap-6 overflow-y-auto px-3 py-5">
      {NAV_GROUPS.map((group) => (
        <div key={group.label}>
          <p className="px-2.5 pb-2 text-[10px] font-bold uppercase tracking-[0.12em] text-white/40">
            {group.label}
          </p>
          <ul ref={listRef} className="relative space-y-0.5">
            {indicatorTop !== null ? (
              <span
                aria-hidden="true"
                className="pointer-events-none absolute inset-x-0 top-0 -z-0 h-[38px] rounded-[var(--radius-control)] bg-white/10 transition-transform duration-200 ease-out"
                style={{ transform: `translate3d(0, ${indicatorTop}px, 0)` }}
              />
            ) : null}

            {group.items.map((item) => (
              <li
                key={item.to}
                ref={(element) => {
                  itemRefs.current[item.to] = element
                }}
                className="relative"
              >
                <NavLink
                  to={item.to}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    `relative flex items-center gap-3 rounded-[var(--radius-control)] px-2.5 py-2 text-[13.5px] font-semibold transition-colors duration-200 ${
                      isActive ? 'text-white' : 'text-white/60 hover:text-white hover:bg-white/5'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <span
                        aria-hidden="true"
                        className={`absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-full bg-turquoise transition-opacity duration-200 ${
                          isActive ? 'opacity-100' : 'opacity-0'
                        }`}
                      />
                      <Icon
                        name={item.icon}
                        size={17}
                        className={isActive ? 'text-turquoise' : 'text-white/50'}
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
    <div className="border-t border-white/10 px-3 py-3">
      <NavLink
        to="/perfil"
        onClick={onNavigate}
        className="flex items-center gap-3 rounded-[var(--radius-control)] px-2.5 py-2 transition-colors hover:bg-white/5"
      >
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-turquoise/15 text-[12px] font-bold text-turquoise">
          {(user?.first_name?.[0] ?? user?.email?.[0] ?? '?').toUpperCase()}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[13px] font-semibold text-white">
            {[user?.first_name, user?.last_name].filter(Boolean).join(' ') || 'Mi cuenta'}
          </span>
          <span className="block truncate text-xs text-white/50">{user?.email}</span>
        </span>
      </NavLink>

      <Button
        variant="ghost"
        size="sm"
        icon="logout"
        className="mt-1 w-full justify-start text-white/60 hover:bg-white/5 hover:text-white"
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
 * Barra lateral en azul marino con la navegación agrupada y un indicador de
 * ruta que se desliza; en pantallas chicas, un menú lateral desplegable.
 */
export function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false)
  const { pathname } = useLocation()
  const itemRefs = useRef<Record<string, HTMLLIElement | null>>({})

  const section = NAV_GROUPS.find((group) =>
    group.items.some((item) => pathname.startsWith(item.to)),
  )?.label

  return (
    <div className="min-h-screen bg-canvas">
      {/* Barra lateral (pantallas grandes) */}
      <aside className="on-dark fixed inset-y-0 left-0 z-30 hidden w-64 flex-col bg-ocean lg:flex">
        <div className="flex h-16 items-center px-5">
          <Logo variant="dark" />
        </div>
        <Navigation itemRefs={itemRefs} />
        <AccountFooter />
      </aside>

      <div className="lg:pl-64">
        {/* Encabezado fijo */}
        <header className="sticky top-0 z-20 border-b border-line bg-canvas/90 backdrop-blur">
          <DemoBanner />

          <div className="flex h-16 items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
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

              <span className="label-caps text-ink-subtle">{section ?? 'Presto'}</span>

              <span className="lg:hidden">
                <Logo compact />
              </span>
            </div>

            <p className="hidden text-[13px] text-ink-muted sm:block">
              {section ? `Finanzas entre personas · ${section}` : 'Finanzas entre personas'}
            </p>
          </div>
        </header>

        <main className="px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
          <div className="mx-auto max-w-[92rem]">
            <Outlet />
          </div>
        </main>
      </div>

      {/* Menú lateral (pantallas chicas) */}
      {menuOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Cerrar el menú"
            onClick={() => setMenuOpen(false)}
            className="absolute inset-0 cursor-default bg-ocean/50 animate-fade-in"
          />

          <div
            id="menu-lateral"
            className="on-dark absolute inset-y-0 left-0 flex w-72 max-w-[85%] flex-col bg-ocean shadow-raised animate-slide-left"
          >
            <div className="flex h-16 items-center justify-between px-5">
              <div onClick={() => setMenuOpen(false)}>
                <Logo variant="dark" />
              </div>
              <Button
                variant="ghost"
                size="sm"
                icon="x"
                className="text-white/70 hover:bg-white/10 hover:text-white"
                aria-label="Cerrar el menú"
                onClick={() => setMenuOpen(false)}
              />
            </div>

            <Navigation itemRefs={itemRefs} onNavigate={() => setMenuOpen(false)} />
            <AccountFooter onNavigate={() => setMenuOpen(false)} />
          </div>
        </div>
      ) : null}
    </div>
  )
}
