# Contexto neural — 24/10/2026

> Atualização de preservação: a permissão de escrita foi corrigida. O push da branch
> `recovery/neural-first-words` foi concluído, incluindo código, dados dos ensaios,
> resultados e checkpoints. Referências abaixo ao bloqueio 403 descrevem o estado
> anterior ao envio. Nenhum merge foi realizado.

## Resultado comprovado e limites

Segundo marco da reconstrução: geração de respostas usando informação de mensagens
anteriores, dentro de um domínio sintético pequeno de oito nomes e oito cores.
710.787 parâmetros, Transformer próprio iniciado do zero, sem modelos prontos,
serviços de IA, busca de respostas ou memória determinística inserida na geração.
Contexto de 384 bytes/tokens UTF-8; 3 blocos, dimensão 128, quatro cabeças, SDPA.

176 exemplos de treino, 16 de validação e 16 de teste. As combinações completas de
nome/cor são separadas por grupo entre splits; o vocabulário e os templates são
compartilhados. O treino inclui respostas de aquisição para permitir conversa real,
e as 24 frases da primeira etapa. Isto mede recombinação limitada, não novas
intenções, nomes inéditos ou domínio do português. Dados escritos pelo Codex e
identificados como sintéticos, isolados do corpus histórico v0.5 e de diálogos humanos.

CPU Linux/Python 3.12.14/PyTorch 2.14.1+cpu, duas threads, seed 25102026. 1.200
etapas, minibatch 8, AdamW lr 0,001, weight decay 0,01 e clip 1,0. Checkpoint
selecionado só pela menor loss de validação nas avaliações a cada 100 etapas:
etapa 1.000, loss de validação 0,149572. Avaliação do teste somente após seleção.
Pesos do checkpoint selecionado efetivamente diferentes da inicialização.
Tempo observado incluindo avaliação: 108,96s. Não é benchmark do hardware Windows.

| Medida | Resultado |
|---|---:|
| Reprodução dos exemplos ensinados | 151/176 |
| Combinações não vistas, histórico de referência | 12/16 |
| Combinações não vistas, respostas intermediárias geradas pelo modelo | 12/16 |
| Recuperação do nome no teste com conversa gerada | 8/8 |
| Recuperação da cor no teste com conversa gerada | 4/8 |

Os resultados não são comparáveis ao teste histórico 0/8 ou ao diagnóstico anterior
4/8. Não representam percentual de conclusão do projeto. O mesmo teste não será
usado para selecionar novas configurações ou ajustar dados.

Exemplo real do chat por CLI depois de carregar o checkpoint:

```text
Você: Meu nome é Ana.
Elysia: Entendi.
Você: Minha cor favorita é verde.
Elysia: Certo.
Você: Qual é o meu nome?
Elysia: Ana.
```

Em uma nova conversa com as mesmas duas informações, perguntar “Qual é minha cor
favorita?” produziu apenas “.”. Outros erros de cor: roxo → rosa, cinza → verde,
preto → rosa. Acertos e falhas completos estão no JSON. A Elysia AINDA NÃO mantém
conversas complexas. Não foram demonstrados raciocínio, conhecimento factual,
correção de informações, nomes arbitrários, memória persistente ou diálogo aberto.

## Usar o chat experimental no Windows

Extraia o pacote na pasta desejada e execute na raiz com Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-first-words-cpu.txt
.\.venv\Scripts\python.exe -m learning.context_words --chat artifacts/context-words/run-002/model.pt
```

Use `/limpar` antes de mudar de conversa e `/sair` para encerrar. O histórico é
local e transitório, não é gravado. O modelo pode produzir respostas erradas. Quando
o contexto enche, o chat pede reinício sem apagar silenciosamente o histórico.
Nenhuma voz ou captura é ativada. As instruções Windows não foram executadas no
computador do proprietário; a CLI equivalente foi testada em Linux.

Para reproduzir o treino em diretório novo:

```powershell
.\.venv\Scripts\python.exe -m learning.context_words --output artifacts/context-words/reproduction --steps 1200
.\.venv\Scripts\python.exe -m pytest -q
```

O checkpoint contém pesos e metadados de inferência; não contém otimizador para
retomar o treino. SHA-256 esperado:
`08b7508ba2e3352af4e7353515ed9615f0db18636a2858d5d0af37d9de653108`.
Dados e métricas de execução têm seus hashes no JSON. Reproduções entre ambientes
podem divergir; seed fixa não garante igualdade binária entre plataformas.

## Integridade e entrega

97 testes passaram, 9 ignorados (CUDA indisponível e dados históricos locais
intencionalmente ausentes). Testes novos cobrem equivalência entre formatação de
treino e inferência, máscara de resposta, origem das referências e separação dos
grupos. Chat por CLI foi exercitado com acerto e erro, sem substituir saídas.

A primeira execução de contexto foi interrompida antes de avaliação do teste porque
faltavam exemplos de respostas intermediárias de aquisição. Está identificada em
artifacts/context-words/run-001/INTERRUPTED.md. O checkpoint entregue é run-002.

O GitHub recusou push e criação de branch com 403. Commits e checkpoints estão
locais; o pacote ZIP e git bundle em /workspace/elysia-backups precisam ser baixados
para preservar uma cópia fora do ambiente enquanto a escrita remota estiver bloqueada.
Não há merge. Não declarar backup remoto concluído. AGENTS.md registra o pedido
permanente de envio das atualizações ao GitHub.

Próximo gargalo real: corpus pt-BR amplo e verificado e avaliação de intenções
novas; prolongar estes templates não leva por si só a conversação geral. Consulte
reports/NEURAL-ROADMAP.md. O painel de progresso em reports/first-words/README.md
continua “não avaliado”: estes pilotos não permitem atualizar os percentuais
históricos nem estimar proximidade ao ChatGPT.
