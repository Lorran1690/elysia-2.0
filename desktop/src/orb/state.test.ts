import { describe, expect, it } from 'vitest'
import {
  interpolateVisualParameters,
  normalizeAudioLevel,
  reduceMotionParameters,
  targetParametersForState,
  transitionOrbState,
} from './state'

describe('orb visual state controller', () => {
  it('maps visual events without depending on the renderer', () => {
    expect(transitionOrbState('idle', { type: 'input-started' })).toBe('listening')
    expect(transitionOrbState('listening', { type: 'request-submitted' })).toBe('thinking')
    expect(transitionOrbState('thinking', { type: 'connection-started' })).toBe('connecting')
    expect(transitionOrbState('connecting', { type: 'response-started' })).toBe('speaking')
    expect(transitionOrbState('speaking', { type: 'response-completed' })).toBe('idle')
  })

  it('keeps the listening audio input normalized and state-local', () => {
    expect(normalizeAudioLevel(-2)).toBe(0)
    expect(normalizeAudioLevel(2)).toBe(1)
    expect(targetParametersForState('listening', 1).audioLevel).toBe(1)
    expect(targetParametersForState('thinking', 1).audioLevel).toBe(0)
  })

  it('settles listening toward a calmer surface when the signal falls away', () => {
    const quiet = targetParametersForState('listening', 0)
    const active = targetParametersForState('listening', 1)

    expect(active.surfaceRipple).toBeGreaterThan(quiet.surfaceRipple)
    expect(active.radialAmplitude).toBeGreaterThan(quiet.radialAmplitude)
    expect(active.luminance).toBeGreaterThan(quiet.luminance)
  })

  it('assigns visually distinct state targets', () => {
    const idle = targetParametersForState('idle')
    const listening = targetParametersForState('listening', 0.7)
    const thinking = targetParametersForState('thinking')
    const connecting = targetParametersForState('connecting')
    const speaking = targetParametersForState('speaking')

    expect(listening.surfaceRipple).toBeGreaterThan(idle.surfaceRipple)
    expect(thinking.flowIntensity).toBeGreaterThan(idle.flowIntensity)
    expect(connecting.networkVisibility).toBeGreaterThan(thinking.networkVisibility)
    expect(speaking.pulseIntensity).toBeGreaterThan(thinking.pulseIntensity)
  })

  it('interpolates state parameters without a discontinuity', () => {
    const idle = targetParametersForState('idle')
    const thinking = targetParametersForState('thinking')
    const result = interpolateVisualParameters(idle, thinking, 0.12)

    expect(result.flowIntensity).toBeGreaterThan(idle.flowIntensity)
    expect(result.flowIntensity).toBeLessThan(thinking.flowIntensity)
    expect(result.cavityStrength).toBeGreaterThan(idle.cavityStrength)
  })

  it('attenuates movement when reduced motion is requested', () => {
    const speaking = targetParametersForState('speaking')
    const reduced = reduceMotionParameters(speaking)

    expect(reduced.surfaceRipple).toBeLessThan(speaking.surfaceRipple)
    expect(reduced.radialAmplitude).toBeLessThan(speaking.radialAmplitude)
    expect(reduced.pulseIntensity).toBeLessThan(speaking.pulseIntensity)
  })
})
