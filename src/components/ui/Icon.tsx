import type { SVGProps } from 'react'

/**
 * Iconografía de la aplicación.
 *
 * Set propio de íconos de trazo (24x24, `currentColor`), sin dependencias
 * externas: geometría simple y consistente, como la de una app financiera.
 */
export type IconName =
  | 'dashboard'
  | 'wallet'
  | 'swap'
  | 'offer'
  | 'loan'
  | 'trending'
  | 'budget'
  | 'report'
  | 'bell'
  | 'user'
  | 'logout'
  | 'plus'
  | 'search'
  | 'filter'
  | 'download'
  | 'check'
  | 'checkCircle'
  | 'alert'
  | 'info'
  | 'x'
  | 'menu'
  | 'chevronRight'
  | 'chevronDown'
  | 'calendar'
  | 'shield'
  | 'arrowUpRight'
  | 'arrowDownLeft'
  | 'clock'
  | 'mail'
  | 'lock'
  | 'coins'
  | 'refresh'
  | 'eye'
  | 'send'
  | 'bank'
  | 'sliders'

const PATHS: Record<IconName, string[]> = {
  dashboard: ['M3 3h7v7H3z', 'M14 3h7v4h-7z', 'M14 11h7v10h-7z', 'M3 14h7v7H3z'],
  wallet: [
    'M3 7a2 2 0 0 1 2-2h12.5a1.5 1.5 0 0 1 0 3H5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2H5',
    'M17.5 11.5h.01',
  ],
  swap: ['M4 8h14l-4-4', 'M20 16H6l4 4'],
  offer: ['M20.6 13.4 12 22l-9-9V3h10l7.6 7.6a2 2 0 0 1 0 2.8z', 'M7.5 7.5h.01'],
  loan: [
    'M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z',
    'M14 3v5h5',
    'M9 13h6',
    'M9 17h4',
  ],
  trending: ['M3 17l6-6 4 4 7-7', 'M17 8h4v4'],
  budget: ['M21.2 15.9A10 10 0 1 1 8 2.8', 'M22 12A10 10 0 0 0 12 2v10z'],
  report: ['M3 21h18', 'M6.5 21v-7', 'M11.5 21V7', 'M16.5 21v-4'],
  bell: ['M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9', 'M13.7 21a2 2 0 0 1-3.4 0'],
  user: ['M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2', 'M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8'],
  logout: ['M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4', 'M16 17l5-5-5-5', 'M21 12H9'],
  plus: ['M12 5v14', 'M5 12h14'],
  search: ['M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16', 'M21 21l-4.35-4.35'],
  filter: ['M22 3H2l8 9.46V19l4 2v-8.54z'],
  download: ['M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4', 'M7 10l5 5 5-5', 'M12 15V3'],
  check: ['M20 6 9 17l-5-5'],
  checkCircle: ['M22 11.1V12a10 10 0 1 1-5.9-9.1', 'M22 4 12 14l-3-3'],
  alert: [
    'M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z',
    'M12 9v4',
    'M12 17h.01',
  ],
  info: ['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20', 'M12 16v-4', 'M12 8h.01'],
  x: ['M18 6 6 18', 'M6 6l12 12'],
  menu: ['M3 6h18', 'M3 12h18', 'M3 18h18'],
  chevronRight: ['M9 18l6-6-6-6'],
  chevronDown: ['M6 9l6 6 6-6'],
  calendar: [
    'M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
    'M8 2v4',
    'M16 2v4',
    'M3 10h18',
  ],
  shield: ['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'],
  arrowUpRight: ['M7 17 17 7', 'M8 7h9v9'],
  arrowDownLeft: ['M17 7 7 17', 'M16 17H7V8'],
  clock: ['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20', 'M12 6v6l4 2'],
  mail: [
    'M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
    'M22 6l-10 7L2 6',
  ],
  lock: ['M4 11h16v10H4z', 'M8 11V7a4 4 0 0 1 8 0v4'],
  coins: ['M9 15a6 6 0 1 0 0-12 6 6 0 0 0 0 12z', 'M15 21a6 6 0 1 0 0-12 6 6 0 0 0 0 12z'],
  refresh: [
    'M21 4v6h-6',
    'M3 20v-6h6',
    'M3.5 9a9 9 0 0 1 14.9-3.4L21 10',
    'M1 14l4.6 4.4A9 9 0 0 0 20.5 15',
  ],
  eye: ['M2 12s3.8-7 10-7 10 7 10 7-3.8 7-10 7-10-7-10-7z', 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6'],
  send: ['M22 2 11 13', 'M22 2l-7 20-4-9-9-4z'],
  bank: ['M3 10h18', 'M5 10v8', 'M9.5 10v8', 'M14.5 10v8', 'M19 10v8', 'M3 21h18', 'M12 2 3 7h18z'],
  sliders: [
    'M4 21v-7',
    'M4 10V3',
    'M12 21v-9',
    'M12 8V3',
    'M20 21v-5',
    'M20 12V3',
    'M1 14h6',
    'M9 8h6',
    'M17 16h6',
  ],
}

export interface IconProps extends Omit<SVGProps<SVGSVGElement>, 'name'> {
  name: IconName
  /** Lado del cuadrado que contiene el ícono, en píxeles. */
  size?: number
}

/** Ícono de la aplicación. */
export function Icon({ name, size = 20, className = '', ...rest }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={`shrink-0 ${className}`}
      {...rest}
    >
      {PATHS[name].map((path) => (
        <path key={path} d={path} />
      ))}
    </svg>
  )
}
