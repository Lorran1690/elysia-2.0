export type QualityLevel = 'low' | 'medium' | 'high'

export type QualitySettings = {
  connectionDistance: number
  connectionFade: number
  label: string
  linkRefreshMs: number
  maxConnections: number
  maxLinksPerParticle: number
  particles: number
  pixelRatio: number
  pointSize: number
}

export const QUALITY_PRESETS: Record<QualityLevel, QualitySettings> = {
  low: {
    connectionDistance: 0.36,
    connectionFade: 3.4,
    label: 'Baixa',
    linkRefreshMs: 108,
    maxConnections: 90,
    maxLinksPerParticle: 2,
    particles: 900,
    pixelRatio: 1,
    pointSize: 0.046,
  },
  medium: {
    connectionDistance: 0.32,
    connectionFade: 4,
    label: 'Media',
    linkRefreshMs: 88,
    maxConnections: 160,
    maxLinksPerParticle: 2,
    particles: 1600,
    pixelRatio: 1.25,
    pointSize: 0.042,
  },
  high: {
    connectionDistance: 0.29,
    connectionFade: 4.6,
    label: 'Alta',
    linkRefreshMs: 72,
    maxConnections: 240,
    maxLinksPerParticle: 2,
    particles: 2400,
    pixelRatio: 1.4,
    pointSize: 0.039,
  },
}
