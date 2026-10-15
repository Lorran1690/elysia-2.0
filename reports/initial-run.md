# Relatório do primeiro experimento

Data do ambiente: 2026-10-15.

## Ambiente observado

- Sistema: Windows 64-bit.
- GPU: NVIDIA GeForce GTX 1650, 4096 MiB de VRAM.
- Driver reportado por `nvidia-smi`: 610.62.
- CUDA reportada pelo driver: 13.3.
- PyTorch usado: `2.11.0+cu128`.
- CUDA compilada no PyTorch: 12.8.
- Dispositivo efetivo: `cuda:0` / NVIDIA GeForce GTX 1650.
- Fallback CPU implementado e testado.

## Modelo

- Arquitetura: decoder-only Transformer causal.
- Blocos: 4.
- Embedding: 256.
- Cabeças: 4.
- Feedforward: 1024.
- Contexto: 256 tokens.
- Vocabulário: 259 tokens, sendo 256 bytes UTF-8 e 3 tokens especiais.
- Parâmetros: 3.357.955.
- Inicialização: aleatória local; nenhum checkpoint externo.

## Treinamento real

Configuração: 100 etapas, lote 2, AdamW, learning rate `0.0003`, clipping de gradiente `1.0`, corpus local de demonstração separado por documentos.

| Etapa | Loss treino | Loss validação |
|---:|---:|---:|
| 1 | 5.5710 | 4.8594 |
| 20 | 3.0171 | 3.2677 |
| 40 | 2.5509 | 2.7490 |
| 60 | 2.4513 | 2.7430 |
| 80 | 2.3367 | 2.5272 |
| 100 | 2.4038 | 2.6851 |

Tempo medido: 3,55 segundos no dispositivo CUDA detectado. Checkpoint: `learning/checkpoints/elysia-v0.1.pt`.

## Verificação

`12 passed in 16.59s`, incluindo codificação UTF-8, formato dos tensores, máscara causal, gradientes, lote, overfitting controlado, checkpoint, determinismo, geração, CPU e GPU disponível.

## Limitações

O corpus foi criado apenas para testar o funcionamento do pipeline. A redução da loss mostra que a rede consegue ajustar pesos e memorizar padrões pequenos; não demonstra domínio de português, conhecimento geral, raciocínio ou inteligência. Não há interface, voz, memória de longo prazo nem controle do computador nesta etapa.
