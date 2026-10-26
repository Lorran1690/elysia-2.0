// App — composição principal da E.L.Y.S.I.A.
const { useState, useEffect: useEffectA, useRef: useRefA, useCallback: useCallbackA } = React;

const PREFS_KEY = 'elysia.appearance.v1';
const DEFAULT_PREFS = { palette: 'original', custom: { from: '#8b5cf6', to: '#d946ef' }, size: 212, speed: 1, morph: true, avatar: 'bust', orbCount: 720, holoCount: 12000, holoScale: 0.86, greet: true };
const num = (v, a, b, d) => (Number.isFinite(v) ? Math.min(b, Math.max(a, v)) : d);
const HEX = /^#[0-9a-f]{6}$/i;

const loadPrefs = () => {
  try {
    const raw = JSON.parse(localStorage.getItem(PREFS_KEY) || 'null');
    if (!raw || typeof raw !== 'object') return DEFAULT_PREFS;
    return {
      palette: raw.palette === 'custom' || PALETTES[raw.palette] ? raw.palette : 'original',
      custom: { from: HEX.test(raw.custom?.from) ? raw.custom.from : '#8b5cf6', to: HEX.test(raw.custom?.to) ? raw.custom.to : '#d946ef' },
      size: num(raw.size, 120, 640, 212),
      speed: num(raw.speed, 0, 2, 1),
      morph: raw.morph !== false,
      avatar: raw.avatar === 'body' ? 'body' : 'bust',
      orbCount: num(raw.orbCount, 360, 6000, 720),
      holoCount: num(raw.holoCount, 3000, 30000, 12000),
      holoScale: num(raw.holoScale, 0.45, 1, 0.86),
      greet: raw.greet !== false,
    };
  } catch { return DEFAULT_PREFS; }
};

const CHAT_KEY = 'elysia.conversation.v1';
const validateBackup = (data) => {
  if (data?.format !== 'elysia-conversation-v1' || !Array.isArray(data.messages)
      || data.messages.length > 32 || data.messages.length % 2 !== 0) throw new Error('Backup inválido.');
  return data.messages.map((m, i) => {
    if (m?.role !== (i % 2 ? 'assistant' : 'user') || typeof m.content !== 'string'
        || !m.content.trim() || m.content.length > 4000) throw new Error('Mensagem inválida no backup.');
    return { role: m.role, content: m.content };
  });
};

const useSize = (ref) => {
  const [s, setS] = useState({ w: 0, h: 0 });
  useEffectA(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => {
      const r = e.contentRect;
      setS({ w: Math.round(r.width), h: Math.round(r.height) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref]);
  return s;
};

const App = () => {
  const [prefs, setPrefs] = useState(loadPrefs);
  const [state, setState] = useState('connecting');
  const [open, setOpen] = useState(null);
  const [intro, setIntro] = useState(() => sessionStorage.getItem('elysia.introSeen') !== '1');
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [manual, setManual] = useState(false);
  const [level, setLevel] = useState(0.45);
  const [formProgress, setFormProgress] = useState(0);
  const [caption, setCaption] = useState('');
  const [greeting, setGreeting] = useState(false);
  const [pinHuman, setPinHuman] = useState(false);
  const [waveKey, setWaveKey] = useState(0);
  const greeted = useRefA(false);
  const levelRef = useRefA(-1);
  const timers = useRefA([]);
  const stageRef = useRefA(null);
  const stage = useSize(stageRef);
  const conversation = useRefA([]);
  const pending = useRefA(false);
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);

  useEffectA(() => { levelRef.current = manual ? level : -1; }, [manual, level]);
  useEffectA(() => { try { localStorage.setItem(PREFS_KEY, JSON.stringify(prefs)); } catch {} }, [prefs]);

  const clearTimers = () => { timers.current.forEach(clearTimeout); timers.current = []; };
  const later = (fn, ms) => { timers.current.push(setTimeout(fn, ms)); };

  const displayHistory = (history) => history.map((m, i) => ({
    id: 'restored-' + i, role: m.role === 'assistant' ? 'elysia' : 'user', text: m.content,
  }));
  const persistChat = (history) => {
    try { localStorage.setItem(CHAT_KEY, JSON.stringify({format: 'elysia-conversation-v1', messages: history})); }
    catch { setError('Não foi possível salvar neste navegador. Use Exportar backup.'); }
  };
  useEffectA(() => {
    try {
      const saved = localStorage.getItem(CHAT_KEY);
      if (saved) {
        const history = validateBackup(JSON.parse(saved));
        conversation.current = history; setMessages(displayHistory(history));
      }
    } catch { setError('Não foi possível restaurar o histórico salvo. Você pode importar um backup.'); }
  }, []);

  useEffectA(() => {
    let active = true;
    fetch('/api/health').then((r) => {
      if (!r.ok) throw new Error('Núcleo indisponível');
      return r.json();
    }).then((data) => { if (active) { setReady(data.ready); setState(data.ready ? 'idle' : 'error'); } })
      .catch(() => { if (active) { setState('error'); setError('Não foi possível conectar ao núcleo. Reinicie o servidor e recarregue a página.'); } });
    return () => { active = false; clearTimers(); };
  }, []);

  useEffectA(() => {
    const onKey = (e) => { if (e.key === 'Escape') setOpen(null); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Apresenta o texto gerado com a transição visual para a forma humanoide.
  const speak = useCallbackA((text, withMessage) => {
    clearTimers();
    setBusy(true);
    setState('thinking');
    setCaption('');
    const id = Date.now();
    later(() => {
      setState('speaking');
      if (withMessage) setMessages((m) => [...m, { id, role: 'elysia', text, shown: '', typing: true }]);
      // aguarda a forma humanoide se formar antes de "falar" o texto
      const startDelay = prefs.morph ? 900 : 200;
      const cps = 30;
      const total = Math.ceil(text.length / cps * 1000);
      for (let k = 1; k <= 40; k += 1) {
        later(() => {
          const shown = text.slice(0, Math.round((text.length * k) / 40));
          if (withMessage) setMessages((m) => m.map((x) => (x.id === id ? { ...x, shown } : x)));
          setCaption(shown);
        }, startDelay + (total * k) / 40);
      }
      later(() => {
        if (withMessage) setMessages((m) => m.map((x) => (x.id === id ? { ...x, shown: undefined, typing: false } : x)));
        setState('idle');
        setBusy(false);
        later(() => setCaption(''), 1600);
      }, startDelay + total + 900);
    }, 1300);
  }, [prefs.morph]);

  const sendMessage = async (text) => {
    if (pending.current || !ready) return;
    setGreeting(false);
    pending.current = true;
    setBusy(true); setError(''); setState('thinking'); setCaption('');
    const candidate = [...conversation.current, { role: 'user', content: text }];
    const id = Date.now() + Math.random();
    setMessages((m) => [...m, { id, role: 'user', text }]);
    try {
      const response = await fetch('/api/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: candidate }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Falha na resposta.');
      if (!data.reply?.trim()) throw new Error('Resposta vazia do núcleo.');
      conversation.current = [...candidate, { role: 'assistant', content: data.reply }];
      persistChat(conversation.current);
      speak(data.reply, true);
    } catch (err) {
      setMessages((m) => m.filter((message) => message.id !== id));
      setError(err.message + ' Sua mensagem não foi adicionada ao histórico.');
      setState('error'); setBusy(false);
    } finally { pending.current = false; }
  };

  const resetChat = () => {
    if (busy || pending.current) return;
    clearTimers(); conversation.current = []; setMessages([]); setError(''); setCaption(''); persistChat([]);
    setState(ready ? 'idle' : 'error');
  };
  const exportChat = () => {
    const blob = new Blob([JSON.stringify({format: 'elysia-conversation-v1',
      exported_at: new Date().toISOString(), messages: conversation.current}, null, 2)], {type:'application/json'});
    const url = URL.createObjectURL(blob); const link = document.createElement('a');
    link.href = url; link.download = 'elysia-conversa-' + new Date().toISOString().replace(/[:.]/g, '-') + '.json';
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const importChat = async (file) => {
    if (!file || busy || pending.current) return;
    try {
      if (file.size > 262144) throw new Error('Backup grande demais.');
      const history = validateBackup(JSON.parse(await file.text()));
      clearTimers(); conversation.current = history; setMessages(displayHistory(history));
      setCaption(''); setError(''); persistChat(history); setState(ready ? 'idle' : 'error');
    } catch (err) { setError('Não foi possível importar: ' + err.message); }
  };
  const endGreeting = useCallbackA(() => setGreeting(false), []);
  const greet = () => { if (!busy && !pending.current) { setGreeting(true); setWaveKey((k) => k + 1); } };
  useEffectA(() => {
    if (intro || !ready || greeted.current) return;
    greeted.current = true;
    if (prefs.greet) greet();
  }, [intro, ready]);
  useEffectA(() => {
    if (!greeting) return;
    // Fallback also ends the greeting with reduced motion or an unavailable image.
    const timer = setTimeout(endGreeting, 9000);
    return () => clearTimeout(timer);
  }, [greeting, waveKey, endGreeting]);
  const fitToScreen = () => setPrefs((o) => ({ ...o, size: Math.round(Math.min(640, Math.max(120, Math.min(stage.w, stage.h) * .34)) / 4) * 4, holoScale: .9 }));
  const setDemoState = (s) => { if (!busy && !pending.current) { setCaption(''); setState(s); } };

  const colors = prefs.palette === 'custom' ? prefs.custom : PALETTES[prefs.palette];
  const form = pinHuman || greeting || (prefs.morph && state === 'speaking') ? 1 : 0;
  const human = formProgress > 0.5;
  const statusText = STATE_LABELS[state];

  const panel = {
    chat: <ChatPanel messages={messages} onSend={sendMessage} busy={busy || !ready} error={error} onReset={resetChat} onExport={exportChat} onImport={importChat} onClose={() => setOpen(null)} />,
    voice: <><PanelHead title="Voz" kicker="Pausada" onClose={() => setOpen(null)} /><p className="note-block">O Voice Core permanece pausado. Converse por texto; o avatar acompanha as respostas sem capturar microfone nem reproduzir áudio.</p></>,
    library: <VaultPanel onClose={() => setOpen(null)} />,
    code: <CodeStudioPanel onClose={() => setOpen(null)} />,
    generation: <GenerationPanel onClose={() => setOpen(null)} />,
    media: <MediaStudioPanel onClose={() => setOpen(null)} />,
    workbench: <WorkbenchPanel onClose={() => setOpen(null)} />,
    capabilities: <CapabilitiesPanel onClose={() => setOpen(null)} onNavigate={setOpen} />,
    settings: <SettingsPanel prefs={prefs} setPrefs={setPrefs} state={state} setDemoState={setDemoState}
      manual={manual} setManual={setManual} level={level} setLevel={setLevel}
      onReplayIntro={() => { setOpen(null); setIntro(true); }}
      onWave={greet} pinHuman={pinHuman} setPinHuman={setPinHuman} onFit={fitToScreen}
      onClose={() => setOpen(null)} />,
  }[open];

  const showCaption = caption && (open !== 'chat');

  return (
    <div className="app" data-panel={open ? 'open' : 'closed'} data-human={human || undefined}
      style={{ '--c-from': colors.from, '--c-to': colors.to, '--form': formProgress }}>
      <div className="ambient" aria-hidden="true" />
      <header className="brand">E.L.Y.S.I.A.</header>
      <Rail open={open} onOpen={setOpen} />

      <main className="stage" ref={stageRef}>
        {stage.w > 0 && (
          <ElysiaPresence
            state={state}
            size={prefs.size}
            speed={prefs.speed}
            colorFrom={colors.from}
            colorTo={colors.to}
            levelRef={levelRef}
            form={form}
            onForm={setFormProgress}
            avatar={prefs.avatar} orbCount={prefs.orbCount} holoCount={prefs.holoCount}
            holoScale={prefs.holoScale} waveKey={waveKey} onWaveEnd={endGreeting}
            width={stage.w}
            height={Math.max(prefs.size, stage.h)}
            label={'Elysia: ' + statusText + (human ? ' · forma humanoide' : ' · orbe')}
          />
        )}
        <div className="status" role="status" aria-live="polite" data-state={state}>
          <span className="status-dot" aria-hidden="true" />
          {statusText}
        </div>
        <p className="caption" aria-hidden={!showCaption} data-on={showCaption || undefined}>
          {caption}<span className="caption-tag">Neural Core · experimental</span>
        </p>
      </main>

      <aside id="context-panel" className="panel" data-open={!!open || undefined} aria-label={open ? MODULES.find((m) => m.id === open).label : undefined} aria-hidden={!open}>
        <div className="panel-inner" key={open || 'none'}>{panel}</div>
      </aside>

      {intro && <IntroSlot onDone={() => { sessionStorage.setItem('elysia.introSeen', '1'); setIntro(false); }} />}
    </div>
  );
};

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
