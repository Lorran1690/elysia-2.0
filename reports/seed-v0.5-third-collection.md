# ELYSIA-Seed v0.5 - terceira coleta controlada

Data de encerramento: 2026-10-17
Fase: 2D - consolidacao ConCI e expansao controlada do corpus
Resultado: concluida localmente; parada obrigatoria mantida.

## Escopo e limites

Esta fase autorizou exclusivamente a auditoria final do artigo ConCI ja coletado e a verificacao individual de tres artigos SciELO previamente indicados. Foram coletados somente dois HTMLs autorizados, ambos sob CC BY 4.0. O terceiro artigo foi bloqueado antes de qualquer download porque sua pagina oficial declara CC BY-NC 4.0.

Nao foram baixados PDF, XML, imagens, anexos, links externos ou qualquer documento fora da lista. Nao foram usados Ollama, APIs comerciais, modelos, pesos ou tokenizadores externos. Nao houve BPE, split, tokenizacao, treinamento neural ou alteracao da interface desktop. Checkpoints, pesos, corpus e resultados da v0.4 permanecem intactos.

## 1. Registro historico e auditoria ConCI

O manifesto completo da Fase 2C foi congelado em [collection-audit.phase-2c.json](../data/corpus-v0.5/collection-audit.phase-2c.json), com SHA-256 `9d217f293b2169b6e90b84c53586c593f230270cdd7b5491fb61f82b96538be0`. O manifesto ativo passou para o esquema `v3` e preserva essa referencia sem reescrever o registro historico.

O HTML original do ConCI foi novamente conferido. Ele permanece imutavel, tem 275974 bytes e SHA-256 `9b2fcbf03e68c371317da99a589f283a981c45171d7553529eb19303f83a82f4`. O documento declara `windows-1252`, embora a resposta HTTP informe UTF-8; somente os derivados foram decodificados como Windows-1252, normalizados em Unicode NFC e gravados em UTF-8. A verificacao encontrou zero caracteres de substituicao e zero caracteres de controle invalidos.

| Derivado ConCI | Bytes | Caracteres | Palavras | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| Extraido da Fase 2C, preservado | 51962 | 50409 | 7691 | `66fb3738457050d92fe823cc6fbc112335388511927f58ec2507225a41fc3bec` |
| Limpo da Fase 2C, preservado | 32194 | 31130 | 4742 | `3e130a86bf96ac5fe6ce7c30330231c943f9dedbdcce3a7a53b84d0fb1696ad7` |
| Extraido revisado da Fase 2D | 51979 | 50426 | 7693 | `44692305689f0422ec93a8b2092c6b5f3a92aee5ef3be253f42962ecbd097322` |
| Limpo revisado da Fase 2D | 35313 | 34161 | 5207 | `5cd116862e1012ea6e0380ba8aec92c2c16e32873e5062aacf05ce36fec21f6e` |

As oito redacoes da Fase 2C foram inspecionadas individualmente. Quatro blocos autorais foram restaurados por nao serem citacoes diretas, tres blocos exclusivamente citacionais continuaram redigidos e um bloco misto teve somente tres spans de citacao redigidos. A nova revisao localizou ainda uma citacao interna em bloco autoral e um bloco exclusivamente citacional; ambos foram tratados sem apagar a argumentacao ao redor.

A versao limpa revisada preserva resumo, secoes, listas e 41 linhas de tabela. Foram removidos 9 blocos de materia preliminar, 6 blocos de resumos estrangeiros, 2 legendas e 2 fontes de figuras, 39 blocos de referencias, 4 blocos exclusivamente citacionais e 4 spans internos de citacao. Nenhuma duplicacao consecutiva foi removida. Amostras do inicio (`RESUMO`), meio (`2.2 Creative Commons`) e fim (`5 CONSIDERACOES FINAIS`) foram verificadas, inclusive as tabelas.

A varredura do texto limpo encontrou zero e-mails, CPFs e telefones. A fonte oficial, autoria, DOI e condicoes de atribuicao permanecem registrados no manifesto. O ConCI agora esta em `approved_for_future_inclusion`; isso nao autoriza tokenizacao, split ou treinamento.

## 2. Auditoria previa dos artigos SciELO

| Item autorizado | Autores verificados | DOI | Pagina canonica e licenca verificada | Decisao |
| --- | --- | --- | --- | --- |
| *A ideia de afetividade na filosofia e na educacao* | Agostinho Morosini; Maria Judith Sucupira da Costa Lins | `10.24109/2176-6681.rbep.105.5844` | [SciELO/RBEP](https://www.scielo.br/j/rbeped/a/Yvgc3v3QyLL3nKYNSQvfkqy/?format=html&lang=pt), CC BY 4.0 | HTML em portugues coletado |
| *Tecnologias digitais e o ensino de triangulos: uma revisao sistematica da literatura* | Barbara Silva Gumiero; Vinicius Pazuch | `10.24109/2176-6681.rbep.105.5980` | [SciELO/RBEP](https://www.scielo.br/j/rbeped/a/9HwMzH7xZBLqnRTS33df56K/?format=html&lang=pt), CC BY-NC 4.0 | bloqueado, sem download |
| *Analise do efeito redistributivo das transferencias intergovernamentais sobre as receitas municipais no semiarido brasileiro* | Luis Alberto da Costa; Napie Galve Araujo Silva; Vilmar Antonio Goncalves Tondolo; Lauro Nogueira | `10.1590/0034-761220240010` | [SciELO/RAP](https://www.scielo.br/j/rap/a/QpnmPNnQ8WmK8ckGFGgBv7w/?format=html&lang=pt), CC BY 4.0 | HTML em portugues coletado |

Para cada fonte aprovada, titulo, DOI, autores, publicacao, pagina canonica, cobertura da representacao HTML, riscos de terceiros, dados pessoais e duplicidade foram conferidos antes da coleta. A atribuicao futura deve creditar autores e publicacao inicial, indicar a fonte e a licenca [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) e registrar alteracoes nos derivados. Os dois artigos coletados continuam em `audited` e `pending_explicit_approval`; nao foram aprovados automaticamente para inclusao futura.

O artigo de triangulos nao atende a autorizacao de CC BY 4.0 porque sua pagina oficial aponta [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). Nenhum arquivo, cabecalho, texto extraido ou texto limpo foi criado para ele.

## 3. Arquivos locais, limpeza e qualidade

Os arquivos integrais e derivados abaixo ficam fora do Git. Cada HTML original esta marcado como somente leitura. Os snapshots de resposta registram URL solicitada e final, `HTTP 200`, tipo de conteudo HTML UTF-8 e ausencia de redirecionamento.

| Documento | HTML original | SHA-256 do original | Texto limpo: bytes / caracteres / palavras | SHA-256 do limpo |
| --- | ---: | --- | --- | --- |
| Afetividade/RBEP | 172821 bytes | `7b424baead4364f5332176e7cf333e7fb26413a99df9ab881560a2ed0f229110` | 39733 / 38377 / 5883 | `5ba727d08946d4da28d33069d438b1412c228e935898d6dc1c07878e5e63b6f0` |
| Redistribuicao/RAP | 247824 bytes | `6228a271ecb046dc02e19395ac60414a3aad208484fc0141cd404a550fd19298` | 59507 / 57456 / 8449 | `21b612fb4683447cc1876b52ddc0fc5dd710553c7f9250eb4b9a459d5bf2c234` |

Nos dois documentos, a extracao ficou restrita a `article#articleText`. Resumo em portugues, secoes, listas e tabelas textuais foram preservados. Resumos em outros idiomas, referencias, elementos editoriais posteriores, imagens e legendas ficaram fora da versao limpa. Nenhum recurso citado foi baixado.

| Documento | Paragrafos / secoes | Remocoes e redacoes relevantes | Qualidade do texto limpo |
| --- | --- | --- | --- |
| Afetividade/RBEP | 85 / 6 | 6 blocos de resumo estrangeiro, 60 de referencias, 1 legenda de figura e 12 blocos de citacao direta redigidos | zero e-mails, CPFs e telefones; zero caracteres invalidos ou de substituicao |
| Redistribuicao/RAP | 123 / 10 | 6 blocos de resumo estrangeiro, 51 de referencias e 8 legendas de figura removidos | zero e-mails, CPFs e telefones; zero caracteres invalidos ou de substituicao |

As amostras de inicio, meio e fim foram revisadas em ambos os artigos. Nao houve deduplicacao interna alem da regra conservadora de blocos consecutivos exatamente iguais, que nao removeu nenhum bloco.

## 4. Duplicidade e composicao atual

Foi feita comparacao por DOI, titulo, primeiro autor, instituicao, hashes e Jaccard de conjuntos de palavras normalizadas. Nenhum par compartilha DOI, titulo, primeiro autor, instituicao ou hash do texto limpo. As similaridades Jaccard ficaram entre `0.123035` e `0.167374`; nenhum par foi marcado como potencial duplicata e nenhuma exclusao automatica foi feita.

O conjunto local auditado agora possui quatro documentos efetivos: eMAG 3.1, ConCI revisado, Afetividade/RBEP e Redistribuicao/RAP. O total limpo e de 275725 bytes, 265487 caracteres e 39232 palavras. A estimativa heuristica, sem executar tokenizador, e de 49042 a 60811 unidades sublexicais. Esse volume continua insuficiente para treinamento linguistico relevante e e enviesado para textos institucionais e academicos.

## 5. Proximo lote proposto, sem coleta

Uma proxima proposta deve ampliar generos e autoria com textos educacionais, informativos e explicativos em portugues brasileiro contemporaneo, todos com licenca individual verificavel ou autorizacao expressa. O lote deve reservar fontes, autores e instituicoes inteiros para validacao e para um teste mantido isolado. Dialogos originais produzidos especificamente para o projeto tambem sao candidatos preferiveis, desde que tenham autoria, consentimento e licenca documentados.

Antes de qualquer nova coleta, sera necessario aprovar cada fonte, versao, licenca, representacao, regra de limpeza, atribuicao e destino no split. O BPE atual nao deve ser reaproveitado automaticamente; um novo tokenizador devera ser treinado somente nos futuros dados de treinamento aprovados.

## 6. Validacao e ponto de parada

Foram executados os testes de auditoria das Fases 2B, 2C e 2D: `27 passed`. Eles cobrem a preservacao dos manifestos historicos, limites de autorizacao, bloqueio por licenca, redacoes ConCI, limpeza SciELO, hashes locais e estados de aprovacao. A verificacao de sintaxe dos novos modulos tambem passou.

Esta fase termina aqui. Nao sera iniciada nova coleta, tokenizacao, split, treinamento ou proxima fase sem aprovacao explicita.
