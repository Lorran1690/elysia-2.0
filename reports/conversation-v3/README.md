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

## Resultado concluído

O treino executou os 1.000 passos em 945,52 segundos, supervisionando 722.125
tokens de resposta. O checkpoint selecionado pela validação foi o passo 1.000.
A loss de validação do candidato caiu de 4,4840 no primeiro passo para 3,5848.
Comparados nas mesmas amostras, o modelo usado pelo app e o candidato tiveram:

| Medida | Modelo do app | Candidato v3 |
| --- | ---: | ---: |
| Loss de validação | 3,7316 | 3,5848 |
| Loss de teste | 3,6649 | 3,4964 |
| Perplexidade de teste | 39,05 | 33,00 |
| Casos semânticos integralmente corretos | 0/16 | 0/16 |
| Casos contextuais integralmente corretos | 0/6 | 0/6 |
| Respostas com abertura de indisponibilidade pela heurística | 9/23 | 16/23 |
| Respostas com repetição forte pela heurística | 5/23 | 10/23 |

A revisão identificada de Codex atribuiu zero a todos os casos nos dois modelos:
não recuperam Joana, sexta-feira às dez horas, caixa laranja ou a última cor verde;
não calculam dezoito canecas nem cumprem as instruções simples. As gerações
completas estão em `generations.json` e as razões por caso em `semantic-review.json`.
Não é uma revisão humana independente. Nenhum caso novo desse diagnóstico deve
ser tratado novamente como teste ainda não visto em ensaios futuros.

A hipótese de que este ajuste de amostragem melhoraria a conversa **não foi
confirmada**. A melhora de previsão dos textos sintéticos não se traduziu em
pertinência, uso de contexto ou menor repetição. Os contadores lexicais são
heurísticos e não cobrem toda repetição nem distinguem toda incerteza legítima.
Não houve fabricação inequívoca de acesso/execução nos casos revistos; isso não
constitui demonstração geral de segurança. O gate de publicação falhou.

**Os pesos do aplicativo não foram alterados.** O candidato, seu estado de
retomada e os marcos intermediários estão preservados em
`artifacts/conversation-v3/`. O SHA-256 do checkpoint selecionado é
`82096bb401678ae443e85cfa0a46c9e0bbead1050ca7b9f260f41e905de21355`.
Dados, código e resultados foram enviados à branch `research/conversation-v3`.
Conversas pessoais não foram usadas nem publicadas.

## Próximo pré-treino e bloqueio concreto

Não repetir ajustes dessa mesma amostra ou escolher pesos por este diagnóstico.
O próximo experimento deve ampliar o pré-treino e a capacidade do núcleo próprio,
com controle de qualidade do material. O perfil próprio de 20.493.696 parâmetros,
o vocabulário 8192 e o corpus de português já estão preparados em
`configs/foundation-gtx1650.yaml` e `data/foundation-pt-v1/`. Esse vocabulário é
incompatível com os pesos 2048 existentes: requer pré-treino novo. A base preparada
continua pequena para capacidade geral e não deve ser apresentada como suficiente
para equivalência ao ChatGPT.

O executor atual não tem CUDA e não acessa o computador do proprietário. O driver
e o reconhecimento da GTX 1650 depois do reinício ainda precisam ser confirmados
com `nvidia-smi` e a calibração existente. A calibração mede memória/vazão, não é
um pré-treino completo. Não há afirmação de que o modelo maior já tenha sido
calibrado ou treinado na GTX, nem que caiba nos 4 GB sob qualquer configuração.
Essa medição é necessária antes de definir o orçamento do novo pré-treino.

A preparação pode ser auditada com `python -m learning.conversation_v3_audit`.
Após o diagnóstico, `python -m learning.conversation_v3_compare` gera a comparação
nos mesmos alvos retidos; recusa sobrescrever o relatório publicado. O teste de
retomada compara pesos e RNG após uma interrupção real por sinal em um modelo
pequeno, sem consumir o diagnóstico semântico do experimento.
