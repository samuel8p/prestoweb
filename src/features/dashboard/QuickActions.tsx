import { Icon } from '../../components/ui/Icon'
import { QUICK_ACTIONS } from './quickActionsData'

export interface QuickActionsProps {
  onAction: (id: string) => void
}

/** Fichas de acceso rápido: cada una con su propia forma. */
export function QuickActions({ onAction }: QuickActionsProps) {
  return (
    <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {QUICK_ACTIONS.map((action) => (
        <li key={action.id}>
          <button
            type="button"
            onClick={() => onAction(action.id)}
            className={`flex h-full w-full flex-col items-start gap-2 p-4 text-left transition-[transform,box-shadow] duration-200 ease-out hover:-translate-y-0.5 hover:shadow-raised active:scale-[0.98] ${action.shape} ${action.tone}`}
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-[0.6rem] bg-white/70">
              <Icon name={action.icon} size={17} className="text-ink" />
            </span>
            <span className="text-sm font-bold text-ink">{action.label}</span>
            <span className="text-[12px] leading-4 text-ink-muted">{action.hint}</span>
          </button>
        </li>
      ))}
    </ul>
  )
}
