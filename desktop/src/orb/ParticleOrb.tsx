import { useFrame } from '@react-three/fiber'
import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { clamp, seededUnit, smoothstep } from './math'
import type { QualitySettings } from './quality'

export type OrbMetrics = {
  connections: number
  fps: number
  particles: number
}

type ParticleField = {
  anchorIndices: number[]
  anchorPositionAttribute: THREE.BufferAttribute
  anchorPositions: Float32Array
  anchorsGeometry: THREE.BufferGeometry
  basePositions: Float32Array
  cells: Map<number, number>
  colorAttribute: THREE.BufferAttribute
  colors: Float32Array
  connectionColorAttribute: THREE.BufferAttribute
  connectionColors: Float32Array
  connectionPositionAttribute: THREE.BufferAttribute
  connectionPositions: Float32Array
  connectionsGeometry: THREE.BufferGeometry
  linkCount: number
  nextInCell: Int32Array
  phases: Float32Array
  pointPositionAttribute: THREE.BufferAttribute
  pointsGeometry: THREE.BufferGeometry
  positions: Float32Array
  sprite: THREE.Texture
  strengths: Float32Array
}

type ParticleOrbProps = {
  onMetrics: (metrics: OrbMetrics) => void
  quality: QualitySettings
}

const CELL_OFFSETS: Array<[number, number, number]> = []

for (let z = -1; z <= 1; z += 1) {
  for (let y = -1; y <= 1; y += 1) {
    for (let x = -1; x <= 1; x += 1) {
      CELL_OFFSETS.push([x, y, z])
    }
  }
}

function cellKey(x: number, y: number, z: number) {
  return (x * 73856093) ^ (y * 19349663) ^ (z * 83492791)
}

function createParticleSprite() {
  const canvas = document.createElement('canvas')
  canvas.width = 32
  canvas.height = 32
  const context = canvas.getContext('2d')

  if (!context) {
    throw new Error('Could not create the particle sprite')
  }

  const glow = context.createRadialGradient(16, 16, 0, 16, 16, 16)
  glow.addColorStop(0, 'rgba(255, 249, 221, 1)')
  glow.addColorStop(0.22, 'rgba(255, 207, 105, 0.95)')
  glow.addColorStop(0.58, 'rgba(243, 143, 37, 0.28)')
  glow.addColorStop(1, 'rgba(243, 143, 37, 0)')
  context.fillStyle = glow
  context.fillRect(0, 0, 32, 32)

  const sprite = new THREE.CanvasTexture(canvas)
  sprite.colorSpace = THREE.SRGBColorSpace
  return sprite
}

function createField(quality: QualitySettings): ParticleField {
  const { particles, maxConnections } = quality
  const basePositions = new Float32Array(particles * 3)
  const positions = new Float32Array(particles * 3)
  const colors = new Float32Array(particles * 3)
  const phases = new Float32Array(particles)
  const strengths = new Float32Array(particles)
  const anchorIndices: number[] = []

  for (let index = 0; index < particles; index += 1) {
    const phi = Math.acos(1 - 2 * seededUnit(index, 1))
    const theta = Math.PI * 2 * seededUnit(index, 2)
    const radius = 0.06 + Math.pow(seededUnit(index, 3), 1.1) * 1.44
    const sinPhi = Math.sin(phi)
    const offset = index * 3

    basePositions[offset] = radius * sinPhi * Math.cos(theta)
    basePositions[offset + 1] = radius * Math.cos(phi)
    basePositions[offset + 2] = radius * sinPhi * Math.sin(theta)
    positions[offset] = basePositions[offset]
    positions[offset + 1] = basePositions[offset + 1]
    positions[offset + 2] = basePositions[offset + 2]
    phases[index] = seededUnit(index, 4) * Math.PI * 2
    strengths[index] = 0.32 + seededUnit(index, 5) * 0.5 + (1 - Math.min(radius / 1.5, 1)) * 0.24

    if (radius < 0.72 && seededUnit(index, 6) > 0.995 && anchorIndices.length < 12) {
      anchorIndices.push(index)
    }
  }

  if (anchorIndices.length === 0) {
    anchorIndices.push(0)
  }

  const pointsGeometry = new THREE.BufferGeometry()
  const pointPositionAttribute = new THREE.BufferAttribute(positions, 3).setUsage(THREE.DynamicDrawUsage)
  const colorAttribute = new THREE.BufferAttribute(colors, 3).setUsage(THREE.DynamicDrawUsage)
  pointsGeometry.setAttribute('position', pointPositionAttribute)
  pointsGeometry.setAttribute('color', colorAttribute)

  const anchorsGeometry = new THREE.BufferGeometry()
  const anchorPositions = new Float32Array(anchorIndices.length * 3)
  const anchorPositionAttribute = new THREE.BufferAttribute(anchorPositions, 3).setUsage(THREE.DynamicDrawUsage)
  anchorsGeometry.setAttribute('position', anchorPositionAttribute)

  const connectionsGeometry = new THREE.BufferGeometry()
  const connectionPositions = new Float32Array(maxConnections * 6)
  const connectionColors = new Float32Array(maxConnections * 6)
  const connectionPositionAttribute = new THREE.BufferAttribute(connectionPositions, 3).setUsage(THREE.DynamicDrawUsage)
  const connectionColorAttribute = new THREE.BufferAttribute(connectionColors, 3).setUsage(THREE.DynamicDrawUsage)
  connectionsGeometry.setAttribute('position', connectionPositionAttribute)
  connectionsGeometry.setAttribute('color', connectionColorAttribute)
  connectionsGeometry.setDrawRange(0, 0)

  return {
    anchorIndices,
    anchorPositionAttribute,
    anchorPositions,
    anchorsGeometry,
    basePositions,
    cells: new Map(),
    colorAttribute,
    colors,
    connectionColorAttribute,
    connectionColors,
    connectionPositionAttribute,
    connectionPositions,
    connectionsGeometry,
    linkCount: 0,
    nextInCell: new Int32Array(particles),
    phases,
    pointPositionAttribute,
    pointsGeometry,
    positions,
    sprite: createParticleSprite(),
    strengths,
  }
}

function updateParticles(field: ParticleField, time: number) {
  const wave = Math.sin(time * 0.21)
  const ringBias = Math.pow(Math.max(0, wave), 3.6)
  const breath = 1 + Math.sin(time * 0.77) * 0.065
  const voidX = Math.sin(time * 0.34) * 0.42
  const voidY = Math.cos(time * 0.29) * 0.27
  const voidZ = Math.sin(time * 0.23 + 1.7) * 0.31
  let anchorCursor = 0

  for (let index = 0; index < field.strengths.length; index += 1) {
    const offset = index * 3
    const phase = field.phases[index]
    const strength = field.strengths[index]
    const radialDrift = 1 + Math.sin(time * 0.93 + phase) * (0.035 + strength * 0.055)
    const internalWave = Math.sin(time * 0.58 + phase * 2.1) * 0.095
    let x = field.basePositions[offset] * breath * radialDrift
    let y = field.basePositions[offset + 1] * breath * radialDrift
    let z = field.basePositions[offset + 2] * breath * radialDrift

    x += Math.sin(time * 0.71 + y * 3.4 + phase) * 0.11 + internalWave
    y += Math.cos(time * 0.65 + z * 4.1 + phase * 0.7) * 0.09
    z += Math.sin(time * 0.61 + x * 3.7 + phase * 1.3) * 0.12

    const voidDistance = Math.hypot(x - voidX, y - voidY, z - voidZ)
    const cavity = 1 - smoothstep(0.1, 0.5, voidDistance)
    if (cavity > 0) {
      x += (x - voidX) * cavity * 0.32
      y += (y - voidY) * cavity * 0.32
      z += (z - voidZ) * cavity * 0.32
    }

    x *= 1 + ringBias * 0.16
    y *= 1 - ringBias * 0.43
    z *= 1 - ringBias * 0.18

    field.positions[offset] = x
    field.positions[offset + 1] = y
    field.positions[offset + 2] = z

    const focalPulse = Math.max(0, Math.sin(time * 1.4 + phase * 2.7))
    const brightness = clamp(0.45 + strength * 0.42 + focalPulse * 0.16, 0, 1)
    field.colors[offset] = 0.55 + brightness * 0.45
    field.colors[offset + 1] = 0.14 + brightness * 0.63
    field.colors[offset + 2] = 0.008 + brightness * 0.11

    if (anchorCursor < field.anchorIndices.length && field.anchorIndices[anchorCursor] === index) {
      const anchorOffset = anchorCursor * 3
      field.anchorPositions[anchorOffset] = x
      field.anchorPositions[anchorOffset + 1] = y
      field.anchorPositions[anchorOffset + 2] = z
      anchorCursor += 1
    }
  }

  field.pointPositionAttribute.needsUpdate = true
  field.colorAttribute.needsUpdate = true
  field.anchorPositionAttribute.needsUpdate = true
}

function updateConnections(field: ParticleField, quality: QualitySettings) {
  const { connectionDistance, maxConnections } = quality
  const distanceSquared = connectionDistance * connectionDistance
  const cells = field.cells
  cells.clear()

  for (let index = 0; index < field.strengths.length; index += 1) {
    const offset = index * 3
    const key = cellKey(
      Math.floor(field.positions[offset] / connectionDistance),
      Math.floor(field.positions[offset + 1] / connectionDistance),
      Math.floor(field.positions[offset + 2] / connectionDistance),
    )
    field.nextInCell[index] = cells.get(key) ?? -1
    cells.set(key, index)
  }

  let links = 0

  outer: for (let index = 0; index < field.strengths.length; index += 1) {
    const offset = index * 3
    const cellX = Math.floor(field.positions[offset] / connectionDistance)
    const cellY = Math.floor(field.positions[offset + 1] / connectionDistance)
    const cellZ = Math.floor(field.positions[offset + 2] / connectionDistance)

    for (const [xOffset, yOffset, zOffset] of CELL_OFFSETS) {
      let candidate = cells.get(cellKey(cellX + xOffset, cellY + yOffset, cellZ + zOffset)) ?? -1

      while (candidate !== -1) {
        if (candidate > index) {
          const candidateOffset = candidate * 3
          const dx = field.positions[offset] - field.positions[candidateOffset]
          const dy = field.positions[offset + 1] - field.positions[candidateOffset + 1]
          const dz = field.positions[offset + 2] - field.positions[candidateOffset + 2]
          const squared = dx * dx + dy * dy + dz * dz

          if (squared < distanceSquared && squared > 0.0018) {
            const proximity = 1 - Math.sqrt(squared) / connectionDistance
            if (proximity < 0.16) {
              candidate = field.nextInCell[candidate]
              continue
            }
            const brightness = clamp(0.08 + proximity * 0.42 + (field.strengths[index] + field.strengths[candidate]) * 0.1, 0, 1)
            const writeOffset = links * 6
            const red = 0.3 + brightness * 0.62
            const green = 0.025 + brightness * 0.4
            const blue = 0.002 + brightness * 0.045

            field.connectionPositions[writeOffset] = field.positions[offset]
            field.connectionPositions[writeOffset + 1] = field.positions[offset + 1]
            field.connectionPositions[writeOffset + 2] = field.positions[offset + 2]
            field.connectionPositions[writeOffset + 3] = field.positions[candidateOffset]
            field.connectionPositions[writeOffset + 4] = field.positions[candidateOffset + 1]
            field.connectionPositions[writeOffset + 5] = field.positions[candidateOffset + 2]
            field.connectionColors[writeOffset] = red
            field.connectionColors[writeOffset + 1] = green
            field.connectionColors[writeOffset + 2] = blue
            field.connectionColors[writeOffset + 3] = red
            field.connectionColors[writeOffset + 4] = green
            field.connectionColors[writeOffset + 5] = blue

            links += 1
            if (links >= maxConnections) {
              break outer
            }
          }
        }

        candidate = field.nextInCell[candidate]
      }
    }
  }

  field.linkCount = links
  field.connectionsGeometry.setDrawRange(0, links * 2)
  field.connectionPositionAttribute.needsUpdate = true
  field.connectionColorAttribute.needsUpdate = true
}

export function ParticleOrb({ onMetrics, quality }: ParticleOrbProps) {
  const field = useMemo(() => createField(quality), [quality])
  const groupRef = useRef<THREE.Group>(null)
  const lastConnectionRefresh = useRef(Number.NEGATIVE_INFINITY)
  const metricsRef = useRef({ elapsed: 0, frames: 0 })
  const onMetricsRef = useRef(onMetrics)

  useEffect(() => {
    onMetricsRef.current = onMetrics
  }, [onMetrics])

  useEffect(() => () => field.sprite.dispose(), [field])

  useFrame((state, delta) => {
    const time = state.clock.elapsedTime
    updateParticles(field, time)

    if (time * 1000 - lastConnectionRefresh.current >= quality.linkRefreshMs) {
      updateConnections(field, quality)
      lastConnectionRefresh.current = time * 1000
    }

    if (groupRef.current) {
      groupRef.current.rotation.y = time * 0.14 + Math.sin(time * 0.22) * 0.11
      groupRef.current.rotation.x = Math.sin(time * 0.17) * 0.09
      groupRef.current.rotation.z = Math.cos(time * 0.19) * 0.035
    }

    metricsRef.current.elapsed += delta
    metricsRef.current.frames += 1
    if (metricsRef.current.elapsed >= 0.6) {
      onMetricsRef.current({
        connections: field.linkCount,
        fps: Math.round(metricsRef.current.frames / metricsRef.current.elapsed),
        particles: quality.particles,
      })
      metricsRef.current.elapsed = 0
      metricsRef.current.frames = 0
    }
  })

  return (
    <group ref={groupRef}>
      <lineSegments geometry={field.connectionsGeometry} frustumCulled={false}>
        <lineBasicMaterial
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          opacity={0.16}
          transparent
          vertexColors
        />
      </lineSegments>
      <points geometry={field.pointsGeometry} frustumCulled={false}>
        <pointsMaterial
          blending={THREE.AdditiveBlending}
          color="#cc751c"
          depthWrite={false}
          map={field.sprite}
          opacity={0.14}
          size={quality.pointSize * 4.2}
          sizeAttenuation
          transparent
          vertexColors
        />
      </points>
      <points geometry={field.pointsGeometry} frustumCulled={false}>
        <pointsMaterial
          blending={THREE.AdditiveBlending}
          color="#fff5d4"
          depthWrite={false}
          map={field.sprite}
          opacity={0.96}
          size={quality.pointSize}
          sizeAttenuation
          transparent
          vertexColors
        />
      </points>
      <points geometry={field.anchorsGeometry} frustumCulled={false}>
        <pointsMaterial
          blending={THREE.AdditiveBlending}
          color="#ffbd57"
          depthWrite={false}
          opacity={0.85}
          map={field.sprite}
          size={quality.pointSize * 2.2}
          sizeAttenuation
          transparent
        />
      </points>
    </group>
  )
}
