# Relatório ELYSIA-Seed v0.2 auditada

Branch: `codex/elysia-seed-v0.2`.

## Escopo da revisão

- O split é realizado antes do BPE. O vocabulário `tokenizer-v0.2-audited.json` é treinado apenas nos dois trabalhos do conjunto de treino.
- TXT passou a ser uma obra por arquivo. Em JSONL, registros com `source_id`, `source`, `document_id` ou `id` são agrupados como uma única obra.
- Duplicatas exatas são removidas; uma assinatura SimHash impede que textos muito próximos cruzem os splits. Isso é uma proteção heurística, não uma prova de que toda paráfrase foi identificada.
- O corpus, o BPE e os tokens são processados em fluxo. Os tokens de cada split ficam em arquivos `uint32` locais e os lotes leem somente as janelas necessárias.
- Checkpoints v3 guardam hashes dos arquivos brutos, split, tokenizador, armazenamento de tokens e arquitetura. Retomar com qualquer assinatura diferente falha.
- A geração usa `torch.load(..., weights_only=True)` e valida tokenizador, vocabulário e fingerprint antes de carregar pesos.

## Artefatos auditados

- Checkpoint: `learning/checkpoints/elysia-seed-v0.2-audited.pt`.
- Tokenizador: `data/processed/tokenizer-v0.2-audited.json`.
- Manifesto do tokenizador: `data/processed/tokenizer-v0.2-audited.manifest.json`.
- Assinatura do split: `c9a65101755a05aa2358eecbc176e42cedd969383bd8334fa026c2657deb8fea`.
- Assinatura dos dados do checkpoint: `3d0502249685b2867fcfa3da6a17585ef7541baf4b2e2e096c8a5b260bd5965e`.

## Corpus local

- 4 arquivos, 4 obras, 0 duplicatas exatas e 0 registros inválidos.
- 4.445 bytes locais autorizados; nenhum dado externo foi baixado.
- Split: 2 obras para treino, 1 para validação e 1 para teste.
- BPE: 504 tokens no vocabulário solicitado de até 512; fingerprint `a32081fee958e524c42168236253f9c9a21c4f3868cd8d99114ed241ebae15b6`.

## Treinamento novo e retomada

Executado localmente em NVIDIA GeForce GTX 1650/CUDA:

| Etapa | Loss treino | Loss validação |
| ---: | ---: | ---: |
| 1 | 6,2490 | 6,1099 |
| 20 | 5,0042 | 5,6404 |
| 30 | 4,1937 | 5,5339 |
| 35, após retomada | 4,4449 | 5,5167 |

- 30 etapas iniciais: 2,55 s.
- Retomada de 30 para 35: 0,62 s.
- Loss de teste após a etapa 35: `5,4371`.
- A recarga segura do checkpoint e uma geração curta foram verificadas. A saída ainda é rudimentar, como esperado para este corpus mínimo.

## Resultados antigos

As métricas previamente registradas para a v0.2 **não são comparáveis** com este relatório. O BPE anterior foi aprendido antes do split e a unidade de TXT era uma linha; os números antigos permanecem no histórico, mas não são evidência auditada de generalização.

## Limitações

O corpus é pequeno demais para qualquer alegação de compreensão de português. A detecção de texto semelhante é deliberadamente leve e pode deixar passar paráfrases distantes. Esta revisão não inicia v0.3, não usa dados externos e não adiciona RoPE, RAG, LoRA, quantização ou novas camadas de produto.
