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
  server.restoreHandlers()
  resetState()
})

afterAll(() => {
  server.close()
})
