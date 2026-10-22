import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Icon } from '../ui/Icon'
import { useAuth } from '../../features/auth/auth-context'

export interface AvatarMenuProps {
  open: boolean
  onClose: () => void
}

/** Menú del avatar: perfil y cerrar sesión. */
export function AvatarMenu({ open, onClose }: AvatarMenuProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [pending, setPending] = useState(false)

  if (!open) {
    return null
  }

  function handleLogout() {
    setPending(true)
    logout()
    navigate('/ingresar', { replace: true })
  }

  return (
    <div className="absolute right-0 top-full z-40 mt-2 w-60 overflow-hidden rounded-[var(--radius-card)] border border-line bg-surface shadow-raised animate-scale-in">
      <div className="border-b border-line px-4 py-3">
        <p className="truncate text-sm font-semibold text-ink">
          {[user?.first_name, user?.last_name].filter(Boolean).join(' ') || 'Mi cuenta'}
        </p>
        <p className="truncate text-xs text-ink-muted">{user?.email}</p>
      </div>

      <div className="p-1.5">
        <Link
          to="/perfil"
          onClick={onClose}
          className="flex items-center gap-2.5 rounded-[var(--radius-control)] px-3 py-2 text-[13px] font-medium text-ink transition-colors hover:bg-surface-muted"
        >
          <Icon name="user" size={16} className="text-ink-subtle" />
          Mi perfil
        </Link>
        <button
          type="button"
          onClick={handleLogout}
          disabled={pending}
          className="flex w-full items-center gap-2.5 rounded-[var(--radius-control)] px-3 py-2 text-[13px] font-medium text-ink transition-colors hover:bg-surface-muted disabled:opacity-60"
        >
          <Icon name="logout" size={16} className="text-ink-subtle" />
          Cerrar sesión
        </button>
      </div>
    </div>
  )
}
