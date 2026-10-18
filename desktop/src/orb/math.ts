export function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(Math.max(value, minimum), maximum)
}

export function smoothstep(edge0: number, edge1: number, value: number) {
  const progress = clamp((value - edge0) / (edge1 - edge0), 0, 1)
  return progress * progress * (3 - 2 * progress)
}

export type MutableVector3 = {
  x: number
  y: number
  z: number
}

export function seededUnit(index: number, salt: number) {
  const value = Math.sin(index * 12.9898 + salt * 78.233) * 43758.5453
  return value - Math.floor(value)
}

export function smoothToward(current: number, target: number, response: number, delta: number) {
  const blend = 1 - Math.exp(-Math.max(0, response) * Math.max(0, delta))
  return current + (target - current) * blend
}

export function sampleFlowField(x: number, y: number, z: number, time: number, phase: number, output: MutableVector3) {
  const drift = time * 0.16 + phase * 0.27
  const a = y * 1.86 + Math.sin(z * 1.17 + drift * 0.71)
  const b = z * 1.52 + Math.cos(x * 1.41 - drift * 0.57)
  const c = x * 1.68 + Math.sin(y * 1.27 + drift * 0.63)

  output.x = Math.cos(a) * 0.82 - Math.sin(b) * 0.48 + Math.cos(c) * 0.22
  output.y = Math.cos(b) * 0.76 - Math.sin(c) * 0.52 + Math.cos(a) * 0.2
  output.z = Math.cos(c) * 0.8 - Math.sin(a) * 0.46 + Math.cos(b) * 0.24

  const magnitude = Math.hypot(output.x, output.y, output.z)
  if (magnitude > 0.0001) {
    const scale = 1 / magnitude
    output.x *= scale
    output.y *= scale
    output.z *= scale
  }
}
