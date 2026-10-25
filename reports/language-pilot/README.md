# Piloto de linguagem pt-BR

Objetivo: sair dos templates sintéticos para um primeiro lote externo com licença,
proveniência, splits por conversa e avaliação aberta. Não representa equivalência
com ChatGPT nem demonstra conversa complexa.

## Dados e direitos

Fonte: OpenAssistant/oasst1, revisão fdf72ae0827c1cda404aff25b6603abec9e3399b.
Arquivo ready.messages de 12/04/2023. A versão original tem 88.838 mensagens em
múltiplos idiomas; o lote pt-BR da fonte contém 1.203 mensagens. A fonte descreve
contribuição humana e marca estas mensagens como não sintéticas, mas isso não prova
que todos os autores realmente escreveram sem auxílio de modelos.

O publicador declara licença Apache 2.0. O arquivo LICENSE e a ficha originais
estão preservados em data/language-pilot, com hashes no manifesto. Atribuição:
OpenAssistant contributors / LAION-AI, OASST1, 2023. Os derivados mantêm IDs de
mensagem/árvore para proveniência, mas não IDs de contas ou timestamps. O arquivo
original multilíngue está fora do Git porque contém metadados e idiomas fora do
escopo; a URL imutável e o hash permitem recuperação e verificação. Nenhum serviço
externo de IA ou modelo pré-treinado foi usado pelo Neural Core.

Filtros exigem pt-BR, revisão positiva, synthetic=false, ausência de model_name,
qualidade mínima 0,6, ao menos dois votos com valor zero nos rótulos PII/spam/
inadequação/idioma/ódio/sexual/violência, limites de comprimento e ausência de padrões
de e-mail, URL e identificadores numéricos. Excluem também poesia/letras e confusão
de identidade com outros assistentes. Caminhos incompletos depois dos filtros são
rejeitados. Isto é triagem automática, não garantia de autoria, factualidade ou
revisão completa de privacidade. Não publicar fonte bruta ou metadados de contas.

Uma revisão encontrou resposta sobre sinuca para pergunta sobre pôquer, apesar de
rótulos positivos. O ID foi explicitamente excluído, e a primeira execução foi
interrompida antes da avaliação final. O registro está em MANUAL_EXCLUSIONS e no
arquivo INTERRUPTED.md. O corpus corrigido tem 111 caminhos em 47 árvores: 96 de
treino (39 grupos), cinco de validação (quatro grupos) e dez de teste (quatro grupos).
Isto é muito pouco para competência conversacional e contém vieses da seleção.

Árvores inteiras, duplicatas textuais longas e prompts iniciais muito próximos são
agrupados antes do split. Prefixos repetidos de ramificações permanecem dentro da
mesma partição. A deduplicação não prova ausência de duplicatas semânticas.
O treino contém cerca de 138 mil caracteres contando prefixos repetidos.
Não é um corpus amplo. Não houve mistura com os ensaios sintéticos anteriores,
alteração do corpus histórico v0.5 ou uso automático de conversas privadas.

## Treinamento e avaliação

Transformer próprio com 2.173.376 parâmetros, quatro blocos de dimensão 192,
quatro cabeças, RoPE, RMSNorm, SwiGLU e SDPA. BPE próprio com vocabulário 1.024,
treinado somente nas mensagens únicas de treino. Não reutiliza tokenizador ou
pesos prontos. Novo checkpoint separado dos pilotos anteriores.

Configuração fixada antes do teste: 1.800 etapas, 400 finais com loss somente na
resposta, AdamW lr base 0,0005, warmup 100 e decaimento cosseno, batch 4, janelas de
128 tokens, limite de contexto 256, clip 1,0, seed 25102027, CPU com duas threads,
orçamento por execução 600 segundos. A seleção usa loss ponderada por token das
respostas na validação, nunca o teste. A avaliação completa reinicia a maior parte
do contexto a cada bloco; não mede memória de documento longo.

Checkpoint de inferência e checkpoint de retomada são separados. last.pt contém
modelo, otimizador, RNG, configuração, fingerprints, histórico e etapa; retomada
recusa dados/config/tokenizador diferentes. As gravações usam arquivo temporário
e substituição. No limite de tempo, salva sem avaliar teste. Em interrupção, tenta
salvar; equivalência determinística de interrupções em qualquer ponto do otimizador
não foi demonstrada. Os testes cobrem RNG de batches e os contratos de máscara,
contagem de alvos e filtros, não todas as falhas possíveis do sistema.

Oito perguntas qualitativas foram definidas antes do treino para saudação,
explicação, instrução, esclarecimento, incerteza, referência ao histórico,
correção e comparação. Não se atribui sucesso por palavras-chave. Este conjunto
não é a avaliação histórica 0/8 nem a avaliação sintética anterior. Os textos e
critérios estão em data/language-pilot/open-evaluation.json.

## Resultado final

- 49.499 tokens BPE na partição de treino, incluindo prefixos de conversa repetidos.
- 870.091 alvos supervisionados processados nas 1.800 etapas.
- Selecionado checkpoint da etapa 400 pela validação; as 400 etapas finais de
  ajuste apenas nas respostas NÃO melhoraram a seleção.
- Validação nas respostas: loss inicial 6,968600 → melhor 5,376288.
- Teste final nas respostas: loss 5,568141, perplexidade 261,95, 4.441 alvos.
- Uma única avaliação final do teste; nenhum peso atualizado durante essa avaliação.
- Oito perguntas abertas: **0/8 atendem aos critérios**, na revisão semântica do
  Codex. Isso não equivale a avaliação independente humana e não é o teste histórico.
- Treino e avaliação em 109,99s, excluindo treino do BPE; pico de RAM amostrado do
  processo 470.593.536 bytes. Não é medição do Windows/GTX 1650.
- 108 testes passaram e 9 foram ignorados (CUDA e artefatos históricos locais).

O modelo produz trechos de português, mas mistura assuntos, inventa informações,
repete frases e gera palavras corrompidas. Para a saudação respondeu com sugestões
de nomes de canal; para o nome do cachorro respondeu sobre dentes. As gerações
completas e os motivos de reprovação foram preservados, sem filtrar apenas trechos
bonitos. Consulte run-002.json e semantic-review.json.

A loss caiu em relação ao modelo aleatório, mas as etapas posteriores aumentaram
o erro de validação enquanto memorizavam o treino. Mais etapas nesses mesmos dados
não demonstraram progresso conversacional. Não combinar porcentagens destes testes
com as estimativas editoriais históricas do dossiê.

## Executar e reproduzir

Na raiz desta branch, com Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-first-words-cpu.txt
.\.venv\Scripts\python.exe -m learning.language_pilot --output artifacts/language-pilot/run-002 --chat
```

O chat é somente experimental; não é a entrega de uma assistente confiável. Use
/limpar para reiniciar o contexto e /sair para encerrar. Não grava histórico, não
ativa voz ou ferramentas. Rejeita contexto longo em vez de descartar mensagens
silenciosamente. A instalação e execução foram verificadas em Linux; os comandos
PowerShell ainda precisam de validação no computador do proprietário.

Para repetir o treino, use outro diretório. Isso inicia pesos e BPE do zero e
repete a avaliação, portanto é reprodução, não um teste virgem para seleção futura:

```powershell
.\.venv\Scripts\python.exe -m learning.language_pilot --output artifacts/language-pilot/reproduction --steps 1800 --sft-steps 400 --seconds 600
```

Se o limite de tempo for atingido, o programa salva last.pt e NÃO avalia o teste.
O comando abaixo retoma somente uma execução inacabada com os mesmos parâmetros:

```powershell
.\.venv\Scripts\python.exe -m learning.language_pilot --output artifacts/language-pilot/reproduction --steps 1800 --sft-steps 400 --seconds 600 --resume
```

Dados derivados e licença estão no Git. Para verificar novamente a fonte bruta
pública, sem substituir o lote já preparado:

```powershell
.\.venv\Scripts\python.exe -m learning.download_oasst_pilot --cache D:/ElysiaSourceCache/oasst1
```

O download é limitado aos três arquivos imutáveis, com hashes esperados e limite de
tamanho. O preparador recusa substituir data/language-pilot já existente. Para
refazer integralmente a preparação, use uma cópia isolada da branch sem essa pasta;
não apague o lote de trabalho para isso. A fonte bruta não precisa ser publicada
novamente, pois a URL e o hash identificam a cópia pública original.

## Decisão de engenharia

**A meta de conversar como ChatGPT não foi atingida.** O modelo de 2,17 milhões de
parâmetros e 49 mil tokens de dados não oferece base para prometer essa equivalência.
O lote foi útil para validar proveniência, tokenizador, treino, retomada e avaliação,
e para evidenciar o gargalo dos dados, não para entregar competência geral.

Próximo marco: uma coleção pt-BR com milhões de tokens e diversas fontes, direitos
verificados, revisão por amostragem, deduplicação e splits por família de origem;
uma trilha de diálogos revisados distinta; e um teste NOVO de intenções abertas.
A escolha do tamanho do próximo modelo depende desse corpus e de um benchmark de
memória/tempo. Não aumentar parâmetros nem comprar computação automaticamente.
Qualidade de fronteira exigiria recursos e pesquisa muito além destes pilotos.

O painel do projeto permanece **não avaliado**, com variação N/A em todos os módulos;
as barras e comparações históricas estão em reports/first-words/README.md. Neural
Core tem infraestrutura validada; competência conversacional não foi comprovada.
Voice Core continua pausado e os módulos fora do Neural Core não foram alterados.

As três verificações do downloader passaram, incluindo rejeição de hash divergente
e de tamanho excessivo sem aceitar arquivos parciais. A CLI foi testada com /limpar
e /sair e preservou a saída incorreta, sem fallback para outro modelo.
