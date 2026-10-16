import { Canvas } from '@react-three/fiber'
import { Activity, Cpu, Info, Settings2, Sparkles } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { OrbMetrics } from './orb/ParticleOrb'
import { ParticleOrb } from './orb/ParticleOrb'
import { QUALITY_PRESETS, type QualityLevel } from './orb/quality'
import './App.css'

const INITIAL_METRICS: OrbMetrics = {
  connections: 0,
  fps: 0,
  particles: QUALITY_PRESETS.high.particles,
}

function App() {
  const [quality, setQuality] = useState<QualityLevel>('high')
  const [metrics, setMetrics] = useState<OrbMetrics>(INITIAL_METRICS)
  const [panelOpen, setPanelOpen] = useState(() => window.innerWidth > 760)
  const settings = QUALITY_PRESETS[quality]

  const rendererOptions = useMemo(
    () => ({
      alpha: false,
      antialias: true,
      powerPreference: 'high-performance' as const,
    }),
    [],
  )

  return (
    <main className="desktop-shell">
      <header className="topbar">
        <div className="brand" aria-label="E.L.Y.S.I.A. Desktop">
          <span className="brand-mark" aria-hidden="true">
            E
          </span>
          <div>
            <strong>E.L.Y.S.I.A.</strong>
            <span>DESKTOP / ORB CORE</span>
          </div>
        </div>

        <div className="topbar-status" aria-label="Nucleo em repouso">
          <span className="status-dot" aria-hidden="true" />
          <span>IDLE</span>
        </div>

        <button
          className="icon-button"
          type="button"
          aria-label={panelOpen ? 'Ocultar controles de qualidade' : 'Mostrar controles de qualidade'}
          title={panelOpen ? 'Ocultar controles de qualidade' : 'Mostrar controles de qualidade'}
          onClick={() => setPanelOpen((open) => !open)}
        >
          <Settings2 size={18} strokeWidth={1.6} />
        </button>
      </header>

      <section className="orb-stage" aria-label="Previa do orbe de particulas em repouso">
        <Canvas
          className="orb-canvas"
          camera={{ fov: 43, position: [0, 0, 4.2] }}
          dpr={[1, settings.pixelRatio]}
          gl={rendererOptions}
        >
          <color attach="background" args={['#0a111a']} />
          <ParticleOrb quality={settings} onMetrics={setMetrics} />
        </Canvas>

        <div className="stage-heading" aria-hidden="true">
          <span>NEURAL ORBIT</span>
          <strong>E.L.Y.S.I.A.</strong>
        </div>

        <div className="stage-mode" aria-hidden="true">
          <span className="stage-mode-dot" />
          IDLE / FLUXO ORGANICO
        </div>

        <aside className={`inspector${panelOpen ? ' inspector-open' : ''}`} aria-label="Controles do orbe">
          <div className="inspector-heading">
            <span>PREVIEW 0.1</span>
            <Info size={14} strokeWidth={1.6} aria-hidden="true" />
          </div>

          <label className="quality-control">
            <span>QUALIDADE</span>
            <select value={quality} onChange={(event) => setQuality(event.target.value as QualityLevel)}>
              {(Object.keys(QUALITY_PRESETS) as QualityLevel[]).map((level) => (
                <option key={level} value={level}>
                  {QUALITY_PRESETS[level].label}
                </option>
              ))}
            </select>
          </label>

          <dl className="metrics-list">
            <div>
              <dt>
                <Activity size={13} strokeWidth={1.6} aria-hidden="true" /> FPS
              </dt>
              <dd>{metrics.fps || '--'}</dd>
            </div>
            <div>
              <dt>
                <Sparkles size={13} strokeWidth={1.6} aria-hidden="true" /> PARTICULAS
              </dt>
              <dd>{metrics.particles.toLocaleString('pt-BR')}</dd>
            </div>
            <div>
              <dt>
                <Cpu size={13} strokeWidth={1.6} aria-hidden="true" /> CONEXOES
              </dt>
              <dd>{metrics.connections.toLocaleString('pt-BR')}</dd>
            </div>
          </dl>
        </aside>
      </section>

      <footer className="bottombar">
        <span>ORBE DE PARTICULAS / ESTADO INICIAL</span>
        <span>QUALIDADE: {settings.label.toUpperCase()}</span>
      </footer>
    </main>
  )
}

export default App
