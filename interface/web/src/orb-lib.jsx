// Port JS (sem tipos) de src/registry/lib/* — lógica preservada do código aprovado.
// orb-state.ts · orb-color.ts · use-in-view.ts · use-reduced-motion.ts · use-orb-animator.ts
const { useEffect: _ue, useRef: _ur, useSyncExternalStore: _uses } = React;

/* ---------- orb-state.ts ---------- */
const ORB_STATES = ['idle', 'connecting', 'listening', 'thinking', 'speaking'];
const ERROR_COLOR_FROM = '#fb7185';
const ERROR_COLOR_TO = '#f43f5e';

const hexToRgb = (hex) => {
  const clean = hex.replace('#', '');
  const full = clean.length === 3 ? clean.split('').map((c) => c + c).join('') : clean;
  const n = Number.parseInt(full, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};

const stateMotion = (state) => {
  switch (state) {
    case 'listening': return 'ripple';
    case 'thinking': return 'pulse';
    case 'speaking': return 'flow';
    default: return 'none';
  }
};

const wave = (x) => 0.5 - 0.5 * Math.cos(x);

const stateEnergy = (state, t) => {
  switch (state) {
    case 'listening': return 0.4 + 0.32 * wave(t * 17) + 0.18 * wave(t * 8.2 + 3);
    case 'speaking': return 0.3 + 0.24 * wave(t * 12.4) + 0.16 * wave(t * 6 + 1.2);
    case 'thinking': return 0.24 + 0.2 * wave(t * 4.8);
    case 'connecting': return 0.12 + 0.1 * wave(t * 3.2);
    case 'error': return 0.2;
    default: return 0;
  }
};

const approach = (current, target, rate, dt) => current + (target - current) * (1 - Math.exp(-rate * dt));

const ENTER_RATE = 14;
const SETTLE_RATE = 5;
const ERROR_RATE = 10;

const stateRate = (state) => {
  if (state === 'idle' || state === 'disabled') return SETTLE_RATE;
  if (state === 'error') return ERROR_RATE;
  return ENTER_RATE;
};

const createStateMix = (initial = 'idle') => {
  const weights = { idle: 0, connecting: 0, listening: 0, thinking: 0, speaking: 0, error: 0, disabled: 0 };
  weights[initial] = 1;
  const keys = Object.keys(weights);
  const update = (state, dt, rate = stateRate(state)) => {
    let total = 0;
    for (const key of keys) {
      const target = key === state ? 1 : 0;
      const next = approach(weights[key], target, rate, dt);
      weights[key] = target === 0 && next < 0.001 ? 0 : next;
      total += weights[key];
    }
    if (total > 0) for (const key of keys) weights[key] /= total;
    return weights;
  };
  return { weights, update };
};

const blendStates = (weights, table) => {
  const out = {};
  for (const key of Object.keys(weights)) {
    const w = weights[key];
    if (w === 0) continue;
    const row = table[key];
    for (const param of Object.keys(row)) out[param] = (out[param] ?? 0) + row[param] * w;
  }
  return out;
};

const blendEnergy = (weights, t) => {
  let energy = 0;
  for (const key of Object.keys(weights)) if (weights[key] > 0) energy += weights[key] * stateEnergy(key, t);
  return energy;
};

const clamp01 = (v) => Math.min(1, Math.max(0, v));

const orbVars = ({ size, speed, colorFrom, colorTo }) => {
  const vars = {};
  if (size != null) vars['--orb-size'] = `${size}px`;
  if (speed != null) vars['--orb-speed'] = `${speed}`;
  if (colorFrom) vars['--orb-color-from'] = colorFrom;
  if (colorTo) vars['--orb-color-to'] = colorTo;
  return vars;
};

/* ---------- orb-color.ts ---------- */
const toLinear = (c) => { const v = c / 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
const toSrgb = (v) => { const c = v <= 0.0031308 ? v * 12.92 : 1.055 * v ** (1 / 2.4) - 0.055; return Math.min(255, Math.max(0, c * 255)); };
const mixRgb = (a, b, t) => [
  toSrgb(toLinear(a[0]) + (toLinear(b[0]) - toLinear(a[0])) * t),
  toSrgb(toLinear(a[1]) + (toLinear(b[1]) - toLinear(a[1])) * t),
  toSrgb(toLinear(a[2]) + (toLinear(b[2]) - toLinear(a[2])) * t),
];
const hexChannel = (c) => Math.round(c).toString(16).padStart(2, '0');
const rgbToHex = ([r, g, b]) => `#${hexChannel(r)}${hexChannel(g)}${hexChannel(b)}`;
const mixHex = (a, b, t) => rgbToHex(mixRgb(hexToRgb(a), hexToRgb(b), t));
const rgba = ([r, g, b], alpha) =>
  `rgba(${Math.round(r)},${Math.round(g)},${Math.round(b)},${Math.min(1, Math.max(0, alpha)).toFixed(3)})`;

/* ---------- use-reduced-motion.ts ---------- */
const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';
const prefersReducedMotion = () => typeof window !== 'undefined' && window.matchMedia(REDUCED_MOTION_QUERY).matches;
const subscribeReducedMotion = (onChange) => {
  const mq = window.matchMedia(REDUCED_MOTION_QUERY);
  mq.addEventListener('change', onChange);
  return () => mq.removeEventListener('change', onChange);
};
const useReducedMotion = () => _uses(subscribeReducedMotion, prefersReducedMotion, () => false);

/* ---------- use-in-view.ts ---------- */
const observeActivity = (el, onChange) => {
  let inView = true;
  let pageVisible = document.visibilityState === 'visible';
  let active = inView && pageVisible;
  const sync = () => { const next = inView && pageVisible; if (next === active) return; active = next; onChange(next); };
  const observer = typeof IntersectionObserver === 'undefined' ? null
    : new IntersectionObserver((entries) => { inView = entries[entries.length - 1]?.isIntersecting ?? true; sync(); });
  observer?.observe(el);
  const onVisibility = () => { pageVisible = document.visibilityState === 'visible'; sync(); };
  document.addEventListener('visibilitychange', onVisibility);
  return () => { observer?.disconnect(); document.removeEventListener('visibilitychange', onVisibility); };
};

/* ---------- use-orb-animator.ts ---------- */
const LEVEL_ATTACK_RATE = 14;
const LEVEL_RELEASE_RATE = 4;
const MAX_FRAME_DT = 0.1;
const smoothLevel = (current, target, dt) =>
  approach(current, target, target > current ? LEVEL_ATTACK_RATE : LEVEL_RELEASE_RATE, dt);
const isSettled = (weights, state) => weights[state] > 0.999;

const useOrbAnimator = (hostRef, { state, levelRef, speed = 1, onFrame }) => {
  const optionsRef = _ur({ state, levelRef, speed, onFrame });
  const wakeRef = _ur(() => {});
  const frameRef = _ur({
    dt: 0, dPhase: 0, phase: 0, time: 0, weights: createStateMix(state).weights,
    level: 0, live: false, reduced: false, state,
  });

  _ue(() => { optionsRef.current = { state, levelRef, speed, onFrame }; wakeRef.current(); }, [state, levelRef, speed, onFrame]);

  _ue(() => {
    const el = hostRef.current;
    if (!el) return;
    const mix = createStateMix(optionsRef.current.state);
    const frame = frameRef.current;
    frame.weights = mix.weights;
    let reduced = prefersReducedMotion();
    let raf = 0, last = null, active = true;

    const tick = (now) => {
      raf = 0;
      const dt = last === null ? 0 : Math.min((now - last) / 1000, MAX_FRAME_DT);
      last = now;
      const opts = optionsRef.current;
      const live = opts.levelRef?.current;
      const hasLive = typeof live === 'number' && live >= 0;
      mix.update(opts.state, dt);
      frame.dPhase = reduced ? 0 : dt * Math.max(0, opts.speed);
      if (!reduced) { frame.time += dt; frame.phase += frame.dPhase; }
      const target = reduced ? 0 : hasLive ? live : blendEnergy(mix.weights, frame.phase);
      frame.level = smoothLevel(frame.level, target, dt);
      frame.dt = dt; frame.live = hasLive; frame.reduced = reduced; frame.state = opts.state;
      opts.onFrame?.(frame);
      const idle = reduced && isSettled(mix.weights, opts.state) && frame.level < 0.001;
      if (active && !idle) raf = requestAnimationFrame(tick);
      else last = null;
    };
    const wake = () => { if (active && raf === 0) raf = requestAnimationFrame(tick); };
    const halt = () => { if (raf !== 0) { cancelAnimationFrame(raf); raf = 0; } last = null; };
    wakeRef.current = wake;
    const unobserve = observeActivity(el, (next) => { active = next; if (next) wake(); else halt(); });
    const unsubscribe = subscribeReducedMotion(() => { reduced = prefersReducedMotion(); wake(); });
    wake();
    return () => { halt(); unobserve(); unsubscribe(); wakeRef.current = () => {}; };
  }, [hostRef]);

  return { frameRef };
};

/* ---------- palettes.ts ---------- */
const PALETTES = {
  original: { label: 'Violeta / magenta', from: '#8b5cf6', to: '#d946ef' },
  white: { label: 'Branco', from: '#ffffff', to: '#ffffff' },
  gold: { label: 'Dourado', from: '#f6df93', to: '#c6882d' },
  silver: { label: 'Prata', from: '#e2e8f0', to: '#94a3b8' },
  ice: { label: 'Gelo', from: '#67e8f9', to: '#3b82f6' },
  ocean: { label: 'Oceano', from: '#38bdf8', to: '#2563eb' },
  aurora: { label: 'Aurora', from: '#34d399', to: '#22d3ee' },
  emerald: { label: 'Esmeralda', from: '#a7f3d0', to: '#10b981' },
  mint: { label: 'Menta', from: '#d1fae5', to: '#5eead4' },
  sunset: { label: 'Pôr do sol', from: '#fb923c', to: '#f472b6' },
  fire: { label: 'Chama', from: '#fde047', to: '#f97316' },
  ruby: { label: 'Rubi', from: '#fb7185', to: '#e11d48' },
  rose: { label: 'Rosa', from: '#f9a8d4', to: '#f472b6' },
  roseGold: { label: 'Rosé dourado', from: '#fecdd3', to: '#e7b56e' },
  lavender: { label: 'Lavanda', from: '#ddd6fe', to: '#a78bfa' },
  cosmic: { label: 'Cósmico', from: '#a78bfa', to: '#22d3ee' },
};

Object.assign(window, {
  ORB_STATES, ERROR_COLOR_FROM, ERROR_COLOR_TO, hexToRgb, stateMotion, stateEnergy, approach,
  createStateMix, blendStates, blendEnergy, clamp01, orbVars, mixRgb, mixHex, rgbToHex, rgba,
  prefersReducedMotion, subscribeReducedMotion, useReducedMotion, observeActivity,
  useOrbAnimator, smoothLevel, PALETTES,
});
