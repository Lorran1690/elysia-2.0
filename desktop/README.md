# E.L.Y.S.I.A. Desktop 0.1

Preview isolado do Orb Core 3D em estado `idle`. Esta pasta nao usa nem modifica o motor neural, os pesos, os corpus ou os scripts de treinamento do repositorio.

## Executar no Windows

```powershell
cd desktop
npm install
npm run dev
```

Abra a URL local exibida pelo Vite. O seletor no canto direito alterna os perfis `Baixa`, `Media` e `Alta`; a telemetria informa FPS, particulas e conexoes no momento da execucao.

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

O chat, os demais estados do orbe e qualquer integracao com IA ficam deliberadamente fora deste preview. Consulte `docs/idle-orb-reference.md` para a analise da referencia, `docs/implementation-report.md` para os resultados de validacao e as diferencas conhecidas.
