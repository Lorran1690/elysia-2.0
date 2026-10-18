# E.L.Y.S.I.A. Desktop 0.2 - Etapas A e B: Orb Core vivo

Data: 2026-10-18
Branch: `feature/elysia-desktop-orb`
Base auditada da Etapa B: `99b3494bb0fb9627ad49fed4e48f3ad84d25bfa2`
Estado: Etapa B pronta para revisao visual. O chat cinematografico e o adaptador neural continuam fora do escopo.

## Auditoria inicial

- O worktree da interface estava limpo e isolado na branch exclusiva antes das alteracoes.
- Nenhum arquivo de `brain/`, `learning/`, `data/`, checkpoints, tokenizadores ou relatorios do motor neural foi alterado.
- A referencia local `WhatsApp Video 2026-10-16 at 19.32.22.mp4` esta acessivel. Seus metadados locais indicam 480 x 864, 30 fps e aproximadamente 60 segundos. O arquivo original nao foi copiado para o repositorio.
- Os arquivos `ai-thiking-orb-and-input.tsx` e `ai-orb.tsx` nao estavam acessiveis no worktree nem nos anexos disponiveis. Nenhum codigo deles foi copiado. A descricao arquitetural sera considerada somente em etapas posteriores, apos aprovacao.
- O projeto [thinking-orbs](https://github.com/Jakubantalik/thinking-orbs) foi avaliado apenas como referencia de nomenclatura de estados. Ele usa Canvas 2D e licenca MIT; nao foi instalado, importado ou reutilizado porque o Orb Core desta interface permanece uma cena Three.js propria.

## O que foi preservado

O preview continua usando React, React Three Fiber e Three.js. A cena continua sendo um unico canvas WebGL com buffers de posicao, cor e conexoes prealocados. A grade espacial para busca local de vizinhos e os controles de qualidade existentes foram preservados.

## Etapa B - Estados vivos

### Arquitetura

- `VisualEvent -> OrbStateController -> TargetParameters -> SmoothInterpolation -> ParticleOrb` esta isolado em `src/orb/state.ts`.
- A maquina tipada cobre `idle`, `listening`, `thinking`, `connecting` e `speaking` e tambem mapeia eventos preparados para entrada, requisicao, conexao, resposta, cancelamento e erro.
- Cada estado define fluxo, coesao, cavidades, visibilidade e densidade das conexoes, amplitude radial, ondulacao superficial, luminosidade, pulso e nivel de audio.
- Os alvos sao interpolados a cada frame. A troca de estado nao altera a dependencia de criacao do campo: os buffers somente sao recriados quando o preset de qualidade muda.
- A preferencia do sistema por movimento reduzido atenua fluxo, pulso e ondulacao, preservando o volume do orbe.

### Comportamentos demonstrativos

- `idle` conserva o fluxo volumetrico refinado da Etapa A.
- `listening` introduz ondulacoes locais na superficie, movimentos coordenados e brilho discreto em funcao de uma intensidade de audio normalizada.
- `thinking` aumenta os fluxos internos, cavidades, agrupamentos e pulsos assimetricos sem rotacao global ou dispersao permanente.
- `connecting` torna a rede local mais coesa e visivel, sem criar raios radiais ou orbitas decorativas.
- `speaking` combina ondas de emissao locais com pulsos suaves, mantendo o mesmo volume dourado.

O painel de demonstracao permite selecionar todos os estados. O sinal mostrado em `listening` e explicitamente `SINAL DE AUDIO SIMULADO`; nao existe captura de microfone nesta etapa.

## Refinamentos aplicados

### Volume e movimento

- A distribuicao inicial passou a preencher um volume esferico por camadas, em vez de depender de uma nuvem visualmente plana.
- O movimento agora combina um campo vetorial tridimensional continuo, lobos de silhueta, duas cavidades moveis e dois focos temporarios de densidade.
- A rotacao global do grupo foi removida. O movimento percebido vem das particulas e das deformacoes internas, nao de uma esfera inteira girando.
- A respiracao volumetrica tem baixa amplitude e e combinada com variacao espacial para evitar um ciclo mecanico uniforme.

### Particulas e brilho

- O corpo dourado ganhou uma camada suave de particulas para reforcar o volume sem adicionar uma esfera, imagem de fundo ou gradiente decorativo.
- Os pontos de destaque foram reduzidos para no maximo cinco e receberam menos opacidade e tamanho, evitando explosoes ou estrelas dominantes.
- A paleta ficou concentrada em ouro e ambar sobre preto profundo, com pontos luminosos quentes e sem efeitos de piscada rapida.

### Conexoes e recursos GPU

- Conexoes sao estritamente locais, com limite de duas por particula e teto global por preset.
- A malha entra e sai por interpolacao de intensidade, evitando o aparecimento abrupto de raios radiais.
- O preset Alto tem limite rigido de 240 conexoes; os buffers nao crescem durante a animacao.
- Ao mudar de preset ou desmontar a cena, geometrias de pontos, ancoras, linhas e a textura procedural sao descartadas explicitamente.

## Comparacao visual honesta

O preview entrega uma massa tridimensional dourada, com densidade irregular, cavidades internas, focos quentes e conexoes locais transitarias. Isso se aproxima das caracteristicas observadas no video: particulas ouro/ambar, volume, nuvem irregular e malha efemera.

Ainda ha diferencas importantes. O video de referencia apresenta transformacoes mais longas entre nuvem, compressao e malha, enquanto esta entrega cobre somente o repouso vivo. Nao ha declaracao de fidelidade exata: a filmagem vertical nao revela o sistema 3D original, sua camera ou seus parametros de particula.

## Artefatos de preview

| Artefato | Conteudo |
| --- | --- |
| [Captura desktop](assets/elysia-orb-core-v0.2.png) | Preview em 1280 x 720. |
| [Captura estreita](assets/elysia-orb-core-v0.2-mobile.png) | Preview em 390 x 844. |
| [Gravacao WebM](assets/elysia-orb-core-v0.2.webm) | Oito segundos do Canvas WebGL em estado `idle`. |

## Validacao executada

- `npm run lint`: aprovado.
- `npm test`: 11 testes aprovados, incluindo o controlador de estados independente do renderer.
- `npm run build`: aprovado.
- Troca repetida entre Baixa, Media e Alta: sem erros no console e sem perda do canvas.
- Preview Alto apos estabilizacao: 2400 particulas, ate 240 conexoes e leitura local entre 73 e 88 FPS no navegador de teste.
- Checagem de pixels das capturas compostas: desktop com 5459 amostras nao pretas e 2686 quentes em 57600 amostras; viewport estreito com 6589 nao pretas e 3565 quentes em 20678 amostras. As duas imagens renderizam o orbe e nao um canvas vazio.
- Revisao da Etapa B no navegador: os cinco controles atualizaram o estado do canvas; `listening` respondeu de 42% a 100% de sinal simulado; o preview permaneceu visivel em viewport desktop e em 390 x 844.
- Capturas consecutivas do estado animado tiveram hashes distintos, confirmando que o canvas continua em movimento; nao houve erro de aplicacao no console durante a revisao.

Essas leituras sao indicativas do preview em navegador e nao substituem um benchmark nativo final em Tauri na GTX 1650. A telemetria de VRAM tambem permanece pendente para uma etapa posterior, sem treinamento CUDA em paralelo.

## Ponto de aprovacao

Esta entrega termina na Etapa B. Nao foram criados chat cinematografico, entrada de mensagem, cartao de resposta, adaptador neural ou chamadas externas. A Etapa C so podera iniciar apos aprovacao visual explicita destes estados vivos.
