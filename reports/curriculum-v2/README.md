# Fundação linguística e currículo v2

Esta etapa prepara dados e verifica a próxima arquitetura. **Não há novos pesos
neurais treinados, nem demonstração de conversas complexas.** Os checkpoints
anteriores continuam preservados. Branch: `recovery/foundation-curriculum-v2`.

## Diagnóstico medido só no treino

`train-text-audit.json` registra 40.745 conversas e 145.957 respostas. A família
mais comum de oito palavras, “como modelo de linguagem de ia não tenho”, aparece
6.455 vezes. Outros prefixos repetidos incluem “como modelo ... não posso”.
23.227 respostas têm algum grupo de quatro palavras repetido pelo menos quatro
vezes. Essa última medida **não é um rótulo de erro**: listas, código ou prosa
legítima podem repetir sequências. As estatísticas não consultaram os textos de
validação ou teste para escolher regras.

## Base informativa nova e procedência

Foram examinados os seis fragmentos do snapshot `20231101.pt` do conjunto
[Wikimedia Wikipedia](https://huggingface.co/datasets/wikimedia/wikipedia), revisão
`b04c8d1ceb2f5cd4588862100d08de323dccfbaa`, com 1.112.246 artigos. Os arquivos
originais somam cerca de 1,58 GB e permanecem no cache; hashes SHA-256 LFS,
tamanhos e caminhos imutáveis estão em `data/source-locks`.

A amostra usa 1% dos buckets de SHA-256 do ID, ao longo de todos os fragmentos;
não usa os primeiros artigos do dump. Dos 11.158 sorteados, foram retidos 7.538,
com filtros de extensão, desambiguação e padrões de identificadores. Isso não é
revisão factual nem garantia de ausência de informação pessoal.

Partições por hash do conteúdo normalizado: 6.787 documentos de treino, 362 de
validação e 389 de teste. Duplicatas integrais ficam no mesmo grupo. Paráfrases e
parágrafos compartilhados ainda podem existir. O snapshot é de novembro de 2023
— não fornece fatos atuais.

Cada artigo mantém título, URL, link para histórico, atribuição aos colaboradores,
licença e modificações aplicadas. A ficha da fonte declara CC-BY-SA-3.0 e GFDL,
ressalvando que alguns textos só estão disponíveis sob Creative Commons; usamos
a opção CC-BY-SA-3.0 declarada. O texto integral dessa licença foi arquivado do
repositório público SPDX com revisão e hash fixos. Os endpoints diretos do texto
CC e dos avisos Wikimedia responderam HTTP 403 na aquisição; não arquivamos
páginas falsas em seu lugar. A ficha original e os links dos termos permanecem
nos avisos. Os textos derivados conservam atribuição e indicação de licença.

## Vocabulário próprio e contexto

BPE de 8.192 tokens, treinado do zero somente nos 6.787 artigos de treino. Exportado
para o formato próprio da Elysia. Todos os artigos passaram pela ida e volta sem
perda; 68 amostras conferem os mesmos IDs nos codificadores rápido e próprio.
Foram preparados 4.623.252 tokens de treino, 250.632 de validação e 288.926 de
teste, em stores uint32 com hashes. São contagens no novo vocabulário: não somar
ou comparar diretamente com contagens do BPE antigo de 2.048 tokens.

Na amostra fixa de 1.000 conversas de **treino** (`tokenizer-context-audit.json`),
a tokenização nova usou 1.550.129 tokens contra 2.143.834 da anterior: redução de
27,69%. Com contexto 2.048, 779 conversas cabem inteiras usando o novo vocabulário,
contra 514 com o antigo no mesmo contexto. No antigo contexto de treino de 256,
apenas uma conversa inteira dessa amostra cabia. Isso mede compressão e cobertura
de histórico, não inteligência. Os checkpoints antigos são incompatíveis com os
novos IDs; a nova arquitetura exige pré-treino próprio desde o início.

## Novo currículo: hipótese experimental

A seleção usa apenas as conversas de treino já licenciadas do corpus Aira.
Validação e teste originais mantêm suas partições e não participam das estatísticas
ou do ajuste das probabilidades. Todos os exemplos continuam marcados como
sintéticos e sem verificação factual independente.

- Preserva o histórico inteiro desde o primeiro usuário até a resposta-alvo.
  Não recorta turnos antigos para encaixar a resposta. Limite: 2.048 tokens.
- Supervisiona só a resposta-alvo, mascarando usuários e respostas anteriores.
- Coloca fora da seleção os prefixos com repetição verbal muito concentrada:
  ao menos 40 palavras, um tetra-grama com quatro ocorrências e pelo menos 45%
  de tetra-gramas duplicados. O original é preservado para revisão. Essa regra
  pode rejeitar escrita repetitiva legítima; não é juízo semântico automático.
- Mantém no máximo dois alvos por grupo conectado original. Prefere um alvo
  contextual profundo e outro independente, com escolha determinística.
- Mantém candidatos lexicais a respostas de indisponibilidade/incerteza, com
  10% da massa de amostragem. Não declara que sejam recusas incorretas. Os demais
  buckets recebem 60% para respostas com contexto e 30% para independentes,
  redistribuindo massa ausente só entre buckets substantivos.
- Atenua famílias de prefixos muito frequentes pela raiz inversa da frequência,
  dentro de cada bucket. Essa proporção é uma hipótese nova, ainda não validada
  por respostas de um modelo treinado.

`train-targets.jsonl.gz` é um índice reproduzível do alvo dentro da conversa
original, com contagens de contexto, fonte e probabilidade. Não é um novo conjunto
de respostas inventadas. `review-queue.jsonl` oferece até 40 casos estratificados
para revisão; permanecem com decisão `pending`. Não há aprovação humana fictícia.

## Arquitetura e recursos

`configs/foundation-v1.yaml` define um candidato próprio de **97.640.192
parâmetros**, 12 blocos, dimensão 768, RoPE, RMSNorm, SwiGLU, SDPA, contexto 2.048
e vocabulário 8.192. A contagem usa tensores meta, sem alocar centenas de MB de
pesos aleatórios só para contar parâmetros.

O dossiê enviado pelo proprietário (seções 7.2 e 25; SHA-256 registrado em
`hardware-target.json`) informa Ryzen 5 3400G, GTX 1650 de 4 GB, 16 GB RAM e
Windows. Essa é configuração histórica informada, não uma GPU detectada aqui.
O perfil padrão agora é `configs/foundation-gtx1650.yaml`: **20.493.696 parâmetros**,
8 blocos, dimensão 384, seis cabeças, contexto máximo 2.048 e calibração inicial
em 512 tokens, batch 1. O perfil de 97,6 milhões permanece separado para hardware
com mais capacidade. Nenhum dos dois é um modelo novo já treinado.

A estimativa de estados do perfil local é 327.899.136 bytes, excluindo ativações
e overhead. Somente uma calibração na própria GTX pode confirmar memória e vazão.
O script `scripts/calibrate-gtx1650.ps1` prepara essa medição em Windows e permite
comparar FP16 e FP32; GPUs GTX sem tensor cores podem não ganhar velocidade com
FP16. O resultado real prevalece sobre qualquer expectativa. O script PowerShell
foi executado nativamente no CI Windows para verificar a recusa sem CUDA. Não
foi executado na GTX do proprietário; este executor local continua sendo Linux.

O preflight confere as partições previamente atribuídas, hashes, vocabulário,
contexto e disponibilidade CUDA. O programa de calibração opcional faz de 2 a
20 passos descartáveis em GPU local para medir memória e vazão. **Não é o
pré-treino completo e não salva um modelo conversacional.** O caminho GPU ainda
não foi executado neste ambiente somente CPU; não há fallback silencioso para
um treino grande em CPU, nem serviço pago usado.

A estimativa de 16 bytes por parâmetro para pesos, gradientes e Adam não inclui
ativações, atenção, buffers e overhead. Não é promessa de que caiba numa GPU
específica. Este corpus amostrado ainda é pequeno para esse modelo; é uma base
inicial reproduzível, não um orçamento suficiente para equivalência ao ChatGPT.
A fonte integral está identificada para uma coleta maior com armazenamento e
computação adequados. A revisão de qualidade e um novo protocolo de avaliação
independente também continuam necessários antes de alegar avanço conversacional.

## Reprodução

No repositório com Python 3.12 e um ambiente virtual:

```bash
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install psutil pytest -r requirements-aira.txt
python -m learning.wiki_foundation --fetch --output scratch/foundation-reproduction
python -m learning.corpus_tokenizer --corpus scratch/foundation-reproduction --vocab-size 8192
python -m learning.curriculum_v2 --tokenizer scratch/foundation-reproduction/tokenizer --output scratch/curriculum-reproduction
python -m learning.foundation_preflight
python -m pytest -q
```

Os dados preparados já estão incluídos, assim a reprodução completa não é necessária
para inspecioná-los. Os preparadores recusam sobrescrever conjuntos existentes.
Para o preflight padrão, os dados publicados permanecem nos caminhos definidos
no perfil. Em uma GPU local com PyTorch CUDA compatível, a calibração opcional é:

```bash
python -m learning.foundation_preflight --benchmark-steps 5 --output scratch/gpu-calibration.json
```

Usar PyTorch CPU não habilita CUDA. Os casos de avaliação já consumidos continuam históricos;
a próxima pesquisa precisará de teste novo, congelado antes de selecionar pesos.

## Resultado da preparação e auditoria

O índice contém 79.294 alvos de 40.669 grupos de treino: 37.301 contextuais,
32.587 independentes e 9.406 candidatos lexicais a indisponibilidade/incerteza.
A massa de amostragem é, respectivamente, 60%, 30% e 10%, com tolerância numérica
de ponto flutuante. Nenhum grupo fornece mais de dois alvos. Dos 145.957 alvos
originais, 14.528 excedem o histórico completo de 2.048 tokens e 26 têm repetição
forte em seu prefixo. Os demais formam o conjunto candidato antes da redução por
grupo; as contagens e regras estão no manifesto.

`integrity-audit.json` confirmou que todos os IDs selecionados pertencem ao treino,
que os grupos respeitam o limite, que as probabilidades somam um, que os 40 casos
da fila preservam texto e máscara e que não há grupos de texto integral entre
partições dos artigos. Todos os hashes de fontes, stores e índice conferem.
A fila continua pendente: não confundir auditoria estrutural com revisão humana.

Na mesma amostra de 1.000 registros, a preparação antiga oferecia 261 janelas de
256 tokens, das quais 96 tinham prefixos candidatos a indisponibilidade: 36,8%.
A seleção nova limita a massa desse bucket a 10%, preservando a categoria. Essa
comparação muda simultaneamente vocabulário, contexto e política de histórico;
não isola uma causa da falha anterior nem prova que o novo modelo responderá bem.

## Calibração no computador informado

Na branch `recovery/foundation-curriculum-v2`, com ambiente virtual e PyTorch
CUDA compatível com o driver instalado, executar no PowerShell do Windows:

```powershell
.\scripts\calibrate-gtx1650.ps1 -Context 512 -Precision auto
# Em execuções separadas, se a primeira couber e concluir:
.\scripts\calibrate-gtx1650.ps1 -Context 1024 -Precision fp16
.\scripts\calibrate-gtx1650.ps1 -Context 512 -Precision fp32
```

O relatório contém o nome e a memória total da GPU detectada, pico de memória e
vazão. A calibração altera pesos aleatórios temporários apenas para medir o custo
de um passo; descarta-os e não publica um checkpoint de conversa. Não afirma que
o contexto 2.048 cabe só porque o teste em 512 cabe. Aqui foi verificado somente
o caminho sem CUDA: relatório explícito de falha, saída 2 e ausência de fallback
para CPU. Não conseguimos acessar ou medir a GTX local a partir deste executor.

## Verificação e estado da entrega

Suíte completa após as alterações: **147 testes aprovados e 9 ignorados**
(13,51 s). Inclui máscara de resposta-alvo, histórico completo, distribuição de
amostragem, limite por grupo, filtros de artigos, contagem em dispositivo meta
e rejeição de calibrações inválidas antes de alocar um modelo na GPU. O caminho
real sem CUDA também foi executado e produziu relatório de falha com código 2.
`git diff --check` passou. A execução PowerShell foi posteriormente verificada no CI Windows somente CPU;
a calibração real da GTX 1650 continua pendente.

O documento do proprietário foi consultado para identificar o hardware; só o
recorte técnico e o hash do documento foram registrados. O arquivo pessoal
integral não foi incluído nesta atualização. A preparação de dados e os perfis
estão concluídos; o próximo treinamento depende de medir o hardware real e
definir um orçamento de pré-treino compatível com os dados e recursos. A meta
de conversas complexas ainda não foi demonstrada.

As regras Git de fim de linha preservam os hashes dos dados preparados mesmo
com `core.autocrlf=true` no Windows. Os stores uint32 e gzip são binários; avisos
originais mantêm os bytes. O script PowerShell usa UTF-8 com BOM para que mensagens
acentuadas sejam reconhecidas também pelo Windows PowerShell 5.1. Isso não substitui
a execução nativa ainda pendente.

A checagem `windows-checkout-integrity.json` usou um clone local esparso com
`core.autocrlf=true` e checkout forçado. O README de controle foi convertido para
CRLF, confirmando que a configuração estava ativa; os dados protegidos mantiveram
todos os hashes, inclusive as partições Aira herdadas e os avisos originais.
O BOM do script também foi preservado. Esse teste foi executado em Linux e não
é um teste nativo de PowerShell ou CUDA.

Para preparar o ambiente do Windows, o repositório já fixa uma build CUDA do
PyTorch em `requirements.txt`; sua compatibilidade com o driver após a formatação
precisa ser confirmada no teste real. A preparação local pode ser feita assim:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-corpus.txt
.\scripts\calibrate-gtx1650.ps1 -Context 512 -Precision auto
```

Esses comandos devem ser executados no computador com a GTX, na branch desta
atualização. Não foram executados remotamente no Windows do proprietário. O
relatório de calibração permite escolher o tamanho de contexto e o orçamento de
treino usando medidas reais, em vez de supor que os 4 GB bastem para todo perfil.

Os novos leitores e escritores de texto usam UTF-8 explícito; os artefatos
preparados usam LF também ao serem regenerados no Windows. O exportador BPE
compartilhado foi ajustado para essa convenção sem alterar tokens ou pesos.
O cache padrão da fonte agora fica em `.cache/sources` no próprio repositório,
ignorado pelo Git, evitando presumir o diretório Linux `/workspace` no Windows.
A suíte local após esses ajustes passou novamente: 147 aprovados, 9 ignorados
(16,15 s). O workflow passou a verificar Linux e Windows, incluindo uma execução
nativa do script PowerShell que deve recusar a calibração no runner sem GPU.
A verificação em CI não equivale a medir a GTX 1650 do proprietário.

### Primeira execução nativa Windows e correções

O CI Windows inicial encontrou seis falhas: quatro leituras UTF-8 tratadas como
CP1252 e dois hashes de manifestos históricos alterados pelo checkout CRLF.
Foram corrigidas as leituras explícitas nos módulos e testes envolvidos, sem
reduzir as verificações, e os inputs históricos de `data/corpus-v0.5` passaram
a preservar os bytes originais no Git. O CI Linux já estava aprovado. A nova
execução Windows verificará as correções antes de declarar compatibilidade.

## Verificação nativa concluída

Após corrigir também um fixture que era gravado na codificação padrão CP1252,
a implementação foi aprovada no CI em **Linux e Windows**. No Windows, foram
147 testes aprovados e 9 ignorados (16,73 s). O script foi executado pelo
Windows PowerShell nativo (`powershell.exe`), produziu o diagnóstico esperado
sem CUDA e esse diagnóstico foi arquivado como artefato do workflow.

Código testado: `c588715f23b8f1a5fe5180855f06f84c30ca7e48`. Evidências em
`ci-verification.json` e no [workflow aprovado](https://github.com/Lorran1690/elysia-2.0/actions/runs/40230246482).
Essa validação cobre software, integridade e caminho de erro. A medição real
da GTX 1650 e o próximo pré-treino continuam pendentes; nenhum resultado desta
etapa autoriza afirmar que o modelo já tenha aprendido a conversar melhor.
