// ElysiaPresence — ParticlesOrb aprovado (matemática original preservada)
// + metamorfose para holograma humanoide com rig procedural (avatar-rig.js):
//   respiração, cabeça que segue o mouse, cabelo com inércia, aceno.
// Com orbCount = 720 e form = 0 o desenho é idêntico ao ParticlesOrb original.
const { useCallback, useEffect, useRef, useMemo } = React;

const TWO_PI = Math.PI * 2;
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
const TIME_OFFSET = 1.7;
const TONE_BUCKETS = 6;
const ALPHA_BUCKETS = 10;
const BUCKETS = TONE_BUCKETS * ALPHA_BUCKETS;
const ANGLE_X = 0.32;
const REF_COUNT = 720;
const ERROR_FROM_RGB = hexToRgb(ERROR_COLOR_FROM);
const ERROR_TO_RGB = hexToRgb(ERROR_COLOR_TO);
const FORM_IN_RATE = 1.35;
const FORM_OUT_RATE = 1.1;

const STATES = {
  idle: { tempo: 1, spin: 0.14, breathe: 0.05, drift: 1, ripple: 0, swell: 0.04, flow: 0, swirl: 0, pulse: 0, pulseRate: 1, ring: 0, jitter: 0, shake: 0, alpha: 0.72, rest: 0 },
  connecting: { tempo: 1, spin: 0.3, breathe: 0.02, drift: 0.2, ripple: 0, swell: 0, flow: 0, swirl: 0, pulse: 0.06, pulseRate: 0.5, ring: 1, jitter: 0, shake: 0, alpha: 0.8, rest: 0.12 },
  listening: { tempo: 1, spin: 0.55, breathe: 0.012, drift: 0, ripple: 1, swell: 0.12, flow: 0, swirl: 0, pulse: 0, pulseRate: 1, ring: 0, jitter: 0, shake: 0, alpha: 0.92, rest: 0.55 },
  thinking: { tempo: 1, spin: 0.32, breathe: 0.01, drift: 0, ripple: 0, swell: 0, flow: 0, swirl: 0, pulse: 1, pulseRate: 1, ring: 0, jitter: 0, shake: 0, alpha: 0.78, rest: 0.3 },
  speaking: { tempo: 1, spin: 0.24, breathe: 0.01, drift: 0, ripple: 0, swell: 0.06, flow: 1, swirl: 1, pulse: 0, pulseRate: 1, ring: 0, jitter: 0.6, shake: 0, alpha: 0.94, rest: 0.55 },
  error: { tempo: 1, spin: 0.08, breathe: 0, drift: 0, ripple: 0, swell: 0, flow: 0, swirl: 0, pulse: 0, pulseRate: 1, ring: 0, jitter: 0.7, shake: 1, alpha: 0.85, rest: 0.2 },
  disabled: { tempo: 0.04, spin: 0, breathe: 0, drift: 0, ripple: 0, swell: 0, flow: 0, swirl: 0, pulse: 0, pulseRate: 1, ring: 0, jitter: 0, shake: 0, alpha: 0.45, rest: 0 },
};

const buildSphere = (count) => {
  const s = {
    count,
    x: new Float32Array(count), y: new Float32Array(count), z: new Float32Array(count),
    ringFrac: new Float32Array(count), seed: new Float32Array(count),
    toneBucket: new Uint8Array(count), tone: new Float32Array(count),
  };
  for (let i = 0; i < count; i += 1) {
    const y = 1 - (i / (count - 1)) * 2;
    const radiusAtY = Math.sqrt(1 - y * y);
    const theta = GOLDEN_ANGLE * i;
    const tone = (i * 0.5436890126) % 1;
    s.x[i] = Math.cos(theta) * radiusAtY;
    s.y[i] = y;
    s.z[i] = Math.sin(theta) * radiusAtY;
    s.ringFrac[i] = (i * 0.61803398875) % 1;
    s.seed[i] = ((i * 0.7548776662) % 1) * TWO_PI;
    s.tone[i] = tone;
    s.toneBucket[i] = Math.min(TONE_BUCKETS - 1, Math.floor(tone * TONE_BUCKETS));
  }
  return s;
};

const smooth = (x) => x * x * (3 - 2 * x);
const clampN = (v, a, b) => (v < a ? a : v > b ? b : v);

// ponteiro global (compartilhado; sem captura de nada além da posição)
const POINTER = { x: 0, y: 0, last: -1e9, inside: false };
if (typeof window !== 'undefined' && !window.__elysiaPointer) {
  window.__elysiaPointer = true;
  window.addEventListener('pointermove', (e) => { POINTER.x = e.clientX; POINTER.y = e.clientY; POINTER.last = performance.now(); POINTER.inside = true; }, { passive: true });
  document.addEventListener('pointerleave', () => { POINTER.inside = false; });
  window.addEventListener('blur', () => { POINTER.inside = false; });
}

const ElysiaPresence = ({
  state = 'idle',
  size = 212,
  speed = 1,
  colorFrom = '#8b5cf6',
  colorTo = '#d946ef',
  levelRef,
  form = 0,
  width,
  height,
  avatar = 'bust',
  orbCount = REF_COUNT,
  holoCount = 9000,
  holoScale = 0.88,
  waveKey = 0,
  onForm,
  onWaveEnd,
  label = 'Elysia',
  className,
}) => {
  const hostRef = useRef(null);
  const canvasRef = useRef(null);
  const colorRef = useRef({ from: colorFrom, to: colorTo });
  const drawRef = useRef(null);
  const formTargetRef = useRef(form);
  const formRef = useRef(form);
  const onFormRef = useRef(onForm);
  const onWaveEndRef = useRef(onWaveEnd);
  const holoScaleRef = useRef(holoScale);
  const [avatarError, setAvatarError] = React.useState(false);
  const rigRef = useRef(null); // { key, def, T, ox, oy, om }
  const swapRef = useRef({ t: 0, x: null, y: null, n: 0 });
  const waveRef = useRef({ pending: false, start: -1 });
  const avClockRef = useRef(0);
  const cw = Math.max(width || size, size);
  const ch = Math.max(height || size, size);
  const nOrb = Math.max(60, Math.round(orbCount));

  const sphere = useMemo(() => buildSphere(nOrb), [nOrb]);

  useEffect(() => { onFormRef.current = onForm; }, [onForm]);
  useEffect(() => { onWaveEndRef.current = onWaveEnd; }, [onWaveEnd]);
  useEffect(() => { holoScaleRef.current = holoScale; }, [holoScale]);
  useEffect(() => { if (waveKey > 0) waveRef.current = { pending: true, start: -1 }; }, [waveKey]);

  // carrega e amostra a silhueta (re-amostra ao trocar avatar ou quantidade)
  useEffect(() => {
    let cancelled = false;
    const R = window.ElysiaRig;
    setAvatarError(false);
    R.loadAvatar(avatar).then((prep) => {
      if (cancelled) return;
      if (!prep) { setAvatarError(true); return; }
      const def = R.AVATARS[avatar];
      const T = R.sampleTargets(def, prep, Math.max(nOrb, Math.round(holoCount)), nOrb);
      const prev = rigRef.current;
      const sw = swapRef.current;
      if (prev && formRef.current > 0.02 && sw.snapX) {
        sw.x = sw.snapX.slice(0, sw.snapN); sw.y = sw.snapY.slice(0, sw.snapN); sw.n = sw.snapN; sw.t = 1;
      }
      rigRef.current = { key: avatar, def, T, ox: new Float32Array(T.count), oy: new Float32Array(T.count), om: new Float32Array(T.count) };
      drawRef.current?.({ ...frameRef.current, dt: 0 });
    }).catch(() => { if (!cancelled) setAvatarError(true); });
    return () => { cancelled = true; };
  }, [avatar, holoCount, nOrb]);

  const onFrame = useCallback((frame) => drawRef.current?.(frame), []);
  const { frameRef } = useOrbAnimator(hostRef, { state, levelRef, speed, onFrame });

  useEffect(() => {
    formTargetRef.current = form;
    if (prefersReducedMotion()) formRef.current = form;
    drawRef.current?.({ ...frameRef.current, dt: 0 });
  }, [form, frameRef]);

  useEffect(() => {
    colorRef.current = { from: colorFrom, to: colorTo };
    drawRef.current?.({ ...frameRef.current, dt: 0 });
  }, [colorFrom, colorTo, frameRef]);

  useEffect(() => {
    const host = hostRef.current;
    const canvas = canvasRef.current;
    if (!host || !canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const R = window.ElysiaRig;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(cw * dpr);
    canvas.height = Math.round(ch * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const center = size / 2;
    const ocx = cw / 2;
    const ocy = ch / 2;
    const smallness = Math.min(1, size / 140);
    const densK = nOrb === REF_COUNT ? 1 : Math.pow(REF_COUNT / nOrb, 0.3);
    const densA = nOrb === REF_COUNT ? 1 : Math.min(1.15, Math.pow(REF_COUNT / nOrb, 0.18));
    const dotScale = (0.55 + 0.45 * smallness) * densK;
    const alphaScale = smallness * smallness * densA;
    const baseRadius = center * 0.62;

    let cap = 0, px, py, pr, bucketOf, order, extra;
    const ensureCap = (n) => {
      if (n <= cap) return;
      cap = n;
      px = new Float32Array(n); py = new Float32Array(n); pr = new Float32Array(n);
      bucketOf = new Uint8Array(n); order = new Uint32Array(n);
      extra = buildSphere(Math.max(2, n));
    };
    ensureCap(nOrb + 64);
    const NB = BUCKETS * 2; // [0,BUCKETS) círculos · [BUCKETS,2B) pontos finos
    const counts = new Uint32Array(NB);
    const starts = new Uint32Array(NB);
    const toneStyles = new Array(TONE_BUCKETS).fill('#fff');

    let paletteKey = '';
    let lastPhase = frameRef.current.phase;
    let lastLevelText = '';
    let lastFormReport = -1;
    let clock = 0, pulseClock = 0, angleY = 0, ringPhase = 0;
    const look = { yaw: 0, pitch: 0, roll: 0, yawHair: 0, pitchHair: 0 };

    const ensurePalette = (errorW) => {
      const { from, to } = colorRef.current;
      const errKey = Math.round(errorW * 64);
      const key = `${from}|${to}|${errKey}`;
      if (key === paletteKey) return;
      paletteKey = key;
      const e = errKey / 64;
      const f = mixRgb(hexToRgb(from), ERROR_FROM_RGB, e);
      const t = mixRgb(hexToRgb(to), ERROR_TO_RGB, e);
      for (let b = 0; b < TONE_BUCKETS; b += 1) toneStyles[b] = rgba(mixRgb(f, t, (b + 0.5) / TONE_BUCKETS), 1);
    };

    const draw = (frame) => {
      const w = frame.weights;
      const p = blendStates(w, STATES);
      const dPhase = Math.max(0, frame.phase - lastPhase);
      lastPhase = frame.phase;
      const dt = frame.dt || 0;
      const level = frame.reduced ? p.rest : frame.level;
      const levelText = frame.level.toFixed(3);
      if (levelText !== lastLevelText) { lastLevelText = levelText; host.style.setProperty('--orb-level', levelText); }

      const rig = rigRef.current;
      const ft = rig ? formTargetRef.current : 0;
      if (frame.reduced) formRef.current = ft;
      else formRef.current = approach(formRef.current, ft, ft > formRef.current ? FORM_IN_RATE : FORM_OUT_RATE, dt);
      if (Math.abs(formRef.current - ft) < 0.0008) formRef.current = ft;
      const F = formRef.current;
      const fr = Math.round(F * 100) / 100;
      if (fr !== lastFormReport) { lastFormReport = fr; onFormRef.current?.(fr); }

      clock += dPhase * p.tempo;
      pulseClock += dPhase * p.tempo * p.pulseRate;
      angleY += dPhase * p.spin * (1 + p.ripple * level * 1.8);
      ringPhase = (ringPhase + dPhase * 0.7) % TWO_PI;
      if (!frame.reduced) avClockRef.current += dt;
      const at = avClockRef.current;
      const t = clock + TIME_OFFSET;
      const pt = pulseClock + TIME_OFFSET;

      const beat = Math.sin(pt * 2.6) * 0.5 + 0.5;
      const beatSharp = beat * beat * beat;
      const breathe = p.breathe * Math.sin(t * 1.1);
      const conv = p.pulse * (0.06 + 0.12 * beatSharp);
      const radius = baseRadius * (1 + breathe + level * p.swell - conv);

      const shakeAmp = p.shake * radius * 0.05;
      const shakeX = shakeAmp * (Math.sin(t * 26) + 0.5 * Math.sin(t * 15.7));
      const shakeY = shakeAmp * (Math.cos(t * 22.5) + 0.5 * Math.sin(t * 13.1));
      const driftAmp = p.drift * radius * 0.055;
      const jitterAmp = p.jitter * radius * (0.012 + level * 0.07);
      const rippleAmp = p.ripple * (0.04 + level * 0.22);
      const pulseAmp = p.pulse * 0.16 * (0.4 + 0.6 * beat);
      const flowAmp = p.flow * (0.18 + level * 0.4);
      const swirlAmp = p.swirl * (0.35 + level * 0.9);
      const ringW = clamp01(p.ring);
      const ringBreath = 1 + p.pulse * 0.4 * Math.sin(pt * 2.6);
      const cosX = Math.cos(ANGLE_X);
      const sinX = Math.sin(ANGLE_X);
      counts.fill(0);

      /* ---------- pose do holograma ---------- */
      const morphing = F > 0.0005 && rig;
      let T = null, def = null, ox, oy, om, fs = 1, ccx = 0, ccy = 0, dotHolo = 1, avEnergy = 0;
      if (morphing) {
        T = rig.T; def = rig.def; ox = rig.ox; oy = rig.oy; om = rig.om;
        ensureCap(T.count + 64);
        // Inclui espaço lateral para a mão durante o aceno, inclusive em telas estreitas.
        const fitWidth = def.crop.w + (def.fitMargin || 0) * 2;
        const figH = Math.min(ch * holoScaleRef.current, (cw * 0.98) * def.crop.h / fitWidth);
        fs = figH / def.crop.h;
        ccx = def.crop.x + def.crop.w / 2;
        ccy = def.crop.y + def.crop.h / 2;
        dotHolo = clampN(figH / 700, 0.55, 1.5) * clampN(Math.pow(9000 / (T.baseCount || T.count), 0.32), 0.55, 1.6);
        avEnergy = clamp01(level * 1.6);

        // olhar: segue o mouse; sem mouse, observa o ambiente sozinha
        const rect = host.getBoundingClientRect();
        const hx = rect.left + ocx + (def.head.cx - ccx) * fs;
        const hy = rect.top + ocy + (def.head.cy - ccy) * fs;
        const now = performance.now();
        const mouseOn = POINTER.inside && now - POINTER.last < 5000;
        let tyaw, tpitch;
        if (mouseOn) {
          tyaw = clampN((POINTER.x - hx) / Math.max(320, rect.width * 0.42), -1, 1) * 0.5;
          tpitch = clampN((POINTER.y - hy) / Math.max(320, rect.height * 0.55), -1, 1) * 0.34;
        } else {
          tyaw = 0.22 * Math.sin(at * 0.31) + 0.09 * Math.sin(at * 0.83 + 1.3);
          tpitch = 0.07 * Math.sin(at * 0.47 + 0.6) + 0.04 * Math.sin(at * 1.1);
        }
        const wave = R.waveAt(waveRef.current.start >= 0 ? at - waveRef.current.start : -1, def);
        // durante o aceno ela olha para frente, com leve inclinação simpática
        tyaw = tyaw * (1 - wave.env * 0.7);
        tpitch = tpitch * (1 - wave.env * 0.7) - wave.env * 0.04;
        const rate = mouseOn ? 4.2 : 1.6;
        look.yaw = approach(look.yaw, tyaw, rate, dt);
        look.pitch = approach(look.pitch, tpitch, rate, dt);
        look.roll = approach(look.roll, -look.yaw * 0.12 + 0.025 * Math.sin(at * 0.6) - wave.env * 0.06, 2.4, dt);
        look.yawHair = approach(look.yawHair, look.yaw, 1.4, dt);
        // Fase contínua: os estados/níveis do orbe não aceleram nem sacodem o corpo.
        const breath = Math.sin(at * (TWO_PI / 5.2));

        // início/fim do aceno
        const wv = waveRef.current;
        if (wv.pending && F > 0.82) { wv.pending = false; wv.start = at; }
        if (wv.start >= 0 && at - wv.start > (def.waveDuration || R.WAVE_DURATION)) { wv.start = -1; onWaveEndRef.current?.(); }

        R.applyPose(def, T, {
          t: at, yaw: look.yaw, pitch: look.pitch, roll: look.roll, yawHair: look.yawHair,
          breath, env: wave.env, osc: wave.osc, oscH: wave.oscH, oscU: wave.oscU,
        }, ox, oy, om);
      }

      const sw = swapRef.current;
      if (sw.t > 0) { sw.t = approach(sw.t, 0, 2.6, dt); if (sw.t < 0.004) sw.t = 0; }
      const swE = sw.t * sw.t;
      const alphaMix = p.alpha * (1 - F) + 0.96 * F;
      const jitHolo = 0.16 * fs; // microvariação estável, sem amplificar com o estado

      // alvo humanoide de uma partícula (posição de tela + alpha + diâmetro)
      const ap = { x: 0, y: 0, a: 0, d: 0 };
      const holoTarget = (k, seed) => {
        const l = T.lum[k];
        ap.x = ocx + (ox[k] - ccx) * fs + jitHolo * Math.sin(at * 3.1 + seed * 7.3);
        ap.y = ocy + (oy[k] - ccy) * fs + jitHolo * Math.cos(at * 2.7 + seed * 5.1);
        const waveB = 0.5 + 0.5 * Math.sin(T.y[k] * 0.012 + at * 4.2);
        const twinkle = 0.76 + 0.24 * Math.sin(at * 2.3 + seed * 11);
        ap.a = clamp01((0.18 + 0.85 * l) * twinkle * (0.85 + 0.4 * avEnergy * waveB)) * om[k] / alphaMix;
        ap.d = (0.42 + l * 1.05) * dotHolo;
      };

      /* ---------- orbe (algoritmo original) ---------- */
      const S = sphere;
      for (let i = 0; i < nOrb; i += 1) {
        const sx = S.x[i], sy = S.y[i], sz = S.z[i];
        const seed = S.seed[i];
        const ringFrac = S.ringFrac[i];
        const twist = swirlAmp > 0.002 ? angleY + swirlAmp * Math.sin(sy * 2.4 + t * 1.6) : angleY;
        const cy = Math.cos(twist), sny = Math.sin(twist);
        const x1 = sx * cy - sz * sny;
        const z1 = sx * sny + sz * cy;
        const y1 = sy * cosX - z1 * sinX;
        const z2 = sy * sinX + z1 * cosX;
        const depth = (z2 + 1) / 2;
        const perspective = 0.65 + depth * 0.45;
        let pointRadius = radius;
        if (rippleAmp > 0.002) pointRadius *= 1 + rippleAmp * (0.5 + 0.5 * Math.sin(sy * 4.5 - t * 6.5));
        if (pulseAmp > 0.002) pointRadius *= 1 - pulseAmp * (0.5 + 0.5 * Math.sin(ringFrac * TWO_PI + pt * 3.1));
        if (flowAmp > 0.002) { const stream = 0.5 + 0.5 * Math.sin(seed * 3 - t * 3.4); pointRadius *= 1 - flowAmp * stream * stream; }
        let offx = shakeX, offy = shakeY;
        if (driftAmp > 0.01) {
          offx += driftAmp * (Math.sin(t * 0.55 + seed * 3.7) + 0.5 * Math.sin(t * 1.3 + seed * 1.3));
          offy += driftAmp * (Math.cos(t * 0.62 + seed * 2.9) + 0.5 * Math.sin(t * 1.05 + seed * 5.1));
        }
        if (jitterAmp > 0.01) { offx += jitterAmp * Math.sin(t * 14 + seed * 9.3); offy += jitterAmp * Math.cos(t * 17 + seed * 6.1); }
        let screenX = ocx + x1 * pointRadius * perspective + offx;
        let screenY = ocy + y1 * pointRadius * perspective + offy;
        let alpha = 0.12 + depth * depth * 0.78;
        let dot = 0.6 + depth * 1.5;
        if (ringW > 0.004) {
          const tone = S.tone[i];
          const ringAngle = (i / nOrb) * TWO_PI + ringPhase + 0.05 * Math.sin(t * 1.3 + seed);
          const ringR = center * (0.58 + 0.13 * ringFrac) * (1 + 0.05 * Math.sin(t + seed * 1.7)) * ringBreath;
          screenX += (ocx + Math.cos(ringAngle) * ringR - screenX) * ringW;
          screenY += (ocy + Math.sin(ringAngle) * ringR - screenY) * ringW;
          alpha += (0.35 + tone * 0.5 - alpha) * ringW;
          dot += (0.75 + tone * 0.9 - dot) * ringW;
        }
        dot *= dotScale;
        alpha *= alphaScale;

        if (morphing) {
          const m = smooth(clamp01(F * 1.7 - T.delay[i] * 0.7));
          if (m > 0) {
            holoTarget(i, seed);
            let tx = ap.x, ty = ap.y;
            if (swE > 0 && i < sw.n) { tx += (sw.x[i] - tx) * swE; ty += (sw.y[i] - ty) * swE; }
            const dx = tx - screenX, dy = ty - screenY;
            const arc = Math.sin(m * Math.PI) * 0.22 * T.sign[i];
            screenX += dx * m - dy * arc;
            screenY += dy * m + dx * arc;
            alpha += (ap.a - alpha) * m;
            dot += (ap.d - dot) * m;
          }
        }
        px[i] = screenX; py[i] = screenY; pr[i] = dot;
        const ab = Math.min(ALPHA_BUCKETS - 1, Math.max(0, Math.floor(alpha * ALPHA_BUCKETS)));
        const b = S.toneBucket[i] * ALPHA_BUCKETS + ab;
        bucketOf[i] = b; counts[b] += 1;
      }

      /* ---------- camada de detalhe do holograma ---------- */
      let drawn = nOrb;
      if (morphing) {
        const cyA = Math.cos(angleY), syA = Math.sin(angleY);
        const E = extra;
        for (let k = nOrb; k < T.count; k += 1) {
          const m = smooth(clamp01(F * 1.7 - T.delay[k] * 0.7));
          if (m <= 0.01) continue;
          const seed = T.seed[k];
          holoTarget(k, seed);
          if (ap.a * m < 0.02) continue;
          const j = k - nOrb;
          const ex = E.x[j], ey = E.y[j], ez = E.z[j];
          const x1 = ex * cyA - ez * syA;
          const z1 = ex * syA + ez * cyA;
          const y1 = ey * cosX - z1 * sinX;
          const r = radius * (0.35 + 0.6 * E.ringFrac[j]);
          const startX = ocx + x1 * r, startY = ocy + y1 * r;
          let tx = ap.x, ty = ap.y;
          if (swE > 0 && k < sw.n) { tx += (sw.x[k] - tx) * swE; ty += (sw.y[k] - ty) * swE; }
          const dx = tx - startX, dy = ty - startY;
          const arc = Math.sin(m * Math.PI) * 0.18 * T.sign[k];
          px[drawn] = startX + dx * m - dy * arc;
          py[drawn] = startY + dy * m + dx * arc;
          pr[drawn] = ap.d * 0.72;
          const alpha = ap.a * 0.82 * m;
          const ab = Math.min(ALPHA_BUCKETS - 1, Math.floor(alpha * ALPHA_BUCKETS));
          const b = BUCKETS + T.tone[k] * ALPHA_BUCKETS + ab;
          bucketOf[drawn] = b; counts[b] += 1;
          drawn += 1;
        }
        // foto da posição atual para transição suave ao trocar de avatar/quantidade
        sw.snapX = px; sw.snapY = py; sw.snapN = drawn;
      } else {
        sw.snapX = null;
      }

      let acc = 0;
      for (let b = 0; b < NB; b += 1) { starts[b] = acc; acc += counts[b]; }
      for (let i = 0; i < drawn; i += 1) { const b = bucketOf[i]; order[starts[b]] = i; starts[b] += 1; }

      ensurePalette(w.error);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, cw, ch);
      ctx.globalCompositeOperation = 'lighter';
      let cursor = 0;
      for (let b = 0; b < NB; b += 1) {
        const count = counts[b];
        if (count === 0) continue;
        const bb = b % BUCKETS;
        const ab = bb % ALPHA_BUCKETS;
        ctx.globalAlpha = clamp01(((ab + 0.5) / ALPHA_BUCKETS) * alphaMix);
        ctx.fillStyle = toneStyles[(bb - ab) / ALPHA_BUCKETS];
        ctx.beginPath();
        if (b < BUCKETS) {
          for (let k = cursor; k < cursor + count; k += 1) {
            const i = order[k];
            ctx.moveTo(px[i] + pr[i], py[i]);
            ctx.arc(px[i], py[i], pr[i], 0, TWO_PI);
          }
        } else {
          for (let k = cursor; k < cursor + count; k += 1) {
            const i = order[k], r = pr[i];
            ctx.rect(px[i] - r, py[i] - r, r * 2, r * 2);
          }
        }
        ctx.fill();
        cursor += count;
      }
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
    };

    drawRef.current = draw;
    draw({ ...frameRef.current, dt: 0 });
    return () => { drawRef.current = null; };
  }, [size, cw, ch, nOrb, sphere, frameRef]);

  return (
    <div
      ref={hostRef}
      role="img"
      aria-label={avatarError ? label + " · avatar indisponível" : label}
      data-state={state}
      className={className}
      style={{
        ...orbVars({ size, speed, colorFrom, colorTo }),
        width: cw,
        height: ch,
        display: 'grid',
        placeItems: 'center',
        opacity: state === 'disabled' ? 0.5 : 1,
        filter: state === 'disabled' ? 'grayscale(0.85)' : 'grayscale(0)',
        transition: 'opacity 0.4s ease, filter 0.4s ease',
      }}
    >
      {avatarError && <span role="status" style={{ position: 'absolute', bottom: 48, fontSize: 12 }}>Não foi possível carregar o avatar. Recarregue a interface.</span>}
      <canvas ref={canvasRef} style={{ width: cw, height: ch }} />
    </div>
  );
};

Object.assign(window, { ElysiaPresence });
