import { describe, expect, it } from 'vitest'

import { cursorFromUrl } from './pagination'
import { defaultReportRange, monthEndIso, monthStartIso, monthsAgoIso, todayIso } from '../dates'
import { createIdempotencyKey } from '../idempotency'

describe('cursorFromUrl', () => {
  it('saca el cursor de la URL de la página siguiente', () => {
    expect(cursorFromUrl('http://api.test/api/v1/ledger/transactions/?cursor=abc123')).toBe(
      'abc123',
    )
  })

  it('devuelve undefined cuando no hay página siguiente', () => {
    expect(cursorFromUrl(null)).toBeUndefined()
    expect(cursorFromUrl(undefined)).toBeUndefined()
    expect(cursorFromUrl('http://api.test/api/v1/ledger/transactions/')).toBeUndefined()
  })
})

describe('fechas', () => {
  it('devuelve el primer y el último día del mes actual', () => {
    expect(monthStartIso()).toMatch(/^\d{4}-\d{2}-01$/)
    expect(monthEndIso()).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('devuelve el primer día del mes de hace 11 meses', () => {
    expect(monthsAgoIso(11)).toMatch(/^\d{4}-\d{2}-01$/)
  })

  it('arma el rango por defecto con 12 meses', () => {
    const range = defaultReportRange()

    expect(range.from).toMatch(/^\d{4}-\d{2}-01$/)
    expect(range.to).toBe(todayIso())
  })
})

describe('createIdempotencyKey', () => {
  it('genera una clave distinta cada vez', () => {
    const first = createIdempotencyKey()
    const second = createIdempotencyKey()

    expect(first).not.toBe(second)
    expect(first.length).toBeGreaterThanOrEqual(32)
  })
})
