import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('App', () => {
  it('renderiza el nombre de la aplicación', () => {
    render(<App />)

    expect(screen.getByText('Presto')).toBeInTheDocument()
  })
})
