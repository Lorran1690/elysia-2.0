# Neural Dialogue v2 — experimento de conversa

Status: treinamento concluído; marco conversacional REPROVADO.

## Objetivo e critério fixado

O objetivo do proprietário permanece conversas complexas com Neural Core próprio.
Este experimento testa um marco muito menor: ao menos 12/24 casos estáticos e 4/8
conversas com histórico gerado totalmente corretos, sem invenção de informação
pessoal ou falsa alegação de acesso a ferramentas. Os critérios foram registrados
em data/neural-dialogue-v2/protocol.json antes de avaliar o modelo. Passar esse
marco NÃO estabelece equivalência com ChatGPT, inteligência geral ou prontidão
para executar ações. Reprovar será registrado como reprovação, sem reduzir a meta.

## O que muda

Modelo novo, iniciado aleatoriamente, com 2.567.616 parâmetros, quatro blocos,
dimensão 192, quatro cabeças, SwiGLU, RMSNorm, RoPE, SDPA, dropout 0,1 e contexto
máximo 512. O vocabulário de 2.048 tokens é o BPE próprio já treinado somente no
split de treino do corpus português v1. Não foram usados pesos de outro LLM,
Ollama, APIs de inferência, busca de respostas ou respostas fixas na geração.
A expansão de vocabulário em relação ao piloto antigo de 1.024 tokens explica
parte do aumento de parâmetros; não é evidência de competência nova.

Fase 1: 8.000 etapas de linguagem, batch 4 e janelas de 256 tokens. Mistura por
batch: 70% corpus técnico v1 e 30% literatura histórica. AdamW com lr base 0,0005,
warmup e decaimento cosseno; clip 1. Seleção pela menor loss ponderada de validação,
com janelas fixas em ambas as fontes. O melhor checkpoint dessa fase inicializa a
fase seguinte; o otimizador é reiniciado conforme protocolo.

Fase 2: 2.000 etapas com loss apenas em respostas de assistente, lr base 0,0002.
80% dos batches vêm de árvores novas filtradas do OASST2; 20% do currículo
sintético pequeno já existente. O suplemento é identificado, não é tratado como
diálogo humano e foi criado antes da especificação de 24 casos. São os mesmos
176 exemplos de saudações, identidade e contexto da etapa diagnóstica anterior;
não houve fabricação de milhares de novas conversas para inflar o corpus.

## Fontes novas e separação

OASST2, revisão 179dd21fc55192153d94adb0e0ce8f69e222bf75, arquivo ready.messages
com SHA-256 a9f240c4c77aa1378364f70d37e753c07ba284e247b019d700e1947a0e5da751.
Licença Apache 2.0 declarada pelo publicador, ficha e licença preservadas. A versão
inclui OASST1, portanto foram excluídas TODAS as 165 árvores portuguesas antigas,
além de duplicatas textuais longas, antes de fazer as divisões. Os dados resultam
em 149 caminhos de treino (42 árvores), 14 de validação (cinco) e 18 de teste
(cinco). O maior grupo ocupa 5,37% dos caminhos de treino. Não se transformou um
teste histórico em treino nem se contou a republicação de mensagens como novidade.

Exigem-se marca nonsynthetic, revisão positiva, qualidade mínima 0,6, rótulos de
PII/spam/inadequação/idioma/ódio/sexual/violência com ao menos dois votos e valor
zero, limites de comprimento e padrões de identificadores ausentes. Caminhos
incompletos são excluídos, assim como identidades de outros assistentes e pedidos
de personificação. Papéis alternam e árvores/grupos completos ficam na mesma
partição. Esses filtros e votos da fonte não substituem revisão factual integral
ou revisão humana independente. IDs de contas e timestamps não foram conservados.

Literatura, somente para pré-treino, não como comportamento de assistente:

| Obra | Autor | Partição |
|---|---|---|
| Triste Fim de Polycarpo Quaresma | Lima Barreto (1881–1922) | Treino |
| O Cortiço | Aluísio Azevedo (1857–1913) | Treino |
| A fallencia | Júlia Lopes de Almeida (1862–1934) | Treino |
| Iracema | José de Alencar (1829–1877) | Validação |
| O Atheneu | Raul Pompéia (1863–1895) | Teste |

As fichas do Project Gutenberg declaram domínio público nos EUA; as datas de
falecimento superam o prazo de 70 anos no Brasil. Isso não é uma declaração de
domínio público em todas as jurisdições. As cópias completas originais e as fichas
foram preservadas, incluindo avisos e licença do Project Gutenberg. Apenas o corpo
entre marcadores editoriais entra no pré-treino, normalizado em NFC; cabeçalho e
licença não são usados como linguagem. Cada autor/obra inteiro fica em uma única
partição. Grafia arcaica e preconceitos históricos são limitações documentadas;
a literatura não é usada como referência factual atual nem resposta de assistente.

São 539.845 tokens literários de treino, 76.410 de validação e 160.049 de teste.
Somados ao corpus v1, há 2.300.319 tokens de prosa disponíveis para treino, antes
de reamostragem. O treino efetivo processa múltiplas janelas dessa base; apresentar
as passagens repetidas como novos dados seria incorreto. Atribuições e condições
das fontes continuam preservadas; não se reclassifica a coleção inteira como MIT.

## Integridade e recuperação

Treino CPU com duas threads; não é benchmark da GTX 1650 do proprietário. O limite
de tempo por execução é 2.700 segundos. Ao atingir limite ou receber SIGINT/SIGTERM,
salva na fronteira de uma etapa completa, sem avaliar o teste. Checkpoint de
retomada contém pesos, otimizador, RNG do PyTorch e de batches, etapa/fase,
configuração, versão de PyTorch e hashes. Mudanças de fonte ou configuração são
recusadas. Gravação atômica evita aceitar arquivo parcial. Um teste interrompe e
retoma um experimento pequeno e compara todos os tensores/RNG exatamente com uma
execução contínua. Isso não garante igualdade entre versões ou plataformas.

Checkpoints intermediários de linguagem são preservados no GitHub e marcados como
pré-treino, não como assistente pronto. O comando de chat recusa esses arquivos;
ele exige um checkpoint da fase de diálogo. Resultados e completamentos de
desenvolvimento não entram de volta no treinamento.

## Avaliação e revisão

A especificação de 24 casos permanece com o hash original do corpus v1. Não houve
coincidência literal de prompts longos com as novas conversas de treino. Após
selecionar os pesos só pela validação, a avaliação gera respostas para os 24 casos
e executa também os oito casos de múltiplos turnos com respostas intermediárias do
próprio modelo. Assim, o teste não depende somente de históricos de referência.

O programa de revisão exige julgamento 0/1/2, motivo, revisor identificado, flags
críticas e hash da geração de cada caso. Recusa perguntas alteradas, revisão
incompleta, notas positivas para erro/resposta vazia e revisão de outro modelo.
Não concede acerto por palavras-chave. O contador calcula o marco pequeno;
a equivalência com ChatGPT fica explicitamente não estabelecida.

## Executar no computador

Com Python 3.12, instale os requisitos CPU e de corpus no ambiente virtual:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-first-words-cpu.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-corpus.txt
```

Para um treino independente, sempre escolher um diretório novo:

```powershell
.\.venv\Scripts\python.exe -m learning.train_dialogue_v2 --output artifacts/neural-dialogue-v2/reproduction
```

Para retomar uma execução inacabada com a mesma receita/dados:

```powershell
.\.venv\Scripts\python.exe -m learning.train_dialogue_v2 --output artifacts/neural-dialogue-v2/reproduction --resume
```

A receita é fixa no protocolo. Uma reprodução da avaliação já vista não será um
novo teste virgem para seleção de configurações. Depois de results.json, a execução
fica congelada e não pode ser retomada para ajustar os mesmos casos.

Após a entrega do checkpoint de diálogo:

```powershell
.\.venv\Scripts\python.exe -m learning.dialogue_v2_chat
```

Chat local em texto, sem ferramentas, voz, microfone ou gravação de histórico.
/limpar reinicia contexto e /sair encerra. Limite de contexto é comunicado sem
apagar mensagens silenciosamente. O modelo pode produzir informações erradas.
Os comandos equivalentes foram desenvolvidos/testados em Linux; não foram
executados no Windows do proprietário.

Para recuperar as fontes de preparação, inclusive as duas versões originais
OASST, com limites de tamanho e hashes fixos:

```powershell
.\.venv\Scripts\python.exe -m learning.fetch_dialogue_v2 --cache D:/ElysiaSourceCache/dialogue-v2
.\.venv\Scripts\python.exe -m learning.dialogue_v2_data --cache D:/ElysiaSourceCache/dialogue-v2 --output scratch/dialogue-v2-reproduction
```

Os originais literários completos já estão versionados; não dependem de uma URL
mutável devolver amanhã a mesma revisão. O gzip multilíngue original OASST não é
republicado com dados de contas; a revisão imutável e o hash permitem recuperação.
Os dados preparados são acessíveis sem autenticar em contas pessoais.

## Resultado final e diagnóstico

10.000 passos concluídos (8.000 de linguagem + 2.000 de diálogo), com
9.635.818 tokens supervisionados e 2.314,5 segundos de computação registrados.
A loss de validação de linguagem caiu de 7,6567 para 3,8340. Essa melhora de
previsão de tokens não se converteu em conversa útil: **0/24 casos estáticos e
0/8 conversas com histórico gerado** totalmente corretos, todos com nota zero.
Há uma fabricação de informação privada: à pergunta sobre a senha doméstica,
o modelo respondeu “azul.” sem saber a senha. Nenhuma equivalência com ChatGPT.

O checkpoint de diálogo escolhido pela regra prévia foi o passo 500, loss
ponderada 3,4753. A loss dos diálogos humanos de validação passou de 4,2985 nesse
passo para 4,7002 no passo 2.000, enquanto a loss sintética continuou caindo.
Isso é compatível com sobreajuste do pequeno conjunto e aprendizado de respostas
curtas recorrentes. As saídas repetem “Certo.” e trechos sobre hipopótamo ou menus,
sem seguir instruções nem manter contexto. O teste humano separado teve loss de
assistente 4,4008 e perplexidade 81,51 (13.914 tokens-alvo), avaliado uma vez.

Todas as saídas estão em `artifacts/neural-dialogue-v2/run-001/results.json`;
`semantic-review.json` registra justificativas e hashes de cada resposta e
`scores.json` aplica o critério sem ajuste posterior. A revisão é do Codex,
não de avaliadores humanos independentes. Os pesos de pré-treino, diálogo e
retomada estão preservados com hashes em `artifact-hashes.json`.

### Próxima hipótese a testar

Não repetir este benchmark para escolher hiperparâmetros. A prioridade é ampliar
conversas portuguesas diversas com licença e procedência verificadas, reduzir a
influência das confirmações sintéticas curtas e usar desenvolvimento separado para
medir relevância, repetição e contexto. O novo experimento deverá ter protocolo
prévio e teste novo independente; os 24 casos atuais passam a ser diagnóstico
histórico. Só aumentar as épocas na mesma amostra não resolve o sobreajuste
observado. Escalar para conversas complexas exige muito mais dados e computação
do que este modelo de 2,57 milhões de parâmetros treinado em CPU.
