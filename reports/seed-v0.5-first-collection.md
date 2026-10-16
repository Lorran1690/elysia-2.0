# ELYSIA-Seed v0.5 - primeira coleta controlada

Data da auditoria: 2026-10-16
Fase: 2 - primeira coleta controlada do corpus brasileiro
Resultado: **bloqueada antes da coleta**

## Escopo autorizado

A autorizacao recebida para esta fase limitava a coleta ao documento **eMAG - Modelo de Acessibilidade em Governo Eletronico, versao 3.1**. Nenhuma outra obra, anexo, curso, pagina externa, dataset ou documento do governo foi selecionado ou baixado.

## Auditoria antes da coleta

A [pagina oficial do eMAG](https://emag.governoeletronico.gov.br/) declara:

- `Versao 3.1 - Abril 2014`;
- licenca `Creative Commons Atribuicao 4.0 Internacional (CC BY 4.0)`;
- autoria institucional atribuida a Equipe do DGE - Departamento de Governo Eletronico;
- um link rotulado `Download do Modelo em PDF (2.2 MBytes)`.

O URL efetivamente selecionado pelo link oficial foi:

`https://www.governoeletronico.gov.br/documentos-e-arquivos/eMAGv31.pdf`

Foi realizada apenas uma verificacao de cabecalhos HTTP, sem salvar corpo de documento. O URL respondeu `301 Moved Permanently` e apontou para:

`https://www.gov.br/governodigital/pt-br/estrategia-de-governanca-digital/do-eletronico-ao-digital`

O destino nao entregou um PDF do eMAG; na verificacao respondeu `403 Forbidden` com `Content-Type: text/html; charset=iso-8859-1`.

Portanto, o arquivo oficial v3.1 solicitado nao estava disponivel nesse URL no momento da auditoria. Como a autorizacao determinava interrupcao caso o arquivo nao estivesse disponivel, nao foi procurada, baixada nem aceita qualquer copia alternativa.

## Resultado da coleta

| Item | Resultado |
| --- | --- |
| Arquivos de fonte baixados | 0 |
| Bytes de fonte salvos | 0 |
| Copia original imutavel | Nao criada |
| Texto extraido | Nao criado |
| Texto limpo | Nao criado |
| SHA-256 de arquivo | Nao aplicavel: nenhum arquivo foi obtido |
| Secoes, palavras, caracteres ou tokens | Nao aplicavel: nenhum texto foi obtido |
| BPE, tokenizador ou treinamento | Nao executados |
| Pesos, checkpoints ou arquitetura v0.4 | Nao alterados |

Nao houve texto a revisar para caracteres invalidos, duplicacoes, dados pessoais, material de terceiros ou qualidade de extracao. A presenca de elementos de terceiros no PDF tambem permanece nao auditada, pois o PDF nao foi disponibilizado pelo URL oficial.

## eduCAPES

Os dois registros eduCAPES autorizados somente para pesquisa de metadados nao foram consultados nesta execucao. O ponto de parada obrigatorio foi acionado durante a etapa 1, antes da coleta, e a fase foi encerrada integralmente para obedecer a instrucao de parar quando o arquivo eMAG autorizado nao estivesse disponivel.

## Manifesto e proxima decisao

O manifesto de candidatos foi atualizado apenas com o resultado da verificacao: `emag-v3-1` voltou a `pending`, conserva `text_collected: false` e registra `blocked_file_unavailable`, com zero arquivos e zero bytes salvos. Nenhum conteudo integral foi incluido no GitHub.

Para reiniciar esta fase sera necessaria uma nova aprovacao explicita que informe um URL oficial acessivel para o arquivo eMAG v3.1, ou que altere formalmente o escopo autorizado. Ate essa decisao, nao ha coleta, tokenizacao, treinamento ou nova consulta de fontes pendente em andamento.
