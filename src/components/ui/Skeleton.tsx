export interface SkeletonProps {
  className?: string
}

/** Bloque de carga: reemplaza al spinner cuando hay una estructura conocida. */
export function Skeleton({ className = '' }: SkeletonProps) {
  return <div className={`animate-pulse rounded-md bg-slate-200/70 ${className}`} />
}

/** Filas de carga para una tabla. */
export function SkeletonRows({ rows = 4, columns = 3 }: { rows?: number; columns?: number }) {
  return (
    <div className="divide-y divide-line">
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex items-center gap-4 px-5 py-3.5">
          {Array.from({ length: columns }).map((__, columnIndex) => (
            <Skeleton
              key={columnIndex}
              className={columnIndex === 0 ? 'h-3.5 w-1/3' : 'h-3.5 w-20'}
            />
          ))}
        </div>
      ))}
    </div>
  )
}
