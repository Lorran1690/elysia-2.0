import { Canvas } from '@react-three/fiber'
import { Activity, Cpu, Info, Settings2, Sparkles } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { OrbMetrics } from './orb/ParticleOrb'
import { ParticleOrb } from './orb/ParticleOrb'
import { QUALITY_PRESETS, type QualityLevel } from './orb/quality'
import {
  ORB_STATE_DESCRIPTIONS,
  ORB_STATE_LABELS,
  ORB_STATES,
  transitionOrbState,
  type OrbState,
} from './orb/state'
import './App.css'

const INITIAL_METRICS: OrbMetrics = {
  connections: 0,
  fps: 0,
  particles: QUALITY_PRESETS.high.particles,
}

function useReducedMotionPreference() {
  const [reducedMotion, setReducedMotion] = useState(() => (
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  ))

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    const syncPreference = () => setReducedMotion(query.matches)

    syncPreference()
    query.addEventListener('change', syncPreference)
    return () => query.removeEventListener('change', syncPreference)
  }, [])

  return reducedMotion
}

function App() {
  const [audioLevel, setAudioLevel] = useState(0.42)
  const [quality, setQuality] = useState<QualityLevel>('high')
  const [metrics, setMetrics] = useState<OrbMetrics>(INITIAL_METRICS)
  const [orbState, setOrbState] = useState<OrbState>('idle')
  const [panelOpen, setPanelOpen] = useState(false)
  const reducedMotion = useReducedMotionPreference()
  const settings = QUALITY_PRESETS[quality]
  const stateLabel = ORB_STATE_LABELS[orbState]

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
            <span>DESKTOP / CORE VISUAL</span>
          </div>
        </div>

        <div className="topbar-status" aria-label={`Estado visual: ${stateLabel}`}>
          <span className="status-dot" aria-hidden="true" />
          <span>{stateLabel}</span>
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

      <section className="orb-stage" aria-label={`Previa do orbe no estado ${stateLabel}`}>
        <Canvas
          className="orb-canvas"
          camera={{ fov: 42, position: [0, 0, 4.35] }}
          dpr={[1, settings.pixelRatio]}
          gl={rendererOptions}
        >
          <color attach="background" args={['#050505']} />
          <ParticleOrb
            audioLevel={audioLevel}
            quality={settings}
            reducedMotion={reducedMotion}
            state={orbState}
            onMetrics={setMetrics}
          />
        </Canvas>

        <div className="stage-mode" aria-hidden="true">
          <span className="stage-mode-dot" />
          CORE / DEMO / {stateLabel}
        </div>

        <aside className={`inspector${panelOpen ? ' inspector-open' : ''}`} aria-label="Controles do orbe">
          <div className="inspector-heading">
            <span>CONTROLES</span>
            <Info size={14} strokeWidth={1.6} aria-hidden="true" />
          </div>

          <section className="state-control" aria-labelledby="state-control-title">
            <span id="state-control-title" className="control-label">ESTADO VISUAL</span>
            <div className="state-switcher" role="radiogroup" aria-label="Estado visual de demonstracao">
              {ORB_STATES.map((state) => (
                <button
                  key={state}
                  className={`state-button${orbState === state ? ' state-button-active' : ''}`}
                  type="button"
                  role="radio"
                  aria-checked={orbState === state}
                  onClick={() => {
                    setOrbState((current) => transitionOrbState(current, { type: 'demo-state-selected', state }))
                  }}
                >
                  {ORB_STATE_LABELS[state]}
                </button>
              ))}
            </div>
            <p className="state-description">{ORB_STATE_DESCRIPTIONS[orbState]}</p>
          </section>

          {orbState === 'listening' && (
            <label className="audio-control">
              <span className="audio-control-heading">
                <span>SINAL DE AUDIO SIMULADO</span>
                <output htmlFor="simulated-audio-level">{Math.round(audioLevel * 100)}%</output>
              </span>
              <input
                id="simulated-audio-level"
                type="range"
                min="0"
                max="100"
                value={Math.round(audioLevel * 100)}
                onChange={(event) => setAudioLevel(Number(event.target.value) / 100)}
              />
            </label>
          )}

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
        <span>ORBE DE PARTICULAS / {stateLabel}</span>
        <span>QUALIDADE: {settings.label.toUpperCase()}</span>
      </footer>
    </main>
  )
}

export default App
