# ELYSIA-Seed v0.5 - segunda coleta controlada

Data: 2026-10-16
Fase: 2C - consolidacao do eMAG 3.1 e coleta de um unico artigo ConCI
Resultado: concluida localmente; parada obrigatoria mantida.

## Escopo autorizado e limites

Esta fase teve somente duas atividades autorizadas:

1. conferencia final dos artefatos locais do eMAG 3.1 coletados na Fase 2B;
2. coleta de uma unica representacao integral do artigo ConCI identificado pelo DOI `10.33467/conci.v4i.15670`.

Nao foram baixados XML, PDF-A, anexos, links externos, o segundo registro eduCAPES, artigos SciELO ou qualquer outro documento. Nao foram usados Ollama, APIs comerciais, modelos externos, pesos, tokenizadores, BPE, splits ou treinamento neural. Checkpoints e artefatos da v0.4 permanecem intactos.

## 1. Conferencia final do eMAG 3.1

Os quatro artefatos locais da Fase 2B foram conferidos novamente contra seus hashes registrados. O HTML original continua marcado como somente leitura e inalterado.

| Artefato local, ignorado pelo Git | Bytes | SHA-256 |
| --- | ---: | --- |
| HTML original | 245543 | `200884cddfa8a769473899f2db6cd34cc819a6573439f9409eec7806ea368d0f` |
| Cabecalhos HTTP | 852 | `fd9714bdcdcf8a3878f1bbea94c86e737a2e9870f1bcf2bdccfd6dbab479b1d0` |
| Texto extraido | 149093 | `493d9a901f48f14b721799cd8ea8a440f59381622a810820a6f022a1c04d8dcd` |
| Texto limpo | 141172 | `a050365d151328d18d7a8ccbb5fe39aaaacbafe4ef24212c4d9d47ea4bb36dbc` |

Foram comparadas dez secoes distribuidas entre introducao, processo de desenvolvimento, recomendacoes, formularios, elementos padronizados e o anexo final. Cada uma permanece presente no HTML original, no texto extraido e no texto limpo. A revisao tambem confirmou:

- 45 titulos de recomendacao, 132 itens de lista, 83 exemplos tecnicos e 75 linhas de tabela preservados;
- as quatro redacoes de citacoes de terceiros em codigo continuam limitadas aos mesmos quatro casos auditados na Fase 2B;
- 11 blocos de agradecimentos, 19 URLs soltas e os controles de interface continuam excluidos conforme a regra anterior;
- NFC, UTF-8 valido, zero caracteres de controle invalidos e zero caracteres de substituicao na versao limpa;
- nenhuma correcao adicional foi necessaria.

O estado atual do eMAG e `approved_for_future_inclusion`. Isto permite somente sua inclusao posterior em um corpus que ainda devera ser formalmente constituido. Nao permite tokenizacao, split, treinamento ou qualquer alteracao de pesos.

## 2. Auditoria previa e coleta do artigo ConCI

Fonte canonica: [ConCI/UFS](https://periodicos.ufs.br/conci/article/view/15670).

- Titulo: *Licencas alternativas de protecao intelectual atribuidas a periodicos tecnicos e/ou cientificos da area da Ciencia da Informacao no contexto da Ciencia Aberta*.
- Autores: Natalia Rodrigues Silva, Nivaldo Calixto Ribeiro e Dalgiza Andrade Oliveira.
- Publicacao: *ConCI: Convergencias em Ciencia da Informacao*, v. 4, 2021, artigo original, p. 1-30.
- DOI: `10.33467/conci.v4i.15670`.
- Licenca declarada na pagina oficial: CC BY 4.0. A atribuicao futura deve creditar autores e publicacao inicial, informar a licenca e indicar alteracoes.

A pagina oficial lista PDF-A, HTML e XML. A representacao HTML foi escolhida por conter o texto integral e foi a unica baixada. O preflight confirmou `HTTP 200`, URL final no mesmo dominio, ausencia de redirecionamento e `Content-Type: text/html; charset=UTF-8`.

URL efetivamente coletado: `https://periodicos.ufs.br/conci/article/download/15670/12129?inline=1`.

## 3. Arquivos locais e hashes ConCI

Todos os arquivos abaixo estao fora do Git e permanecem somente na maquina de coleta.

| Artefato local, ignorado pelo Git | Bytes | SHA-256 |
| --- | ---: | --- |
| HTML original | 275974 | `9b2fcbf03e68c371317da99a589f283a981c45171d7553529eb19303f83a82f4` |
| Cabecalhos HTTP | 729 | `ffd45f8412d6ee10c198e0b8f05f5e7c21e4db73aa58c6c4598cf0ba09f13e0f` |
| Texto extraido | 51962 | `66fb3738457050d92fe823cc6fbc112335388511927f58ec2507225a41fc3bec` |
| Texto limpo | 32194 | `3e130a86bf96ac5fe6ce7c30330231c943f9dedbdcce3a7a53b84d0fb1696ad7` |

O HTML original foi preservado como somente leitura. Os textos extraido e limpo sao derivados locais e nao foram publicados.

## 4. Extracao, limpeza e qualidade ConCI

O servidor informou UTF-8 no cabecalho HTTP, mas o proprio HTML declara `windows-1252` e nao e UTF-8 valido em seus bytes originais. O original nao foi modificado. Somente as versoes derivadas foram decodificadas como Windows-1252, normalizadas em Unicode NFC e salvas em UTF-8. Esta divergencia esta registrada no manifesto.

| Medida | Texto extraido | Texto limpo |
| --- | ---: | ---: |
| Bytes | 51962 | 32194 |
| Caracteres | 50409 | 31130 |
| Palavras | 7691 | 4742 |
| SHA-256 | `66fb3738457050d92fe823cc6fbc112335388511927f58ec2507225a41fc3bec` | `3e130a86bf96ac5fe6ce7c30330231c943f9dedbdcce3a7a53b84d0fb1696ad7` |

A extracao identificou 122 paragrafos e 41 linhas de tabela. Quatro elementos de imagem foram deixados fora da representacao textual. A versao limpa preserva o resumo em portugues, as secoes do artigo, argumentos dos autores, listas e tabelas textuais; foram revisadas amostras do inicio (`RESUMO`), meio (`2.2 Creative Commons`) e fim (`5 CONSIDERACOES FINAIS`).

Transformacoes registradas:

- 9 blocos de capa, autores, afiliacoes e contato retirados da versao limpa; os dados de autoria indispensaveis ficaram no preambulo de atribuicao;
- 6 blocos de resumos em ingles e espanhol retirados, pois o lote busca portugues brasileiro;
- 2 legendas de figura e 2 fontes associadas removidas porque as imagens nao foram incorporadas;
- 39 blocos de referencias removidos para nao transportar bibliografia repetitiva nem material de terceiros sem auditoria propria;
- 8 blocos que aparentavam conter citacao direta de terceiros redigidos;
- 0 blocos consecutivos duplicados removidos.

Na versao limpa, a varredura encontrou zero e-mails, CPFs e telefones; nao ha caracteres de controle invalidos nem caracteres de substituicao. A varredura automatica nao substitui uma revisao humana contextual.

Sem treinar ou executar tokenizador, a estimativa heuristica para o ConCI limpo e de `5928` a `7351` unidades sublexicais. Para o eMAG limpo, a estimativa permanece `24617` a `30525`. Nao foi criado BPE, split ou modelo neural.

## 5. Manifesto versionado e estados

O manifesto principal [collection-audit.json](../data/corpus-v0.5/collection-audit.json) passou para o esquema `v2`, capaz de registrar mais de um documento sem ampliar a autorizacao. O manifesto completo da Fase 2B foi preservado sem alteracoes em [collection-audit.phase-2b.json](../data/corpus-v0.5/collection-audit.phase-2b.json), inclusive com seus hashes e sua decisao original.

| Documento | Coletado | Auditado | Aprovado para inclusao futura | Estado atual |
| --- | --- | --- | --- | --- |
| eMAG 3.1 HTML | sim | sim | sim, somente para inclusao posterior | `approved_for_future_inclusion` |
| Artigo ConCI HTML | sim | sim | nao, depende de nova aprovacao | `audited` |

O segundo registro eduCAPES, as demais fontes candidatas e qualquer fonte adicional continuam fora desta coleta. Nenhum candidato foi promovido automaticamente.

## 6. Riscos pendentes e recomendacoes

Dois documentos ainda sao insuficientes para constituir um corpus linguistico. O eMAG e um documento tecnico institucional; o ConCI e um artigo academico. Ambos introduzem vieses de genero, dominio e autoria. O proximo lote, caso aprovado, deve diversificar autores, tipos textuais e instituicoes, verificar licenca e versao por arquivo e reservar uma fonte de teste realmente isolada.

Antes de qualquer preparacao de corpus, tokenizacao ou treinamento, e necessario definir por nova aprovacao explicita: quais documentos terao inclusao efetiva, como sera feita a atribuicao, a politica para citacoes de terceiros e o protocolo de split por fonte e autoria.

## Ponto de parada

Testes locais foram executados para validar o manifesto historico v1, o manifesto v2, a limpeza do ConCI, os limites de autorizacao e os hashes locais quando os artefatos estao presentes. Esta fase termina aqui. Nenhuma nova coleta, preparacao de corpus, tokenizacao ou treinamento sera iniciada sem aprovacao explicita.
