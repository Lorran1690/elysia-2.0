# E.L.Y.S.I.A. Desktop 0.2

Preview isolado do Orb Core 3D com demonstracao dos estados `idle`, `listening`, `thinking`, `connecting` e `speaking`. Esta pasta nao usa nem modifica o motor neural, os pesos, os corpus ou os scripts de treinamento do repositorio.

## Executar no Windows

```powershell
cd desktop
npm install
npm run dev
```

Abra a URL local exibida pelo Vite e use o botao de controles no canto direito. O painel alterna os estados visuais e os perfis `Baixa`, `Media` e `Alta`; a telemetria informa FPS, particulas e conexoes no momento da execucao. Em `listening`, o controle de sinal e uma simulacao manual: o preview nao pede acesso ao microfone.

## Validar

```powershell
npm test
npm run build
```

O host Tauri 2 esta preparado em `src-tauri/`, mas nao deve ser empacotado nesta fase. Para testar a janela nativa depois de validar o preview web e os requisitos locais:

```powershell
npm run tauri dev
```

## Escopo desta entrega

- Orbe real em Three.js/React Three Fiber, com buffers de particulas e de linhas.
- Movimento continuo baseado em tempo, respiracao, cavidades temporarias e transicao entre nuvem, malha e compressao em anel.
- Busca espacial por grade para limitar a procura de conexoes proximas.
- Presets de qualidade adequados para validacao na maquina-alvo.
- Maquina de estados visual tipada, interpolada dentro do mesmo `ParticleOrb` sem recriar buffers por transicao.
- Controles demonstrativos para os cinco estados e entrada de intensidade sonora simulada entre `0` e `1`.

O chat cinematografico e qualquer integracao neural real ficam deliberadamente fora deste preview. Consulte `docs/idle-orb-reference.md` para a analise da referencia e `docs/cinematic-orb-v0.2.md` para o historico e a validacao das etapas A e B.
