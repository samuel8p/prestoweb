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
      className={`inline-flex rounded-[var(--radius-control)] border border-line-strong bg-surface p-0.5 shadow-card ${className}`}
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
            className={`inline-flex items-center gap-1.5 rounded-[0.4rem] px-3 py-1.5 text-[13px] font-semibold transition-[background-color,color,transform] duration-200 ease-out active:scale-[0.97] ${
              selected
                ? 'bg-teal text-white'
                : 'text-ink-muted hover:bg-surface-muted hover:text-ink'
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
