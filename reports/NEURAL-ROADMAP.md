# Neural Core próprio: marcos de competência

> Atualização de preservação: a permissão de escrita foi corrigida. O push da branch
> `recovery/neural-first-words` foi concluído, incluindo código, dados dos ensaios,
> resultados e checkpoints. Referências abaixo ao bloqueio 403 descrevem o estado
> anterior ao envio. Nenhum merge foi realizado.

Objetivo do proprietário: conversas complexas comparáveis ao ChatGPT. Isso é uma
aspiração, não uma capacidade entregue ou uma promessa de equivalência. Os ensaios
iniciais têm centenas de milhares de parâmetros e poucos exemplos sintéticos.
Eles validam mecânica de treino e comportamento limitado; não substituem
pré-treinamento linguístico. Não extrapolar métricas desses ensaios para inteligência.

## 1. Preservar antes de escalar

Código, proveniência, configs, avaliações com erros e pesos devem ser preservados
no GitHub conforme AGENTS.md. Em 24/10/2026 tanto git push quanto criação de branch
pelo conector retornaram 403. O trabalho pode avançar localmente, mas envio remoto
está pendente. Pacotes em /workspace/elysia-backups são cópias no mesmo ambiente;
somente o download pelo proprietário ou envio remoto cria uma cópia fora dele.

## 2. Evidência inicial

Primeiras palavras: geração neural real com pesos aleatórios treinados. 24/24
frases ensinadas; 4/8 variações muito próximas. Não é avaliação de conversa geral.

Contexto: ensaio separado com nomes e cores, combinações agrupadas por split,
validação para selecionar checkpoint e teste depois de congelar essa escolha.
Medir tanto históricos com respostas intermediárias de referência quanto
conversas em que essas respostas são geradas. Não usar mecanismo de lookup para
simular memória. Esta memória é somente contexto transitório, não memória persistente.

## 3. Linguagem antes de respostas complexas

Recuperar ou formar corpus pt-BR com fonte, versão, direitos, atribuição e hashes.
Inspecionar materiais antes de treinamento; excluir dados pessoais, conteúdo sem
direitos e duplicatas. Os candidatos históricos v0.5 são planejamento, não corpus
baixado ou automaticamente aprovado. Não misturar os ensaios sintéticos com a
trilha histórica de diálogos humanos. Não substituir o Transformer por modelos
prontos. Não treinar sobre o próprio teste ou selecionar modelos por ele.

Separar documentos e grupos de origem antes do BPE. Treinar tokenizador só no
treino. Medir loss, perplexidade e compressão, além de geração livre e avaliações
fixas novas. Comparar modelo aleatório e baseline sob os mesmos dados e orçamento.
Corpora maiores ou loss menor não provam instrução, factualidade ou raciocínio.

## 4. Conversação e avaliação

Antes de declarar conversa útil, testar saudações variadas, respostas a perguntas
novas, referência a mensagens anteriores, correções, ambiguidades, admissão de
incerteza, instruções, mudança de assunto e manutenção de contexto. A avaliação
deve conter intenções e formulações diferentes das de treino, com critérios
definidos antes do teste, e relatar também falhas e taxas por categoria.

Adicionar avaliação de conversa com histórico gerado, múltiplas sementes e revisão
humana. Perguntas fora do domínio e afirmações falsas precisam de testes próprios;
um modelo pequeno pode gerar respostas erradas com alta confiança. Não usar em
decisões ou ações externas com base nesses ensaios.

## 5. Limites de recursos e continuidade

GTX 1650 4 GB / 16 GB RAM são hardware histórico do proprietário, não hardware
comprovado do ambiente de execução. Os ensaios atuais usam CPU Linux. Estimar
tokens/s, memória e custo por arquitetura antes de treinos maiores. Fixar orçamento,
checkpoint, cancelamento e política de retomada. Não autorizar gastos automaticamente.

Qualidade no nível de sistemas de fronteira depende de dados, pesquisa e computação
muito além desses pilotos. Se os recursos locais forem insuficientes, apresentar
o limite e uma decisão concreta ao proprietário, sem prometer atingir o objetivo
apenas prolongando um treino pequeno.

Voice Core permanece pausado: palavras aqui significam texto, sem TTS ou microfone.
