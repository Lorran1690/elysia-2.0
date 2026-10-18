import { useFrame } from '@react-three/fiber'
import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { clamp, sampleFlowField, seededUnit, smoothstep, smoothToward, type MutableVector3 } from './math'
import type { QualitySettings } from './quality'

export type OrbMetrics = {
  connections: number
  fps: number
  particles: number
}

type ConnectionEdge = {
  from: number
  key: number
  luminosity: number
  opacity: number
  targetOpacity: number
  to: number
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
  degrees: Uint8Array
  edgeByKey: Map<number, ConnectionEdge>
  edges: ConnectionEdge[]
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

function edgeKey(first: number, second: number, particleCount: number) {
  return first < second ? first * particleCount + second : second * particleCount + first
}

function createParticleSprite() {
  const canvas = document.createElement('canvas')
  canvas.width = 48
  canvas.height = 48
  const context = canvas.getContext('2d')

  if (!context) {
    throw new Error('Could not create the particle sprite')
  }

  const glow = context.createRadialGradient(24, 24, 0, 24, 24, 24)
  glow.addColorStop(0, 'rgba(255, 246, 214, 0.92)')
  glow.addColorStop(0.18, 'rgba(255, 199, 92, 0.74)')
  glow.addColorStop(0.5, 'rgba(239, 137, 34, 0.16)')
  glow.addColorStop(1, 'rgba(239, 137, 34, 0)')
  context.fillStyle = glow
  context.fillRect(0, 0, 48, 48)

  const sprite = new THREE.CanvasTexture(canvas)
  sprite.colorSpace = THREE.SRGBColorSpace
  return sprite
}

function createField(quality: QualitySettings): ParticleField {
  const { particles, maxConnections } = quality
  const connectionCapacity = maxConnections
  const basePositions = new Float32Array(particles * 3)
  const positions = new Float32Array(particles * 3)
  const colors = new Float32Array(particles * 3)
  const phases = new Float32Array(particles)
  const strengths = new Float32Array(particles)
  const anchorIndices: number[] = []

  for (let index = 0; index < particles; index += 1) {
    const phi = Math.acos(1 - 2 * seededUnit(index, 1))
    const theta = Math.PI * 2 * seededUnit(index, 2)
    const radialSeed = seededUnit(index, 3)
    const radius = Math.cbrt(radialSeed) * (1.05 + seededUnit(index, 4) * 0.28)
    const sinPhi = Math.sin(phi)
    const offset = index * 3
    const strength = 0.25 + seededUnit(index, 5) * 0.58 + (1 - radius / 1.34) * 0.17

    basePositions[offset] = radius * sinPhi * Math.cos(theta)
    basePositions[offset + 1] = radius * Math.cos(phi)
    basePositions[offset + 2] = radius * sinPhi * Math.sin(theta)
    positions[offset] = basePositions[offset]
    positions[offset + 1] = basePositions[offset + 1]
    positions[offset + 2] = basePositions[offset + 2]
    phases[index] = seededUnit(index, 6) * Math.PI * 2
    strengths[index] = strength

    if (seededUnit(index, 7) > 0.9982 && anchorIndices.length < 5) {
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
  const connectionPositions = new Float32Array(connectionCapacity * 6)
  const connectionColors = new Float32Array(connectionCapacity * 6)
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
    degrees: new Uint8Array(particles),
    edgeByKey: new Map(),
    edges: Array.from({ length: connectionCapacity }, () => ({
      from: -1,
      key: -1,
      luminosity: 0,
      opacity: 0,
      targetOpacity: 0,
      to: -1,
    })),
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

function disposeField(field: ParticleField) {
  field.pointsGeometry.dispose()
  field.anchorsGeometry.dispose()
  field.connectionsGeometry.dispose()
  field.sprite.dispose()
}

function updateParticles(field: ParticleField, time: number) {
  const breath = 1 + Math.sin(time * 0.61) * 0.028 + Math.sin(time * 0.17 + 0.9) * 0.022
  const cavityAX = Math.sin(time * 0.23) * 0.44
  const cavityAY = Math.cos(time * 0.19 + 0.4) * 0.31
  const cavityAZ = Math.sin(time * 0.16 + 1.5) * 0.35
  const cavityBX = Math.cos(time * 0.13 + 2.2) * 0.34
  const cavityBY = Math.sin(time * 0.21 + 0.7) * 0.39
  const cavityBZ = Math.cos(time * 0.18) * 0.28
  const nodeAX = Math.sin(time * 0.17 + 0.6) * 0.48
  const nodeAY = Math.cos(time * 0.2) * 0.29
  const nodeAZ = Math.cos(time * 0.14 + 0.9) * 0.43
  const nodeBX = Math.cos(time * 0.12 + 2.1) * 0.4
  const nodeBY = Math.sin(time * 0.16 + 1.1) * 0.37
  const nodeBZ = Math.sin(time * 0.2 + 2.5) * 0.34
  const flow: MutableVector3 = { x: 0, y: 0, z: 0 }
  let anchorCursor = 0

  for (let index = 0; index < field.strengths.length; index += 1) {
    const offset = index * 3
    const phase = field.phases[index]
    const strength = field.strengths[index]
    const baseX = field.basePositions[offset]
    const baseY = field.basePositions[offset + 1]
    const baseZ = field.basePositions[offset + 2]
    const lobe = Math.sin(baseX * 2.2 + baseZ * 1.7 + time * 0.19) * 0.062
      + Math.cos(baseY * 2.6 - baseX * 1.15 - time * 0.13) * 0.052
    const shellScale = breath * (1 + lobe + Math.sin(phase + time * 0.31) * 0.026)
    let x = baseX * shellScale
    let y = baseY * shellScale
    let z = baseZ * shellScale

    sampleFlowField(x * 0.84, y * 0.84, z * 0.84, time, phase, flow)
    const flowStrength = 0.035 + strength * 0.071
    x += flow.x * flowStrength
    y += flow.y * flowStrength
    z += flow.z * flowStrength

    const cavityADistance = Math.hypot(x - cavityAX, y - cavityAY, z - cavityAZ)
    const cavityBDistance = Math.hypot(x - cavityBX, y - cavityBY, z - cavityBZ)
    const cavityA = 1 - smoothstep(0.1, 0.56, cavityADistance)
    const cavityB = 1 - smoothstep(0.12, 0.48, cavityBDistance)
    const cavity = Math.max(cavityA, cavityB)

    if (cavityA > 0) {
      x += (x - cavityAX) * cavityA * 0.25
      y += (y - cavityAY) * cavityA * 0.25
      z += (z - cavityAZ) * cavityA * 0.25
    }

    if (cavityB > 0) {
      x += (x - cavityBX) * cavityB * 0.19
      y += (y - cavityBY) * cavityB * 0.19
      z += (z - cavityBZ) * cavityB * 0.19
    }

    const nodeA = 1 - smoothstep(0.16, 0.78, Math.hypot(x - nodeAX, y - nodeAY, z - nodeAZ))
    const nodeB = 1 - smoothstep(0.13, 0.7, Math.hypot(x - nodeBX, y - nodeBY, z - nodeBZ))
    const density = Math.max(nodeA, nodeB)

    if (nodeA > 0) {
      x += (nodeAX - x) * nodeA * 0.045
      y += (nodeAY - y) * nodeA * 0.045
      z += (nodeAZ - z) * nodeA * 0.045
    }

    if (nodeB > 0) {
      x += (nodeBX - x) * nodeB * 0.037
      y += (nodeBY - y) * nodeB * 0.037
      z += (nodeBZ - z) * nodeB * 0.037
    }

    field.positions[offset] = x
    field.positions[offset + 1] = y
    field.positions[offset + 2] = z

    const localPulse = Math.max(0, Math.sin(time * 0.74 + phase * 1.8 + baseY * 1.5))
    const brightness = clamp(0.2 + strength * 0.34 + density * 0.23 + localPulse * 0.12 - cavity * 0.09, 0, 1)
    field.colors[offset] = 0.52 + brightness * 0.42
    field.colors[offset + 1] = 0.13 + brightness * 0.55
    field.colors[offset + 2] = 0.008 + brightness * 0.08

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

function reserveEdge(field: ParticleField, key: number) {
  for (const edge of field.edges) {
    if (edge.from === -1) {
      edge.key = key
      field.edgeByKey.set(key, edge)
      return edge
    }
  }

  for (const edge of field.edges) {
    if (edge.targetOpacity === 0 && edge.opacity < 0.025) {
      field.edgeByKey.delete(edge.key)
      edge.key = key
      edge.opacity = 0
      field.edgeByKey.set(key, edge)
      return edge
    }
  }

  return null
}

function refreshConnectionTargets(field: ParticleField, quality: QualitySettings, time: number) {
  const { connectionDistance, maxConnections, maxLinksPerParticle } = quality
  const distanceSquared = connectionDistance * connectionDistance
  const cells = field.cells
  const degrees = field.degrees
  const particleCount = field.strengths.length
  cells.clear()
  degrees.fill(0)

  for (const edge of field.edges) {
    edge.targetOpacity = 0
  }

  for (let index = 0; index < particleCount; index += 1) {
    const offset = index * 3
    const key = cellKey(
      Math.floor(field.positions[offset] / connectionDistance),
      Math.floor(field.positions[offset + 1] / connectionDistance),
      Math.floor(field.positions[offset + 2] / connectionDistance),
    )
    field.nextInCell[index] = cells.get(key) ?? -1
    cells.set(key, index)
  }

  let desired = 0
  const start = Math.floor(time * 37) % particleCount

  outer: for (let step = 0; step < particleCount; step += 1) {
    const index = (start + step) % particleCount
    if (degrees[index] >= maxLinksPerParticle) {
      continue
    }

    const offset = index * 3
    const cellX = Math.floor(field.positions[offset] / connectionDistance)
    const cellY = Math.floor(field.positions[offset + 1] / connectionDistance)
    const cellZ = Math.floor(field.positions[offset + 2] / connectionDistance)

    for (const [xOffset, yOffset, zOffset] of CELL_OFFSETS) {
      let candidate = cells.get(cellKey(cellX + xOffset, cellY + yOffset, cellZ + zOffset)) ?? -1

      while (candidate !== -1) {
        if (candidate > index && degrees[candidate] < maxLinksPerParticle) {
          const candidateOffset = candidate * 3
          const dx = field.positions[offset] - field.positions[candidateOffset]
          const dy = field.positions[offset + 1] - field.positions[candidateOffset + 1]
          const dz = field.positions[offset + 2] - field.positions[candidateOffset + 2]
          const squared = dx * dx + dy * dy + dz * dz

          if (squared < distanceSquared && squared > 0.0024) {
            const proximity = 1 - Math.sqrt(squared) / connectionDistance
            const cadence = 0.5 + Math.sin(time * 0.61 + field.phases[index] + field.phases[candidate]) * 0.5
            if (proximity > 0.2 && cadence > 0.08) {
              const key = edgeKey(index, candidate, particleCount)
              const edge = field.edgeByKey.get(key) ?? reserveEdge(field, key)

              if (edge) {
                edge.from = index
                edge.to = candidate
                edge.targetOpacity = 0.05 + proximity * 0.24 + cadence * 0.035
                edge.luminosity = 0.52 + (field.strengths[index] + field.strengths[candidate]) * 0.24
                degrees[index] += 1
                degrees[candidate] += 1
                desired += 1

                if (desired >= maxConnections) {
                  break outer
                }
              }
            }
          }
        }

        candidate = field.nextInCell[candidate]
      }
    }
  }
}

function updateConnectionGeometry(field: ParticleField, quality: QualitySettings, delta: number) {
  let links = 0

  for (const edge of field.edges) {
    if (edge.from === -1) {
      continue
    }

    edge.opacity = smoothToward(edge.opacity, edge.targetOpacity, quality.connectionFade, delta)
    if (edge.targetOpacity === 0 && edge.opacity < 0.012) {
      field.edgeByKey.delete(edge.key)
      edge.from = -1
      edge.to = -1
      edge.key = -1
      edge.luminosity = 0
      edge.opacity = 0
      continue
    }

    if (edge.opacity < 0.008) {
      continue
    }

    const fromOffset = edge.from * 3
    const toOffset = edge.to * 3
    const writeOffset = links * 6
    const brightness = clamp(edge.opacity * edge.luminosity, 0, 1)
    const red = 0.18 + brightness * 0.69
    const green = 0.025 + brightness * 0.39
    const blue = 0.002 + brightness * 0.04

    field.connectionPositions[writeOffset] = field.positions[fromOffset]
    field.connectionPositions[writeOffset + 1] = field.positions[fromOffset + 1]
    field.connectionPositions[writeOffset + 2] = field.positions[fromOffset + 2]
    field.connectionPositions[writeOffset + 3] = field.positions[toOffset]
    field.connectionPositions[writeOffset + 4] = field.positions[toOffset + 1]
    field.connectionPositions[writeOffset + 5] = field.positions[toOffset + 2]
    field.connectionColors[writeOffset] = red
    field.connectionColors[writeOffset + 1] = green
    field.connectionColors[writeOffset + 2] = blue
    field.connectionColors[writeOffset + 3] = red
    field.connectionColors[writeOffset + 4] = green
    field.connectionColors[writeOffset + 5] = blue
    links += 1
  }

  field.linkCount = links
  field.connectionsGeometry.setDrawRange(0, links * 2)
  field.connectionPositionAttribute.needsUpdate = true
  field.connectionColorAttribute.needsUpdate = true
}

export function ParticleOrb({ onMetrics, quality }: ParticleOrbProps) {
  const field = useMemo(() => createField(quality), [quality])
  const lastConnectionRefresh = useRef(Number.NEGATIVE_INFINITY)
  const lifecycleRef = useRef<{ activeField: ParticleField; mounted: boolean } | null>(null)
  const metricsRef = useRef({ elapsed: 0, frames: 0 })
  const onMetricsRef = useRef(onMetrics)

  useEffect(() => {
    onMetricsRef.current = onMetrics
  }, [onMetrics])

  useEffect(() => {
    const lifecycle = lifecycleRef.current ?? { activeField: field, mounted: false }
    lifecycleRef.current = lifecycle
    lifecycle.activeField = field
    lifecycle.mounted = true

    return () => {
      lifecycle.mounted = false
      const retiringField = field

      // React's development replay remounts the same field before this frame runs.
      requestAnimationFrame(() => {
        if (!lifecycle.mounted || lifecycle.activeField !== retiringField) {
          disposeField(retiringField)
        }
      })
    }
  }, [field])

  useFrame((state, delta) => {
    const time = state.clock.elapsedTime
    updateParticles(field, time)

    if (time * 1000 - lastConnectionRefresh.current >= quality.linkRefreshMs) {
      refreshConnectionTargets(field, quality, time)
      lastConnectionRefresh.current = time * 1000
    }

    updateConnectionGeometry(field, quality, delta)

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
    <group>
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
          depthWrite={false}
          map={field.sprite}
          opacity={0.22}
          size={quality.pointSize * 5.2}
          sizeAttenuation
          transparent
          vertexColors
        />
      </points>
      <points geometry={field.pointsGeometry} frustumCulled={false}>
        <pointsMaterial
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          map={field.sprite}
          opacity={0.93}
          size={quality.pointSize * 1.1}
          sizeAttenuation
          transparent
          vertexColors
        />
      </points>
      <points geometry={field.anchorsGeometry} frustumCulled={false}>
        <pointsMaterial
          blending={THREE.AdditiveBlending}
          color="#f2a33e"
          depthWrite={false}
          map={field.sprite}
          opacity={0.12}
          size={quality.pointSize}
          sizeAttenuation
          transparent
        />
      </points>
    </group>
  )
}
