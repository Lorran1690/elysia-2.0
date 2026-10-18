# ELYSIA-Seed v0.5 - Fase 2F: consolidacao da qualidade textual

Data: 2026-10-17

Branch: `codex/elysia-seed-v0.5`

Commit-base auditado: `5f727e0fe71069c7fdc4b615b9f0b463d051742d`

Status: encerrada localmente; aguarda aprovacao explicita antes de qualquer coleta, tokenizacao, split ou treinamento.

## Escopo e salvaguardas

Esta fase trabalhou apenas sobre os quatro documentos ja coletados localmente. Nenhum documento adicional foi baixado; nao houve uso de Ollama, APIs comerciais, pesos externos, BPE, tokenizacao, splits definitivos ou treinamento. A interface desktop e os artefatos da v0.4 nao foram modificados.

O manifesto anterior foi congelado em `data/corpus-v0.5/collection-audit.phase-2e.json` com SHA-256 `f8568086b4b6454dee15edd44c729215a33f504c4ce588224ee1fb60ff7d6185`. Os manifestos das Fases 2B, 2C e 2D continuam referenciados de forma imutavel pelo novo manifesto atual.

## Proveniencia e estado dos quatro documentos

| Documento | Estado apos 2F | SHA-256 do original | SHA-256 do texto limpo atual |
| --- | --- | --- | --- |
| eMAG 3.1 | `approved_for_future_inclusion` | `200884cddfa8a769473899f2db6cd34cc819a6573439f9409eec7806ea368d0f` | `a050365d151328d18d7a8ccbb5fe39aaaacbafe4ef24212c4d9d47ea4bb36dbc` |
| ConCI 2021 | `approved_for_future_inclusion` | `9b2fcbf03e68c371317da99a589f283a981c45171d7553529eb19303f83a82f4` | `5cd116862e1012ea6e0380ba8aec92c2c16e32873e5062aacf05ce36fec21f6e` |
| Afetividade/RBEP 2024 | `approved_for_future_inclusion` | `7b424baead4364f5332176e7cf333e7fb26413a99df9ab881560a2ed0f229110` | `267c4b3e5493111dc4abe984d2ef0fdca461f9c8ecdd32fc4f288a23e9e2c818` |
| Redistribuicao/RAP 2024 | `approved_for_future_inclusion` | `6228a271ecb046dc02e19395ac60414a3aad208484fc0141cd404a550fd19298` | `9961f6117a6306892667d0f2a86c26530dee89f1f1a40adbec8d101cd594a9cf` |

Os HTMLs originais permanecem locais, somente leitura e fora do Git. Os dois artigos SciELO mantem evidencia individual de CC BY 4.0 no HTML original e exigem credito aos autores, a publicacao, a URL da fonte, a licenca e as alteracoes feitas nos derivados.

## Afetividade/RBEP

A revisao usou somente o HTML original preservado. Foram analisadas individualmente 31 marcacoes de aspas inseridas em 23 paragrafos autorais:

- 28 foram classificadas como citacoes diretas de terceiros e substituidas pontualmente por `[citacao direta de terceiro removida]`.
- 2 foram classificadas como expressoes tecnicas e mantidas.
- 1 foi classificada como simbolo ortografico e mantida.
- Os 12 blocos de citacao direta ja redigidos na Fase 2E foram preservados.
- Citacoes sem trecho delimitado por aspas foram tratadas como parafrase ou analise autoral; nenhum texto ao redor das remocoes foi resumido ou reescrito.

O derivado novo e local e se chama `scielo-rbeped-affectivity-2024.phase-2f.clean.txt`. A promocao para `approved_for_future_inclusion` significa apenas que passou esta auditoria limitada; nao autoriza treinamento nem elimina a necessidade de atribuicao e nova verificacao caso o corpus seja publicado.

## Redistribuicao/RAP

As quatro tabelas textuais do HTML oficial foram conferidas: 35 linhas e 136 celulas numericas foram mantidas sem reconstruir valores. A tabela textual foi colocada imediatamente apos sua mencao original quando a associacao era objetiva:

| Tabela modal | Resultado |
| --- | --- |
| `ModalTablet1` / Tabela 1 | Inserida apos a mencao explicita a Tabela 1. |
| `ModalTablet2` / Tabela 2 | Inserida apos a mencao explicita a Tabela 2. |
| `ModalTablet3` / Tabela 3 | Inserida apos a mencao explicita a Tabela 3. |
| `ModalTablet4` / Tabela 4 | Mantida em apendice proprio: o corpo menciona `Tabela 6`, enquanto o HTML modal a chama de Tabela 4. A associacao nao foi forcada. |

O novo texto extraido e o novo texto limpo ficam somente no armazenamento local, com o sufixo `.phase-2f`. A citacao direta substantiva ja identificada permanece redigida. Graficos, imagens, PDFs, XMLs e outros recursos nao foram baixados nem reconstruidos.

## Qualidade consolidada

| Medida | Resultado |
| --- | --- |
| Bytes limpos | 275.620 |
| Caracteres limpos | 265.602 |
| Palavras | 39.231 |
| Estimativa heuristica de tokens, sem tokenizador | 49.041 a 60.810 |
| UTF-8, NFC, caracteres de substituicao e controles invalidos | Validados; nenhum problema no texto limpo. |
| E-mails, CPFs e telefones no texto limpo | Zero correspondencias nos quatro documentos. |
| Duplicacao | Relatorio informativo dos seis pares; sem remocao automatica. |

O volume continua muito pequeno e enviesado para material institucional e academico. Ele nao sustenta alegacoes de competencia conversacional, generalizacao ampla ou treinamento linguistico relevante.

## Proposta de expansao, sem coleta

O proximo corpus deve combinar dialogos originais autorizados, textos explicativos, documentacao tecnica, material educacional e artigos informativos. A meta de planejamento e ao menos 5 milhoes de tokens para experimentos limitados, com 20 milhoes como referencia antes de discutir cobertura linguistica mais ampla. Isso nao e uma alegacao de sufiencia para um modelo geral.

| Familia candidata | Genero e estimativa | Licenca ou condicao | Riscos e condicao antes de coletar |
| --- | --- | --- | --- |
| Dialogos originais da ELYSIA | Conversacional; 600 mil a 1,5 milhao de tokens | CC0 1.0 preferida ou CC BY 4.0 com autorizacao assinada | Exigir consentimento, remocao de dados pessoais, autoria humana e diversidade de participantes. |
| Textos explicativos e de suporte originais | Instrucional; 800 mil a 2 milhoes | CC0 1.0 ou CC BY 4.0 com protocolo autoral | Auditar duplicacao de templates, conteudo sintetico e cobertura tematica. |
| Guia do usuario do Omeka, IBICT/ENAP | Documentacao tecnica; 35 mil a 70 mil | CC BY 4.0 declarada no item oficial | Avaliar texto extraido, referencias e elementos visuais antes de qualquer download. [Fonte oficial](https://repositorio.enap.gov.br/bitstream/1/3162/1/Guia%20do%20usu%C3%A1rio%20do%20Omeka%20-%20Ebook.pdf) |
| Artigos da RAC via SciELO | Informativo/academico; 1,5 a 4,5 milhoes | CC BY 4.0 declarada pelo periodico; confirmar item a item | Remover referencias e citacoes de terceiros, verificar figuras e diversidade de autores. [Politica oficial](https://www.scielo.br/journal/rac/about/?ilang=pt_BR) |
| Artigos de Em Aberto/INEP | Educacional e de politicas; 500 mil a 1,8 milhao | Declaracao de reutilizacao CC BY 4.0; confirmar representacao canonica de cada item | Risco de excecao por artigo, PDF, citacoes e vies academico. [Pagina oficial](https://emaberto.inep.gov.br/ojs3/index.php/emaberto/about/submissions) |
| Documentacao OGC-API do SGB | Tecnico; 80 mil a 300 mil | CC BY 4.0 declarada pelo servico | Delimitar escopo de endpoints e evitar repeticao gerada por esquema. [Servico oficial](https://geoservicos.sgb.gov.br/ogcapi?f=html) |

Nenhuma dessas familias esta aprovada para coleta nesta fase. Antes de qualquer download, cada arquivo devera receber auditoria de URL canonica, licenca no item, atribuicao, terceiros, privacidade, formato, versao e risco de duplicacao. Em uma fase futura, os splits devem isolar integralmente documento, autor, origem e grupo de derivacao; o teste final deve ficar intocado ate uma unica avaliacao final.

## Validacao executada

- Reconstrucao deterministica do manifesto da Fase 2F a partir dos HTMLs locais e comparacao exata com o manifesto gravado.
- Verificacao de hashes, proveniencia, somente leitura dos originais, UTF-8/NFC, dados pessoais e deduplicacao.
- Testes de regressao adicionados para a classificacao de todas as 31 marcacoes inline, redacao obrigatoria das 28 citacoes diretas e nao associacao forcada da quarta tabela.
- Compilacao sintatica dos novos modulos Python concluida.

O ambiente local nao possui o interpretador Python/pytest do projeto; a verificacao integrada equivalente foi executada com o interpretador local disponivel. A suite completa deve ser confirmada pela CI apos o commit.

## Limites e ponto de parada

Esta fase nao criou corpus de treinamento, tokenizador, BPE, split, checkpoint ou pesos. A aprovacao atual e limitada a `approved_for_future_inclusion`; ela nao permite iniciar treinamento. A proxima acao exige aprovacao explicita para uma coleta limitada e nova auditoria por documento.
