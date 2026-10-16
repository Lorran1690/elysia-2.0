import { describe, expect, it } from 'vitest'
import { clamp, seededUnit, smoothstep } from './math'

describe('orb math', () => {
  it('clamps values to the requested interval', () => {
    expect(clamp(-1, 0, 1)).toBe(0)
    expect(clamp(0.4, 0, 1)).toBe(0.4)
    expect(clamp(2, 0, 1)).toBe(1)
  })

  it('uses smooth interpolation at its boundaries', () => {
    expect(smoothstep(0, 1, 0)).toBe(0)
    expect(smoothstep(0, 1, 1)).toBe(1)
    expect(smoothstep(0, 1, 0.5)).toBe(0.5)
  })

  it('keeps the particle seed deterministic and normalized', () => {
    const seed = seededUnit(42, 7)
    expect(seededUnit(42, 7)).toBe(seed)
    expect(seed).toBeGreaterThanOrEqual(0)
    expect(seed).toBeLessThan(1)
  })
})
