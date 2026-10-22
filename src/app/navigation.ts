import type { IconName } from '../components/ui/Icon'

/** Una sección del producto (una entrada del menú). */
export interface NavSection {
  id: string
  label: string
  to: string
  icon: IconName
}

/**
 * Menú del escritorio: cinco secciones.
 *
 * Avisos no entra: se llega desde la campana del encabezado. Perfil y cerrar
 * sesión viven en el menú del avatar.
 */
export const NAV_SECTIONS: NavSection[] = [
  { id: 'inicio', label: 'Inicio', to: '/', icon: 'dashboard' },
  { id: 'prestamos', label: 'Préstamos', to: '/prestamos', icon: 'loan' },
  { id: 'inversiones', label: 'Inversiones', to: '/inversiones', icon: 'trending' },
  { id: 'presupuestos', label: 'Presupuestos', to: '/presupuestos', icon: 'budget' },
  { id: 'reportes', label: 'Reportes', to: '/reportes', icon: 'report' },
]

/** Barra inferior del móvil: cinco destinos. */
export const MOBILE_SECTIONS: NavSection[] = [
  { id: 'inicio', label: 'Inicio', to: '/', icon: 'dashboard' },
  { id: 'prestamos', label: 'Préstamos', to: '/prestamos', icon: 'loan' },
  { id: 'inversiones', label: 'Inversiones', to: '/inversiones', icon: 'trending' },
  { id: 'presupuestos', label: 'Presupuestos', to: '/presupuestos', icon: 'budget' },
]

/** Destinos adicionales del menú "Más" del móvil. */
export const MOBILE_EXTRA_SECTIONS: NavSection[] = [
  { id: 'reportes', label: 'Reportes', to: '/reportes', icon: 'report' },
  { id: 'avisos', label: 'Avisos', to: '/avisos', icon: 'bell' },
  { id: 'perfil', label: 'Perfil', to: '/perfil', icon: 'user' },
]

/** Una entrada del buscador global. */
export interface SearchEntry {
  id: string
  label: string
  hint: string
  icon: IconName
  group: 'Secciones' | 'Acciones'
  /** A dónde navegar. */
  to?: string
  /** Acción a ejecutar (abre un modal de la pantalla actual). */
  action?: string
}

/**
 * Índice del buscador global.
 *
 * Solo del cliente: son rutas y acciones de la app, sin llamadas a la API.
 */
export const SEARCH_ENTRIES: SearchEntry[] = [
  {
    id: 'inicio',
    label: 'Inicio',
    hint: 'Saldos y acciones rápidas',
    icon: 'dashboard',
    group: 'Secciones',
    to: '/',
  },
  {
    id: 'prestamos',
    label: 'Mis préstamos',
    hint: 'Préstamos como prestatario y prestamista',
    icon: 'loan',
    group: 'Secciones',
    to: '/prestamos?vista=prestamos',
  },
  {
    id: 'ofertas',
    label: 'Ofertas del marketplace',
    hint: 'Buscar y aceptar una oferta',
    icon: 'offer',
    group: 'Secciones',
    to: '/prestamos?vista=ofertas',
  },
  {
    id: 'inversiones',
    label: 'Inversiones',
    hint: 'Plazos fijos y posiciones',
    icon: 'trending',
    group: 'Secciones',
    to: '/inversiones',
  },
  {
    id: 'presupuestos',
    label: 'Presupuestos',
    hint: 'Categorías y límites mensuales',
    icon: 'budget',
    group: 'Secciones',
    to: '/presupuestos',
  },
  {
    id: 'reportes',
    label: 'Reportes',
    hint: 'Movimientos, gasto, préstamos e inversiones',
    icon: 'report',
    group: 'Secciones',
    to: '/reportes',
  },
  {
    id: 'avisos',
    label: 'Avisos',
    hint: 'Notificaciones y preferencias',
    icon: 'bell',
    group: 'Secciones',
    to: '/avisos',
  },
  {
    id: 'perfil',
    label: 'Mi perfil',
    hint: 'Datos de la cuenta y verificación KYC',
    icon: 'user',
    group: 'Secciones',
    to: '/perfil',
  },
  {
    id: 'accion-ingresar',
    label: 'Ingresar dinero',
    hint: 'Abrir el movimiento de depósito',
    icon: 'arrowDownLeft',
    group: 'Acciones',
    action: 'ingresar',
  },
  {
    id: 'accion-transferir',
    label: 'Transferir',
    hint: 'Abrir el movimiento de transferencia',
    icon: 'swap',
    group: 'Acciones',
    action: 'transferir',
  },
  {
    id: 'accion-retirar',
    label: 'Retirar',
    hint: 'Abrir el movimiento de retiro',
    icon: 'arrowUpRight',
    group: 'Acciones',
    action: 'retirar',
  },
  {
    id: 'accion-nueva-oferta',
    label: 'Publicar una oferta',
    hint: 'Abrir el formulario de oferta',
    icon: 'offer',
    group: 'Acciones',
    action: 'nueva-oferta',
  },
  {
    id: 'accion-buscar-ofertas',
    label: 'Buscar ofertas',
    hint: 'Ir al buscador del marketplace',
    icon: 'search',
    group: 'Acciones',
    to: '/prestamos?vista=ofertas&buscar=1',
  },
  {
    id: 'accion-movimientos',
    label: 'Ver todos los movimientos',
    hint: 'Historial paginado',
    icon: 'swap',
    group: 'Acciones',
    to: '/billetera',
  },
]
