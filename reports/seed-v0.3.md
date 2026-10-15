# Relatório ELYSIA-Seed v0.3

Branch: `codex/elysia-seed-v0.3`, criada a partir de `b64316c`.

## Auditoria da v0.2

A baseline é um Transformer decoder-only com quatro blocos pré-norm. Cada bloco usa projeção QKV fundida, atenção causal manual, embeddings posicionais absolutos, `LayerNorm` e feedforward GELU de dimensão 1.024. A geração recalculava todo o contexto a cada token; não havia cache. O limite de contexto é 256 tokens. A v0.2 já preservava corpus local, tokenizador auditado, splits e tokens em disco.

## Componentes implementados

- RoPE aplicado somente a Query e Key, incluindo o deslocamento de posição ao usar cache.
- RMSNorm com cálculo da magnitude em `float32` para estabilidade e retorno no dtype original.
- SwiGLU com largura interna `round(2 * ffn / 3)`, mantendo sua projeção em aproximadamente a mesma quantidade de parâmetros da GELU.
- Backend `scaled_dot_product_attention` com rota manual correta caso a função não exista no PyTorch local.
- KV cache por camada. Quando a janela chega a 256 tokens, a geração a reconstrói a partir do contexto recente para não ultrapassar o limite.

Não foi implementado GQA: para este modelo pequeno e esta GTX 1650 não havia justificativa mensurável antes da experiência. Não foram usados BF16, precisão mista, kernels de terceiros, pesos externos, APIs, Ollama ou datasets externos.

## Configurações e validação

As seis configurações em `configs/seed-v0.3-*.yaml` usam a mesma semente (`2026`), os mesmos hashes/split auditados da v0.2 e BPE local congelado. Cada uma foi inicializada do zero, treinada por 30 etapas e salva em `learning/checkpoints/elysia-seed-v0.3-*.pt`.

| Experimento | Parâmetros | Test loss | Etapa (ms) | Tokens/s treino | Geração sem cache tok/s | Com cache tok/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline manual | 3.483.640 | 5,4745 | 23,32 | 5.488,7 | 174,9 | 27,3 |
| RoPE | 3.418.104 | 5,4918 | 23,00 | 5.565,7 | 129,7 | 122,4 |
| RMSNorm | 3.481.336 | 5,4399 | 21,02 | 6.089,8 | 202,3 | 188,3 |
| SwiGLU | 3.486.032 | 5,3236 | 16,31 | 7.847,9 | 228,3 | 248,6 |
| SDPA | 3.483.640 | 5,4745 | 12,63 | 10.137,3 | 334,0 | 46,8 |
| RoPE + RMSNorm + SwiGLU + SDPA | 3.418.192 | 5,5192 | 25,58 | 5.004,4 | 135,2 | 111,5 |

As diferenças de parâmetros são pequenas: RoPE remove a tabela absoluta de 65.536 parâmetros; RMSNorm remove os vieses da LayerNorm; SwiGLU ficou a menos de 1% da baseline. O artefato completo e reproduzível está em `reports/seed-v0.3-results.json`.

## Recursos e GTX 1650

Os benchmarks usaram CUDA na NVIDIA GeForce GTX 1650, lote 2 e sequência 64 para treino; geração determinística de 32 tokens, lote 1 e prompt de 16 tokens. O pico de VRAM foi 82,7–84,2 MiB; o RSS do processo foi 1,14–1,23 GiB, incluindo PyTorch e alocadores do processo. O KV cache do prompt de 16 tokens ocupa 131.072 bytes neste modelo.

SDPA foi o backend mais rápido para treino e geração sem cache. O cache não foi uma vitória universal neste microbenchmark: a sobrecarga de chamadas por token prejudicou baseline e SDPA; somente SwiGLU melhorou de 228,3 para 248,6 tokens/s. Portanto, o cache permanece um recurso de correção e escalabilidade de contexto, não uma alegação de velocidade geral nesta GPU e neste tamanho de modelo.

## Testes e segurança

- `36 passed` localmente, incluindo RoPE, RMSNorm, SwiGLU, equivalência manual/SDPA, cache multi-token, janela de contexto, CPU e CUDA.
- CI continua CPU-only e executa a mesma suíte.
- Checkpoints continuam com `weights_only=True`, fingerprints do tokenizador, hashes de dados, manifests, RNG e fingerprint de arquitetura. Pesos de arquiteturas incompatíveis são rejeitados na retomada.

## Decisões

- **Aprovado para investigação futura:** SwiGLU, pois obteve a menor loss de teste nesta execução curta, contagem semelhante de parâmetros e melhor resultado de cache. SDPA também é aprovado como backend opcional de treino pelo ganho de throughput, mas não como evidência de cache rápido.
- **Mantido opcional:** RMSNorm e RoPE. Funcionam corretamente, mas este corpus pequeno não demonstra vantagem confiável de qualidade.
- **Rejeitado nesta etapa:** combinação completa, que teve a maior loss de teste; GQA e precisão mista, por falta de evidência prática neste hardware.

## Limitações e recomendação para v0.4

Quatro obras locais e 30 etapas apenas testam engenharia, não compreensão nem superioridade linguística. As medições de geração são curtas e específicas da GTX 1650. A recomendação é investigar uma configuração SwiGLU com SDPA opcional e repetir os testes com um corpus autorizado maior e avaliações fixas. A v0.4 não foi iniciada.
