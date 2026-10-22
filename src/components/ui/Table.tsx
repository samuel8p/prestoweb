import type { ReactNode } from 'react'

export interface TableProps {
  children: ReactNode
  className?: string
}

/** Contenedor con scroll horizontal para tablas anchas en pantallas chicas. */
export function Table({ children, className = '' }: TableProps) {
  return (
    <div className={`w-full overflow-x-auto ${className}`}>
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  )
}

export function TableHead({ children }: { children: ReactNode }) {
  return (
    <thead className="bg-surface-muted">
      <tr className="border-b border-line">{children}</tr>
    </thead>
  )
}

export function TableBody({ children }: { children: ReactNode }) {
  return <tbody className="divide-y divide-line">{children}</tbody>
}

export function TableRow({
  children,
  className = '',
  onClick,
}: {
  children: ReactNode
  className?: string
  onClick?: () => void
}) {
  return (
    <tr
      className={`transition-colors ${onClick ? 'cursor-pointer hover:bg-surface-muted' : ''} ${className}`}
    >
      {children}
    </tr>
  )
}

export function TableHeader({
  children,
  align = 'left',
  className = '',
}: {
  children: ReactNode
  align?: 'left' | 'right' | 'center'
  className?: string
}) {
  const alignment =
    align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'

  return (
    <th
      scope="col"
      className={`px-5 py-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-muted ${alignment} ${className}`}
    >
      {children}
    </th>
  )
}

export function TableCell({
  children,
  align = 'left',
  className = '',
}: {
  children: ReactNode
  align?: 'left' | 'right' | 'center'
  className?: string
}) {
  const alignment =
    align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'

  return <td className={`px-5 py-3 align-middle text-ink ${alignment} ${className}`}>{children}</td>
}
