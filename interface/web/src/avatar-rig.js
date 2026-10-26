// avatar-rig.js — esqueleto procedural para as silhuetas de partículas da Elysia.
// Amostra partículas da imagem de referência e classifica cada uma em partes do corpo
// (cabeça, cabelo, tronco, braço, mão) para animar respiração, cabeça, cabelo e aceno.
(function (root) {
  const TWO_PI = Math.PI * 2;
  const clamp01 = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);
  const sstep = (a, b, x) => { const t = clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); };
  const TONE_BUCKETS = 6;

  // Coordenadas no espaço de pixels da imagem original
  const AVATARS = {
    bust: {
      label: 'Busto',
      src: 'assets/avatar-bust-violet.png',
      crop: { x: 0, y: 0, w: 1024, h: 1536 },
      head: { cx: 512, cy: 292, rx: 140, ry: 164 },
      chinY: 452, neckY: 590, pivot: [512, 535],
      chest: { x: 512, y: 780, rx: 260, ry: 210 },
      shoulderY: 565,
      neck: [[512, 428], [512, 610], 70],
      torso: [], // contorno anatômico abaixo, sem confundir quadril e cabelo
      arm: { S: [274, 603], E: [194, 1044], W: [390, 1180], T: [518, 1336], r: 50, xMax: 550, dirE: [-190, 145], dirW: [-35, -235], shortestWave: true, outlinePad: 10, waveGain: 0.5,
        outline: [[229, 568], [274, 567], [311, 627], [332, 690], [324, 750], [300, 830], [283, 900], [274, 950], [264, 1000], [265, 1030], [270, 1050], [305, 1075], [341, 1100], [381, 1125], [430, 1150], [448, 1184], [477, 1221], [506, 1275], [528, 1327], [525, 1347], [513, 1350], [473, 1315], [438, 1278], [404, 1250], [365, 1223], [310, 1196], [250, 1164], [194, 1133], [151, 1094], [133, 1063], [132, 1022], [147, 958], [168, 877], [182, 787], [184, 702], [199, 624]],
      },
      armR: { S: [750, 603], E: [835, 1061], W: [628, 1205], T: [529, 1334], r: 50 },
      synthHand: false, separateHands: true,
      hairMaxY: 1536, hairRootY: 150, hairLen: 1150, hairAmp: 11, hairFollow: 420, hairLag: 0.09,
      breathLift: 6.7, headShift: 24, lean: 12, fade: 170, fitMargin: 280,
      layeredTorso: true,
      waveDuration: 5.2,
    },
    body: {
      label: 'Corpo',
      src: 'assets/avatar-body.png',
      crop: { x: 0, y: 8, w: 683, h: 892 },
      head: { cx: 340, cy: 122, rx: 70, ry: 102 },
      chinY: 215, neckY: 292, pivot: [340, 268],
      chest: { x: 340, y: 405, rx: 150, ry: 120 },
      shoulderY: 298,
      neck: [[340, 200], [340, 300], 38],
      torso: [[212, 296], [300, 278], [380, 278], [472, 296], [462, 420], [432, 560], [470, 650], [505, 760], [495, 905], [190, 905], [180, 760], [212, 650], [252, 560], [226, 420]],
      arm: { S: [214, 330], E: [152, 560], W: [112, 772], T: [102, 862], r: 38, xMax: 238, dirE: [-150, 165], dirW: [22, -200] },
      armR: { S: [468, 330], E: [530, 560], W: [572, 772], T: [584, 862], r: 38 },
      synthHand: false,
      hairMaxY: 640, hairRootY: 60, hairLen: 520, hairAmp: 10, hairFollow: 300, hairLag: 0.12,
      breathLift: 4, headShift: 10, lean: 6, fade: 120,
    },
  };

  const segDist = (px, py, a, b) => {
    const abx = b[0] - a[0], aby = b[1] - a[1];
    const t = clamp01(((px - a[0]) * abx + (py - a[1]) * aby) / (abx * abx + aby * aby));
    return [Math.hypot(px - a[0] - abx * t, py - a[1] - aby * t), t];
  };
  const inPoly = (x, y, poly) => {
    let c = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const xi = poly[i][0], yi = poly[i][1], xj = poly[j][0], yj = poly[j][1];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
    }
    return c;
  };
  const inArm = (x, y, a) => {
    if (a.outline) {
      if (inPoly(x, y, a.outline)) return true;
      const pad = y > a.W[1] ? 8 : a.outlinePad;
      for (let i = 0, j = a.outline.length - 1; i < a.outline.length; j = i++) {
        if (segDist(x, y, a.outline[j], a.outline[i])[0] < pad) return true;
      }
      return false;
    }
    const r = a.r;
    return segDist(x, y, a.S, a.E)[0] < r || segDist(x, y, a.E, a.W)[0] < r || segDist(x, y, a.W, a.T)[0] < r;
  };
  const angleOf = (v) => Math.atan2(v[1], v[0]);
  const wrapPi = (a) => { while (a > Math.PI) a -= TWO_PI; while (a < -Math.PI) a += TWO_PI; return a; };

  // Cintura da nova referência: o ponto mais estreito é y≈1000, não y=1120.
  const BUST_SIDE = [[700, 329], [750, 331], [800, 326], [850, 334], [900, 357], [950, 379], [1000, 389], [1050, 374], [1100, 331], [1150, 301], [1200, 280], [1250, 260], [1300, 241], [1350, 235], [1450, 240], [1536, 260]];
  AVATARS.bust.torso = [[250, 570], [385, 552], [640, 552], [774, 570],
    ...BUST_SIDE.map(([y, x]) => [1040 - x + 6, y]),
    ...BUST_SIDE.slice().reverse().map(([y, x]) => [x - 6, y])];
  AVATARS.bust.armR.outline = AVATARS.bust.arm.outline.map(([x, y]) => [1040 - x, y]);
  AVATARS.bust.armR.outlinePad = 10;

  // Contorno do tronco independente do antebraço que o encobre na referência.
  const bustSide = (y) => {
    const nodes = BUST_SIDE;
    if (y <= nodes[0][0]) return nodes[0][1];
    for (let k = 1; k < nodes.length; k += 1) {
      if (y > nodes[k][0]) continue;
      const u = clamp01((y - nodes[k - 1][0]) / (nodes[k][0] - nodes[k - 1][0]));
      const p0 = nodes[Math.max(0, k - 2)][1], p1 = nodes[k - 1][1];
      const p2 = nodes[k][1], p3 = nodes[Math.min(nodes.length - 1, k + 1)][1];
      return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u * u * u);
    }
    return nodes[nodes.length - 1][1];
  };

  // pré-calcula rotações-alvo do aceno
  for (const def of Object.values(AVATARS)) {
    const A = def.arm;
    A.L1 = Math.hypot(A.E[0] - A.S[0], A.E[1] - A.S[1]);
    A.L2 = Math.hypot(A.W[0] - A.E[0], A.W[1] - A.E[1]);
    A.dU = wrapPi(angleOf(A.dirE) - angleOf([A.E[0] - A.S[0], A.E[1] - A.S[1]]));
    let dF = wrapPi(angleOf(A.dirW) - angleOf([A.W[0] - A.E[0], A.W[1] - A.E[1]]));
    // No busto de mãos juntas, usa o caminho curto a partir da nova pose de repouso.
    if (dF < 0 && !A.shortestWave) dF += TWO_PI;
    A.dF = dF;
  }

  /* ---------- carregamento e amostragem ---------- */
  const prepCache = {};
  const prepareFromImage = (def, img) => {
    const SW = 400, SH = Math.round((SW * def.crop.h) / def.crop.w);
    const c = document.createElement('canvas');
    c.width = SW; c.height = SH;
    const g = c.getContext('2d', { willReadFrequently: true });
    g.drawImage(img, def.crop.x, def.crop.y, def.crop.w, def.crop.h, 0, 0, SW, SH);
    const data = g.getImageData(0, 0, SW, SH).data;
    const lum = new Float32Array(SW * SH);
    const cdf = new Float64Array(SW * SH);
    let total = 0;
    for (let i = 0; i < SW * SH; i += 1) {
      const l = Math.max(data[i * 4], data[i * 4 + 1], data[i * 4 + 2]) / 255;
      lum[i] = l;
      total += l > 0.09 ? Math.pow(l - 0.09, 1.6) : 0;
      cdf[i] = total;
    }
    return { SW, SH, lum, cdf, total };
  };

  const loadAvatar = (key) => {
    if (prepCache[key]) return prepCache[key];
    const def = AVATARS[key];
    prepCache[key] = new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(prepareFromImage(def, img));
      img.onerror = () => resolve(null);
      img.src = def.src;
    });
    return prepCache[key];
  };

  const mulberry = (a) => () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };

  // gera os alvos: [0, orbCount) ordenados por altura (casam com a esfera); depois os extras
  const sampleTargets = (def, prep, holoCount, orbCount) => {
    const base = Math.max(holoCount, orbCount);
    const synthN = def.synthHand ? Math.round(base * 0.05) : 0;
    const fillN = def.layeredTorso ? Math.min(600, Math.round(base * 0.03)) : 0;
    const N = base + synthN + fillN;
    const rand = mulberry(17);
    const T = {
      count: N, synthStart: base,
      x: new Float32Array(N), y: new Float32Array(N), lum: new Float32Array(N),
      delay: new Float32Array(N), sign: new Float32Array(N), seed: new Float32Array(N),
      tone: new Uint8Array(N), headW: new Float32Array(N), hairW: new Float32Array(N),
      hz: new Float32Array(N), rise: new Float32Array(N), chestW: new Float32Array(N),
      armT: new Float32Array(N), handW: new Float32Array(N), fade: new Float32Array(N), synth: new Uint8Array(N),
    };
    if (fillN) {
      T.baseCount = base;
      T.underlay = new Uint8Array(N);
      T.attachment = new Float32Array(N);
    }
    const { SW, SH, lum, cdf, total } = prep;
    const sx = def.crop.w / SW, sy = def.crop.h / SH;
    const pick = () => {
      const v = rand() * total;
      let lo = 0, hi = SW * SH - 1;
      while (lo < hi) { const mid = (lo + hi) >> 1; if (cdf[mid] < v) lo = mid + 1; else hi = mid; }
      return lo;
    };
    const tmp = [];
    for (let k = 0; k < base; k += 1) {
      const idx = pick();
      tmp.push([def.crop.x + ((idx % SW) + rand()) * sx, def.crop.y + (Math.floor(idx / SW) + rand()) * sy, lum[idx]]);
    }
    const head = tmp.slice(0, Math.min(orbCount, base)).sort((a, b) => b[1] - a[1]);
    for (let k = 0; k < head.length; k += 1) tmp[k] = head[k];
    for (let k = 0; k < base; k += 1) { T.x[k] = tmp[k][0]; T.y[k] = tmp[k][1]; T.lum[k] = tmp[k][2]; }

    // mão procedural (busto): o braço da imagem termina antes do punho
    if (synthN) {
      const A = def.arm;
      const dx = A.T[0] - A.W[0], dy = A.T[1] - A.W[1], L = Math.hypot(dx, dy);
      const ux = dx / L, uy = dy / L, vx = -uy, vy = ux;
      const hl = def.handLen, hw = def.handW;
      for (let k = 0; k < synthN; k += 1) {
        let u, v;
        const r = rand();
        if (r < 0.42) { // palma
          const a = rand() * TWO_PI, rr = Math.sqrt(rand());
          u = hl * 0.36 + Math.cos(a) * rr * hl * 0.2; v = Math.sin(a) * rr * hw * 0.5;
        } else if (r < 0.9) { // quatro dedos
          const f = Math.floor(rand() * 4);
          const fl = [0.86, 1, 0.95, 0.78][f];
          u = hl * 0.52 + rand() * hl * 0.45 * fl; v = (-0.36 + f * 0.24) * hw + (rand() - 0.5) * hw * 0.14;
        } else { // polegar
          const s = rand();
          u = hl * (0.25 + s * 0.3); v = -hw * (0.5 + s * 0.4) + (rand() - 0.5) * hw * 0.12;
        }
        const i = base + k;
        T.x[i] = A.T[0] + ux * u + vx * v;
        T.y[i] = A.T[1] + uy * u + vy * v;
        T.lum[i] = 0.35 + rand() * 0.55;
        T.synth[i] = 1;
      }
    }

    const h = def.head, A = def.arm, R = def.armR;
    const bottom = def.crop.y + def.crop.h;
    for (let i = 0; i < base + synthN; i += 1) {
      const x = T.x[i], y = T.y[i];
      T.seed[i] = rand() * TWO_PI;
      T.sign[i] = rand() < 0.5 ? -1 : 1;
      T.tone[i] = Math.min(TONE_BUCKETS - 1, Math.floor(rand() * TONE_BUCKETS));
      const d = Math.hypot((x - def.chest.x) / def.crop.h * 1.1, (y - def.chest.y) / def.crop.h);
      T.delay[i] = clamp01(d / 0.62 * 0.7 + rand() * 0.3);
      const hdx = (x - h.cx) / h.rx, hdy = (y - h.cy) / h.ry;
      const e = hdx * hdx + hdy * hdy;
      const inHead = e < 1;
      T.hz[i] = inHead ? Math.sqrt(1 - e) : 0;
      // braço que acena
      let armT = -1, handW = 0;
      if (T.synth[i]) { armT = 1; handW = 1; }
      else if (A.outline ? inArm(x, y, A) : y > A.S[1] - 12 && x < A.xMax) {
        const [d1, t1] = segDist(x, y, A.S, A.E);
        const [d2, t2] = segDist(x, y, A.E, A.W);
        const [d3, t3] = segDist(x, y, A.W, A.T);
        const m = Math.min(d1, d2, d3);
        // As mãos do novo busto se encontram; o aceno não deve puxar a outra mão.
        const rightDistance = def.separateHands ? Math.min(segDist(x, y, R.S, R.E)[0], segDist(x, y, R.E, R.W)[0], segDist(x, y, R.W, R.T)[0]) : Infinity;
        if ((A.outline || m < A.r) && m <= rightDistance) {
          const s = d1 <= d2 && d1 <= d3 ? t1 * A.L1 : d2 <= d3 ? A.L1 + t2 * A.L2 : A.L1 + A.L2 + t3 * 60;
          armT = sstep(A.L1 - 28, A.L1 + 28, s);
          // O punho fica antes dos dedos: a mão inteira acompanha a rotação.
          handW = A.outline ? sstep(0, 0.2, t3) : sstep(A.L1 + A.L2 - 12, A.L1 + A.L2 + 20, s);
        }
      }
      // A borda do tórax e da cintura não pertence ao braço, mesmo se as máscaras se tocam.
      if (def.layeredTorso && y < 1060 && x > bustSide(y) - 4) { armT = -1; handW = 0; }
      T.armT[i] = armT; T.handW[i] = handW;
      if (T.attachment && armT >= 0) {
        const travel = ((x - A.S[0]) * (A.E[0] - A.S[0]) + (y - A.S[1]) * (A.E[1] - A.S[1])) / A.L1;
        T.attachment[i] = armT > 0.5 ? 1 : sstep(0, 120, travel);
      }
      const core = inHead || segDist(x, y, def.neck[0], def.neck[1])[0] < def.neck[2] || inPoly(x, y, def.torso) || inArm(x, y, A) || inArm(x, y, R);
      const hair = !core && !T.synth[i] && y < def.hairMaxY && y > h.cy - h.ry * 1.3;
      T.hairW[i] = hair ? 1 : 0;
      if (T.synth[i] || armT >= 0) T.headW[i] = 0;
      else if (hair) T.headW[i] = y < def.chinY ? 1 : clamp01(1 - (y - def.chinY) / def.hairFollow) * 0.9;
      else T.headW[i] = sstep(def.neckY, def.chinY, y) * (Math.abs(x - h.cx) < h.rx * 1.7 ? 1 : 0);
      T.rise[i] = clamp01((bottom - y) / (bottom - def.shoulderY));
      const cx = (x - def.chest.x) / def.chest.rx, cy = (y - def.chest.y) / def.chest.ry;
      T.chestW[i] = armT >= 0 ? 0 : Math.exp(-(cx * cx + cy * cy));
      T.fade[i] = T.synth[i] ? 1 : sstep(bottom, bottom - def.fade, y);
    }

    // Camada de partículas do abdômen sob o braço: só aparece quando ele se afasta.
    // A imagem frontal não contém esses pixels ocultos; não se pode arrancar o braço
    // e esperar que o tronco atrás dele já esteja amostrado.
    if (fillN) {
      const fillRand = mulberry(72019);
      const readLum = (x, y) => {
        const gx = Math.max(0, Math.min(SW - 1, Math.floor((x - def.crop.x) / sx)));
        const gy = Math.max(0, Math.min(SH - 1, Math.floor((y - def.crop.y) / sy)));
        return lum[gy * SW + gx];
      };
      for (let j = 0; j < fillN; j += 1) {
        const i = base + synthN + j;
        const edge = j < Math.round(fillN * 0.3);
        let x, y;
        for (let attempt = 0; attempt < 300; attempt += 1) {
          y = 1080 + fillRand() * 260;
          const left = bustSide(y);
          const u = ((j % 18) + fillRand() * 0.16) / 18;
          x = edge ? left + 1 + fillRand() * 6 : left + u * (def.chest.x - left) + 3 * Math.sin(y * 0.014 + u * 4);
          if (inArm(x, y, A)) break;
        }
        const sourceY = Math.max(920, y - 180), left = bustSide(y), srcLeft = bustSide(sourceY);
        const sourceX = srcLeft + (x - left) / (def.chest.x - left) * (def.chest.x - srcLeft);
        T.x[i] = x; T.y[i] = y;
        T.lum[i] = edge ? 0.24 + fillRand() * 0.22 : Math.max(0.11, Math.min(0.45, readLum(sourceX, sourceY) * 0.72));
        T.seed[i] = fillRand() * TWO_PI; T.sign[i] = fillRand() < 0.5 ? -1 : 1;
        T.tone[i] = Math.floor(fillRand() * TONE_BUCKETS); T.delay[i] = 0.35 + fillRand() * 0.3;
        T.armT[i] = -1; T.fade[i] = 1; T.underlay[i] = 1;
        T.rise[i] = clamp01((bottom - y) / (bottom - def.shoulderY));
        const cx = (x - def.chest.x) / def.chest.rx, cy = (y - def.chest.y) / def.chest.ry;
        T.chestW[i] = Math.exp(-(cx * cx + cy * cy));
      }
    }
    return T;
  };

  /* ---------- pose ---------- */
  // P: { t, yaw, pitch, roll, yawHair, breath, env, osc, oscH, oscU }
  const applyPose = (def, T, P, ox, oy, om) => {
    const n = T.count;
    const h = def.head, A = def.arm;
    const cyw = Math.cos(P.yaw), syw = Math.sin(P.yaw);
    const cp = Math.cos(P.pitch), sp = Math.sin(P.pitch);
    const cr = Math.cos(P.roll), sr = Math.sin(P.roll);
    const pvx = def.pivot[0], pvy = def.pivot[1];
    const chestLift = P.breath * def.breathLift * 0.24;
    const lean = P.yaw * def.lean;
    const env = P.env;
    const armOn = env > 0.0005;
    const gain = A.waveGain === undefined ? 1 : A.waveGain;
    const thU = env * A.dU + P.oscU * gain, thF = env * A.dF + P.osc * gain, thH = thF + P.oscH * gain;
    const cu = Math.cos(thU), su = Math.sin(thU), cf = Math.cos(thF), sf = Math.sin(thF), ch = Math.cos(thH), sh = Math.sin(thH);
    const Sx = A.S[0], Sy = A.S[1];
    const Ex = Sx + cu * (A.E[0] - Sx) - su * (A.E[1] - Sy), Ey = Sy + su * (A.E[0] - Sx) + cu * (A.E[1] - Sy);
    const Wx = Ex + cf * (A.W[0] - A.E[0]) - sf * (A.W[1] - A.E[1]), Wy = Ey + sf * (A.W[0] - A.E[0]) + cf * (A.W[1] - A.E[1]);
    const handA = sstep(0.35, 0.9, env);
    const hairDiff = (P.yaw - P.yawHair);
    const t = P.t;
    for (let i = 0; i < n; i += 1) {
      let x = T.x[i], y = T.y[i];
      const at = T.armT[i];
      let alpha = T.fade[i];
      if (at >= 0 && armOn) {
        const dx0 = x - Sx, dy0 = y - Sy;
        const ux = Sx + cu * dx0 - su * dy0, uy = Sy + su * dx0 + cu * dy0;
        const ex = x - A.E[0], ey = y - A.E[1];
        let fx = Ex + cf * ex - sf * ey, fy = Ey + sf * ex + cf * ey;
        const hw = T.handW[i];
        if (hw > 0) {
          const wx = x - A.W[0], wy = y - A.W[1];
          const hx = Wx + ch * wx - sh * wy, hy = Wy + sh * wx + ch * wy;
          fx += (hx - fx) * hw; fy += (hy - fy) * hw;
        }
        if (A.outline) {
          // Interpola o ângulo em torno do cotovelo, não duas posições:
          // a articulação mantém volume mesmo com o antebraço dobrado.
          // Ângulos contínuos: não inverter a dobra ao cruzar ±PI.
          const theta = thU + (thF - thU) * at;
          const c = Math.cos(theta), s = Math.sin(theta);
          x = Ex + c * ex - s * ey;
          y = Ey + s * ex + c * ey;
          if (hw > 0) {
            const wx = T.x[i] - A.W[0], wy = T.y[i] - A.W[1];
            x += (Wx + ch * wx - sh * wy - x) * hw;
            y += (Wy + sh * wx + ch * wy - y) * hw;
          }
          const attach = T.attachment ? T.attachment[i] : 1;
          x = T.x[i] + (x - T.x[i]) * attach;
          y = T.y[i] + (y - T.y[i]) * attach;
        } else {
          x = ux + (fx - ux) * at; y = uy + (fy - uy) * at;
        }
        alpha += (1 - alpha) * env;
      }
      if (T.underlay && T.underlay[i]) alpha *= sstep(0.04, 0.28, env);
      if (T.synth[i]) alpha = handA;
      const hwt = T.headW[i];
      if (hwt > 0) {
        const dx = x - h.cx, dy = y - h.cy, z = T.hz[i];
        const nx = dx * cyw + z * h.rx * syw * 0.85;
        const ny = dy * cp + z * h.ry * sp * 0.5;
        const rx = h.cx + nx - pvx, ry = h.cy + ny - pvy;
        const fx = pvx + rx * cr - ry * sr + P.yaw * def.headShift;
        const fy = pvy + rx * sr + ry * cr + P.pitch * def.headShift * 0.7;
        x += (fx - x) * hwt; y += (fy - y) * hwt;
      }
      const hr = T.hairW[i];
      if (hr > 0) {
        const k = clamp01((y - def.hairRootY) / def.hairLen);
        const s = T.seed[i];
        const amp = 0.8 + def.hairAmp * k;
        x += amp * (0.62 * Math.sin(t * 1.15 + y * 0.011 + s * 0.35) + 0.38 * Math.sin(t * 2.05 + y * 0.024 + s)) - hairDiff * k * def.hairLen * def.hairLag;
        y += k * 1.6 * Math.sin(t * 1.6 + s);
      }
      const cw = T.chestW[i];
      if (cw > 0.01) {
        x += (x - def.chest.x) * 0.014 * P.breath * cw;
        y += ((y - def.chest.y) * 0.01 * P.breath - chestLift) * cw;
      }
      const r = T.rise[i];
      x += lean * r * r;
      ox[i] = x; oy[i] = y; om[i] = alpha;
    }
  };

  // envelope do aceno: sobe (0.9s), acena (~2.2s), desce (0.9s)
  const WAVE_DURATION = 4.0;
  const waveAt = (w, def) => {
    // A nova pose começa com o braço bem dobrado; dá tempo para abri-lo sem chicotear.
    if (def && def.waveDuration) w *= WAVE_DURATION / def.waveDuration;
    if (w < 0 || w > WAVE_DURATION) return { env: 0, osc: 0, oscH: 0, oscU: 0 };
    const up = sstep(0, 0.95, w), down = 1 - sstep(WAVE_DURATION - 0.95, WAVE_DURATION, w);
    const env = Math.min(up, down);
    const hold = sstep(0.7, 1.1, w) * (1 - sstep(WAVE_DURATION - 1.1, WAVE_DURATION - 0.7, w));
    const ph = (w - 0.7) * TWO_PI * 1.55;
    return { env, osc: hold * 0.3 * Math.sin(ph), oscH: hold * 0.28 * Math.sin(ph - 0.9), oscU: hold * 0.035 * Math.sin(ph + 0.4) };
  };

  root.ElysiaRig = { AVATARS, loadAvatar, prepareFromImage, sampleTargets, applyPose, waveAt, WAVE_DURATION, TONE_BUCKETS };
})(window);
