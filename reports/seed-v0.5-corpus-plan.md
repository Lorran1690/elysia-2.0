# ELYSIA-Seed v0.5: plano do corpus brasileiro contemporaneo

Data do plano: 2026-10-15
Branch: `codex/elysia-seed-v0.5`
Baseline preservado: `80140df0242c309911efaace921eafdf05b6a0f3`

## Escopo e ponto de parada

Esta fase e exclusivamente de pesquisa, verificacao de metadados e planejamento. Nenhum texto integral foi baixado, nenhum dataset foi incorporado, nenhum tokenizador foi treinado, nenhum peso foi modificado e nenhum treinamento neural foi executado. O manifesto verificavel esta em [`data/corpus-v0.5/source-candidates.json`](../data/corpus-v0.5/source-candidates.json).

O repositorio de referencia [MiniMind](https://github.com/jingyaogong/minimind) foi considerado apenas como referencia externa de organizacao de etapas de treinamento do zero. Nenhum codigo, peso, dataset, tokenizer, arquitetura ou dependencia daquele repositorio foi importado nesta fase.

O trabalho para aqui apos a entrega deste plano. Uma nova aprovacao explicita e necessaria antes de selecionar ou baixar qualquer arquivo.

## 1. Auditoria de preservacao da v0.4

O baseline aprovado foi mantido como referencia historica, sem alterar arquivos da v0.4. A validacao automatizada da v0.5 compara os anchors no manifesto com [`reports/seed-v0.4-final-evaluation.json`](seed-v0.4-final-evaluation.json).

| Item congelado | Valor auditado |
| --- | --- |
| Checkpoint best | `elysia-seed-v0.4-machado-extended-best.pt` |
| SHA-256 do best | `f8e2ec643cd963ebfd47c9c7b6d87a8a5b79af9c0fb7f8e1e75744106e1943d3` |
| Checkpoint last | `elysia-seed-v0.4-machado-extended-last.pt` |
| SHA-256 do last | `0585ed247ccc7d8259390e250393b27b43a429368424f9d6de71c6b02fbc15c1` |
| Etapa | `1.000` |
| Pesos best/last | Idênticos, embora os arquivos tenham metadados diferentes |
| Parametros | `3.490.136` |
| Arquitetura | 4 camadas, embedding 256, 4 heads, FFN 1024, contexto 256, dropout 0 |
| Fingerprint da arquitetura | `1ec4192799a32ee7a0320ccf71a9bfe1f3f708f2e5c9193faa294a3b1e776ae7` |
| BPE Machado | byte-level, vocabulario 512, fingerprint `d7b27519afcc8a19deb57691617e7a1478893bbf3d71768508a998ca48d887a8` |
| Fingerprint de dados | `eb4d6655b08d35a51e91779ff72c15d8f904c6b1fd64a4321d3ed87ea484ca06` |
| Fingerprint do split | `7fca4ee72e780084b1a364cf80424e9d0d3a1cb2ad9cacc3c257c8002282e757` |
| Avaliacao final | Quincas Borba, loss `4,19284883`, perplexidade `66,21114692` |

O BPE da v0.4 esta explicitamente marcado como nao reutilizavel na v0.5. Alterar o vocabulario invalida a correspondencia das embeddings, portanto pesos e embeddings da v0.4 nao devem migrar para o futuro experimento.

## 2. Manifesto de candidatos e matriz de licencas

O manifesto contem 28 registros de metadados e zero arquivos de conteudo:

| Fonte | Registros | Aprovados para proposta | Pendentes | Rejeitados | Situacao |
| --- | ---: | ---: | ---: | ---: | --- |
| eMAG | 1 | 1 | 0 | 0 | Documentacao tecnica com evidencia de CC BY 4.0 na pagina oficial |
| Padrao Digital de Governo | 1 | 0 | 1 | 0 | Catalogo de licencas; CC0 e MIT devem ser atribuídos por artefato, nunca por portal |
| eduCAPES | 6 | 2 | 3 | 1 | Registros individuais com evidencia de direitos; arquivos e cadeia de versoes ainda devem ser auditados |
| SciELO Brasil | 20 | 0 | 16 | 4 | Triagem multi-area; licenca por metadado individual registrada, mas PDF/XML e riscos ainda precisam ser revisados |
| **Total** | **28** | **3** | **20** | **5** | Nenhum texto foi coletado |

`Aprovado para proposta` significa apenas que a fonte e elegivel para uma futura triagem. Nao significa autorizacao para baixar, processar ou treinar. Uma licenca desconhecida permanece pendente por regra de validacao.

### Evidencias por familia de fonte

- **eMAG:** a pagina oficial do [eMAG 3.1](https://emag.governoeletronico.gov.br/) declara CC BY 4.0. Antes de qualquer coleta, a versao exata, o aviso e anexos devem ser registrados no manifesto de lote.
- **Padrao Digital:** a pagina oficial de [legislacao e licencas](https://www.gov.br/ds/downloads/legislacao) informa CC0 1.0 Universal e MIT. Isto nao transfere automaticamente uma dessas licencas a todos os guias, paginas e componentes.
- **SciELO:** os [criterios da colecao SciELO Brasil](https://www.scielo.br/media/files/Criterios_SciELO_Brasil_.pdf) descrevem CC BY como padrao desde 2015, mas tambem registram excecoes historicas. Por isso os 20 registros continuam pendentes ate que o arquivo do item traga a licenca compatível e passe em auditoria de privacidade e duplicacao. O manifesto preserva DOI, URL de metadado e evidencia individual de CC BY 4.0 quando ela existe.
- **eduCAPES:** acesso aberto nao foi tratado como permissao. So entraram registros com campo individual de direitos pesquisado, como [Ciencia Aberta no CNPq](https://educapes.capes.gov.br/handle/capes/1023510?mode=full) e [licencas na Ciencia da Informacao](https://educapes.capes.gov.br/handle/capes/1140501?mode=full).

Os quatro artigos SciELO e o recurso eduCAPES rejeitados nao foram descartados por falta de valor academico. Foram excluidos do primeiro lote por riscos de privacidade, grupos vulneraveis, menores, saude sensivel, conversas em aplicativos ou material visual potencialmente protegido. Essa e uma decisao de reducao de risco, nao um julgamento sobre as obras.

## 3. Protocolo para material original brasileiro

O componente mais importante para linguagem cotidiana, perguntas frequentes, instrucoes e dialogos nao deve vir de conversas privadas nem de raspagem de redes sociais. A proposta e criar um programa de textos autorais para a E.L.Y.S.I.A. com estes requisitos:

1. Termo escrito por autor ou roteirista, identificando obra, data, versao, permissao de treinamento, armazenamento, avaliacao e eventual distribuicao.
2. Licenca preferencial CC0 1.0; CC BY 4.0 apenas quando autoria, fonte e registro de alteracoes puderem ser preservados. Sem um termo claro, o item fica pendente.
3. Declaracao de originalidade: sem copia de datasets, obras de terceiros, conversas privadas ou conteudo gerado/destilado por modelo comercial.
4. Pauta editorial para dialogos roteirizados, FAQs, instrucoes, textos narrativos curtos e explicacoes cotidianas em variantes brasileiras diversas.
5. Revisao humana de dados pessoais, referencias a terceiros, discurso de odio, segredos comerciais e conteudo inadequado ao escopo antes de qualquer ingestao.
6. Manifesto por documento com hash, autor, licenca, genero, grupo de derivacao e decisao de auditoria.

## 4. Composicao proposta do corpus

Esta distribuicao e uma meta de curadoria para uma futura coleta, nao uma medicao do corpus atual. Cada fonte, autor e serie terao limites para reduzir concentracao indevida.

| Faixa linguistica ou genero | Meta inicial | Exemplos de origem aceitavel | Regra de concentracao |
| --- | ---: | --- | --- |
| Documentacao tecnica e institucional | 20% | eMAG, artefatos individuais do Padrao Digital com licenca confirmada | Maximo 15% por artefato-fonte |
| Explicacoes educacionais | 20% | eduCAPES e textos autorais revisados | Maximo 10% por autor |
| Artigos informativos e cientificos | 20% | SciELO auditada por documento | Maximo 10% por periodico e 5% por autor |
| Instrucoes, FAQs e guias | 15% | Material original autorizado e documentacao permissiva | Maximo 15% por serie |
| Portugues cotidiano e dialogos roteirizados | 15% | Dialogos originais autorizados | Maximo 5% por roteirista ou personagem-serie |
| Narrativas originais curtas | 5% | Obras escritas para o projeto | Maximo 5% por autor |
| Textos de revisao, glossarios e metadados editoriais | 5% | Apenas quando autorizados e uteis | Excluir referencias bibliograficas repetidas |

O objetivo e mesclar registro formal, tecnico e cotidiano sem fingir que um pequeno corpus pode cobrir todo o portugues brasileiro. Conteudo medico sensivel, relatos de caso, conversas privadas, dados de menores e obras sem licenca clara ficam fora do primeiro lote.

## 5. Tres escalas de corpus futuro

Todas as faixas abaixo sao estimativas de planejamento. Os valores de armazenamento consideram copias locais de fonte, texto limpo, manifestos, deduplicacao e token stores. Eles nao sao medições reais e nao autorizam coleta.

| Escala | Corpus limpo alvo | Tokens de treinamento planejados | Armazenamento local estimado | Parametros propostos apenas para estudo | Principal limitacao |
| --- | ---: | ---: | ---: | --- | --- |
| A. Experimental pequeno | 3 a 6 milhoes de tokens BPE | 30 a 90 milhoes | 0,2 a 1 GB de fontes; 0,05 a 0,2 GB processados | manter referencia de 3,49 M ou testar ate 5 M somente depois de benchmark | Cobertura limitada e alta sensibilidade a repeticao |
| B. Intermediario | 20 a 50 milhoes de tokens BPE | 200 a 750 milhoes | 2 a 10 GB de fontes; 0,4 a 1,5 GB processados | 5 a 10 M depois de teste de VRAM | Ainda pequeno para conversa confiavel; curadoria vira o gargalo |
| C. Ampliado | 100 a 250 milhoes de tokens BPE | 1 a 5 bilhoes | 10 a 50 GB de fontes; 2 a 8 GB processados | 10 a 20 M somente se couber em VRAM e for justificado | A GTX 1650 tende a tornar iteracao e multiplas sementes muito lentas |

O primeiro conjunto de candidatos anotados soma apenas uma faixa preliminar de aproximadamente 181.500 a 451.500 tokens, com muitas fontes ainda pendentes ou rejeitadas. Ele e uma amostra para auditoria de procedencia, nao uma base suficiente para treinar um modelo linguistico contemporaneo.

## 6. Estrategia de deduplicacao e qualidade

O processo futuro deve preservar a copia de origem localmente e criar uma copia limpa separada. Nenhuma limpeza pode apagar proveniencia, termos de uso ou hash da origem.

1. Normalizar Unicode para NFC, line endings e espacos somente na copia limpa.
2. Remover boilerplate tecnico, navegacao, cabecalhos e rodapes apenas com regra versionada e revisao de amostras; manter a copia original intacta.
3. Detectar duplicatas exatas por SHA-256 do arquivo e por SHA-256 do texto limpo canônico.
4. Agrupar versoes relacionadas por DOI, handle, titulo, autor, serie, URL de origem e familia de obra antes de criar os splits.
5. Usar similaridade por n-gramas e MinHash/SimHash para encaminhar quase duplicatas a revisao humana. Trechos acima do limiar definido no protocolo nao podem atravessar splits.
6. Separar referencias, bibliografias, tabelas, anexos e textos de licenca para evitar treinamento excessivo em boilerplate. A decisao por tipo de bloco precisa ficar registrada.
7. Executar verificacao de PII e auditoria humana em fontes com entrevistas, estudos qualitativos, saude, escolas, imagens, mensagens ou grupos vulneraveis.
8. Exigir declaracao de origem nao sintetica para todo material autoral novo.

## 7. Plano de novo Byte-Level BPE

O proximo tokenizador sera novo e independente do BPE de Machado. Ele so podera ser treinado depois que o inventario e os splits estiverem congelados.

1. Formar primeiro o split de treino por grupos completos. Separar internamente o treino em uma porcao de construcao do BPE e uma porcao de desenvolvimento do BPE, ambas ainda pertencentes ao treino.
2. Aprender merges exclusivamente na porcao de construcao do treino. Validacao e teste nao podem influenciar os merges, o vocabulario, a limpeza nem a selecao do tokenizador.
3. Comparar vocabularios `1.024`, `2.048`, `4.096` e `8.192`, incluindo os 256 bytes base. Nao escolher automaticamente o maior; o custo de embedding, a fragmentacao e a estabilidade precisam ser comparados.
4. Medir bytes por token, cobertura, taxa de fragmentacao, comprimento de sequencia e comportamento de tokens especiais somente em amostras internas do treino durante a escolha.
5. Usar uma bateria textual de treino com acentuacao (`acao`, `informacao`, `saude`, `nao`, `amanha`), linguagem cotidiana (`ta`, `ce`, `pra`, `ne`), termos tecnicos (`API`, `JSON`, `UTF-8`, `GPU`, `SHA-256`), compostos e hifenizados, URLs e textos longos.
6. Depois de congelar o BPE escolhido, apenas reportar sua eficiencia em validacao e deixar o teste isolado para a avaliacao final do modelo. Nenhum merge e retreinado apos essa etapa.

Se o vocabulario mudar, as embeddings e a camada de saida devem nascer do zero. Pesos, token ids e embeddings da v0.4 nao sao compatíveis com esse experimento.

## 8. Estrategia de splits e teste realmente novo

Proposta inicial: 75% treino, 15% validacao e 10% teste por grupo de documentos, ajustada somente depois de conhecer o inventario aprovado.

- Definir um `group_id` que una obra, autor, responsavel institucional, serie, versoes de idioma, DOI/handle, familia de derivacao e cluster de quase duplicacao.
- Um `group_id` inteiro vai para uma unica particao. Capitulos, paginas, traducoes, preprints, republicacoes e documentos quase duplicados jamais podem atravessar splits.
- Balancear os grupos por fonte, genero, tamanho e variante linguistica quando isso nao conflitar com o isolamento por autor e obra.
- Reservar o novo teste antes do treinamento do BPE e antes de qualquer experimento neural. Nao inspecionar seus textos para escolher arquitetura, vocabulário, hiperparametros ou filtros.
- Armazenar, para cada documento aprovado, hash de origem, hash limpo, versao, licenca, decisao PII, grupo, split e fingerprints globais do inventario e dos splits.
- O teste de Quincas Borba da v0.4 permanece historico e nao pode ser reutilizado como teste da v0.5.

## 9. Planejamento computacional para o hardware-alvo

Hardware alvo: GTX 1650 de 4 GB, Ryzen 5 3400G, 16 GB de RAM e Windows. A v0.4 mediu `10.377,1 tokens/s` na GTX 1650, com modelo de 3,49 M de parametros, batch 1 e sequencias de 256 tokens. Essa medicao e uma referencia inicial, nao uma promessa: vocabulario, contexto, arquitetura, batch, I/O, checkpoints, avaliacao e versao de CUDA mudam o throughput e o consumo.

| Escala | Token budget | Limite inferior pelo throughput v0.4 | Custo experimental recomendado |
| --- | ---: | ---: | --- |
| Experimental pequeno | 30 a 90 M | 0,8 a 2,4 horas | Uma configuracao, seed fixa, checkpoints locais e validacao definida antes do treino |
| Intermediario | 200 a 750 M | 5,4 a 20,1 horas | Uma configuracao piloto por vez; estimar VRAM antes de rodada longa |
| Ampliado | 1 a 5 B | 26,8 a 133,9 horas | Nao iniciar sem benchmark de memoria, plano de recuperacao e janela de energia/tempo dedicada |

Esses tempos sao piso teorico de processamento de tokens no regime da v0.4 e nao incluem preparacao, validacao, escrita de checkpoint, falhas, reexecucoes nem variacao de arquitetura. Para qualquer escala, o plano futuro deve:

- Medir VRAM e RAM com um passo de treino antes de adotar tamanho de modelo, contexto ou batch.
- Registrar token budget, epocas efetivas, taxa de aprendizado, seed, configuracao, temperatura, versoes e hashes em manifesto de experimento.
- Salvar checkpoints localmente com hashes e manter o melhor checkpoint definido apenas por validacao congelada.
- Usar o teste uma unica vez para avaliacao final; nao fazer repeticoes para escolher um resultado favoravel.
- Tratar cada seed adicional como um novo custo completo, nao como um detalhe gratuito.

## 10. Riscos e recomendacao do primeiro lote futuro

Riscos principais:

- Licencas de paginas e catalogos podem diferir da licenca do arquivo final.
- CC BY resolve direitos autorais do artigo, mas nao autoriza automaticamente anexos, imagens, datasets, transcricoes ou material de terceiros.
- Um corpus apenas academico e institucional tende a super-representar prosa formal e nao produz conversacao confiavel.
- Dialogos cotidianos podem introduzir PII, vieses e conteudo privado; por isso so dialogos originais e roteirizados foram propostos.
- Artigos com preprints, traducoes ou repositorios espelho criam vazamento entre split e duplicacao invisivel.
- O hardware disponivel favorece experimentos pequenos e auditaveis; nao justifica promessas de capacidade conversacional, programacao ou controle de PC.

Recomendacao para uma proxima autorizacao, sem executa-la agora:

1. Aprovar um lote inicial muito pequeno, com eMAG e os dois registros eduCAPES marcados como aprovados para proposta.
2. Escolher no maximo alguns artigos SciELO pendentes de baixo risco e verificar manualmente, por arquivo, licenca, versao, autores, anexos, PII e duplicacao antes de baixar.
3. Criar antes o termo para textos originais, a pauta editorial e o checklist de PII; nao aceitar conversas reais.
4. Atualizar o manifesto com hashes e decisoes apenas depois de uma aprovacao de coleta separada.
5. Parar novamente apos a auditoria do primeiro lote, antes de treinamento de BPE ou rede neural.

## Verificacao desta fase

O modulo [`learning/v05_corpus_plan.py`](../learning/v05_corpus_plan.py) valida que o manifesto permanece somente de metadados, que ha 20 artigos SciELO preliminares, que nenhum texto foi coletado e que os anchors da v0.4 continuam intactos. Os testes correspondentes ficam em [`tests/test_v05_corpus_plan.py`](../tests/test_v05_corpus_plan.py).

Ponto de parada obrigatorio atingido: nenhuma coleta, tokenizacao, treinamento ou alteracao de pesos foi iniciada.
