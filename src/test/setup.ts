import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'

import { resetState } from './msw/handlers'
import { server } from './msw/server'

beforeAll(() => {
  server.listen({ onUnhandledFrame: 'error' })
})

afterEach(() => {
  cleanup()
  // `resetHandlers` y no `restoreHandlers`: en MSW 3.0.3 `restoreHandlers` no
  // saca los handlers agregados con `server.use` y el override de un test se
  // filtraba al siguiente.
  server.resetHandlers()
  resetState()
})

afterAll(() => {
  server.close()
})
