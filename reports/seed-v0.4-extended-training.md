# ELYSIA-Seed v0.4 — Fase 5: pré-treinamento experimental controlado

Status: concluído e parado no limite de etapas autorizado. Nenhum treinamento adicional foi iniciado.

Base: `47f3cfe` na branch `codex/elysia-seed-v0.4`. A configuração completa e versionada está em `configs/seed-v0.4-machado-extended.yaml`.

## Escopo e controles

Esta execução usou somente o corpus local já auditado: Dom Casmurro para treino, Memórias Póstumas de Brás Cubas para validação e Quincas Borba reservado para uma avaliação final futura. O conjunto de teste não foi tokenizado, avaliado, usado para escolher checkpoints ou usado para alterar hiperparâmetros nesta rodada.

- Arquitetura: Transformer decoder-only próprio, 4 blocos, embedding 256, 4 cabeças, SwiGLU, SDPA, contexto 256, vocabulário BPE 512 e inicialização aleatória com seed `2026`.
- Otimização: AdamW, learning rate `0,0003`, weight decay `0,01`, clipping de gradiente `1,0`, batch 1 e FP32.
- Scheduler: cosseno com warmup de 50 etapas. Este é um novo experimento e não retoma o scheduler encerrado do piloto de 200 etapas.
- Limites aplicados: máximo de 1.000 etapas e 600 segundos, interrompendo no primeiro limite.
- Checkpoints: último estado salvo a cada ponto de avaliação e melhor estado salvo somente quando a loss fixa de validação diminuiu.
- Retomada: os checkpoints preservam modelo, otimizador, scheduler, estado RNG e gerador de batches; a retomada valida hashes do corpus, tokenizador e protocolo de validação antes de continuar.
- Early stopping: habilitado, paciência de 5 avaliações e melhora mínima de `0,0005`. Não foi acionado, pois a referência de validação melhorou em todos os pontos.

## Protocolo de validação fixa

O protocolo da Fase 4 usava batches aleatórios de validação. Portanto, as losses desta fase não devem ser comparadas diretamente com as losses de validação da Fase 4 como se fossem a mesma métrica.

Nesta fase, foram construídas 256 janelas determinísticas de 256 tokens, distribuídas do offset 0 ao 178.361 da obra de validação. Cada avaliação usou exatamente as mesmas 65.536 previsões de próximo token, aproximadamente 36,7% dos 178.618 tokens de validação. O fingerprint do protocolo é `4463ddf827b154fcdb32ebc405450b23fe42f574d30c71a55a05e3689a9b6090` e o hash do token store de validação é `04afd06dfe51274c23d293ca58ee3d839170a52fb8298d0fb4cae735dce4fb50`.

O custo por avaliação foi de cerca de 0,45 s na GPU. Há também um modo opcional de validação completa, em janelas não sobrepostas, mas ele permaneceu desativado para esta execução; ele não participa da escolha do melhor checkpoint.

## Resultado do treinamento

- Etapas executadas: 1.000 de 1.000.
- Motivo de parada: `steps_limit`.
- Tempo total: 24,67 s.
- Tokens de treino processados: 256.000.
- Épocas equivalentes sobre Dom Casmurro: 1,4294.
- Throughput observado: 10.377,1 tokens/s.
- Parâmetros: 3.490.136.

| Etapa | Loss treino | Loss de validação fixa | Learning rate |
| ---: | ---: | ---: | ---: |
| 0 | - | 6,2996 | 0,000006 |
| 100 | 5,2539 | 5,4063 | 0,000298 |
| 200 | 4,9903 | 4,9667 | 0,000282 |
| 300 | 4,2787 | 4,6087 | 0,000252 |
| 400 | 4,0773 | 4,4438 | 0,000210 |
| 500 | 4,2248 | 4,3659 | 0,000162 |
| 600 | 3,9287 | 4,3119 | 0,000113 |
| 700 | 4,2045 | 4,2759 | 0,000068 |
| 800 | 4,0101 | 4,2575 | 0,000032 |
| 900 | 3,8021 | 4,2510 | 0,000008 |
| 1000 | 3,8810 | 4,2500 | 0,000000 |

O melhor checkpoint é a etapa 1.000, com loss de validação fixa `4,2500`. O último checkpoint também é a etapa 1.000. Seus pesos são idênticos; os hashes dos arquivos diferem porque cada checkpoint preserva seu próprio estado de progresso e papel.

## Recursos e checkpoints

- GPU: NVIDIA GeForce GTX 1650.
- Pico de VRAM alocada pelo PyTorch: 105,7 MiB.
- RAM residente: 1,079 GiB no início e pico amostrado de 1,259 GiB.
- Melhor checkpoint local: `learning/checkpoints/elysia-seed-v0.4-machado-extended-best.pt`, 41.977.224 bytes, SHA-256 `f8e2ec643cd963ebfd47c9c7b6d87a8a5b79af9c0fb7f8e1e75744106e1943d3`.
- Último checkpoint local: `learning/checkpoints/elysia-seed-v0.4-machado-extended-last.pt`, 41.977.224 bytes, SHA-256 `0585ed247ccc7d8259390e250393b27b43a429368424f9d6de71c6b02fbc15c1`.
- Os dois checkpoints novos e o checkpoint do piloto da Fase 4 permanecem locais e ignorados pelo Git.
- O checkpoint de 200 etapas foi preservado sem alteração: SHA-256 `e5a0134d793942eeb5905f1aacd01ad0ccde41b4657650bfe99ee8455c04a117`.

## Geração de texto

Foram usados os mesmos quatro prompts da Fase 4, com 80 tokens novos, temperatura `0,8`, top-k `20` e seed `12026`. Como o melhor checkpoint é a última etapa, as amostras do melhor e do último são iguais. Todas as saídas, inclusive as menos favoráveis, estão em `reports/seed-v0.4-extended-training-results.json`.

O modelo não treinado teve 115 caracteres inválidos ou de controle nas quatro saídas. Melhor e último checkpoint tiveram zero. Isso mostra melhora de decodificação em nível de byte/BPE, mas não prova domínio de português.

### Saídas do melhor e último checkpoint

Prompt: `Capítulo primeiro.`

```text
Capítulo primeiro. Pria a da de me
beição co tinver nia,
fuas cados só sa.

Tugos me, mas videisóde sento achavr S. Tendo tão bem lejo, e os e fazia de outros e pu
```

Prompt: `A vida é`

```text
A vida é um que tanto do posso, melhor certim, não acabincipensando passim mas a melhor para doz o vez a do que me lodada a a fel nuntallingorranhio nos de s, mas ficaça. Acl
```

Prompt: `Quando o dia`

```text
Quando o dia esta fusas benvengo riam ca ntivesitava, que a o você «Se ludade de meu sem vidovirtambem sude
nãosóser o viria de que ser muzes
mesma não s
```

Prompt: `O leitor verá`

```text
O leitor verá que me sudellos varcidos que nos de de meve do vi que este postallia,
que o indo muito. Capitu não tambem que me palmos vidas, e mesma não pa-me o e a da tanta esta frupódo,
```

## Análise qualitativa

- Formação de palavras: há mais palavras reconhecíveis e frases curtas plausíveis do que no modelo não treinado, mas ainda há muitas palavras truncadas ou inventadas, como `certim`, `ntivesitava` e `sudellos`.
- Continuidade gramatical: conectivos e estruturas locais aparecem, porém as relações entre frases são frágeis e a concordância é frequentemente quebrada.
- Repetição: as métricas encontraram duas repetições adjacentes de palavra nas quatro saídas do melhor/último checkpoint. Há repetição estrutural mais ampla, como sequências de `que`, `de` e `não`, que requer leitura humana e não é resumida por essa métrica simples.
- Caracteres inválidos: zero no melhor/último checkpoint, contra 115 no modelo não treinado.
- Coerência local: ainda baixa; as frases contêm fragmentos literários e palavras portuguesas, mas não sustentam uma ideia confiável.
- Memorização: uma busca conservadora não encontrou sequência exata de cinco ou mais palavras das saídas geradas dentro de Dom Casmurro. Isso não exclui memorização parcial, parafraseamento ou memorização que apareceria sob outros prompts.

## Overfitting, limitações e recomendação

A loss fixa de validação caiu de 6,2996 para 4,2500 sem reversão nas 11 avaliações. Não há evidência de aumento da loss de validação neste recorte, mas isso não é evidência suficiente de ausência de overfitting: o corpus tem somente três obras, um único autor, português literário histórico e apenas 1,43 época de treino.

O modelo não conversa, não demonstra compreensão de português e não é apropriado para programação, controle do PC ou respostas factuais. O resultado demonstra apenas que o modelo pequeno aprendeu padrões superficiais do corpus sob um protocolo reproduzível.

Recomendação para o próximo ciclo: congelar esta configuração, obter aprovação antes de avaliar uma única vez o teste reservado e, separadamente, propor um corpus contemporâneo licenciado e muito mais diversificado. Não prolongar este treinamento automaticamente nem ajustar hiperparâmetros com base no teste.

## Ponto de parada

Nenhum dataset adicional foi baixado, não houve aumento de arquitetura, não foi iniciada a v0.5 e não será executado outro treinamento sem aprovação explícita.
