# Corpus português v1 — preparação e auditoria

**Entrega:** 2.163 documentos, 2.277.416 tokens BPE e 24 novos casos de avaliação
congelados antes de qualquer treino neural deste lote. Não foram atualizados pesos
neurais; os três checkpoints de inferência anteriores foram conferidos por SHA-256.

A integridade do lote passou. A prontidão para conversa ampla não passou: as fontes
continuam técnicas, há variantes de português misturadas e faltam diálogos variados
com revisão humana independente. O lote permite um próximo piloto de linguagem no
domínio técnico; não é prova de evolução conversacional nem autorização inferida
para gastos ou mudanças de modelo.

## Volume real

| Partição | Documentos | Grupos de tópico | Tokens BPE, incluindo BOS/EOS |
|---|---:|---:|---:|
| Treino | 1.736 | 695 | 1.760.474 |
| Validação | 234 | 89 | 249.328 |
| Teste | 193 | 77 | 267.614 |
| Total | 2.163 | 861 | 2.277.416 |

O corpo limpo contém 8.474.762 bytes UTF-8. A contagem de tokens foi executada; não
foi estimada a partir de palavras ou bytes. O treino anterior tinha 49.499 tokens;
a nova contagem é cerca de 35,6 vezes maior, mas usa outro vocabulário. Essa razão
mede volume, não melhoria de capacidade ou comparabilidade de loss.

## Fontes e licenças

| Família | Material | Licença do texto | Tokens de treino | Participação |
|---|---|---|---:|---:|
| MDN | Prosa das páginas pt-BR de MDN translated-content | CC-BY-SA-2.5, mantida nos derivados | 913.776 | 51,91% |
| Python | Traduções não fuzzy da documentação 3.14 | PSF-2.0, conforme cabeçalhos e licença oficial | 814.895 | 46,29% |
| Ibict/Enap | Corpo do Guia do usuário do Omeka, 2018 | CC-BY-4.0 | 31.803 | 1,81% |

MDN: revisão d2f749e082684aacee7be1de1c0586471be19844.
Python pt-BR: revisão 39154eb93cabd5b11f2d528b508897ed9552a156.
Omeka: PDF SHA-256 33651a12f25521fbc4cffeaf373b872b842bb7db34736b5a8edbe47df9c76879.

Cada documento tem URL original, revisão, hash da fonte, hash do texto derivado,
atribuição, licença, descrição das alterações e grupo. As evidências de licença
estão em data/corpus-pt-v1/licenses, com hashes em provenance.json. O aviso CC0 da
infraestrutura do repositório Python foi preservado como evidência suplementar;
ele não substitui a licença PSF dos textos subjacentes. O código da Elysia não foi
relicenciado. A coleção mantém as licenças de cada família; não se apresenta todo
o corpus como MIT ou como material sem restrições.

Os originais públicos estão no cache separado e podem ser recuperados pelas
revisões/URL e hashes, sem depender deste computador. Imagens, código de exemplo
em blocos, biografias do livro e outros idiomas do dataset de diálogo não foram
republicados. O arquivo source-index.jsonl identifica fontes retidas e excluídas.

## Limpeza e separação

A extração de Markdown mantém prosa, rótulos de referências e termos curtos de
API. Remove blocos de código, imagens, HTML, navegação e parágrafos que dependem
de código inline substancial. A extração de PO usa somente traduções não fuzzy,
não obsoletas e não vazias, remove diretivas/blocos e preserva terminologia curta.
Históricos de versões e avisos de remoção foram excluídos. O PDF é extraído com
pdftotext; entram apenas páginas de corpo, sem créditos, referências, biografias,
legendas e imagens. Normaliza NFC, espaços e hifenização de quebra de linha.

O primeiro passe encontrou trechos em inglês e lacunas causadas pela remoção de
referências/termos. Isso foi corrigido antes de qualquer treino neural; os registros
estão em quality-corrections.json e nos manifestos de passes intermediários.
Não se preservou volume artificialmente mantendo material reconhecidamente ruim.

A triagem final removeu 2.641 parágrafos que não passaram na heurística de português,
423 parágrafos repetidos e dez parágrafos com padrões de identificadores. Essas
contagens são de unidades diferentes das exclusões por documento/entrada PO;
não devem ser somadas como número de documentos. Detectar zero padrões restantes
não prova ausência de todo dado pessoal. A checagem não substitui revisão integral
humana. O idioma da pasta pt-BR não garante uso exclusivamente brasileiro; foram
observadas construções de português europeu, registradas como limitação.

Grupos inteiros mantêm páginas de uma API, objeto JavaScript ou unidade Python
na mesma partição. Todo o livro Omeka é um único grupo de treino. A atribuição usa
hash fixo de grupo e seed; autores e fontes não são completamente separados entre
partições. A deduplicação cobre parágrafos exatos e uma heurística de documentos
próximos; não garante ausência de paráfrases ou sobreposição semântica.

## Tokenização própria, sem modelo pronto

BPE de vocabulário 2.048, treinado do zero somente nos textos de treino, com a
biblioteca Rust tokenizers 0.22.2 para acelerar o algoritmo. Não foi baixado um
vocabulário, tokenizador ou modelo pré-treinado. As regras foram exportadas para o
ByteBPETokenizer do projeto. Foram verificadas a aplicação das regras em 18 amostras
e a reconstrução exata do texto em TODOS os documentos. Testes adicionais verificam
que uma sequência frequente somente em dados reservados não entra no vocabulário.

Os armazenamentos tokens-*.bin são uint32 little-endian; os índices dão documento,
grupo e faixa de tokens. O carregador learning.prepared_corpus verifica hashes e
recusa partições reservadas quando for_training=True. Foi testado com make_batch
do Neural Core existente. Não recomputa splits.

O vocabulário novo não pode substituir o tokenizador dos checkpoints antigos:
eles têm outra dimensão/fingerprint. Um próximo treino deverá usar modelo e
checkpoint compatíveis. A preparação desta etapa não demonstra que isso já foi
feito. Não aponte o treinador legado diretamente para a pasta com todos os JSONL,
pois ele recalcularia divisões; consuma as partições auditadas pelo carregador.

## Diálogos, em trilha separada

Foram lidos 16 exemplos curtos de árvores distintas do TREINO histórico OASST1.
Seis ficaram como candidatos criativos; dez foram rejeitados ou ficaram pendentes,
com motivo individual. Entre os problemas: afirmações erradas sobre dentes de cães,
calorias sem quantidades, explicação incompleta de gramática e cronologia confusa.
Não se transferiu qualquer diálogo histórico de validação/teste para treino.

Os textos aceitos não foram reescritos nem multiplicados sinteticamente. O revisor
foi o Codex, não um humano independente. São exemplos já usados no piloto anterior,
não seis novas conversas humanas coletadas. Predominam tarefas criativas; esse
pequeno conjunto NÃO é um currículo de conversa ampla e não foi usado em treino
neural nesta etapa. Licença Apache 2.0, IDs de origem e log de decisões foram
preservados em data/corpus-pt-v1/dialogues.

## Avaliação nova, ainda não consumida

Os 24 casos em evaluation/portuguese-v1.json cobrem contexto, correção, explicação,
esclarecimento, incerteza, instruções, resumo, reescrita, comparação, aritmética,
extração, formato e planejamento. Foram escritos pelo Codex para AVALIAÇÃO, não
como diálogos humanos ou dados de treino. Critérios e escala 0/1/2 estão congelados;
nenhuma nota é concedida automaticamente por palavras-chave.

A coleta rejeita documentos com coincidência literal de prompts longos do novo
conjunto. O hash da especificação está no manifesto. Ainda foram executadas ZERO
avaliações neurais desse conjunto. O resultado histórico 0/8 não foi trocado por
este novo teste. Os resultados de todos os pilotos anteriores permanecem intactos.

## Validação e limites de prontidão

A auditoria verificou todos os hashes de textos e armazenamentos, índices contínuos,
atribuição/licença por documento e ausência de grupos ou parágrafos idênticos
atravessando partições. Os dados são reproduzíveis e o lote passou nos contratos de
integridade. A suíte passou com 119 testes e nove ignorados; dois novos testes do
carregador também passaram, totalizando 121 verificações aprovadas. Os skips se
referem a CUDA indisponível e artefatos históricos locais ausentes.

Os critérios de prontidão para linguagem ampla continuam reprovados: somente três
famílias de fonte, maior família com 51,91% dos tokens de treino, forte concentração
técnica e ausência de diálogos diversos revisados independentemente. O limite de
25% por família e quatro famílias é um critério de pesquisa deste plano, não uma
prova matemática de competência ou uma exigência de aprovação do usuário.

Próxima prioridade de dados: fontes não técnicas com direitos claros e diversidade
de autores, além de diálogos revisados com esclarecimento, correção e contexto.
Não resolver essa lacuna apenas repetindo documentos, fabricando milhares de
respostas ou aumentando parâmetros. Um piloto técnico limitado pode usar este
material, mas deve continuar distinguindo loss menor de conversa útil.

## Usar os artefatos e reproduzir

No ambiente Python 3.12 do Neural Core, com PyTorch CPU já instalado:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-corpus.txt
.\.venv\Scripts\python.exe -m learning.audit_portuguese_corpus
.\.venv\Scripts\python.exe -m pytest -q tests/test_portuguese_corpus.py
```

Em ambiente novo, crie .venv e instale primeiro requirements-first-words-cpu.txt,
depois requirements-corpus.txt. Para recuperar fontes, Git e acesso à internet são
necessários. Para refazer a extração do PDF, também é necessário pdftotext/Poppler.
Os artefatos já preparados podem ser auditados sem refazer downloads ou extração.

```powershell
.\.venv\Scripts\python.exe -m learning.fetch_corpus_sources --cache D:/ElysiaSourceCache/corpus-pt-v1
.\.venv\Scripts\python.exe -m learning.portuguese_corpus --cache D:/ElysiaSourceCache/corpus-pt-v1 --output scratch/corpus-pt-v1-reproduction
.\.venv\Scripts\python.exe -m learning.corpus_tokenizer --corpus scratch/corpus-pt-v1-reproduction
.\.venv\Scripts\python.exe -m learning.review_corpus_dialogues --output scratch/corpus-pt-v1-reproduction/dialogues
.\.venv\Scripts\python.exe -m learning.audit_portuguese_corpus --corpus scratch/corpus-pt-v1-reproduction --output scratch/corpus-pt-v1-reproduction-audit.json
```

Os comandos de reconstrução recusam sobrescrever fontes alteradas ou um lote já
existente. Versões das dependências, extrator PDF e hashes estão em provenance.json.
A recuperação Git esparsa foi exercitada com uma fonte local nova e o caminho de
cache existente foi conferido com as fontes reais. Os comandos PowerShell ainda
não foram executados no computador do proprietário; a validação foi em Linux.
.gitattributes fixa LF nos arquivos de dados para proteger hashes no Windows.

## Estado do projeto

Progresso geral e percentuais por módulo permanecem não avaliados; variação N/A.
O painel histórico em reports/first-words/README.md não foi reinterpretado como
medição atual. A mudança comprovada desta etapa é a base de dados e sua auditoria.
Não houve novo treino neural, mudança de competência demonstrada, voz, captura de
tela ou alteração em outros projetos. A instrução permanente de preservar cada
atualização no GitHub continua em AGENTS.md.
