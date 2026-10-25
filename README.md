# E.L.Y.S.I.A. 2.0

## Piloto de linguagem com conversas licenciadas

[Relatório e instruções](reports/language-pilot/README.md): Transformer próprio de
2,17 milhões de parâmetros, BPE treinado só no treino, corpus pt-BR OASST1 filtrado,
checkpoints de inferência e retomada. A nova avaliação aberta teve **0/8 critérios
atendidos**; este piloto ainda não conversa de forma confiável. Os modelos e
resultados dos ensaios anteriores permanecem preservados. Branch desta etapa:
`recovery/neural-language-pilot`.

## Recuperação — primeiras palavras (24/10/2026)

Segundo marco: [chat experimental com contexto](reports/context-words/README.md).
Recuperação de informações em combinações sintéticas não vistas: 12/16, inclusive
com respostas intermediárias geradas. Ainda não é conversação geral. Código, resultados e checkpoints estão preservados no GitHub na branch
`recovery/neural-first-words`; a permissão de escrita foi corrigida.

Treino diagnóstico do Transformer próprio a partir de pesos aleatórios: 24/24
exemplos ensinados e 4/8 variações próximas por correspondência exata. Ainda não
é conversação confiável. Dados sintéticos, pesos, limites e instruções de execução
estão em [reports/first-words/README.md](reports/first-words/README.md).

Primeira etapa experimental: uma rede neural pequena, inicializada aleatoriamente e treinada localmente para validar um pipeline de linguagem. Este repositório é independente do projeto anterior.

## Limites desta etapa

- Não usa Ollama, APIs de IA, pesos ou tokenizadores pré-treinados.
- Não oferece interface gráfica, holograma, voz ou controle do computador.
- O corpus incluído é pequeno e criado apenas para testes; não prova que o modelo aprendeu português.
- Redução de loss em overfitting controlado demonstra o funcionamento do treinamento, não inteligência geral.

## Ambiente Windows

Instale Python 3.12 ou mais recente dentro da faixa suportada pelo PyTorch e crie um ambiente virtual:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

O arquivo de requisitos fixa a build CUDA 12.8 do PyTorch. Ela foi validada neste computador com driver NVIDIA 610.62, CUDA reportada 13.3 e GTX 1650. Em outro computador, o código continua usando CPU quando `torch.cuda.is_available()` for falso.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Treinamento

```powershell
.\.venv\Scripts\python.exe -m learning.train --config configs/seed-v0.1.yaml --steps 100
```

Para forçar CPU ou CUDA:

```powershell
.\.venv\Scripts\python.exe -m learning.train --device cpu --steps 20
.\.venv\Scripts\python.exe -m learning.train --device cuda --steps 20
```

O checkpoint fica em `learning/checkpoints/elysia-v0.1.pt`. Executar novamente com o mesmo caminho retoma o estado salvo quando o número de etapas configurado for maior que o passo já salvo.

## ELYSIA-Seed v0.2

A v0.2 vive em uma branch separada e preserva a configuração e o checkpoint da v0.1. A revisão auditada divide as obras antes do BPE, treina o BPE somente no split de treino e usa armazenamento de tokens em disco:

```powershell
.\.venv\Scripts\python.exe -m learning.train --config configs/seed-v0.2.yaml --data-dir data/raw --checkpoint learning/checkpoints/elysia-seed-v0.2-audited.pt --steps 100
```

TXT é tratado como uma obra inteira; JSONL agrupa registros por identificador de fonte quando disponível. O checkpoint recusa retomada quando corpus, split, tokenizador ou arquitetura não correspondem. Dados externos ainda não foram baixados; qualquer fonte pública deverá ser aprovada antes do uso.

## Geração

Depois do treinamento, gere tokens a partir dos pesos salvos:

```powershell
.\.venv\Scripts\python.exe -m learning.generate_text --prompt "E.L.Y.S.I.A." --tokens 80 --temperature 0.8 --top-k 20
```

Para gerar com o checkpoint BPE da v0.2:

```powershell
.\.venv\Scripts\python.exe -m learning.generate_text --checkpoint learning/checkpoints/elysia-seed-v0.2-audited.pt --tokenizer-path data/processed/tokenizer-v0.2-audited.json --prompt "E.L.Y.S.I.A." --tokens 80
```

## ELYSIA-Seed v0.3

A v0.3 mantém a v0.2 como baseline e adiciona escolhas experimentais para RoPE, RMSNorm, SwiGLU, SDPA e KV cache. As ablações locais podem ser reproduzidas sem dados externos:

```powershell
.\.venv\Scripts\python.exe -m learning.ablate --device cuda --steps 30
```

O relatório e o resultado completo ficam em `reports/seed-v0.3.md` e `reports/seed-v0.3-results.json`. Use `use_cache=True` com `brain.generate.generate` para a geração com cache.

## Estrutura

`brain/` contém o tokenizador e o Transformer; `learning/` contém dados, treino e avaliação; `tests/` contém os testes automatizados; `data/raw/` contém somente o corpus de demonstração local.
