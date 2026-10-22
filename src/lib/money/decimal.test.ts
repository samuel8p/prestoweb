import { describe, expect, it } from 'vitest'

import { compareDecimals, percentOf } from './decimal'

describe('compareDecimals', () => {
  it('compara importes sin convertirlos a número', () => {
    expect(compareDecimals('1500.50', '1500.5')).toBe(0)
    expect(compareDecimals('1500.51', '1500.50')).toBe(1)
    expect(compareDecimals('1500.49', '1500.50')).toBe(-1)
    expect(compareDecimals('0.00', '0')).toBe(0)
  })

  it('ordena los importes negativos', () => {
    expect(compareDecimals('-10.00', '-2.00')).toBe(-1)
    expect(compareDecimals('-2.00', '-10.00')).toBe(1)
    expect(compareDecimals('-10.00', '-10.00')).toBe(0)
  })

  it('no pierde precisión con importes grandes', () => {
    expect(compareDecimals('9007199254740993.01', '9007199254740993.02')).toBe(-1)
    expect(compareDecimals('9007199254740993.02', '9007199254740993.01')).toBe(1)
  })

  it('rechaza importes que no son decimales válidos', () => {
    expect(() => compareDecimals('abc', '1.00')).toThrow(/importe/i)
    expect(() => compareDecimals('1.00', '')).toThrow(/importe/i)
    expect(() => compareDecimals('1.234', '1.00')).toThrow(/importe/i)
  })
})

describe('percentOf', () => {
  it('calcula el porcentaje redondeado', () => {
    expect(percentOf('30.00', '120.00')).toBe(25)
    expect(percentOf('30.00', '120.50')).toBe(25)
    expect(percentOf('1.00', '3.00')).toBe(33)
  })

  it('devuelve 0 cuando no se gastó nada', () => {
    expect(percentOf('0.00', '100.00')).toBe(0)
  })

  it('admite que se pase del límite', () => {
    expect(percentOf('150.00', '100.00')).toBe(150)
  })

  it('devuelve 0 si el límite es cero', () => {
    expect(percentOf('10.00', '0.00')).toBe(0)
  })
})
