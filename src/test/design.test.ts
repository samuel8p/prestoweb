import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * Verificaciones del sistema de diseño.
 *
 * No son visuales: comprueban el contrato escrito en `src/index.css` (la
 * paleta y el movimiento) para que un cambio futuro no rompa el contraste ni
 * la preferencia de movimiento reducido sin que nadie lo note.
 */
const css = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf-8')

function token(name: string): string {
  const match = new RegExp(`--color-${name}:\\s*(#[0-9a-fA-F]{6})`).exec(css)
  if (!match?.[1]) {
    throw new Error(`No está definido el token --color-${name}`)
  }
  return match[1]
}

function channel(value: number): number {
  const normalized = value / 255
  return normalized <= 0.03928 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4
}

function luminance(hex: string): number {
  const clean = hex.replace('#', '')
  const red = channel(parseInt(clean.slice(0, 2), 16))
  const green = channel(parseInt(clean.slice(2, 4), 16))
  const blue = channel(parseInt(clean.slice(4, 6), 16))
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue
}

/** Razón de contraste entre dos colores (1 a 21). */
function contrast(foreground: string, background: string): number {
  const a = luminance(foreground)
  const b = luminance(background)
  const lighter = Math.max(a, b)
  const darker = Math.min(a, b)
  return (lighter + 0.05) / (darker + 0.05)
}

describe('paleta', () => {
  it('el texto principal cumple AA sobre la arena y sobre las superficies', () => {
    expect(contrast(token('ink'), token('canvas'))).toBeGreaterThanOrEqual(4.5)
    expect(contrast(token('ink'), token('surface'))).toBeGreaterThanOrEqual(4.5)
  })

  it('el texto secundario y el sutil cumplen AA', () => {
    expect(contrast(token('ink-muted'), token('canvas'))).toBeGreaterThanOrEqual(4.5)
    expect(contrast(token('ink-muted'), token('surface'))).toBeGreaterThanOrEqual(4.5)
    expect(contrast(token('ink-subtle'), token('canvas'))).toBeGreaterThanOrEqual(4.5)
  })

  it('el azul de acción lleva texto blanco', () => {
    expect(contrast('#ffffff', token('primary'))).toBeGreaterThanOrEqual(4.5)
    expect(contrast('#ffffff', token('primary-hover'))).toBeGreaterThanOrEqual(4.5)
    expect(contrast('#ffffff', token('primary-deep'))).toBeGreaterThanOrEqual(4.5)
  })

  it('el azul de acción sirve como color de enlace sobre fondos claros', () => {
    expect(contrast(token('primary'), token('canvas'))).toBeGreaterThanOrEqual(4.5)
    expect(contrast(token('primary'), token('surface'))).toBeGreaterThanOrEqual(4.5)
  })

  it('el cromo oscuro lleva texto blanco', () => {
    expect(contrast('#ffffff', token('chrome'))).toBeGreaterThanOrEqual(4.5)
    expect(contrast('#ffffff', token('chrome-800'))).toBeGreaterThanOrEqual(4.5)
  })

  it('los acentos se leen solo sobre el fondo oscuro', () => {
    expect(contrast(token('aqua'), token('chrome'))).toBeGreaterThanOrEqual(4.5)
    expect(contrast(token('aqua'), token('chrome-800'))).toBeGreaterThanOrEqual(4.5)
    expect(contrast(token('turquoise'), token('chrome'))).toBeGreaterThanOrEqual(4.5)
    expect(contrast(token('turquoise'), token('chrome-800'))).toBeGreaterThanOrEqual(4.5)
  })

  it('el sol es decorativo: no se usa como texto ni como botón', () => {
    // Sobre el fondo claro no llega a 4.5: solo puede ser un detalle.
    expect(contrast(token('sun'), token('canvas'))).toBeLessThan(4.5)
    expect(contrast(token('sun'), token('chrome'))).toBeGreaterThanOrEqual(4.5)
  })

  it('los colores de estado cumplen AA sobre su fondo', () => {
    expect(contrast(token('success'), token('success-bg'))).toBeGreaterThanOrEqual(4.5)
    expect(contrast(token('danger'), token('danger-bg'))).toBeGreaterThanOrEqual(4.5)
    expect(contrast(token('warning'), token('warning-bg'))).toBeGreaterThanOrEqual(4.5)
  })

  it('el borde de los controles se distingue del fondo (3:1)', () => {
    expect(contrast(token('line-strong'), token('surface'))).toBeGreaterThanOrEqual(3)
    expect(contrast(token('line-strong'), token('canvas'))).toBeGreaterThanOrEqual(3)
  })

  it('el gradiente del saldo es el único gradiente de la app', () => {
    const gradients = css.match(/linear-gradient\([^)]*\)/g) ?? []
    const meaningful = gradients.filter((gradient) => !gradient.includes('90deg, transparent'))

    expect(meaningful.length).toBeLessThanOrEqual(1)
  })
})

describe('movimiento', () => {
  it('respeta prefers-reduced-motion', () => {
    expect(css).toContain('prefers-reduced-motion: reduce')
    expect(css).toMatch(/animation-duration:\s*0\.01ms\s*!important/)
    expect(css).toMatch(/transition-duration:\s*0\.01ms\s*!important/)
  })

  it('solo anima transform y opacity (nada de propiedades de layout)', () => {
    const section = css.slice(css.indexOf('@keyframes'), css.indexOf('@layer base'))
    const properties = Array.from(section.matchAll(/^\s{4}([a-z-]+):/gm)).map(
      (match: RegExpExecArray) => match[1] ?? '',
    )

    expect(properties.length).toBeGreaterThan(0)
    expect(properties.every((property) => ['opacity', 'transform'].includes(property))).toBe(true)
  })

  it('la fuente variable está autohospedada', () => {
    expect(css).toContain("@import '@fontsource-variable/manrope/wght.css'")
  })
})
