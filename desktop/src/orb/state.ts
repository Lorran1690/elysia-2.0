import { clamp, smoothToward } from './math'

export const ORB_STATES = ['idle', 'listening', 'thinking', 'connecting', 'speaking'] as const

export type OrbState = (typeof ORB_STATES)[number]

export type OrbVisualParameters = {
  audioLevel: number
  cavityStrength: number
  cohesion: number
  connectionDensity: number
  flowIntensity: number
  luminance: number
  networkVisibility: number
  pulseIntensity: number
  radialAmplitude: number
  surfaceRipple: number
}

export type VisualEvent =
  | { type: 'demo-state-selected'; state: OrbState }
  | { type: 'input-started' }
  | { type: 'input-ended' }
  | { type: 'request-submitted' }
  | { type: 'connection-started' }
  | { type: 'response-started' }
  | { type: 'response-completed' }
  | { type: 'cancelled' }
  | { type: 'error' }

const STATE_TARGETS: Record<OrbState, Omit<OrbVisualParameters, 'audioLevel'>> = {
  idle: {
    cavityStrength: 1,
    cohesion: 1,
    connectionDensity: 0.84,
    flowIntensity: 1,
    luminance: 1,
    networkVisibility: 0.9,
    pulseIntensity: 0.24,
    radialAmplitude: 0.03,
    surfaceRipple: 0.1,
  },
  listening: {
    cavityStrength: 0.82,
    cohesion: 1.08,
    connectionDensity: 0.94,
    flowIntensity: 0.88,
    luminance: 1.08,
    networkVisibility: 1.08,
    pulseIntensity: 0.48,
    radialAmplitude: 0.11,
    surfaceRipple: 0.8,
  },
  thinking: {
    cavityStrength: 1.48,
    cohesion: 0.96,
    connectionDensity: 0.98,
    flowIntensity: 1.58,
    luminance: 1.16,
    networkVisibility: 1.24,
    pulseIntensity: 0.7,
    radialAmplitude: 0.1,
    surfaceRipple: 0.34,
  },
  connecting: {
    cavityStrength: 0.9,
    cohesion: 1.13,
    connectionDensity: 1,
    flowIntensity: 1.16,
    luminance: 1.18,
    networkVisibility: 1.34,
    pulseIntensity: 0.58,
    radialAmplitude: 0.07,
    surfaceRipple: 0.3,
  },
  speaking: {
    cavityStrength: 1.04,
    cohesion: 1.03,
    connectionDensity: 0.9,
    flowIntensity: 1.26,
    luminance: 1.2,
    networkVisibility: 1.06,
    pulseIntensity: 0.9,
    radialAmplitude: 0.16,
    surfaceRipple: 1.08,
  },
}

export const ORB_STATE_LABELS: Record<OrbState, string> = {
  idle: 'IDLE',
  listening: 'LISTENING',
  thinking: 'THINKING',
  connecting: 'CONNECTING',
  speaking: 'SPEAKING',
}

export const ORB_STATE_DESCRIPTIONS: Record<OrbState, string> = {
  idle: 'Fluxo interno calmo e volumetrico.',
  listening: 'Ondas reativas com entrada de sinal simulada.',
  thinking: 'Fluxos internos, cavidades e densidade em reorganizacao.',
  connecting: 'Rede local mais coesa, sem raios radiais.',
  speaking: 'Ondas de emissao e pulsos suaves de composicao.',
}

export function normalizeAudioLevel(value: number) {
  return Number.isFinite(value) ? clamp(value, 0, 1) : 0
}

export function targetParametersForState(state: OrbState, audioLevel = 0): OrbVisualParameters {
  const target = STATE_TARGETS[state]
  const normalizedAudio = state === 'listening' ? normalizeAudioLevel(audioLevel) : 0

  if (state === 'listening') {
    return {
      ...target,
      audioLevel: normalizedAudio,
      connectionDensity: 0.86 + normalizedAudio * 0.12,
      luminance: 1.01 + normalizedAudio * 0.29,
      networkVisibility: 0.94 + normalizedAudio * 0.22,
      pulseIntensity: 0.24 + normalizedAudio * 0.6,
      radialAmplitude: 0.035 + normalizedAudio * 0.15,
      surfaceRipple: 0.14 + normalizedAudio * 1.08,
    }
  }

  return {
    ...target,
    audioLevel: normalizedAudio,
    luminance: target.luminance + normalizedAudio * 0.22,
    pulseIntensity: target.pulseIntensity + normalizedAudio * 0.36,
    radialAmplitude: target.radialAmplitude + normalizedAudio * 0.07,
    surfaceRipple: target.surfaceRipple + normalizedAudio * 0.42,
  }
}

export function reduceMotionParameters(parameters: OrbVisualParameters): OrbVisualParameters {
  return {
    ...parameters,
    flowIntensity: Math.min(parameters.flowIntensity, 0.72),
    pulseIntensity: parameters.pulseIntensity * 0.28,
    radialAmplitude: parameters.radialAmplitude * 0.22,
    surfaceRipple: parameters.surfaceRipple * 0.2,
  }
}

export function interpolateVisualParameters(
  current: OrbVisualParameters,
  target: OrbVisualParameters,
  delta: number,
  response = 4.6,
): OrbVisualParameters {
  return {
    audioLevel: smoothToward(current.audioLevel, target.audioLevel, response * 1.5, delta),
    cavityStrength: smoothToward(current.cavityStrength, target.cavityStrength, response, delta),
    cohesion: smoothToward(current.cohesion, target.cohesion, response, delta),
    connectionDensity: smoothToward(current.connectionDensity, target.connectionDensity, response, delta),
    flowIntensity: smoothToward(current.flowIntensity, target.flowIntensity, response, delta),
    luminance: smoothToward(current.luminance, target.luminance, response, delta),
    networkVisibility: smoothToward(current.networkVisibility, target.networkVisibility, response, delta),
    pulseIntensity: smoothToward(current.pulseIntensity, target.pulseIntensity, response, delta),
    radialAmplitude: smoothToward(current.radialAmplitude, target.radialAmplitude, response, delta),
    surfaceRipple: smoothToward(current.surfaceRipple, target.surfaceRipple, response, delta),
  }
}

export function transitionOrbState(current: OrbState, event: VisualEvent): OrbState {
  switch (event.type) {
    case 'demo-state-selected':
      return event.state
    case 'input-started':
      return 'listening'
    case 'input-ended':
      return current === 'listening' ? 'idle' : current
    case 'request-submitted':
      return 'thinking'
    case 'connection-started':
      return 'connecting'
    case 'response-started':
      return 'speaking'
    case 'response-completed':
    case 'cancelled':
    case 'error':
      return 'idle'
  }
}
