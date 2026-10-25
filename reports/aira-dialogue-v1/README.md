# Expansão de conversas sintéticas e novo piloto

Status: corpus preparado e auditado; novo piloto em andamento. Não há demonstração de conversas complexas.

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
python -m pip install -r requirements-aira.txt
python -m learning.aira_corpus --fetch --cache /caminho/cache --output /caminho/novo
python -m learning.aira_dialogue
# Se interrompido, preservar o diretório e retomar sem mudar código/dados:
python -m learning.aira_dialogue --resume
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
