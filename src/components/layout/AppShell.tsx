import { useCallback, useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'

import { AvatarMenu } from './AvatarMenu'
import { NotificationsPanel } from './NotificationsPanel'
import { SearchDialog } from './SearchDialog'
import { Icon } from '../ui/Icon'
import { Logo } from '../ui/Logo'
import { MOBILE_EXTRA_SECTIONS, MOBILE_SECTIONS, NAV_SECTIONS } from '../../app/navigation'
import { DemoBanner } from '../../features/meta/DemoBanner'
import { useDismissable } from '../../lib/useDismissable'

/**
 * Estructura de la aplicación.
 *
 * Encabezado con la navegación del escritorio y, a la derecha, el buscador,
 * la campana de avisos y el menú del avatar. En el móvil, barra inferior con
 * cinco destinos.
 */
export function AppShell() {
  const [searchOpen, setSearchOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [avatarOpen, setAvatarOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const { pathname } = useLocation()
  const notificationsRef = useRef<HTMLDivElement>(null)
  const avatarRef = useRef<HTMLDivElement>(null)

  const closeNotifications = useCallback(() => setNotificationsOpen(false), [])
  const closeAvatar = useCallback(() => setAvatarOpen(false), [])

  useDismissable(notificationsOpen, closeNotifications)
  useDismissable(avatarOpen, closeAvatar)
  useDismissable(moreOpen, () => setMoreOpen(false))

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setSearchOpen(true)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Al cambiar de ruta se cierran los paneles abiertos (ajuste durante el
  // render, sin setState dentro de un efecto).
  const [lastPath, setLastPath] = useState(pathname)
  if (pathname !== lastPath) {
    setLastPath(pathname)
    setNotificationsOpen(false)
    setAvatarOpen(false)
    setMoreOpen(false)
  }

  return (
    <div className="min-h-screen bg-canvas pb-20 lg:pb-0">
      <header className="sticky top-0 z-30 bg-ocean text-white on-dark">
        <DemoBanner />

        <div className="mx-auto flex h-16 max-w-[92rem] items-center gap-3 px-4 sm:px-6 lg:px-8">
          <Logo variant="dark" />

          <nav aria-label="Principal" className="ml-6 hidden items-center gap-1 lg:flex">
            {NAV_SECTIONS.map((section) => (
              <NavLink
                key={section.id}
                to={section.to}
                end={section.to === '/'}
                className={({ isActive }) =>
                  `rounded-[var(--radius-control)] px-3 py-2 text-[13.5px] font-semibold transition-colors duration-200 ${
                    isActive
                      ? 'bg-white/12 text-white'
                      : 'text-white/65 hover:bg-white/5 hover:text-white'
                  }`
                }
              >
                {section.label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setSearchOpen(true)}
              aria-label="Buscar"
              aria-haspopup="dialog"
              className="flex h-9 items-center gap-2 rounded-[var(--radius-control)] px-2.5 text-white/75 transition-colors duration-200 hover:bg-white/10 hover:text-white sm:w-56 sm:justify-start"
            >
              <Icon name="search" size={17} />
              <span className="hidden text-[13px] sm:inline">Buscar…</span>
              <kbd className="ml-auto hidden rounded border border-white/20 px-1.5 py-0.5 text-[10px] font-semibold text-white/60 sm:block">
                ⌘K
              </kbd>
            </button>

            <div className="relative" ref={notificationsRef}>
              <button
                type="button"
                onClick={() => {
                  setNotificationsOpen((open) => !open)
                  setAvatarOpen(false)
                }}
                aria-label="Avisos"
                aria-expanded={notificationsOpen}
                className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-control)] text-white/75 transition-colors duration-200 hover:bg-white/10 hover:text-white"
              >
                <Icon name="bell" size={18} />
              </button>
              <NotificationsPanel open={notificationsOpen} onClose={closeNotifications} />
            </div>

            <div className="relative" ref={avatarRef}>
              <button
                type="button"
                onClick={() => {
                  setAvatarOpen((open) => !open)
                  setNotificationsOpen(false)
                }}
                aria-label="Mi cuenta"
                aria-expanded={avatarOpen}
                className="flex h-9 w-9 items-center justify-center rounded-full bg-turquoise/20 text-[13px] font-bold text-turquoise transition-colors duration-200 hover:bg-turquoise/30"
              >
                <span aria-hidden="true">P</span>
              </button>
              <AvatarMenu open={avatarOpen} onClose={closeAvatar} />
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[92rem] px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        <Outlet />
      </main>

      {/* Barra inferior del móvil */}
      <nav
        aria-label="Navegación móvil"
        className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 backdrop-blur lg:hidden"
      >
        <ul className="grid grid-cols-5">
          {MOBILE_SECTIONS.map((section) => (
            <li key={section.id}>
              <NavLink
                to={section.to}
                end={section.to === '/'}
                className={({ isActive }) =>
                  `flex flex-col items-center gap-1 px-1 py-2.5 text-[10.5px] font-semibold transition-colors duration-200 ${
                    isActive ? 'text-teal' : 'text-ink-muted'
                  }`
                }
              >
                <Icon name={section.icon} size={20} />
                {section.label}
              </NavLink>
            </li>
          ))}
          <li>
            <button
              type="button"
              onClick={() => setMoreOpen(true)}
              aria-expanded={moreOpen}
              className="flex w-full flex-col items-center gap-1 px-1 py-2.5 text-[10.5px] font-semibold text-ink-muted transition-colors duration-200"
            >
              <Icon name="menu" size={20} />
              Más
            </button>
          </li>
        </ul>
      </nav>

      {moreOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Cerrar"
            onClick={() => setMoreOpen(false)}
            className="absolute inset-0 cursor-default bg-ocean/50 animate-fade-in"
          />
          <div className="absolute inset-x-0 bottom-0 rounded-t-2xl border-t border-line bg-surface p-4 shadow-raised animate-fade-up">
            <ul className="space-y-1">
              {MOBILE_EXTRA_SECTIONS.map((section) => (
                <li key={section.id}>
                  <NavLink
                    to={section.to}
                    onClick={() => setMoreOpen(false)}
                    className="flex items-center gap-3 rounded-[var(--radius-control)] px-3 py-2.5 text-sm font-semibold text-ink transition-colors hover:bg-surface-muted"
                  >
                    <Icon name={section.icon} size={18} className="text-ink-subtle" />
                    {section.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}

      <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  )
}
