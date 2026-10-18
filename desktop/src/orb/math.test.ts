import { describe, expect, it } from 'vitest'
import { clamp, sampleFlowField, seededUnit, smoothstep, smoothToward } from './math'

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

  it('eases values without depending on the frame rate', () => {
    expect(smoothToward(0, 1, 4, 0)).toBe(0)
    expect(smoothToward(0, 1, 4, 0.5)).toBeGreaterThan(0.8)
    expect(smoothToward(1, 0, 4, 0.5)).toBeLessThan(0.2)
  })

  it('samples a finite, normalized three-dimensional flow field', () => {
    const output = { x: 0, y: 0, z: 0 }

    sampleFlowField(0.3, -0.4, 0.8, 12.5, 2.1, output)

    expect(Number.isFinite(output.x)).toBe(true)
    expect(Number.isFinite(output.y)).toBe(true)
    expect(Number.isFinite(output.z)).toBe(true)
    expect(Math.hypot(output.x, output.y, output.z)).toBeCloseTo(1, 5)
  })
})
