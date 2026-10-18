# ELYSIA-Seed v0.5 - revisao final de qualidade e plano de corpus

Data de encerramento: 2026-10-17

Branch: `codex/elysia-seed-v0.5`

Baseline solicitado: `69ebde17adf248be48d08422efa3624d6bf5ae63`

Fase: 2E - revisao final dos artigos SciELO e planejamento do corpus

Status: encerrada. Nenhuma coleta nova, tokenizacao, split ou treinamento foi iniciado.

## Escopo e preservacao

Esta fase revisou somente os dois HTMLs SciELO ja coletados na Fase 2D:

1. `scielo-rbeped-affectivity-2024`
2. `scielo-rap-redistribution-2024`

Os HTMLs originais continuam locais, somente leitura e ignorados pelo Git. Os derivados completos tambem continuam locais. O repositorio versiona apenas os manifestos, regras de auditoria, testes e este relatorio.

| Registro preservado | SHA-256 |
| --- | --- |
| Fase 2B | `1fe003668cc80033df6da7c89b8ce09710592faac98ea76bb256d781ca91d160` |
| Fase 2C | `9d217f293b2169b6e90b84c53586c593f230270cdd7b5491fb61f82b96538be0` |
| Fase 2D congelada | `199896aeb63a3d2d603458ca339b12d39008c45dc07e31c03e6b35e9c971a855` |
| Manifesto ativo da Fase 2E | `f8568086b4b6454dee15edd44c729215a33f504c4ce588224ee1fb60ff7d6185` |

As fases historicas permanecem separadas em `data/corpus-v0.5/collection-audit.phase-2b.json`, `data/corpus-v0.5/collection-audit.phase-2c.json` e `data/corpus-v0.5/collection-audit.phase-2d.json`.

## Resultado individual: afetividade

Fonte oficial: [Revista Brasileira de Estudos Pedagogicos - SciELO](https://www.scielo.br/j/rbeped/a/Yvgc3v3QyLL3nKYNSQvfkqy/?format=html&lang=pt)

| Campo | Valor auditado |
| --- | --- |
| Titulo | A ideia de afetividade na filosofia e na educacao |
| Autores | Agostinho Morosini; Maria Judith Sucupira da Costa Lins |
| DOI | `10.24109/2176-6681.rbep.105.5844` |
| Licenca declarada no HTML | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| SHA-256 do HTML original | `7b424baead4364f5332176e7cf333e7fb26413a99df9ab881560a2ed0f229110` |
| SHA-256 do texto limpo | `5ba727d08946d4da28d33069d438b1412c228e935898d6dc1c07878e5e63b6f0` |
| Mudanca no texto limpo nesta fase | Nenhuma; o derivado anterior foi preservado |
| Estado final | `audited` |

Os 12 blocos removidos foram examinados individualmente. Todos sao citacoes diretas de terceiros; nenhum continha argumento original que justificasse restauracao. A analise autoral imediatamente anterior e posterior a cada bloco permaneceu no texto limpo.

| Bloco | Atribuicao da citacao | Decisao |
| ---: | --- | --- |
| 1 | Platao, 1980 | Manter redacao |
| 2 | Aristoteles, 2014 | Manter redacao |
| 3 | Maritain, 1959 | Manter redacao |
| 4 | Macedo, 1980 | Manter redacao |
| 5 | Rates e Sucupira Lins, 2021 | Manter redacao |
| 6 | Von Hildebrand, 2007 | Manter redacao |
| 7 | Maritain, 2006 | Manter redacao |
| 8 | Mounier, 2004 | Manter redacao |
| 9 | Piaget, 1973 | Manter redacao |
| 10 | Von Hildebrand, 2007 | Manter redacao |
| 11 | Sucupira Lins, 2022b | Manter redacao |
| 12 | Von Hildebrand, 2020 | Manter redacao |

O HTML, os derivados e as amostras de inicio, meio e fim estao em UTF-8/NFC; nao ha caracteres de substituicao, controles invalidos, CPF, telefone ou email no texto limpo. O documento nao foi promovido porque ainda ha diversas citacoes diretas embutidas em paragrafos autorais. A revisao contextual desses trechos precisa ser feita antes de declarar o material apropriado para inclusao futura.

## Resultado individual: redistribuicao

Fonte oficial: [Revista de Administracao Publica - SciELO](https://www.scielo.br/j/rap/a/QpnmPNnQ8WmK8ckGFGgBv7w/?format=html&lang=pt)

| Campo | Valor auditado |
| --- | --- |
| Titulo | Analise do efeito redistributivo das transferencias intergovernamentais sobre as receitas municipais no semiarido brasileiro |
| Autores | Luis Alberto da Costa; Napie Galve Araujo Silva; Vilmar Antonio Goncalves Tondolo; Lauro Nogueira |
| DOI | `10.1590/0034-761220240010` |
| Licenca declarada no HTML | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| SHA-256 do HTML original | `6228a271ecb046dc02e19395ac60414a3aad208484fc0141cd404a550fd19298` |
| Estado final | `approved_for_future_inclusion` |

A causa das zero linhas de tabela da Fase 2D foi identificada: as tabelas estao em quatro modais `ModalTablet*` no mesmo HTML oficial, fora de `article#articleText`. A extracao anterior leu o artigo, mas nao esses modais. Nao havia ausencia de tabelas no HTML nem necessidade de reconstruir valores.

| Derivado | Fase 2D | Fase 2E | Diferenca |
| --- | ---: | ---: | ---: |
| Texto extraido | 70.296 bytes; `5711dede700fe35297db0648507df42eb2fbc6a55621e985b8869aaadaccb568` | 73.883 bytes; `f860ad5dc73e8d3d632756542b3c3c51fc72a1194bf4ff17b93250157ddd31c2` | +3.587 bytes |
| Texto limpo | 59.507 bytes, 57.456 caracteres, 8.449 palavras; `21b612fb4683447cc1876b52ddc0fc5dd710553c7f9250eb4b9a459d5bf2c234` | 62.981 bytes, 60.881 caracteres, 8.996 palavras; `726897e129f433d01e64f60da5e5a9e45454c43a63b05d47a9aa8e43a5ab374e` | +3.474 bytes; +3.425 caracteres; +547 palavras |

Foram preservadas 4 tabelas, 35 linhas e 136 celulas numericas textuais, na ordem do HTML. `colspan` e `rowspan` aparecem explicitamente quando existem, sem completar lacunas ou inferir valores. Uma citacao direta substantiva de terceiro foi redigida; marcadores curtos de notacao tecnica foram mantidos.

Os nove elementos de imagem e os graficos disponiveis somente como imagem nao foram baixados, lidos por OCR ou reconstruidos. Essa e uma limitacao registrada, nao uma alegacao de completude visual. O texto limpo revisado tambem passou em UTF-8, NFC, caracteres invalidos e varredura de CPF, email e telefone.

## Qualidade, direitos e repeticao

Os dois artigos foram conferidos contra os HTMLs locais quanto a titulo, DOI, autoria e licenca individual CC BY 4.0. A atribuicao futura precisa creditar autores, publicacao inicial, URL, licenca e alteracoes feitas nos derivados.

A deduplicacao continua apenas informativa: compara DOI, titulo, primeiro autor, instituicao, hashes e Jaccard de conjuntos de palavras para todos os seis pares do lote atual. Nenhum bloco foi removido automaticamente por similaridade.

| Documento | Estado | Caracteres limpos | Palavras limpas | Estimativa heuristica de unidades sublexicais |
| --- | --- | ---: | ---: | ---: |
| eMAG 3.1 | `approved_for_future_inclusion` | 135.493 | 19.693 | 24.617 a 30.525 |
| ConCI 2021 | `approved_for_future_inclusion` | 34.161 | 5.207 | 6.509 a 8.071 |
| Afetividade 2024 | `audited` | 38.377 | 5.883 | 7.354 a 9.119 |
| Redistribuicao 2024 | `approved_for_future_inclusion` | 60.881 | 8.996 | 11.245 a 13.944 |
| **Total atual** | - | **268.912** | **39.779** | **49.725 a 61.659** |

As estimativas nao sao contagem de um tokenizador real. Nenhum BPE foi treinado, executado ou escolhido nesta fase.

## Proposta de diversificacao futura

Esta proposta nao autoriza coleta. Toda fonte exige uma nova aprovacao explicita, uma auditoria de versao, licenca, terceiros, PII, duplicacao e proveniencia antes de qualquer download.

| Familia candidata | Genero e variedade | Base de direitos | Obrigacoes e riscos |
| --- | --- | --- | --- |
| Textos autorais da E.L.Y.S.I.A. | Dialogos roteirizados, atendimento, instrucoes, explicacoes cotidianas | Termo individual; preferencia por CC0 1.0 | Declaracao de originalidade, autoria documentada, revisao de PII e proibicao de texto copiado ou sintetico nao declarado |
| [Guia do usuario do Omeka - IBICT](https://repositorio.enap.gov.br/bitstream/1/3162/1/Guia%20do%20usu%C3%A1rio%20do%20Omeka%20-%20Ebook.pdf) | Documentacao tecnica em portugues brasileiro | CC BY 4.0 declarada na obra | Credito, licenca e alteracoes; revisar PDF, screenshots, referencias e componentes de terceiros |
| SciELO por artigo | Prosa informativa e cientifica de autores e periodicos diversos | Licenca confirmada individualmente no item | Nunca inferir licenca do portal; retirar citacoes, figuras, anexos e versoes quase duplicadas conforme auditoria |
| [eduCAPES: Ciencia aberta no CNPq](https://educapes.capes.gov.br/handle/capes/1023510?mode=full) e [Licencas na Ciencia da Informacao](https://educapes.capes.gov.br/handle/capes/1140501?mode=full) | Educacional e institucional | Registros apontam CC BY 4.0 | Confirmar autores, arquivo canonico, cadeia de versoes e licenca no arquivo antes de coletar |
| [Atos oficiais brasileiros](https://www.planalto.gov.br/ccivil_03/leis/l9610.htm) | Instrucoes e prosa institucional | Lei 9.610, art. 8, IV: textos de atos oficiais nao sao objeto de protecao autoral | Congelar versao e data; tratar linguagem muito formal, mudancas legislativas e temas politicamente sensiveis |

Materiais com CC BY-NC, CC BY-NC-SA, CC BY-ND, licenca desconhecida ou apenas alegada pelo portal continuam excluidos. Por exemplo, registros da ENAP com restricoes NC/SA nao devem ser incorporados por equivalencia a CC BY.

O futuro inventario deve receber um `group_id` que una documento, autor, instituicao, serie, DOI/handle, versoes e quase-duplicatas. Um grupo inteiro vai para uma unica particao futura. O tokenizador devera ser treinado somente nos novos dados de treino aprovados depois que esse inventario e suas particoes estiverem congelados; teste final permanece isolado ate a avaliacao final do modelo.

## Criterios antes de qualquer treinamento

1. Aprovar uma lista fechada de fontes e arquivos, um a um.
2. Registrar hash, URL, data, versao, autor, licenca, atribuicao, PII e grupos de derivacao.
3. Verificar diversidade de autores, instituicoes, temas, epocas, generos e registro linguistico; volume maior nao basta.
4. Separar treino, validacao e teste por grupo antes de qualquer BPE.
5. Treinar um novo tokenizador somente nos novos dados de treino aprovados.
6. Executar benchmark de RAM/VRAM e documentar o experimento antes de modificar pesos.

## Validacao e encerramento

- `34 passed` nos testes de auditoria v0.5 relevantes, incluindo a nova Fase 2E.
- A suite completa `pytest -q` foi tentada, mas 10 modulos neurais nao foram coletados porque o unico interpretador Python local disponivel e o do Blender e ele nao possui PyTorch. Nenhum teste neural foi executado, nenhum pacote de ML foi instalado no repositorio e nenhum peso foi carregado.
- A CI configurada em `.github/workflows/tests.yml` usa Python 3.12 e executa `python -m pytest -q` sem GPU.
- Nenhuma pasta neural, checkpoint, peso, tokenizador, split ou interface desktop foi alterado.

Ponto de parada atingido. A proxima coleta, tokenizacao ou treinamento requer aprovacao explicita.
