# ELYSIA-Seed v0.4 - Relatorio final consolidado

Status: Fase 6 concluida, congelada e parada. Nenhum treinamento, alteracao de pesos, aumento de arquitetura ou coleta adicional foi iniciado depois deste relatorio.

Base auditada: commit `22fdd0d` na branch `codex/elysia-seed-v0.4`.

## Escopo e conclusao curta

Esta versao e um experimento de pre-treinamento local muito pequeno, iniciado de pesos aleatorios e treinado somente sobre tres romances historicos de Machado de Assis. Ela nao e um assistente conversacional, nao demonstra compreensao, raciocinio avancado, programacao, controle de computador ou confiabilidade factual.

A Fase 6 executou uma unica avaliacao final do checkpoint congelado da etapa 1.000 sobre Quincas Borba. O registro integral, incluindo protocolo, hashes e recursos, esta em `reports/seed-v0.4-final-evaluation.json`. O executor se recusa a sobrescrever esse manifesto, para impedir uma segunda avaliacao acidental.

## Historico das fases

| Fase | Resultado | Limite aplicado |
| --- | --- | --- |
| 1 | A configuracao `SwiGLU + SDPA` sem RoPE e sem RMSNorm foi escolhida para investigar o corpus, depois de benchmarks sintéticos locais. | Os benchmarks nao foram interpretados como qualidade linguistica. |
| 2 | Foi proposta uma coleta juridicamente conservadora, separando direitos da obra, edicao e transcricao. | Nenhuma fonte foi baixada nesta fase. |
| 3 | Foram coletados e auditados somente Dom Casmurro, Memorias Posthumas de Braz Cubas e Quincas Borba, em TXT do Project Gutenberg. | Originais e copias limpas permaneceram locais; Wikisource e Tycho Brahe nao foram incorporados. |
| 4 | O piloto de 200 etapas confirmou que o pipeline treinava, salvava e gerava texto. | O teste Quincas Borba foi medido uma vez no piloto e nao serviu para selecao. Isso significa que ele ja nao era um teste globalmente inedito. |
| 5 | O experimento controlado de 1.000 etapas selecionou a etapa 1.000 pela loss fixa de Memorias Posthumas de Braz Cubas. | Quincas Borba nao foi tokenizado nem avaliado na Fase 5 e nao orientou checkpoint ou hiperparametro. |
| 6 | O melhor checkpoint foi auditado e avaliado uma unica vez, em modo de inferencia, sobre toda a particao Quincas Borba. | Pesos, otimizador, arquitetura e corpus permaneceram sem mudanca; nenhum novo dataset foi baixado. |

## Modelo congelado

O checkpoint usado foi `learning/checkpoints/elysia-seed-v0.4-machado-extended-best.pt`.

| Campo | Valor |
| --- | --- |
| SHA-256 do melhor checkpoint | `f8e2ec643cd963ebfd47c9c7b6d87a8a5b79af9c0fb7f8e1e75744106e1943d3` |
| Etapa | `1.000` |
| Papel | `best_validation` |
| Parametros | `3.490.136` |
| Configuracao | decoder-only Transformer, 4 blocos, embedding 256, 4 cabecas, feedforward SwiGLU 1.024, contexto 256, LayerNorm, posicoes absolutas, SDPA, dropout 0 |
| Fingerprint da arquitetura | `1ec4192799a32ee7a0320ccf71a9bfe1f3f708f2e5c9193faa294a3b1e776ae7` |
| Tokenizador | BPE byte-level, vocabulario 512 |
| Fingerprint do tokenizador | `d7b27519afcc8a19deb57691617e7a1478893bbf3d71768508a998ca48d887a8` |
| Fingerprint dos dados do checkpoint | `eb4d6655b08d35a51e91779ff72c15d8f904c6b1fd64a4321d3ed87ea484ca06` |
| Fingerprint do split | `7fca4ee72e780084b1a364cf80424e9d0d3a1cb2ad9cacc3c257c8002282e757` |

O ultimo checkpoint tambem esta na etapa 1.000, com SHA-256 `0585ed247ccc7d8259390e250393b27b43a429368424f9d6de71c6b02fbc15c1`. Seus 54 tensores de pesos sao identicos aos do melhor checkpoint. Os hashes de arquivo diferem porque os checkpoints carregam metadados de progresso e papel distintos, nao porque os pesos do modelo diferem.

## Dados, proveniencia e direitos

O manifesto local `data/corpus-v0.4/audit-manifest.json` tem SHA-256 `d55cbe99459951fd7c8a053970f8ebedd6b1744f5a05403c779de26e00278b37`. A limpeza removeu apenas cabecalhos e rodapes tecnicos do Gutenberg, normalizou Unicode NFC e preservou os originais sem alteracao. Foram encontrados zero duplicatas exatas, zero documentos invalidos e tres grupos distintos no teste de similaridade aproximada.

| Obra | Split | Pagina oficial | Limpo | Caracteres | Palavras | Tokens BPE | SHA-256 limpo |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| Dom Casmurro | treino | [Project Gutenberg 55752](https://www.gutenberg.org/ebooks/55752) | 389.167 B | 381.078 | 67.381 | 179.099 | `22119569360067b6eb907f227b18be52d3883561c05b9070012eaf047cf4ac59` |
| Memorias Posthumas de Braz Cubas | validacao | [Project Gutenberg 54829](https://www.gutenberg.org/ebooks/54829) | 374.427 B | 367.821 | 63.538 | 178.618 | `f91b052f708125757e73fdfcc90fc7b2dda9f76dd84b501ef1682d95c39bd9c0` |
| Quincas Borba | teste | [Project Gutenberg 55682](https://www.gutenberg.org/ebooks/55682) | 461.932 B | 453.507 | 78.553 | 220.490 | `0476447eba5a37435d26a9090d8f467e3292c3109975f29574d3c92e6492c974` |

Total limpo: 1.225.526 bytes, 1.202.406 caracteres, 209.472 palavras e 578.207 tokens BPE, contando os marcadores de documento. Machado de Assis morreu em 1908; a aprovacao do projeto registrou o dominio publico no Brasil. O Project Gutenberg declara cada eBook como dominio publico nos Estados Unidos, mas sua [politica de permissao](https://www.gutenberg.org/policy/permission.html) exige verificacao local independente e regula o uso da marca. A proveniencia, os avisos e a atribuicao foram mantidos no manifesto; esta nota nao substitui uma analise juridica para novo uso ou redistribuicao.

## Treinamento e validacao que selecionaram o checkpoint

Na Fase 5, somente Dom Casmurro alimentou atualizacoes de pesos. Foram processados 256.000 tokens de treino, equivalentes a 1,4294 passagens pelo token store de treino, em 1.000 etapas e 24,67 s na GTX 1650. A velocidade observada foi 10.377,1 tokens/s.

A selecao usou somente Memorias Posthumas de Braz Cubas: 256 janelas fixas de 256 tokens, com 65.536 alvos de proximo token por medicao. A loss fixa caiu de `6,2996` na etapa 0 para `4,2500` na etapa 1.000. Esse protocolo nao usou Quincas Borba e nao e diretamente comparavel ao protocolo de validacao do piloto da Fase 4.

## Avaliacao final de Quincas Borba

Esta foi a unica avaliacao final registrada para o checkpoint congelado. O manifesto registra `evaluation_count: 1`, carregamento de pesos em modo seguro, ausencia de otimizador e `weights_updated: false`.

O token store ja auditado de Quincas Borba foi reutilizado sem escrita: SHA-256 `889ee0e6484d1ea890e814d6636f95c604647c502f362ad00592e40b1cff2469`, com 220.490 tokens. A execucao ativou algoritmos deterministas do PyTorch e colocou o modelo em `eval()`.

### Tratamento do contexto

Foram avaliados todos os 220.489 alvos de proximo token, da posicao 1 ate a ultima posicao do token store. O protocolo possui 861 janelas completas de 256 alvos e uma janela final curta de 73 alvos. As faixas de alvos nao se sobrepoem. Cada janela posterior reutiliza apenas o token de fronteira anterior como contexto de entrada sem pontua-lo uma segunda vez; nenhum alvo e contado duas vezes. O modelo nao recebe contexto anterior alem dessa fronteira ao iniciar cada janela, portanto esta metrica mede previsao causal em blocos de no maximo 256 tokens, e nao memoria de documento longo.

| Metrica | Resultado |
| --- | ---: |
| Loss media ponderada por token | `4,19284883` |
| Perplexidade, `exp(loss)` | `66,21114692` |
| Bits por byte | `2,88726956` |
| Alvos avaliados | `220.489` |
| Tokens textuais para bits por byte | `220.488` |
| EOS excluido do calculo de bits por byte | `1` |
| Tempo de avaliacao | `1,8202 s` |
| RAM antes / pico amostrado | `778,28 MiB` / `1.027,84 MiB` |
| VRAM alocada antes / pico PyTorch | `13,31 MiB` / `57,17 MiB` |
| VRAM reservada antes / pico PyTorch | `30,00 MiB` / `72,00 MiB` |

Loss e perplexidade incluem o alvo EOS final. Bits por byte usa a soma de NLL somente dos tokens textuais, dividida pelos 461.932 bytes UTF-8 do texto limpo e por `ln(2)`. A diferenca e intencional e esta documentada no manifesto.

Quincas Borba ja foi avaliado no piloto da Fase 4, com outro checkpoint e outro protocolo, onde a loss reportada foi `5,2785`. Por isso, este resultado final da Fase 6 nao deve ser apresentado como um teste globalmente inedito nem usado para escolher configuracoes futuras. Ele descreve somente o checkpoint congelado da Fase 5 sob o protocolo final desta fase.

## Amostras reais de geracao

As amostras abaixo ja foram geradas pelo mesmo checkpoint congelado na Fase 5, com temperatura `0,8`, top-k `20`, seed `12026` e 80 tokens novos. Foram preservadas para evitar uma nova rodada de geracao apos o teste final.

Prompt: `Capítulo primeiro.`

```text
Capítulo primeiro. Pria a da de me
beição co tinver nia,
fuas cados só sa.

Tugos me, mas videisóde sento achavr S. Tendo tão bem lejo, e os e fazia de outros e pu
```

Prompt: `A vida é`

```text
A vida é um que tanto do posso, melhor certim, não acabincipensando passim mas a melhor para doz o vez a do que me lodada a a fel nuntallingorranhio nos de s, mas ficaça. Acl
```

As saidas contem mais fragmentos reconheciveis de portugues que a inicializacao aleatoria, mas tambem palavras inventadas, repeticao e baixa continuidade semantica. Elas nao demonstram compreensao, capacidade conversacional confiavel ou conhecimento factual.

## Limitacoes demonstradas e pendencias tecnicas

- O corpus tem tres livros, um unico autor, variante historica e pouco mais de 1,2 MB limpos. Ele nao representa portugues brasileiro contemporaneo, dialogo, codigo ou instrucao tecnica moderna.
- O teste deixou de ser uma medida inteiramente virgem porque foi medido no piloto da Fase 4. Nao deve ser reutilizado para ajuste de arquitetura, taxa de aprendizado, numero de etapas ou tokenizador.
- A avaliacao por blocos reinicia a maior parte do contexto a cada 256 alvos. Ela nao mede capacidade de reter informacao em documento longo.
- Ha somente uma semente e uma rodada longa; nao ha intervalo de confianca, repeticao independente nem comparacao justa com outras arquiteturas sobre um corpus suficiente.
- A geracao ainda apresenta palavras corrompidas, repeticao e falta de coerencia. O modelo nao e adequado para conversacao, programacao, automacao de PC, decisao ou respostas factuais.
- A situacao juridica foi documentada para esta coleta limitada; qualquer publicacao de corpus derivado, novo uso geográfico ou redistribuicao exige nova verificacao das condicoes aplicaveis.
- O BPE de Machado e especifico deste experimento e nao deve ser carregado para o proximo corpus apenas por conveniencia.

## Proposta de corpus brasileiro contemporaneo

Nenhuma fonte desta secao foi baixada. Cada candidato exigira uma nova aprovacao por lote e uma ficha de proveniencia por documento antes de qualquer coleta. A politica proposta veda pesos pre-treinados externos, texto destilado de modelos comerciais e contribuicoes sem declaracao de autoria/origem.

### 1. Textos explicativos autorais encomendados pelo projeto

- URL oficial: ainda inexistente, pois o conteudo deve ser criado para o projeto; antes da coleta, publicar uma pagina de politica e um modelo de cessao no repositorio ou dominio do projeto.
- Responsavel: cada autor identificado e o responsavel editorial do projeto.
- Licenca exata proposta: [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/deed.pt-br) como preferencia; [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt_BR) somente se a atribuicao e o registro de mudancas forem mantidos.
- Permissoes e obrigacoes: contrato escrito deve mencionar treinamento, armazenamento, avaliacao, versao derivada e distribuicao pretendida; autoria, versao e revogacao nao retroativa precisam constar no manifesto.
- Tamanho planejado: 2 a 5 milhoes de palavras, aproximadamente 3 a 8 milhoes de tokens BPE, antes de filtragem. E uma meta de coleta, nao uma medicao existente.
- Variante, qualidade e uso: portugues brasileiro contemporaneo; artigos educacionais, explicacoes, tutoriais e perguntas frequentes escritos sob pauta editorial.
- Risco de dados pessoais: baixo se a pauta proibir historias identificaveis; revisao manual e detector de PII continuam obrigatorios.
- Risco de duplicacao ou texto sintetico: medio sem controle; exigir declaracao do autor de que o texto e original, nao copiado e nao gerado/destilado de modelo.

### 2. Dialogos originais autorizados

- URL oficial: ainda inexistente; cada lote devera receber URL de manifesto proprio antes de ser aceito.
- Responsavel: roteiristas ou participantes que cedam os dialogos, com responsavel de privacidade nomeado.
- Licenca exata proposta: CC0 1.0 ou CC BY 4.0, acompanhada de termo especifico de consentimento e de retirada de identificadores.
- Permissoes e obrigacoes: o termo deve proibir a inclusao de conversas privadas, dados de terceiros, segredos comerciais e atendimento real; manter atribuicao se CC BY for escolhida.
- Tamanho planejado: 0,5 a 2 milhoes de palavras, aproximadamente 0,8 a 3 milhoes de tokens BPE.
- Variante, qualidade e uso: portugues brasileiro contemporaneo, fala natural escrita e cenarios de assistencia, sem fingir que sao conversas de pessoas reais.
- Risco de dados pessoais: alto se os dialogos vierem de conversas existentes; por isso a proposta aceita apenas material roteirizado ou explicitamente cedido e revisado.
- Risco de duplicacao ou texto sintetico: medio; usar hashes, SimHash por dialogo e declaracao de que nenhum trecho veio de outro dataset ou modelo generativo.

### 3. eMAG - Modelo de Acessibilidade em Governo Eletronico

- URL oficial: [eMAG 3.1](https://emag.governoeletronico.gov.br/).
- Responsavel: Departamento de Governo Eletronico do governo federal, conforme a pagina da obra.
- Licenca exata: CC BY 4.0, declarada na propria pagina; conferir a copia e o aviso antes da coleta.
- Permissoes e obrigacoes: copiar, redistribuir e adaptar, inclusive comercialmente, com credito, link da licenca e indicacao de mudancas, conforme [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt_BR).
- Tamanho estimado: 92 paginas; planejamento inicial de aproximadamente 0,05 a 0,12 milhao de tokens BPE apos extracao de texto. Medir somente apos aprovacao.
- Variante, qualidade e uso: portugues brasileiro tecnico e educacional. E util para acessibilidade e documentacao, mas de 2014 e pequeno demais para representar linguagem contemporanea sozinho.
- Risco de dados pessoais: baixo no texto normativo; verificar exemplos, creditos e anexos antes de extrair.
- Risco de duplicacao ou texto sintetico: medio, pois o material pode reaparecer em outros portais; deduplicar por hash e excluir cursos do eMAG com licencas diferentes.

### 4. Artigos SciELO Brasil com licenca CC BY por item

- URL oficial: [criterios SciELO Brasil](https://www.scielo.br/media/files/Criterios_SciELO_Brasil_.pdf) e [colecao SciELO Brasil](https://www.scielo.br/).
- Responsavel: autores e periodicos de cada artigo; o SciELO informa sua politica, mas nao substitui a verificacao do item individual.
- Licenca exata: aceitar apenas itens cujo PDF/XML declare CC BY 4.0. A politica descreve CC BY como padrao desde 2015, mas registra excecoes historicas CC BY-NC e CC BY-NC-ND, que devem ser excluidas.
- Permissoes e obrigacoes: para CC BY, atribuir autores/publicacao, linkar a licenca e indicar mudancas. Preservar DOI, metadados de autoria e licenca no manifesto.
- Tamanho estimado: primeiro lote limitado a 1.000 artigos selecionados, cerca de 5 a 10 milhoes de palavras ou 7 a 15 milhoes de tokens BPE. E uma estimativa de planejamento, nao uma afirmacao sobre a colecao completa.
- Variante, qualidade e uso: majoritariamente portugues brasileiro formal, explicativo e informativo; filtrar idioma e area para evitar concentracao excessiva em uma disciplina.
- Risco de dados pessoais: medio; excluir relatos de caso, anexos, entrevistas e artigos que exponham identificadores ou dados sensiveis.
- Risco de duplicacao ou texto sintetico: alto para preprints, versoes aceitas, referencias e textos de revistas repetidos; deduplicar DOI, titulo, hash e similaridade, e excluir material declarado como gerado por IA sem autoria clara.

### 5. Documentacao do Padrao Digital de Governo

- URL oficial: [legislacao e licencas do Padrao Digital de Governo](https://www.gov.br/ds/downloads/legislacao).
- Responsavel: Secretaria de Governo Digital e orgaos responsaveis pelo Padrao Digital de Governo.
- Licenca exata: a pagina informa CC0 1.0 Universal e MIT. Cada artefato deve ser classificado pela licenca que consta nele; nao presumir que qualquer pagina `gov.br` tenha a mesma permissao.
- Permissoes e obrigacoes: CC0 busca dispensar direitos na extensao permitida; MIT exige preservar aviso de copyright e permissao em software. Manter URL, versao e aviso no manifesto mesmo quando a licenca nao exigir atribuicao.
- Tamanho estimado: lote inicial de documentacao textual de 0,1 a 0,5 milhao de tokens BPE, excluindo arquivos binarios, exemplos copiados de terceiros e blocos de codigo duplicados.
- Variante, qualidade e uso: portugues brasileiro contemporaneo tecnico, institucional e de produto digital; complementar para instrucao e documentacao.
- Risco de dados pessoais: baixo, mas revisar formulários, exemplos e capturas de tela.
- Risco de duplicacao ou texto sintetico: medio; versoes de componentes e snippets podem se repetir. Preservar historico de versao e deduplicar por bloco/documento.

### 6. Recursos educacionais individuais do eduCAPES com CC BY explicita

- URL oficial: [Portal eduCAPES](https://educapes.capes.gov.br/).
- Responsavel: autor e instituicao/publisher indicados em cada registro, nao o portal de forma generica.
- Licenca exata: aceitar somente registros cujo campo de direitos declare explicitamente CC BY 4.0 ou CC0. A disponibilidade em acesso aberto, sem essa declaracao, nao basta.
- Permissoes e obrigacoes: para CC BY, atribuir autor e fonte, incluir a licenca e indicar modificacoes. Preservar registro, identificador persistente, versao e termo de direitos no manifesto.
- Tamanho estimado: apos triagem, lote inicial de 500 a 1.000 recursos textuais, com meta de 2 a 8 milhoes de tokens BPE. Valores de planejamento, sujeitos a revisao de formato e licenca.
- Variante, qualidade e uso: portugues brasileiro educacional em disciplinas diversas; a qualidade depende de avaliacao editorial e da remocao de referencias bibliograficas duplicadas.
- Risco de dados pessoais: medio a alto em trabalhos que tragam entrevistas, estudos de caso ou apendices. Excluir antes de extracao.
- Risco de duplicacao ou texto sintetico: medio; versoes depositadas e artigos de origem podem coincidir com SciELO ou outros repositorios. Deduplicar por DOI, handle, titulo, hash e similaridade.

### Fontes excluidas nesta proposta

- Textos de sites que se declaram CC BY-ND, porque a clausula SemDerivacoes nao e compativel com a limpeza e transformacao previstas para corpus.
- Itens SciELO, eduCAPES ou outros repositorios sem licenca individual inequivoca, mesmo que estejam disponiveis publicamente.
- Wikipedia/Wikimedia em portugues, por ora. A [licenca CC BY-SA 4.0](https://foundation.wikimedia.org/wiki/Terms_of_Use) permite reuso com atribuicao e compartilhamento pela mesma licenca, mas exige uma politica de atribuição e uma analise juridica especifica sobre distribuicao de corpus e derivados; nao sera coletada sem aprovacao propria.
- Qualquer texto de modelo, conjunto destilado, raspagem de redes sociais, conversas privadas ou dados sem declaracao de origem e permissao.

## Split e tokenizador para a proxima versao

Antes de treinar um novo tokenizador, a coleta aprovada deve produzir um inventario por documento contendo fonte, autor/responsavel, genero, data, licenca, hash, versao, grupo de derivacao e resultado de revisao de PII/sintetico. Capitulo, trecho ou paragrafos de uma mesma obra nao podem atravessar splits.

O split proposto e 70% treino, 15% validacao e 15% teste, por grupos completos de autoria, obra, serie e fonte derivada. O teste deve conter autores, obras e grupos de duplicacao inteiramente ausentes de treino e validacao, mas ainda representar generos planejados. A alocacao final so deve ser congelada depois da auditoria do inventario, antes de qualquer BPE ou treinamento. O conjunto de teste novo ficara isolado ate a avaliacao final da proxima versao.

O BPE de Machado nao sera reaproveitado. Um novo BPE deve ser treinado apenas nos textos da nova particao de treino, com vocabulários candidatos medidos em compressao, cobertura, bytes por token e comportamento em portugues brasileiro. Validacao e teste nao devem influenciar pares BPE, limpeza ou escolha de vocabulario.

## Estimativa computacional para planejamento futuro

Como referencia limitada, a Fase 5 observou 10.377,1 tokens/s na GTX 1650 para esta arquitetura, batch 1 e sequencias de 256 tokens. Mantendo de forma puramente linear o mesmo regime, uma passagem por 10 milhoes de tokens levaria cerca de 16 minutos; 100 milhoes, 2,68 horas; 1 bilhao, 26,77 horas. Sao limites inferiores de agenda, nao garantias: I/O, checkpoints, validacao, novo BPE, falhas, memoria e qualquer mudanca de modelo podem alterar muito o custo. Estes numeros nao autorizam treinamento futuro.

## Encerramento

Os checkpoints completos, corpus original, copias limpas, tokenizador e token stores permanecem locais e ignorados pelo Git quando apropriado. O repositorio recebe apenas codigo de avaliacao, testes, manifesto de avaliacao e relatorios. A proxima versao nao foi iniciada. Este e o ponto de parada obrigatorio, aguardando aprovacao explicita.
