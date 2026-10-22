import { describe, expect, it } from 'vitest'

import { formatDate, formatDateTime, formatMoney, formatRate } from './format'

describe('formatMoney', () => {
  it('formatea el importe con separador de miles y la moneda', () => {
    expect(formatMoney('1500.50', 'ARS')).toBe('ARS 1.500,50')
    expect(formatMoney('123456789.99', 'USD')).toBe('USD 123.456.789,99')
  })

  it('completa los decimales que faltan', () => {
    expect(formatMoney('1500.5', 'ARS')).toBe('ARS 1.500,50')
    expect(formatMoney('0', 'ARS')).toBe('ARS 0,00')
  })

  it('mantiene el signo de los importes negativos', () => {
    expect(formatMoney('-12.00', 'USD')).toBe('USD -12,00')
  })

  it('no convierte el importe a número', () => {
    // Con Number, 0.1 + 0.2 no da 0.3: acá la comparación es de strings.
    expect(formatMoney('9007199254740993.01', 'ARS')).toBe('ARS 9.007.199.254.740.993,01')
  })

  it('devuelve un guion si el importe no es válido', () => {
    expect(formatMoney('nope', 'ARS')).toBe('—')
  })
})

describe('formatRate', () => {
  it('muestra la tasa anual con dos decimales', () => {
    expect(formatRate('24.00')).toBe('24,00%')
    expect(formatRate('7.5')).toBe('7,50%')
  })

  it('devuelve un guion si la tasa no es válida', () => {
    expect(formatRate('abc')).toBe('—')
  })
})

describe('formatDate y formatDateTime', () => {
  it('formatea la fecha en formato local', () => {
    expect(formatDate('2026-10-22')).toBe('22/10/2026')
  })

  it('formatea la fecha y hora en UTC', () => {
    expect(formatDateTime('2026-10-22T03:23:23.573828Z')).toBe('22/10/2026, 03:23 UTC')
  })

  it('devuelve un guion si la fecha no es válida', () => {
    expect(formatDate('no-es-fecha')).toBe('—')
  })
})
