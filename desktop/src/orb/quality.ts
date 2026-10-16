export type QualityLevel = 'low' | 'medium' | 'high'

export type QualitySettings = {
  connectionDistance: number
  label: string
  linkRefreshMs: number
  maxConnections: number
  particles: number
  pixelRatio: number
  pointSize: number
}

export const QUALITY_PRESETS: Record<QualityLevel, QualitySettings> = {
  low: {
    connectionDistance: 0.35,
    label: 'Baixa',
    linkRefreshMs: 104,
    maxConnections: 320,
    particles: 1200,
    pixelRatio: 1,
    pointSize: 0.04,
  },
  medium: {
    connectionDistance: 0.3,
    label: 'Media',
    linkRefreshMs: 82,
    maxConnections: 600,
    particles: 2400,
    pixelRatio: 1.5,
    pointSize: 0.035,
  },
  high: {
    connectionDistance: 0.27,
    label: 'Alta',
    linkRefreshMs: 66,
    maxConnections: 900,
    particles: 3600,
    pixelRatio: 1.75,
    pointSize: 0.028,
  },
}
