import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

import { Button } from './ui/Button'
import { Illustration } from './ui/Illustration'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  error: Error | null
}

/**
 * Cortafuegos de errores.
 *
 * Si una pantalla se rompe, la app muestra un mensaje y un botón para
 * reintentar en lugar de quedar en blanco. El error técnico también queda en
 * la consola del navegador.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  override state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Error de render en la aplicación:', error, info.componentStack)
  }

  handleReset = (): void => {
    this.setState({ error: null })
  }

  override render(): ReactNode {
    const { error } = this.state

    if (!error) {
      return this.props.children
    }

    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-12">
        <div className="w-full max-w-md rounded-[var(--radius-card)] border border-line bg-surface p-7 text-center shadow-raised">
          <div className="flex justify-center">
            <Illustration name="error" />
          </div>

          <h1 className="mt-4 text-lg font-bold text-ink">Algo salió mal</h1>
          <p className="mt-1.5 text-[13px] leading-5 text-ink-muted">
            La pantalla no se pudo mostrar. Podés reintentar; si sigue igual, recargá la página.
          </p>

          <pre className="mt-4 overflow-x-auto rounded-[var(--radius-control)] bg-surface-muted p-3 text-left text-[11px] leading-4 text-ink-muted">
            {error.message}
          </pre>

          <div className="mt-5 flex justify-center gap-2">
            <Button variant="secondary" onClick={this.handleReset}>
              Reintentar
            </Button>
            <Button onClick={() => window.location.reload()}>Recargar la página</Button>
          </div>
        </div>
      </div>
    )
  }
}
