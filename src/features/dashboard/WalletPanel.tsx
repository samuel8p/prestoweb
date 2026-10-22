import { useState } from 'react'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { describeError } from '../../lib/api/errors'
import { useMyAlias, useSetAlias } from '../auth/api'
import type { Account } from '../../lib/api/types'

export interface WalletPanelProps {
  accounts: Account[]
  onDone: () => void
}

/**
 * Tu billetera: el alias público y los identificadores de las cuentas.
 *
 * El alias es lo que la otra persona usa para transferirte; si todavía no
 * tenés uno, se puede crear desde acá.
 */
export function WalletPanel({ accounts, onDone }: WalletPanelProps) {
  const alias = useMyAlias()
  const setAlias = useSetAlias()
  const [draft, setDraft] = useState('')
  const [copied, setCopied] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const value = alias.data?.alias ?? null

  async function copy(text: string) {
    try {
      await navigator.clipboard?.writeText(text)
      setCopied(text)
      window.setTimeout(() => setCopied(null), 2000)
    } catch {
      setError('No pudimos copiar. Marcá el texto a mano.')
    }
  }

  async function handleCreateAlias(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    try {
      await setAlias.mutateAsync(draft.trim())
      setDraft('')
    } catch (caught) {
      setError(describeError(caught).message)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      {error ? <Alert tone="danger">{error}</Alert> : null}

      {/* Alias */}
      <section>
        <p className="label-caps text-ink-subtle">Tu alias</p>
        {alias.isLoading ? (
          <p className="mt-2 text-sm text-ink-muted">Cargando…</p>
        ) : value ? (
          <div className="mt-2 flex items-center justify-between gap-3 rounded-[var(--radius-control)] bg-surface-muted px-4 py-3">
            <span className="truncate text-base font-bold text-ink tabular">@{value}</span>
            <Button size="sm" variant="secondary" icon="check" onClick={() => void copy(value)}>
              {copied === value ? 'Copiado' : 'Copiar'}
            </Button>
          </div>
        ) : (
          <form className="mt-2 flex flex-col gap-3" onSubmit={handleCreateAlias}>
            <p className="text-[13px] leading-5 text-ink-muted">
              Todavía no tenés un alias. Crealo para que te transfieran sin buscar tu cuenta.
            </p>
            <Input
              label="Alias"
              placeholder="ana.presto"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
            />
            <div className="flex justify-end">
              <Button type="submit" loading={setAlias.isPending} disabled={!draft.trim()}>
                Crear alias
              </Button>
            </div>
          </form>
        )}
      </section>

      {/* Identificadores de las cuentas */}
      <section>
        <p className="label-caps text-ink-subtle">Identificadores de tus cuentas</p>
        <ul className="mt-2 space-y-2">
          {accounts.map((account) => (
            <li
              key={account.id}
              className="flex items-center justify-between gap-3 rounded-[var(--radius-control)] bg-surface-muted px-4 py-3"
            >
              <span className="min-w-0">
                <span className="block text-[11px] font-semibold uppercase tracking-wide text-ink-subtle">
                  {account.currency}
                </span>
                <span className="block truncate text-[13px] text-ink tabular">{account.id}</span>
              </span>
              <Button size="sm" variant="ghost" icon="check" onClick={() => void copy(account.id)}>
                {copied === account.id ? 'Copiado' : 'Copiar'}
              </Button>
            </li>
          ))}
        </ul>
      </section>

      <div className="flex justify-end border-t border-line pt-4">
        <Button variant="secondary" onClick={onDone}>
          Cerrar
        </Button>
      </div>
    </div>
  )
}
