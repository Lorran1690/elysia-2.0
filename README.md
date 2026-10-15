# E.L.Y.S.I.A. 2.0

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

A v0.2 vive em uma branch separada e preserva a configuração e o checkpoint da v0.1. Ela adiciona um Byte-Level BPE treinado somente sobre os textos locais de demonstração:

```powershell
.\.venv\Scripts\python.exe -m learning.train --config configs/seed-v0.2.yaml --data-dir data/raw --checkpoint learning/checkpoints/elysia-seed-v0.2.pt --steps 100
```

O pipeline v0.2 aceita TXT e JSONL, valida UTF-8, normaliza NFC, remove duplicações e separa documentos em treino, validação e teste. Dados externos ainda não foram baixados; qualquer fonte pública deverá ser aprovada antes do uso.

## Geração

Depois do treinamento, gere tokens a partir dos pesos salvos:

```powershell
.\.venv\Scripts\python.exe -m learning.generate_text --prompt "E.L.Y.S.I.A." --tokens 80 --temperature 0.8 --top-k 20
```

Para gerar com o checkpoint BPE da v0.2:

```powershell
.\.venv\Scripts\python.exe -m learning.generate_text --checkpoint learning/checkpoints/elysia-seed-v0.2.pt --tokenizer-path data/processed/tokenizer-v0.2.json --prompt "E.L.Y.S.I.A." --tokens 80
```

## Estrutura

`brain/` contém o tokenizador e o Transformer; `learning/` contém dados, treino e avaliação; `tests/` contém os testes automatizados; `data/raw/` contém somente o corpus de demonstração local.
