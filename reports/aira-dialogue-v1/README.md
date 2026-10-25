# Expansão de conversas sintéticas e novo piloto

Status: corpus e treino concluídos. Marco experimental REPROVADO: 0/8 casos integralmente corretos, incluindo 0/3 conversas com contexto. A meta de conversas complexas permanece não atingida.

## Fonte e limites

Fonte: [Instruct-Aira v3](https://huggingface.co/datasets/nicholasKluge/instruct-aira-dataset-v3),
revisão imutável `1ca52371453cc9e52b650ba4314f2ca0a69f58ba`, split português,
50.000 conversas originais. O autor publica o conjunto sob Apache 2.0; cópias
integrais da licença e da ficha estão em `data/aira-pt-v1/SOURCE-*`.
São **respostas sintéticas de modelos já ajustados**, com prompts provenientes de
outros conjuntos públicos. Não são conversas humanas verificadas. A licença
publicada pelo distribuidor não prova revisão independente dos direitos de cada
prompt. Não houve download de pesos desses modelos nem uso de API de inferência.

A busca também encontrou Tucano-SFT (mistura com licenças por componente),
PortugueseDolly (tradução com versões contraditórias sobre o tradutor e restrição
não comercial) e evol-instruct-portuguese (ficha sem licença suficiente).
Estes três conjuntos não foram adicionados. Aira foi escolhido pela ficha com
procedência declarada, licença integral e conversas com múltiplos turnos.

O preparador rejeita papéis inválidos, respostas menores que 20 caracteres,
conversas incompletas, comprimentos excessivos, identidades de outros assistentes,
padrões de identificadores e sobreposição textual com os diálogos históricos.
Não substitui anotação humana, verificação factual ou auditoria completa de PII.
Só o corpus filtrado é publicado; o original permanece no cache local e pode
ser recuperado por URL imutável, tamanho e SHA-256 fixos. Não publicar o parquet
original indiscriminadamente. Paráfrases e contaminação anterior de benchmarks
podem permanecer, apesar dos filtros de coincidências exatas normalizadas.

As partições seguem componentes conexos: perguntas iniciais iguais ou mensagens
iguais com pelo menos 80 caracteres unem conversas, inclusive transitivamente.
O hash do grupo define treino/validação/teste (90/5/5 buckets; proporções reais
podem variar). Cada fragmento gzip tem hash e tamanho no manifesto. Todos os
registros mantêm `synthetic: true` e `independently_fact_checked: false`.

## Protocolo do piloto

Inicializar do próprio checkpoint de linguagem de 8.000 passos, anterior ao
sobreajuste com confirmações curtas; não inicializar do diálogo v2 reprovado.
Manter o Transformer de 2.567.616 parâmetros e o próprio BPE 2.048.
Não misturar as antigas confirmações sintéticas de diagnóstico.

2.000 passos, batch 4, contexto de treino 256, AdamW lr base 0,00015, warmup
100 passos e decaimento cosseno, clip 1, CPU 2 threads. Treinar somente respostas
com a pergunta completa presente. Não sortear caudas desconectadas da resposta.
Por conversa, considerar a primeira e a última resposta; manter o máximo de
turnos anteriores que couberem; rejeitar se o par final completo não couber.
Apenas a última resposta da janela recebe loss. Isso limita o piloto a interações
curtas e não testa conversas extensas de forma adequada.

Selecionar só pela loss de assistente na validação fixa a cada 250 passos.
Validação e teste usam registros com `int(id[:8],16) % 10 == 0`, regra prévia
para limitar custo. Teste separado avaliado uma vez no checkpoint selecionado.
A loss sintética é uma métrica auxiliar e não prova qualidade semântica.

O conjunto `evaluation/aira-v1.json` foi congelado antes do treino e contém oito
novos casos, três deles com histórico realmente gerado. O carregador aborta se
houver sobreposição textual normalizada detectada com esses prompts. As saídas
finais são geradas uma vez e devem ser revisadas semanticamente. Os 24 casos
antigos não serão executados para escolher este modelo. Nenhum resultado nesse
pequeno teste estabelece equivalência com ChatGPT. O marco mínimo deste piloto
é 6/8 casos integralmente corretos, incluindo os três de contexto, sem invenção
de informação privada ou falsa alegação de acesso. Não reduzir a meta após ver
as respostas. É somente um marco experimental, muito menor que o objetivo geral.

## Reprodução

```bash
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install psutil -r requirements-aira.txt
python -m learning.aira_corpus --fetch --cache /caminho/cache --output /caminho/novo
# Os resultados publicados estão congelados. Para reprodução idêntica em diretório novo:
python -c "from pathlib import Path; from learning.aira_dialogue import train; train(Path('scratch/aira-reproduction'))"
# Se essa reprodução for interrompida, retomar o mesmo diretório:
python -c "from pathlib import Path; from learning.aira_dialogue import train; train(Path('scratch/aira-reproduction'), resume=True)"
```

O preparador recusa sobrescrever partições existentes. O treinador verifica hashes
dos fragmentos, fonte, código, tokenizer e checkpoint inicial. O estado inclui
modelo, otimizador e RNG; uma execução finalizada não pode ser reavaliada por
`--resume`. O comando de chat existente aceita explicitamente um checkpoint:

```bash
python -m learning.dialogue_v2_chat --checkpoint artifacts/aira-dialogue-v1/run-001/sft-model.pt
```

## Auditoria e verificações

50.000 registros originais, 45.175 retidos: 40.745 de treino, 2.163 de validação
e 2.267 de teste. Destes, apenas um registro de validação tem um único par;
os demais têm vários turnos. 4.825 foram rejeitados pelos filtros declarados.
O corpus comprimido ocupa cerca de 93 MiB, em fragmentos de até 500 registros.
A auditoria independente do preparador (`python -m learning.aira_audit`) confirmou
hashes, tamanhos, contagens, IDs únicos e nenhuma pergunta inicial ou mensagem
longa idêntica entre partições. Isso não mede diversidade semântica nem factualidade.

Suíte local após a implementação: 135 testes aprovados, 9 ignorados (33,76 s).
CI do commit de preparação: sucesso,
https://github.com/Lorran1690/elysia-2.0/actions/runs/40186336468 .
Recursos observados em `resources.json`: 3 CPUs lógicas, cerca de 9,7 GiB RAM,
PyTorch CPU, nenhuma GPU CUDA.

### Preparação das janelas

Uma tentativa de carregamento foi interrompida antes de criar qualquer checkpoint
ou executar passos de treino. O histórico era recodificado repetidamente durante
a busca de uma janela que coubesse. A nova construção codifica cada par uma vez,
remove apenas o BOS intermediário e concatena os mesmos tokens. Testes com cinco
limites de contexto conferem igualdade exata dos IDs e máscaras com a construção
de referência. Em uma amostra fixa dos primeiros 100 registros do fragmento
train-0000, ambas produzem 19 janelas; o tempo observado caiu de 3,519 s para
0,367 s. É uma medição de preparação, não ganho de capacidade neural nem benchmark
de treinamento. O protocolo estatístico e os dados permaneceram iguais.

### Janelas efetivamente usadas

O corpus completo contém 45.175 conversas, mas este piloto curto não treina em
todas. Cabem 8.697 janelas de 7.785 registros de treino. A validação fixa possui
50 janelas de 45 registros e o teste fixo 58 janelas de 55 registros. A contagem
`usable_multiturn_records` indica registros de origem com vários turnos; não
significa que todos os turnos caibam na janela. A restrição a respostas completas
curtas cria viés de seleção, registrado como limite do experimento.

A checagem adicional dos IDs originais encontrou 50.000 identificadores únicos
em 50.000 linhas. Após otimização da preparação, suíte local: **136 passaram,
9 ignorados** (17,75 s); CI também passou:
https://github.com/Lorran1690/elysia-2.0/actions/runs/40186800707 .

### Recuperação e verificação final do código

O teste mecânico novo compara uma execução contínua de três passos com uma
interrupção após o primeiro passo e retomada. Usa um Transformer minúsculo, dados
artificiais e geração substituída por fixture; não mede respostas reais. Históricos
de loss, tensores dos pesos, RNG dos batches e RNG do PyTorch coincidem exatamente.
Também verifica que uma execução finalizada recusa nova avaliação por retomada.
A suíte completa após esse teste passou: **137 aprovados, 9 ignorados** (34,33 s).
O treino real continua com o mesmo código e protocolo congelados; apenas o teste
e a documentação foram adicionados enquanto ele executava.

## Resultado final

Treino concluído nos 2.000 passos previstos, com 946.013 tokens-alvo de assistente
e 841,97 segundos de computação registrados (aproximadamente 14 minutos; não
inclui a preparação). O melhor checkpoint foi o último, selecionado só pela
validação. Loss de assistente de validação: 4,4547 no passo 1 → 3,3932 no passo
2.000; perplexidade: 86,03 → 29,76. No teste sintético separado, executado uma vez,
loss 3,1740 e perplexidade 23,90 em 6.435 tokens-alvo de assistente.

**Revisão semântica: 0/8 casos integralmente corretos, 0/3 conversas com contexto,
1/16 pontos.** Só o caso sobre informação pessoal recebeu crédito parcial:
o modelo admite falta de acesso, mas desvia para texto fornecido e repetições.
Os demais casos não respondem às perguntas. Nenhum caso tem uma fabricação
crítica privada ou de acesso identificada nesta amostra pequena; isso não
estabelece segurança geral. Não comparar diretamente essas contagens ou losses
com os 24 casos antigos: são conjuntos distintos, não uma medição pareada.

As saídas repetem “Não tenho acesso a informações específicas”, referências a
contatos e fragmentos sem relação com o pedido. A geração gulosa entra em ciclos.
A redução de loss não se traduziu em seguimento de instruções, cálculos simples
ou recuperação do contexto. Não selecionar novas configurações ou novos exemplos
de treino usando estes oito casos: agora são diagnóstico histórico.

As saídas completas, inclusive as ruins, estão em
`artifacts/aira-dialogue-v1/run-001/results.json`. A revisão registra uma nota,
justificativa e hash por caso em `semantic-review.json`; as contagens e o marco
fixo estão em `scores.json`. A revisão foi feita pelo Codex, sem avaliador humano
independente. Os hashes do checkpoint de inferência, retomada e resultados estão
em `artifact-hashes.json`. O checkpoint intermediário do passo 500 também foi
preservado no GitHub durante o treinamento.

O trabalho ampliou e auditou a base de conversas, melhorou a preparação e a
recuperação do treino e produziu novos pesos próprios. **Não produziu uma
assistente de conversa útil ou equivalente ao ChatGPT.** O objetivo amplo fica
bloqueado pela escala atual de pré-treino, modelo, contexto e computação,
e pela falta de validação humana independente. Os requisitos concretos para
avançar estão em [next-stage.md](next-stage.md); ampliar só as épocas desse
piloto não constitui uma solução demonstrada.

O carregamento real pelo comando de chat também foi verificado com o checkpoint
final: à saudação “Bom dia, Elysia.”, respondeu repetidamente sobre não ter acesso
a informações do “texto fornecido”. Isso confirma que o checkpoint é executável,
mas também expõe a ausência de uma saudação pertinente. O smoke test não é
pontuado como parte dos oito casos congelados.

As instruções de reprodução usam um diretório novo, pois os resultados finais
publicados são imutáveis. O checkpoint já incluído pode ser usado no chat sem
repetir o treinamento. A repetição exata serve à reprodução, não transforma
os oito casos já consumidos em um teste novo para escolher hiperparâmetros.
