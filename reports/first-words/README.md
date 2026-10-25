# Neural Core — primeiras palavras, 24/10/2026

> Atualização de preservação: a permissão de escrita foi corrigida. O push da branch
> `recovery/neural-first-words` foi concluído, incluindo código, dados dos ensaios,
> resultados e checkpoints. Referências abaixo ao bloqueio 403 descrevem o estado
> anterior ao envio. Nenhum merge foi realizado.

Base recuperada: `codex/elysia-seed-v0.5`, commit `c05120076930994602147bb696882adf94c7cc1f`.
Branch de recuperação: `recovery/neural-first-words`. Push autorizado pelo proprietário; sem merge.

## O que foi demonstrado

Treinamento real a partir de inicialização aleatória do ElysiaTransformer existente,
com 292.291 parâmetros, dois blocos, dimensão 96, quatro cabeças, contexto de 192
bytes/tokens, atenção causal SDPA e tokenização UTF-8 própria. Não usa modelos ou
pesos externos, busca de respostas, rede, voz ou microfone na inferência.

O ensaio supervisiona somente a resposta e EOS, ignorando pergunta e padding na
loss. Usa 24 pares sintéticos escritos pelo Codex, separados e identificados em
`data/first-words/`. Eles não são diálogos humanos, dados aprovados da v0.5 nem
corpus de produção. Este pequeno ensaio de memorização não substitui a preparação
de corpus amplo, licenciado e revisado para desenvolvimento linguístico.

CPU, duas threads, seed 24102026, 1.000 etapas AdamW, lr 0,002, weight decay 0,01,
clip de gradiente 1,0, batch completo. Uma única execução; configuração fixada
antes da avaliação final. Loss de treino: 5,587825 → 0,000212. Tempo observado,
incluindo avaliação: 47,04 segundos; não representa benchmark do Windows/GTX 1650.

24/24 respostas ensinadas foram reproduzidas. 4/8 variações não vistas tiveram
correspondência exata. As variações são próximas dos exemplos ensinados, inclusive
mudanças de pontuação; este conjunto NÃO mede generalização a temas novos e NÃO é
a avaliação histórica 0/8. A pergunta “Qual seu nome?” gerou “Elysia.”, resposta
plausível mas diferente da referência; a pontuação exata foi preservada. Outras
perguntas geraram texto corrompido, por exemplo “Me diga seu nome.” → “Estou ndonto
eintoia.”. Todos os acertos e erros estão em `run-001.json`.

Os pesos foram efetivamente atualizados, salvos e recarregados com `weights_only=True`;
a igualdade dos pesos após recarga foi verificada. O checkpoint contém pesos e
metadados de inferência, sem otimizador ou retomada. Para reproduzir o treino,
use um diretório novo. Os hashes de dados e checkpoint estão no JSON.

## Usar no Windows

Na raiz do projeto extraído, com Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-first-words-cpu.txt
.\.venv\Scripts\python.exe -m learning.first_words --checkpoint artifacts/first-words/run-001/model.pt --ask "Qual é o seu nome?"
.\.venv\Scripts\python.exe -m learning.first_words --checkpoint artifacts/first-words/run-001/model.pt --ask "Você está aprendendo?"
```

As respostas são geradas byte a byte com seleção greedy e EOS; não existe tabela
de respostas na inferência. Perguntas longas são recusadas pelo limite de contexto.
Não mantém histórico entre perguntas. O modelo pode errar mesmo em perguntas simples.

Para reproduzir o experimento em outro diretório:

```powershell
.\.venv\Scripts\python.exe -m learning.first_words --output artifacts/first-words/run-002 --steps 1000
.\.venv\Scripts\python.exe -m pytest -q tests/test_first_words.py
```

A instalação CPU é separada dos requisitos CUDA históricos, que foram preservados.
O treino e as instruções foram executados em Linux/Python 3.12.14/PyTorch
2.14.1+cpu; os comandos PowerShell são instruções de reprodução, ainda não validadas
no computador do proprietário. O checkpoint está incluído no Git e no pacote ZIP desta entrega. Conserve também
uma cópia própria do pacote. A orientação permanente de envio ao GitHub está
registrada em `AGENTS.md`.

## Validação

Suíte histórica: 88 testes passaram, 9 ignorados (CUDA indisponível e arquivos
históricos locais ausentes). Novos testes: 3 passaram, cobrindo máscara de resposta,
EOS/padding, rejeição de truncamento, separação de perguntas e inferência efetiva
pelos logits. Não foi alterado código do Transformer ou corpora históricos.

## Painel de evidências

**Progresso geral: não avaliado** · barra: `░░░░░░░░░░` · variação: N/A.
Os 38% históricos não podem ser transportados para o projeto recuperado.
As barras vazias abaixo indicam ausência de estimativa auditada, não prova de ausência de código.
Não há soma ou média automática.

| Módulo | Barra | Atual | Comparação histórica / evidência |
|---|---|---|---|
| Neural Core | ░░░░░░░░░░ | Não avaliado | Antes 82%; treino e inferência pequenos validados agora |
| Competência conversacional | ░░░░░░░░░░ | Não avaliado | Antes 8%; memorização 24/24 e variações próximas 4/8, sem conversa geral |
| Cognitive Core | ░░░░░░░░░░ | Não avaliado | Antes 78%; não recuperado nesta missão |
| Autonomia | ░░░░░░░░░░ | Não avaliado | Antes 40%; não validada |
| Code Core | ░░░░░░░░░░ | Não avaliado | Antes 60%; não validado |
| Vision Core | ░░░░░░░░░░ | Não avaliado | Antes 43%; não validado |
| Image Core | ░░░░░░░░░░ | Não avaliado | Antes 43%; não validado |
| Knowledge Vault | ░░░░░░░░░░ | Não avaliado | Antes 35%; não recuperado |
| Computer Control | ░░░░░░░░░░ | Não avaliado | Sem implementação validada |
| Knowledge Graph | ░░░░░░░░░░ | Não avaliado | Sem implementação validada |
| Agent Orchestration | ░░░░░░░░░░ | Não avaliado | Sem implementação validada |
| Security Core | ░░░░░░░░░░ | Não avaliado | Sem implementação validada |
| Media Studio | ░░░░░░░░░░ | Não avaliado | Sem implementação validada |
| Avatar | ░░░░░░░░░░ | Não avaliado | Antes 25%; não validado |
| Voice Core | ░░░░░░░░░░ | Pausado | Antes 10%; nenhuma voz desenvolvida |

## Próximo marco

Corpus pt-BR diversificado com proveniência e direitos verificados, avaliação nova
por famílias de intenção, várias sementes e perguntas realmente distintas. Não
ajustar este experimento repetidamente para melhorar os mesmos oito itens de teste.
Também sobreviveram checkpoints históricos v0.1–v0.4 piloto no Git; o checkpoint
final Machado estendido específico permanece ausente. Eles não foram usados aqui.
