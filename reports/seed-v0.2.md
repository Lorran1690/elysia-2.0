# Relatório ELYSIA-Seed v0.2

Branch: `codex/elysia-seed-v0.2`.

## Alterações

- Corrigido o decode incremental de bytes UTF-8 incompletos durante geração.
- Checkpoints v2 agora guardam estados Python, PyTorch, CUDA e do gerador de lotes.
- O carregamento usa `weights_only=True`, valida campos, configuração do modelo e fingerprint do tokenizador.
- A divisão exige pelo menos três documentos e produz treino, validação e teste disjuntos.
- O carregador lê TXT e JSONL linha a linha, valida UTF-8, normaliza NFC, remove duplicações e registra hashes/erros.
- Adicionado Byte-Level BPE próprio, com vocabulário JSON versionado e tokens especiais.
- Adicionada CI para a suíte sem GPU.

## Tokenizadores

| Tokenizador | Vocabulário | Bytes | Tokens | Bytes/token | Limite uniforme estimado (bits/byte) |
|---|---:|---:|---:|---:|---:|
| ByteTokenizer v0.1 | 259 | 4.417 | 4.417 | 1,000 | 8,0168 |
| ELYSIA-BPE v0.2 | 512 | 4.417 | 1.744 | 2,5327 | 3,5535 |

O limite em bits/byte é uma comparação uniforme baseada no vocabulário, não perplexidade nem evidência de compreensão.

## Dataset local

- Arquivos válidos: 4.
- Documentos: 16 linhas não vazias.
- Duplicações: 0.
- Registros inválidos: 0.
- Caracteres: 4.417.
- Bytes UTF-8: 4.417.
- Origem: textos criados especificamente para demonstração técnica.
- Dados externos: nenhum baixado.

## Treino controlado

- Arquitetura separada da v0.1, com 4 blocos, embedding 256, 4 cabeças, feedforward 1024 e contexto 256.
- Vocabulário BPE: 512.
- Parâmetros: 3.487.744.
- Dispositivo: NVIDIA GeForce GTX 1650 via CUDA 12.8 (`torch 2.11.0+cu128`).
- 50 etapas iniciais em 1,32 s; retomada verificada até a etapa 55 em 0,47 s.
- Loss de treino: `6,2579` na etapa 1, `4,0510` na etapa 50 e `3,8236` na etapa 55.
- Loss de validação: `6,1603` na etapa 1, `5,5991` na etapa 50 e `5,5814` na etapa 55.
- Loss no split de teste na etapa 55: `5,6726`.

Isso demonstra ajuste em um corpus pequeno; não demonstra que o modelo compreende português.

## Testes

`21 passed in 7.02s`, incluindo BPE, Unicode, TXT/JSONL, deduplicação, splits, máscara causal, gradientes, overfitting, checkpoint seguro, restauração de RNG, determinismo, geração, CPU e GPU disponível.

## Limitações e v0.3 proposta

O corpus ainda é pequeno demais para conclusões linguísticas. A próxima etapa poderia ampliar dados autorizados, medir melhor perplexidade e criar avaliações fixas de texto não visto. Isso é apenas uma proposta; a v0.3 não foi iniciada.
