// Ícones, painéis contextuais e controles da interface E.L.Y.S.I.A.
const { useState: useStateP, useEffect: useEffectP, useRef: useRefP } = React;

const Icon = ({ name }) => {
  const p = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.4, strokeLinecap: 'round', strokeLinejoin: 'round' };
  const paths = {
    chat: <><path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v7a2.5 2.5 0 0 1-2.5 2.5H10l-4 3.5V16h0a2 2 0 0 1-2-2z" {...p} /></>,
    voice: <><rect x="9" y="3.5" width="6" height="11" rx="3" {...p} /><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v2.5" {...p} /></>,
    library: <><path d="M5 4.5h3.5v15H5zM10.5 4.5H14v15h-3.5z" {...p} /><path d="m16 5.2 3.2-.8 3 14.4-3.2.8z" {...p} transform="translate(-2.2 0)" /></>,
    code: <><path d="m8.5 8-4 4 4 4M15.5 8l4 4-4 4M13.2 6l-2.4 12" {...p} /></>,
    media: <><rect x="3.5" y="5" width="17" height="14" rx="2.5" {...p} /><path d="m3.5 15.5 4.5-4 4 3.5 2.5-2 6 4.5" {...p} /><circle cx="15.5" cy="9.5" r="1.4" {...p} /></>,
    settings: <><path d="M4 7h9M17 7h3M4 17h3M11 17h9" {...p} /><circle cx="15" cy="7" r="2.2" {...p} /><circle cx="9" cy="17" r="2.2" {...p} /></>,
    workbench: <><rect x="4" y="4" width="16" height="16" rx="2" {...p}/><path d="M7 8h10M7 12h5M7 16h7" {...p}/></>,
    capabilities: <><circle cx="12" cy="5" r="2" {...p}/><circle cx="6" cy="18" r="2" {...p}/><circle cx="18" cy="18" r="2" {...p}/><path d="m11 7-4 9m6-9 4 9M8 18h8" {...p}/></>,
    close: <path d="M6 6l12 12M18 6 6 18" {...p} />,
    send: <path d="M5 12h13M13 6.5 18.5 12 13 17.5" {...p} />,
    attach: <path d="m19 11.5-7 7a4.5 4.5 0 0 1-6.4-6.4l7.6-7.6a3 3 0 0 1 4.2 4.2l-7.4 7.4a1.5 1.5 0 0 1-2.1-2.1l6.6-6.6" {...p} />,
    search: <><circle cx="11" cy="11" r="6" {...p} /><path d="m20 20-4.5-4.5" {...p} /></>,
  };
  return <svg viewBox="0 0 24 24" aria-hidden="true">{paths[name]}</svg>;
};

const MODULES = [
  { id: 'chat', label: 'Conversa por texto' },
  { id: 'voice', label: 'Conversa por voz' },
  { id: 'library', label: 'Biblioteca · Knowledge Vault' },
  { id: 'code', label: 'Código e ferramentas' },
  { id: 'media', label: 'Media Studio' },
  { id: 'workbench', label: 'Bancada de análise' },
  { id: 'capabilities', label: 'Habilidades e evolução' },
  { id: 'settings', label: 'Aparência e configurações' },
];

const STATE_LABELS = {
  idle: 'Em repouso', connecting: 'Conectando', listening: 'Ouvindo', thinking: 'Pensando',
  speaking: 'Falando', error: 'Falha — algo deu errado', disabled: 'Desativada',
};

const Rail = ({ open, onOpen }) => (
  <nav className="rail" aria-label="Módulos">
    {MODULES.map((m) => (
      <button
        key={m.id}
        className="rail-btn"
        aria-label={m.label}
        aria-expanded={open === m.id}
        aria-controls="context-panel"
        data-active={open === m.id || undefined}
        onClick={() => onOpen(open === m.id ? null : m.id)}
      >
        <Icon name={m.id} />
        <span className="tip" role="tooltip">{m.label}</span>
      </button>
    ))}
  </nav>
);

const PanelHead = ({ title, kicker, onClose }) => (
  <header className="panel-head">
    <div>
      {kicker && <span className="kicker">{kicker}</span>}
      <h2>{title}</h2>
    </div>
    <button className="icon-btn" onClick={onClose} aria-label="Fechar painel (Esc)"><Icon name="close" /></button>
  </header>
);

const DemoTag = ({ children = 'Demonstração' }) => <span className="demo-tag">{children}</span>;

/* ---------- Conversa por texto ---------- */
const ChatPanel = ({ messages, onSend, busy, error, onReset, onExport, onImport, onClose }) => {
  const [text, setText] = useStateP('');
  const listRef = useRefP(null);
  const inputRef = useRefP(null);
  useEffectP(() => { inputRef.current?.focus(); }, []);
  useEffectP(() => { const el = listRef.current; if (el) el.scrollTop = el.scrollHeight; }, [messages]);
  const submit = (e) => {
    e.preventDefault();
    const v = text.trim();
    if (!v || busy) return;
    onSend(v);
    setText('');
  };
  return (
    <>
      <PanelHead title="Conversa" kicker="Neural Core próprio · experimental" onClose={onClose} />
      <p className="note-block">Modelo local em desenvolvimento. Pode produzir respostas incorretas ou repetitivas. Histórico salvo neste navegador; contexto curto. Exporte um backup para guardar fora do computador.</p>
      <button className="pill-btn ghost" disabled={busy} onClick={onReset}>Nova conversa</button>
      <div className="backup-controls">
        <button className="pill-btn ghost" disabled={busy} onClick={onExport}>Exportar backup</button>
        <label className="pill-btn ghost">Restaurar backup
          <input type="file" accept=".json,application/json" disabled={busy} aria-label="Restaurar backup"
            onChange={(e) => { onImport(e.target.files?.[0]); e.target.value = ''; }} />
        </label>
      </div>
      {error && <p className="note-block" role="alert">{error}</p>}
      <div className="chat-list" ref={listRef} aria-live="polite">
        {messages.length === 0 && (
          <p className="empty">Escreva uma mensagem curta para conversar com o núcleo local da Elysia.</p>
        )}
        {messages.map((m) => (
          <div key={m.id} className={'msg msg-' + m.role}>
            {m.role === 'elysia' && <div className="msg-meta">Elysia · Neural Core</div>}
            <p>{m.shown ?? m.text}{m.typing && <span className="caret" aria-hidden="true" />}</p>
          </div>
        ))}
      </div>
      <form className="composer" onSubmit={submit}>
        <button type="button" className="icon-btn" aria-label="Anexar arquivo (não conectado)" title="Anexos não conectados nesta versão" disabled><Icon name="attach" /></button>
        <label className="sr-only" htmlFor="msg">Mensagem</label>
        <input id="msg" ref={inputRef} value={text} onChange={(e) => setText(e.target.value)} placeholder="Mensagem para Elysia" autoComplete="off" />
        <button type="submit" className="icon-btn send" aria-label="Enviar" disabled={!text.trim() || busy}><Icon name="send" /></button>
      </form>
    </>
  );
};

/* ---------- Conversa por voz ---------- */
const VoicePanel = ({ state, onListen, onRespond, onStop, onClose }) => (
  <>
    <PanelHead title="Voz" kicker="Simulação" onClose={onClose} />
    <p className="note-block">Microfone desligado. Não há reconhecimento nem síntese de voz conectados — os botões abaixo apenas simulam o fluxo para ver a presença da Elysia reagir.</p>
    <div className="voice-flow">
      <button className="pill-btn" aria-pressed={state === 'listening'} onClick={onListen}>
        <span className="dot" /> Simular escuta
      </button>
      <button className="pill-btn" aria-pressed={state === 'speaking' || state === 'thinking'} onClick={onRespond}>
        <span className="dot" /> Simular resposta
      </button>
      <button className="pill-btn ghost" onClick={onStop}>Encerrar</button>
    </div>
    <ol className="steps">
      <li data-on={state === 'listening' || undefined}>Ouvindo <span>orbe em ondulação</span></li>
      <li data-on={state === 'thinking' || undefined}>Processando <span>pulso contido</span></li>
      <li data-on={state === 'speaking' || undefined}>Respondendo <span>forma humanoide</span></li>
      <li data-on={state === 'idle' || undefined}>Repouso <span>retorna ao orbe</span></li>
    </ol>
  </>
);

/* ---------- Aparência e configurações ---------- */
const HEX_RE = /^#[0-9a-f]{6}$/i;

const HexField = ({ label, value, onChange }) => {
  const [draft, setDraft] = useStateP(value);
  useEffectP(() => setDraft(value), [value]);
  const valid = HEX_RE.test(draft);
  return (
    <label className="hex-field" data-invalid={!valid || undefined}>
      <span>{label}</span>
      <input type="color" value={value} aria-label={label + ' (seletor)'} onInput={(e) => onChange(e.currentTarget.value)} onChange={(e) => onChange(e.currentTarget.value)} />
      <input
        type="text" value={draft} maxLength={7} spellCheck={false} aria-label={label + ' (hexadecimal)'} aria-invalid={!valid}
        onChange={(e) => { let v = e.target.value.trim(); if (v && v[0] !== '#') v = '#' + v; setDraft(v); if (HEX_RE.test(v)) onChange(v.toLowerCase()); }}
        onBlur={() => { if (!HEX_RE.test(draft)) setDraft(value); }}
      />
    </label>
  );
};

const SettingsPanel = ({ prefs, setPrefs, state, setDemoState, manual, setManual, level, setLevel, onReplayIntro, onClose }) => {
  const set = (k, v) => setPrefs((old) => ({ ...old, [k]: v }));
  const colors = prefs.palette === 'custom' ? prefs.custom : PALETTES[prefs.palette];
  return (
    <>
      <PanelHead title="Aparência" kicker="Configurações" onClose={onClose} />

      <section className="set-group" aria-labelledby="pal-h">
        <h3 id="pal-h">Paleta <span className="muted">{prefs.palette === 'custom' ? 'Personalizada' : PALETTES[prefs.palette].label}</span></h3>
        <div className="swatches" role="radiogroup" aria-label="Paletas de cores">
          {Object.entries(PALETTES).map(([key, v]) => (
            <button key={key} role="radio" aria-checked={prefs.palette === key} title={v.label} aria-label={v.label}
              onClick={() => set('palette', key)}>
              <span className="sw" style={{ background: `linear-gradient(135deg, ${v.from}, ${v.to})` }} />
              <span className="sw-label">{v.label}</span>
            </button>
          ))}
          <button role="radio" aria-checked={prefs.palette === 'custom'} aria-label="Personalizada"
            onClick={() => setPrefs((o) => ({ ...o, palette: 'custom', custom: o.palette === 'custom' ? o.custom : { from: colors.from, to: colors.to } }))}>
            <span className="sw sw-custom" style={{ background: `linear-gradient(135deg, ${prefs.custom.from}, ${prefs.custom.to})` }} />
            <span className="sw-label">Personalizada</span>
          </button>
        </div>
        {prefs.palette === 'custom' && (
          <div className="custom-row">
            <HexField label="Cor inicial" value={prefs.custom.from} onChange={(v) => set('custom', { ...prefs.custom, from: v })} />
            <HexField label="Cor final" value={prefs.custom.to} onChange={(v) => set('custom', { ...prefs.custom, to: v })} />
          </div>
        )}
      </section>

      <section className="set-group">
        <h3>Presença</h3>
        <label className="range">
          <span>Tamanho do orbe <output>{prefs.size}px</output></span>
          <input type="range" min="120" max="320" step="4" value={prefs.size} onChange={(e) => set('size', +e.target.value)} />
        </label>
        <label className="range">
          <span>Velocidade <output>{prefs.speed.toFixed(1)}×</output></span>
          <input type="range" min="0" max="2" step="0.1" value={prefs.speed} onChange={(e) => set('speed', +e.target.value)} />
        </label>
        <label className="check">
          <input type="checkbox" checked={prefs.morph} onChange={(e) => set('morph', e.target.checked)} />
          <span>Assumir forma humanoide ao falar</span>
        </label>
        <button className="link-btn" onClick={() => setPrefs((o) => ({ ...o, palette: 'original', size: 212, speed: 1 }))}>Restaurar referência (violeta/magenta · 212px · 1×)</button>
      </section>

      <section className="set-group">
        <h3>Teste de estados <DemoTag /></h3>
        <div className="state-grid">
          {Object.keys(STATE_LABELS).map((s) => (
            <button key={s} aria-pressed={state === s} onClick={() => setDemoState(s)}>{STATE_LABELS[s].split(' —')[0]}</button>
          ))}
        </div>
        <label className="check">
          <input type="checkbox" checked={manual} onChange={(e) => setManual(e.target.checked)} />
          <span>Nível simulado</span>
        </label>
        {manual && (
          <label className="range">
            <span>Amplitude <output>{Math.round(level * 100)}%</output></span>
            <input type="range" min="0" max="1" step="0.01" value={level} onChange={(e) => setLevel(+e.target.value)} />
          </label>
        )}
      </section>

      <section className="set-group">
        <h3>Abertura</h3>
        <button className="pill-btn ghost" onClick={onReplayIntro}>Rever abertura provisória</button>
      </section>
      <p className="note-block">Apenas preferências de aparência são salvas neste navegador. Áudio, credenciais e conversas não são armazenados.</p>
    </>
  );
};

/* ---------- Abertura provisória (IntroSlot) ---------- */
// Ponto de integração para a intro cinematográfica original: passe `children` para substituir.
const IntroSlot = ({ onDone, children }) => {
  const [phase, setPhase] = useStateP('in');
  useEffectP(() => {
    if (children) return;
    const reduced = prefersReducedMotion();
    const t1 = setTimeout(() => setPhase('bloom'), reduced ? 300 : 2700);
    const t2 = setTimeout(() => setPhase('out'), reduced ? 600 : 3500);
    const t3 = setTimeout(onDone, reduced ? 900 : 4200);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, []);
  return (
    <div className="intro" data-phase={phase} aria-label="Abertura">
      {children || (
        <>
          <div className="intro-line" />
          <div className="intro-core" />
          <div className="intro-word" aria-hidden="true">{'E.L.Y.S.I.A.'.split('').map((c, i) => <span key={i} style={{ '--i': i }}>{c}</span>)}</div>
        </>
      )}
      <button className="skip" onClick={onDone}>Pular</button>
    </div>
  );
};

Object.assign(window, { Icon, MODULES, STATE_LABELS, Rail, ChatPanel, VoicePanel, SettingsPanel, IntroSlot, DemoTag });
