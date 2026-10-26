# Ensaio de conversação v3

Hipótese congelada antes do treino: reduzir o peso de aberturas genéricas e treinar
continuações com histórico intacto pode reduzir o colapso de respostas observado
no aplicativo. É um experimento limitado no Transformer próprio de 2.567.616
parâmetros, não uma demonstração de conversação complexa.

O candidato parte do checkpoint de pré-treino próprio, anterior ao ajuste que
colapsou. Preserva o BPE 2048 compatível e usa até 512 tokens de contexto. Os índices
são preparados a partir das partições agrupadas Aira já versionadas. Todo esse
material é sintético, sem revisão factual ou humana independente. Não usa pesos
pré-treinados externos nem APIs de linguagem.

A amostragem atribui 60% às continuações contextuais, 30% às respostas isoladas e
10% aos candidatos lexicais de incerteza/indisponibilidade. A regra não declara que
incerteza seja errada. No máximo dois alvos por grupo; aberturas frequentes têm
peso reduzido pela frequência. O histórico não é cortado; supervisiona-se somente
a última resposta. O orçamento inicial é de 1.000 passos, lote 4, taxa máxima
0,0002, aquecimento de 50 passos e decaimento cosseno, em CPU.

Checkpoint escolhido exclusivamente pela loss dos tokens da resposta em 128 alvos
de validação. Mais 128 alvos de teste ficam para a medição final. Essas amostras
limitadas e os filtros lexicais não equivalem a avaliação semântica independente.
O diagnóstico novo `evaluation/conversation-v3.json`, congelado antes do treino,
compara candidato e checkpoint usado no app. Não é usado para escolher o passo.
Perguntas idênticas desse diagnóstico são excluídas de todos os turnos de usuário
do material preparado, em todas as partições.

Só substituir os pesos do aplicativo se o candidato superar a referência em
avaliação semântica, acertar integralmente pelo menos 12/16 casos, incluindo 5/6
contextuais, e não inventar acesso ou execução. Revisão de Codex será identificada
como tal; não é revisão humana independente. Redução de loss, isoladamente, não
autoriza publicar um modelo como melhor para conversar.

Reprodução no ambiente com dependências do projeto e requirements-corpus:

```sh
python -m learning.conversation_v3 prepare
python -m learning.conversation_v3 train
python -m learning.conversation_v3 diagnose
```

Preparação publicada e execução finalizada são imutáveis. `train --resume` retoma
apenas execução parcial com a mesma configuração e hashes. O diagnóstico recusa
sobrescrever uma avaliação já consumida. Conversas pessoais não entram no treino.
