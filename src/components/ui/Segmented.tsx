import { Icon } from './Icon'
import type { IconName } from './Icon'

export interface SegmentOption<T extends string> {
  value: T
  label: string
  icon?: IconName
}

export interface SegmentedProps<T extends string> {
  /** Etiqueta accesible del grupo de control. */
  label: string
  value: T
  options: Array<SegmentOption<T>>
  onChange: (value: T) => void
  className?: string
}

/**
 * Control segmentado: para elegir entre pocas opciones (por ejemplo, la
 * moneda de una pantalla).
 */
export function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
  className = '',
}: SegmentedProps<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className={`inline-flex rounded-[var(--radius-control)] border border-line-strong bg-surface p-0.5 shadow-xs ${className}`}
    >
      {options.map((option) => {
        const selected = option.value === value

        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option.value)}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors ${
              selected
                ? 'bg-brand-600 text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            {option.icon ? <Icon name={option.icon} size={15} /> : null}
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
