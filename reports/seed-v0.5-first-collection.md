# ELYSIA-Seed v0.5 - primeira coleta controlada

Data da coleta: 2026-10-16
Fase: 2B - coleta oficial do eMAG 3.1 em HTML
Resultado: concluida localmente e auditada; nao aprovada para treinamento.

## Escopo e decisao anterior

A tentativa anterior de usar o PDF oficial foi bloqueada porque o URL do PDF redirecionava para uma pagina generica. A autorizacao da Fase 2B substituiu exclusivamente o formato: permitiu somente a pagina HTML oficial do eMAG em `https://emag.governoeletronico.gov.br/`.

Nenhum PDF, imagem, script, folha de estilo, anexo, curso, link externo, artigo SciELO ou outro dataset foi baixado como parte da coleta do eMAG.

## Verificacao e coleta

Preflight em `2026-10-16T18:14:52.9755768-03:00`:

- resposta `HTTP 200 OK`;
- URL final igual ao URL autorizado, sem redirecionamento;
- `Content-Type: text/html; charset=UTF-8`;
- titulo `eMAG - Modelo de Acessibilidade em Governo Eletronico`;
- versao `3.1 - Abril 2014`;
- declaracao de licenca `CC BY 4.0`;
- corpo completo do modelo presente, incluindo introducao, recomendacoes, glossario e anexo.

A coleta ocorreu em `2026-10-16T18:15:16.7369580-03:00`. O HTML original foi preservado localmente como somente leitura, sem alteracoes, e seus cabecalhos HTTP foram guardados separadamente.

| Artefato local, ignorado pelo Git | Bytes | SHA-256 |
| --- | ---: | --- |
| HTML original | 245543 | `200884cddfa8a769473899f2db6cd34cc819a6573439f9409eec7806ea368d0f` |
| Cabecalhos HTTP | 852 | `fd9714bdcdcf8a3878f1bbea94c86e737a2e9870f1bcf2bdccfd6dbab479b1d0` |
| Texto extraido | 149093 | `493d9a901f48f14b721799cd8ea8a440f59381622a810820a6f022a1c04d8dcd` |
| Texto limpo | 141172 | `a050365d151328d18d7a8ccbb5fe39aaaacbafe4ef24212c4d9d47ea4bb36dbc` |

## Licenca e atribuicao

A [pagina oficial do eMAG](https://emag.governoeletronico.gov.br/) declara a versao 3.1 e a licenca Creative Commons Atribuicao 4.0 Internacional. Qualquer derivado futuro devera creditar a Equipe do DGE - Departamento de Governo Eletronico, a fonte oficial, a licenca CC BY 4.0 e indicar alteracoes.

## Extracao e qualidade

A extracao produziu uma representacao textual da area principal e uma versao limpa da coluna tecnica. A versao limpa contem `135493` caracteres, `19693` palavras e `72` secoes, com UTF-8 valido, normalizacao Unicode NFC, nenhum caractere de controle invalido e nenhum caractere de substituicao.

As amostras estruturais revisadas foram:

- inicio: `1. Introducao`;
- meio: `Recomendacao 3.6 - Fornecer alternativa em texto para as imagens do sitio`;
- fim: `7. Anexo 1 - Tabela de Contraste de Cores`.

O HTML tem uma ocorrencia de fechamento de paragrafo malformado antes de um titulo. Ela foi reparada apenas em memoria durante a extracao; a copia HTML original continua inalterada.

Regras aplicadas:

- preservar titulos, subtitulos, recomendacoes, explicacoes tecnicas, listas, glossario, anexo textual e exemplos de codigo;
- usar somente a coluna tecnica `p-esquerda` para a versao limpa;
- remover sumario lateral, controles, navegacao repetida, links `Voltar ao sumario`, botoes `Topo`, links de exemplos navegaveis, imagens e legendas visuais;
- remover `19` URLs externas soltas do texto corrido;
- preservar exemplos tecnicos mantidos em `textarea`, mas redigir `4` citacoes diretas de terceiros neles;
- remover a secao de agradecimentos, que continha `11` blocos com nomes de pessoas e nao agregava conteudo tecnico;
- remover apenas blocos tecnicos consecutivos exatamente iguais; nao houve ocorrencias adicionais.

A verificacao automatica de dados pessoais encontrou zero e-mails, CPFs e telefones na versao limpa. Ela nao substitui revisao humana de entidades nominais ou de contexto.

## Estimativa de tokens

Sem treinar ou executar tokenizador, a estimativa preliminar para o texto limpo e de `24617` a `30525` unidades sublexicais, usando uma faixa heuristica de 1,25 a 1,55 unidades por palavra em portugues. Nao foi criado split definitivo, BPE ou treinamento neural.

## Registros eduCAPES: metadados somente

Nenhum conteudo integral dos registros eduCAPES foi baixado.

1. `capes/1140501`: autoria confirmada como Natalia Rodrigues Silva, Nivaldo Calixto Ribeiro e Dalgiza Andrade Oliveira; DOI `10.33467/conci.v4i.15670`; pagina canonica na [ConCI/UFS](https://periodicos.ufs.br/conci/article/view/15670), que declara CC BY 4.0. A pagina lista PDF-A, HTML e XML, mas nenhum arquivo foi requisitado. Status: `pending` para futura auditoria individual.
2. `capes/1023510`: autoria confirmada como Adriana Maria Tonini, Paulo Henrique de Assis Santana e Thais Machado Scherrer; capitulo 16 de *Topicos sobre dados abertos para editores cientificos*, DOI `10.21452/978-85-93910-04-3.cap16`. O registro aponta para a [UFOP](https://www.repositorio.ufop.br/handle/123456789/19961); a obra da [ABEC](https://www.abecbrasil.org.br/publicacoes/) declara CC BY 4.0. URLs de arquivo foram identificados somente como metadados e nao foram baixados. Status: `pending` para futura auditoria individual.

## Limites e ponto de parada

Um documento tecnico unico nao forma um corpus linguistico suficiente. O eMAG esta marcado como `selected`, `collected` e `audited`, mas `approved_for_future_inclusion` permanece `false` e a decisao para uso futuro e `pending_explicit_approval`.

O manifesto historico de pesquisa permanece separado e continua validando zero downloads. O novo [manifesto de coleta](../data/corpus-v0.5/collection-audit.json) contem somente metadados, hashes e caminhos locais ignorados pelo Git; nao contem o HTML ou os textos completos.

Nao foram usados Ollama, APIs de IA, modelos ou pesos externos. Nenhum checkpoint, peso, tokenizador ou artefato da v0.4 foi alterado. A proxima coleta exige nova autorizacao explicita, auditoria por arquivo e revisao de licenca, terceiros e privacidade.
