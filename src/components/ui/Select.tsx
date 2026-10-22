import { useId } from 'react'
import type { ReactNode, SelectHTMLAttributes } from 'react'

import { Icon } from './Icon'
import type { IconName } from './Icon'

export interface SelectOption {
  value: string
  label: string
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string
  options: SelectOption[]
  error?: string
  hint?: ReactNode
  icon?: IconName
  hideLabel?: boolean
}

/** Selector con etiqueta y error accesibles. */
export function Select({
  label,
  options,
  error,
  hint,
  icon,
  hideLabel = false,
  id,
  className = '',
  ...rest
}: SelectProps) {
  const generatedId = useId()
  const selectId = id ?? generatedId
  const errorId = `${selectId}-error`
  const hintId = `${selectId}-hint`

  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={selectId}
        className={hideLabel ? 'sr-only' : 'text-[13px] font-medium text-slate-700'}
      >
        {label}
      </label>

      <div className="relative">
        {icon ? (
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
            <Icon name={icon} size={16} />
          </span>
        ) : null}

        <select
          id={selectId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : hint ? hintId : undefined}
          className={`w-full appearance-none rounded-[var(--radius-control)] border bg-white py-2 pl-3 pr-9 text-sm text-slate-900 shadow-xs transition-colors focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500 ${
            error
              ? 'border-rose-400 focus:border-rose-500 focus:ring-rose-100'
              : 'border-line-strong focus:border-brand-500 focus:ring-brand-100'
          } ${icon ? 'pl-9' : ''} ${className}`}
          {...rest}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
          <Icon name="chevronDown" size={15} />
        </span>
      </div>

      {hint && !error ? (
        <p id={hintId} className="text-xs text-slate-500">
          {hint}
        </p>
      ) : null}

      {error ? (
        <p id={errorId} role="alert" className="text-xs font-medium text-rose-600">
          {error}
        </p>
      ) : null}
    </div>
  )
}
