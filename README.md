# E.L.Y.S.I.A. 2.0

## Elysia para Android

[Baixar Elysia-Android.apk](https://raw.githubusercontent.com/Lorran1690/elysia-2.0/refs/heads/feature/media-creation/artifacts/android/Elysia-Android.apk) · [Guia Android](desktop/ANDROID.md).

Interface para telefone com navegação por toque, rotação, biblioteca privada,
ferramentas locais, editor, composição de mídia e visualização central dos orbes
e avatares originais. Em Configurações → Sistema, conecte seu computador por
HTTPS privado para usar o Neural Core próprio e o serviço de geração. O modelo
continua experimental e pode produzir respostas incorretas ou repetitivas.
[Configuração da conexão privada](reports/phone-connection/README.md).

Abra o link no telefone, baixe o APK e confirme a instalação. Depois, use
**Configurações → Sistema → Verificar atualizações** no próprio aplicativo.
O código, o APK e seus hashes ficam no GitHub; os registros pessoais ficam no
armazenamento privado do app. Com o Drive instalado no telefone, use Exportar
e escolha uma pasta privada para guardar seus backups. Desinstalar ou limpar os dados remove os registros
locais. [Verificação da conexão e do APK atual](reports/phone-connection/README.md)
e [testes históricos do build 7](reports/android/README.md).

## Elysia Desktop 2.2 · Tauri 2

[Baixar o instalador Windows](https://github.com/Lorran1690/elysia-2.0/releases/download/native-d44aab78a5cd/Elysia-Setup-x64.exe) · [Presença no centro](reports/desktop-appearance-update/windows-presence-center.png) · [Atualizações no app](reports/desktop-appearance-update/windows-settings-update.png).

Janela desktop Tauri 2, frontend React/TypeScript compilado com Vite, estilos
Tailwind, integração Rust e preferências/conversas em SQLite privado. Quatro áreas
consolidadas, configurações amplas, busca por atalhos e três músicas originais com
volume e seleção. Controles de orbes e avatares em Aparência, com paletas, partículas,
movimento e visualização central. Botão Atualizar Elysia no topo e em Sistema, com
download e SHA-256 antes de abrir o instalador. Ícone aprovado pelo proprietário; avatares, orbes e pesos do
Neural Core preservados. [Guia da versão nativa](desktop/README.md).

Instalação, reinstalação, remoção, reabertura do histórico, som, biblioteca, cinema
e ferramentas foram verificados na janela WebView2 real do Windows. O instalador
prepara o WebView2 se necessário. O fluxo em uma máquina sem Runtime é documentado;
o runner de validação já o tinha instalado. [Relatórios](reports/desktop-appearance-update/README.md).

Instale esta versão uma vez para receber o botão de atualização. Depois, use
**Configurações → Sistema → Verificar atualizações** para baixar e abrir a
instalação das próximas versões pelo próprio aplicativo.

Para trazer conversas do app anterior, exporte o backup e importe em Configurações
→ Dados e privacidade. Registros privados não são enviados ao GitHub. Esta entrega
altera a interface e a integração desktop; não melhora os modelos de geração.


## Versão anterior do aplicativo Windows

[Baixar instalador Elysia-Setup-x64.exe](https://github.com/Lorran1690/elysia-2.0/releases/download/desktop-53d215020157/Elysia-Setup-x64.exe).

A interface v11 reúne conversa pelo núcleo próprio experimental, biblioteca
privada, editor de código, bancada de análise, estúdios de mídia e integração
com ComfyUI local. Veja [como instalar e atualizar](interface/DESKTOP.md).
O arquivo `Elysia-Setup-x64.exe` instala o aplicativo no menu Iniciar; o ZIP
continua disponível como alternativa portátil.

## Criação de mídia e código

[Aplicativo Windows com criação de mídia e editor](https://github.com/Lorran1690/elysia-2.0/releases/tag/desktop-cf8fe9b6a3da).

Composição e exportação PNG, síntese musical WAV, animações WebM curtas, editor de
código e gravação em pasta escolhida do Google Drive para computador. Veja
[capacidades, armazenamento e limites](interface/MEDIA.md). A geração por difusão está disponível em um painel separado, por
[ComfyUI local com instalação e modelos próprios](interface/GENERATIVE-MEDIA.md).
Vídeo neural realista continua sem validação; Voice Core permanece pausado.

## Módulos locais

[Baixar aplicativo Windows com os novos módulos](https://github.com/Lorran1690/elysia-2.0/releases/tag/desktop-93786c19a134).

Biblioteca privada com notas, documentos e fontes, busca textual e backup;
ferramentas de cálculo, validação de JSON, estatísticas e SHA-256; visualização
local de imagens, áudio e vídeo. Veja [funcionamento e limites](interface/MODULES.md).
O código é preservado no GitHub. Registros pessoais ficam fora do repositório e
precisam de backup privado externo. O Voice Core permanece pausado.

## Fundação e currículo novos — preparados, sem novo treino neural

[Relatório e calibração para a GTX 1650](reports/curriculum-v2/README.md):
7.538 artigos portugueses com procedência, BPE próprio de 8.192 tokens e 79.294
alvos de conversa com histórico completo e amostragem equilibrada. Perfil local
de 20,49 milhões de parâmetros e script Windows para medir a GPU de 4 GB informada
no dossiê. Dados e código preparados; nenhum ganho conversacional demonstrado
nesta etapa. Branch: `recovery/foundation-curriculum-v2`.

## Estado atual — pesquisa de conversação

O [treino neural v2](reports/neural-dialogue-v2/README.md) completou 10.000 passos,
mas reprovou: 0/24 respostas estáticas e 0/8 conversas com contexto corretas.
O [novo corpus e piloto Aira](reports/aira-dialogue-v1/README.md) adiciona 45.175
conversas **sintéticas**, com licença Apache 2.0 publicada pela fonte e partições
auditadas. O piloto completou 2.000 passos e reprovou o novo teste: 0/8 casos
integralmente corretos, incluindo 0/3 conversas com contexto. A loss melhorou, mas
as respostas continuam repetitivas e sem pertinência. Pesos próprios, corpus, protocolo e avaliações são preservados
na branch `recovery/neural-dialogue-v2`. Ainda não há conversas complexas
comparáveis ao ChatGPT.

## Corpus português v1 — preparado e auditado

[Relatório, fontes e reprodução](reports/corpus-pt-v1/README.md): 2.163 documentos,
2.277.416 tokens BPE (1.760.474 no treino), três fontes com licenças e atribuições,
splits por grupos e 24 casos de avaliação, consumidos posteriormente no treino v2. BPE treinado
do zero só no treino e exportado para o formato próprio da Elysia. Pesos neurais
anteriores preservados, sem novo treino nesta etapa. A base ainda é técnica e não
constitui um currículo de conversação ampla. Branch: `recovery/portuguese-corpus-v1`.

## Piloto de linguagem com conversas licenciadas

[Relatório e instruções](reports/language-pilot/README.md): Transformer próprio de
2,17 milhões de parâmetros, BPE treinado só no treino, corpus pt-BR OASST1 filtrado,
checkpoints de inferência e retomada. A nova avaliação aberta teve **0/8 critérios
atendidos**; este piloto ainda não conversa de forma confiável. Os modelos e
resultados dos ensaios anteriores permanecem preservados. Branch desta etapa:
`recovery/neural-language-pilot`.

## Recuperação — primeiras palavras (24/10/2026)

Segundo marco: [chat experimental com contexto](reports/context-words/README.md).
Recuperação de informações em combinações sintéticas não vistas: 12/16, inclusive
com respostas intermediárias geradas. Ainda não é conversação geral. Código, resultados e checkpoints estão preservados no GitHub na branch
`recovery/neural-first-words`; a permissão de escrita foi corrigida.

Treino diagnóstico do Transformer próprio a partir de pesos aleatórios: 24/24
exemplos ensinados e 4/8 variações próximas por correspondência exata. Ainda não
é conversação confiável. Dados sintéticos, pesos, limites e instruções de execução
estão em [reports/first-words/README.md](reports/first-words/README.md).

Primeira etapa experimental: uma rede neural pequena, inicializada aleatoriamente e treinada localmente para validar um pipeline de linguagem. Este repositório é independente do projeto anterior.

## Limites desta etapa

- Não usa Ollama, APIs de IA, pesos ou tokenizadores pré-treinados.
- Oferece interface local com avatar; voz, holograma físico e controle do computador permanecem indisponíveis.
- Os primeiros corpora sintéticos eram diagnósticos. As fontes ampliadas têm procedência e limites próprios; sua inclusão não prova que o modelo aprendeu a conversar.
- Redução de loss em overfitting controlado demonstra o funcionamento do treinamento, não inteligência geral.

## Ambiente Windows

Instale Python 3.12 ou mais recente dentro da faixa suportada pelo PyTorch e crie um ambiente virtual:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

O arquivo de requisitos fixa a build CUDA 12.8 do PyTorch. O registro histórico cita validação em outro computador com driver NVIDIA 610.62, CUDA reportada 13.3 e GTX 1650. O ambiente atual de pesquisa tem somente CPU; essa configuração de GPU não foi revalidada aqui. Em outro computador, o código continua usando CPU quando `torch.cuda.is_available()` for falso.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Treinamento

```powershell
.\.venv\Scripts\python.exe -m learning.train --config configs/seed-v0.1.yaml --steps 100
```

Para forçar CPU ou CUDA:

```powershell
.\.venv\Scripts\python.exe -m learning.train --device cpu --steps 20
.\.venv\Scripts\python.exe -m learning.train --device cuda --steps 20
```

O checkpoint fica em `learning/checkpoints/elysia-v0.1.pt`. Executar novamente com o mesmo caminho retoma o estado salvo quando o número de etapas configurado for maior que o passo já salvo.

## ELYSIA-Seed v0.2

A v0.2 vive em uma branch separada e preserva a configuração e o checkpoint da v0.1. A revisão auditada divide as obras antes do BPE, treina o BPE somente no split de treino e usa armazenamento de tokens em disco:

```powershell
.\.venv\Scripts\python.exe -m learning.train --config configs/seed-v0.2.yaml --data-dir data/raw --checkpoint learning/checkpoints/elysia-seed-v0.2-audited.pt --steps 100
```

TXT é tratado como uma obra inteira; JSONL agrupa registros por identificador de fonte quando disponível. O checkpoint recusa retomada quando corpus, split, tokenizador ou arquitetura não correspondem. Dados externos ainda não foram baixados; qualquer fonte pública deverá ser aprovada antes do uso.

## Geração

Depois do treinamento, gere tokens a partir dos pesos salvos:

```powershell
.\.venv\Scripts\python.exe -m learning.generate_text --prompt "E.L.Y.S.I.A." --tokens 80 --temperature 0.8 --top-k 20
```

Para gerar com o checkpoint BPE da v0.2:

```powershell
.\.venv\Scripts\python.exe -m learning.generate_text --checkpoint learning/checkpoints/elysia-seed-v0.2-audited.pt --tokenizer-path data/processed/tokenizer-v0.2-audited.json --prompt "E.L.Y.S.I.A." --tokens 80
```

## ELYSIA-Seed v0.3

A v0.3 mantém a v0.2 como baseline e adiciona escolhas experimentais para RoPE, RMSNorm, SwiGLU, SDPA e KV cache. As ablações locais podem ser reproduzidas sem dados externos:

```powershell
.\.venv\Scripts\python.exe -m learning.ablate --device cuda --steps 30
```

O relatório e o resultado completo ficam em `reports/seed-v0.3.md` e `reports/seed-v0.3-results.json`. Use `use_cache=True` com `brain.generate.generate` para a geração com cache.

## Estrutura

`brain/` contém o tokenizador e o Transformer; `learning/` contém dados, treino e avaliação; `tests/` contém os testes automatizados; `data/raw/` contém somente o corpus de demonstração local.

## Interface do avatar conectada

Execute `python -m interface.server` e abra http://127.0.0.1:8765 para conversar
com o modelo próprio experimental, pela interface do avatar fornecida pelo
proprietário. Veja [instruções, dependências e limites](interface/README.md).
A integração não altera pesos nem comprova capacidade de conversação complexa.

## Aplicativo Windows e backups

O [aplicativo da Elysia](interface/DESKTOP.md) inclui núcleo, pesos e interface.
Use `Elysia-Setup-x64.exe` nas Releases para instalar o aplicativo. O pacote ZIP
portátil e `Elysia.cmd` com a `.venv` instalada continuam como alternativas. Conversas têm exportação e restauração de backup.

### Correção da tela preta no Windows

Baixe a [versão corrigida do aplicativo](https://github.com/Lorran1690/elysia-2.0/releases/tag/desktop-a7014f9815f1).
Os arquivos JavaScript agora mantêm seus bytes no checkout Windows. O pacote
foi testado com renderização da interface e resposta do núcleo real em um navegador
Windows. [Registro da verificação](reports/desktop-black-screen/verification.json).

## Pesquisa de conversação v3

Foi concluído um novo ajuste de 1.000 passos com históricos completos e amostragem
balanceada. Melhorou a loss em dados sintéticos, mas **não melhorou a conversa**:
candidato e modelo do app acertaram 0/16 casos novos; a repetição lexical aumentou.
Os pesos do aplicativo foram preservados. [Resultados, pesos e próximo passo](reports/conversation-v3/README.md).

## Bancada e evolução

O aplicativo inclui [bancada de análise e catálogo de habilidades](interface/WORKBENCH.md),
com referência arquitetural ao Eleven e estados verificáveis. O
[memorando funcional](docs/MEMORANDO-FUNCIONAL-2026-10-26.md) registra a visão
de longo prazo; não representa uma lista de capacidades já concluídas.

## Geração por modelos de mídia

O EXE inclui um [adaptador de modelos de imagem e vídeo](interface/GENERATIVE-MEDIA.md)
para ComfyUI local. Motor, pesos e GPU precisam ser configurados separadamente.
As composições Canvas e o Cinema 3D continuam disponíveis e são recursos distintos.
