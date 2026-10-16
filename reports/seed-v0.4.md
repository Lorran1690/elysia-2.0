# ELYSIA-Seed v0.4 — Fases 1 e 2

Status: proposta e piloto de arquitetura concluídos; corpus externo não baixado e pré-treinamento principal aguardando aprovação explícita.

Branch: `codex/elysia-seed-v0.4`, criada a partir de `8dedd83`.

## Fase 1 — consolidação da arquitetura

Foi adicionado o experimento A, `SwiGLU + SDPA` sem RoPE e sem RMSNorm. O experimento B compara essa configuração com SwiGLU isolado, SDPA isolado e a combinação completa da v0.3. Cada medição usou dois aquecimentos e duas repetições medianas; o benchmark é de tensores sintéticos, separado do piloto de corpus.

| Configuração | Parâmetros | Treino ms/etapa | Treino tok/s | Geração sem cache tok/s | Com cache tok/s | Pico VRAM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SwiGLU + SDPA | 3.486.032 | 16,27 | 7.865,2 | 117,3 | 131,9 | 84,0 MiB |
| SwiGLU | 3.486.032 | 32,50 | 3.938,8 | 60,2 | 41,2 | 84,0 MiB |
| SDPA | 3.483.640 | 31,07 | 4.120,1 | 119,6 | 80,1 | 83,9 MiB |
| RoPE + RMSNorm + SwiGLU + SDPA | 3.418.192 | 57,70 | 2.218,2 | 39,1 | 42,2 | 82,6 MiB |

Os números são específicos de tensores aleatórios, sequência 64 no treino e geração de 32 tokens na GTX 1650. Não são loss linguística nem prova de superioridade. O resultado favorece provisoriamente `SwiGLU + SDPA` por throughput e pelo pequeno ganho de cache neste teste.

### Cache além da janela

Foram comparadas gerações determinísticas com e sem cache para prompts de 7, 251 e 256 tokens, gerando 12 tokens em cada caso. As três configurações tiveram igualdade bit a bit nos três casos, inclusive quando a geração ultrapassou a janela de 256 tokens e o cache foi reconstruído pelo contexto recente.

### Piloto curto no corpus local

Foi executado apenas um piloto de 10 etapas com `SwiGLU + SDPA`, sobre o mesmo corpus local de demonstração já versionado na v0.3. Isto não é o pré-treinamento linguístico da v0.4.

- GPU: NVIDIA GeForce GTX 1650.
- Parâmetros: 3.485.519, pois o tokenizador piloto tem vocabulário 503.
- Tokens: 768 treino, 568 validação e 557 teste.
- Loss na etapa 1: treino `6,2934`, validação `6,1260`.
- Loss na etapa 10: treino `5,6225`, validação `5,6822`, teste `5,5565`.
- Tempo do piloto: `1,03 s`.
- Checkpoint: `learning/checkpoints/elysia-seed-v0.4-pilot.pt`, 39,9 MiB.
- Tokens/s e uso de recursos do benchmark sintético estão em `reports/seed-v0.4-architecture.json`.

O piloto confirma que a configuração treina e salva um checkpoint próprio; não mede generalização linguística significativa.

## Fase 2 — proposta de corpus

O critério jurídico usado aqui é conservador. A Lei brasileira de Direitos Autorais informa, no art. 41, a duração patrimonial de 70 anos contados de 1º de janeiro do ano seguinte ao falecimento do autor; cada obra e edição ainda precisa ser verificada. [Lei 9.610/1998](https://www.planalto.gov.br/ccivil_03/leis/l9610.htm)

### Candidata 1 — Project Gutenberg: Machado de Assis

Fonte: [Project Gutenberg](https://www.gutenberg.org/ebooks/search/?query=Machado+de+Assis&submit_search=Go%21). Obras candidatas: [Dom Casmurro](https://www.gutenberg.org/ebooks/55752), [Memórias Póstumas de Brás Cubas](https://www.gutenberg.org/ebooks/54829) e [Quincas Borba](https://www.gutenberg.org/ebooks/55682).

- Autor e obras: Machado de Assis, romances brasileiros do século XIX.
- Situação declarada: cada página declara “Public domain in the USA”.
- Condições: a política do [Project Gutenberg](https://www.gutenberg.org/policy/permission.html) explica que a maioria dos eBooks é domínio público nos EUA, mas exige confirmação independente fora dos EUA; a marca Project Gutenberg tem regras próprias. A cópia usada deverá conservar atribuição e aviso de origem.
- Tamanho estimado: 203 kB, 210 kB e 264 kB para os arquivos HTML indicados nas páginas; o texto limpo será menor e será medido após aprovação.
- Variante e qualidade: português brasileiro literário do Império, edição digital revisada; boa qualidade ortográfica histórica, baixa representatividade do Brasil contemporâneo.
- Riscos: duplicação com Wikisource, outras digitalizações e obras repetidas do mesmo autor; deduplicar por hash e assinatura aproximada.
- Justificativa: três obras brasileiras conhecidas, com autoria e páginas individuais rastreáveis. Candidata forte para uma camada histórica, condicionada à confirmação de uso no Brasil.

### Candidata 2 — Wikisource: textos brasileiros em domínio público

Fonte institucional: [Wikisource: Sobre](https://pt.wikisource.org/wiki/Wikisource:Sobre), [Autor: Machado de Assis](https://pt.wikisource.org/wiki/Machado_de_Assis), [Dom Casmurro](https://pt.wikisource.org/wiki/Dom_Casmurro) e [Memórias Póstumas de Brás Cubas](https://pt.wikisource.org/wiki/Mem%C3%B3rias_P%C3%B3stumas_de_Br%C3%A1s_Cubas).

- Autor e obras: páginas de autores e transcrições brasileiras, começando por Machado de Assis.
- Situação declarada: a página institucional informa que a Wikisource aceita obras em domínio público ou compatíveis com CC-BY-SA; a transcrição e a obra original podem ter camadas de direitos diferentes.
- Condições: preservar atribuição, histórico e licença da transcrição; revisar a página individual antes do uso e não presumir que toda edição digital seja livre para redistribuição sem condições.
- Tamanho estimado: variável por obra; medir somente após uma lista aprovada de páginas.
- Variante e qualidade: literatura brasileira histórica; qualidade depende da digitalização, OCR e revisão comunitária.
- Riscos: as mesmas obras podem aparecer no Gutenberg, duplicação de revisões e marcação wiki misturada ao texto.
- Justificativa: boa fonte complementar e metadados de edição, mas não substitui um corpus brasileiro contemporâneo.

### Candidata 3 — Corpus Histórico do Português Tycho Brahe

Fonte: [página do corpus](https://www.tycho.iel.unicamp.br/~tycho/corpus/), [catálogo](https://www.tycho.iel.unicamp.br/~tycho/corpus/catalogo.html) e [termos/créditos](https://www.tycho.iel.unicamp.br/~tycho/corpus/termos.html).

- Identificação: corpus anotado histórico, desenvolvido no IEL-UNICAMP/IME-USP, com textos portugueses históricos e ferramentas linguísticas.
- Período e variante: principalmente português histórico, descrito no site como textos escritos entre 1500 e 1900; não representa português brasileiro contemporâneo.
- Tamanho estimado: a descrição do site informa aproximadamente 2 milhões de palavras; confirmar a versão exata no manifesto antes de qualquer uso.
- Qualidade: alta utilidade acadêmica por ter anotação morfossintática, mas exige limpeza das anotações e preservação da estrutura.
- Direitos e condições: a página consultada oferece downloads e citação, mas não apresenta uma licença de treinamento/redistribuição suficientemente clara para este projeto. Portanto, fica bloqueado até confirmação escrita dos responsáveis.
- Riscos: mistura de períodos, autores, variantes e possíveis direitos sobre edição/anotação; grande risco de duplicação com acervos históricos.
- Justificativa: excelente candidato acadêmico para estudo histórico, não prioridade para um modelo brasileiro atual.

### Candidata 4 — textos originais autorizados

- Fonte: textos produzidos pela equipe do projeto ou cedidos por autores mediante autorização escrita específica.
- Direitos: a autorização deverá cobrir treinamento, armazenamento, avaliação, redistribuição do corpus ou apenas do modelo, conforme a escolha do autor.
- Tamanho e período: variável; priorizar português brasileiro contemporâneo, gêneros variados e metadados de autoria/registro.
- Qualidade: potencialmente a melhor adequação ao objetivo, se houver revisão e diversidade suficientes.
- Riscos: consentimento incompleto, identificação pessoal, duplicação e amostra pequena.
- Justificativa: é a única candidata já alinhada simultaneamente à variante brasileira atual e a uma cadeia de direitos controlável.

## Proposta para aprovação

1. Priorizar um núcleo contemporâneo de textos originais com autorização escrita.
2. Adicionar, como camada histórica separada, obras do Gutenberg e/ou Wikisource somente após verificação individual para uso no Brasil e redistribuição prevista.
3. Não usar Tycho Brahe até receber confirmação das condições de treinamento e redistribuição.
4. Manter cada obra como unidade de split, registrar URL, autor, edição, licença, data de consulta, hash e tamanho, e excluir textos cuja licença não cubra o uso planejado.

Até a aprovação, nenhum arquivo externo foi baixado e nenhum pré-treinamento longo foi iniciado. A coleta descrita abaixo ocorreu somente depois da aprovação explícita.

## Fase 3 — coleta autorizada e auditoria

Após a aprovação, foram baixados somente os três TXT aprovados pelas URLs diretas do Project Gutenberg. Os originais ficam em `data/corpus-v0.4/originals/` e as cópias limpas em `data/corpus-v0.4/clean/`; ambos os diretórios são ignorados pelo Git. O repositório recebeu somente o script, o manifesto e esta documentação. Nenhuma obra da Wikisource ou do Tycho Brahe foi incorporada.

### Proveniência e hashes

| Obra | URL | Original | SHA-256 original | Limpo | SHA-256 limpo |
| --- | --- | ---: | --- | ---: | --- |
| Dom Casmurro | `https://www.gutenberg.org/ebooks/55752` | 418.230 B | `0fc3dbf384544d81d87e5a731e67b7976ac3a57acb378f0f354d12a3b52bd0c7` | 389.167 B | `22119569360067b6eb907f227b18be52d3883561c05b9070012eaf047cf4ac59` |
| Memórias Póstumas de Brás Cubas | `https://www.gutenberg.org/ebooks/54829` | 403.243 B | `edfe4370698ed5716a9692b980a8d6ee77b4ff8116503bb2e08675f1d10d303a` | 374.427 B | `f91b052f708125757e73fdfcc90fc7b2dda9f76dd84b501ef1682d95c39bd9c0` |
| Quincas Borba | `https://www.gutenberg.org/ebooks/55682` | 492.850 B | `d23baeb1a449950e20a3257df0452b860578246eed2f1d5f8a8e62cede6669b9` | 461.932 B | `0476447eba5a37435d26a9090d8f467e3292c3109975f29574d3c92e6492c974` |

Total original: 1.314.323 bytes. Total limpo: 1.225.526 bytes, 1.202.406 caracteres e 209.472 palavras.

### Limpeza e direitos

Os três arquivos são UTF-8 e foram conferidos com decodificação estrita. O script `learning/prepare_corpus_v04.py` normaliza NFC, remove somente o cabeçalho anterior ao marcador `START OF THE PROJECT GUTENBERG EBOOK` e o rodapé posterior ao marcador `END OF THE PROJECT GUTENBERG EBOOK`, normaliza finais de linha e reduz linhas vazias consecutivas. Não foi detectada introdução moderna, tradução ou seção de tradutor nos primeiros 5.000 caracteres de nenhuma cópia limpa. As páginas individuais declaram as obras como public domain in the USA; a política do [Project Gutenberg](https://www.gutenberg.org/policy/permission.html) alerta que a situação fora dos EUA deve ser confirmada separadamente. A autorização desta coleta no Brasil foi fornecida pelo solicitante; atribuição, URLs, avisos e hashes permanecem no manifesto.

### Deduplicação, divisão e BPE

- 3 arquivos, 3 obras e 0 registros inválidos.
- Duplicação exata: 0; clusters aproximados: 3, um por obra.
- Split determinístico por obra, seed `2026`: Dom Casmurro em treino, Memórias Póstumas em validação e Quincas Borba em teste.
- Fingerprint do split: `7fca4ee72e780084b1a364cf80424e9d0d3a1cb2ad9cacc3c257c8002282e757`.
- BPE novo de 512 tokens, treinado exclusivamente em Dom Casmurro; fingerprint `d7b27519afcc8a19deb57691617e7a1478893bbf3d71768508a998ca48d887a8`.
- Tokens armazenados incrementalmente: 179.099 treino, 178.618 validação e 220.490 teste; total 578.207.
- Bytes por token: 2,1729 treino, 2,0962 validação e 2,0950 teste; média ponderada 2,1195.
- O BPE foi congelado antes de tokenizar validação e teste. Os token stores e o vocabulário ficam locais e ignorados pelo Git até nova verificação de redistribuição.

O manifesto completo está em `data/corpus-v0.4/audit-manifest.json`. O procedimento é reproduzível com `python -m learning.prepare_corpus_v04`; ele não baixa arquivos e não inicia treinamento.

### Proposta contemporânea futura

Ainda não foram baixadas fontes contemporâneas. A segunda proposta é:

1. **Textos originais autorizados pelo projeto:** coletar textos brasileiros contemporâneos encomendados ou cedidos por autores, com autorização escrita cobrindo treinamento, armazenamento, avaliação e a forma de distribuição do modelo. É a opção prioritária para conversação e variante brasileira.
2. **Dumps da Wikimedia em português:** [índice oficial de dumps](https://dumps.wikimedia.org/) e [Termos de Uso da Wikimedia](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use/pt-br). Podem fornecer material explicativo e informativo com atribuição/share-alike, mas misturam Brasil, Portugal e outros países, têm discussões e metadados, e exigem filtrar páginas, históricos e dados pessoais.
3. **Materiais educacionais e institucionais brasileiros com licença explícita:** selecionar portais ou autores que publiquem textos em CC BY ou CC BY-SA e cuja licença cubra reutilização e derivados. Cada item precisará ser verificado individualmente; a existência de uma licença no portal não autoriza automaticamente todo documento ali hospedado.
4. **Textos conversacionais próprios anonimizados:** criar diálogos escritos especificamente para o projeto por colaboradores identificados, com consentimento e remoção de nomes, contatos, identificadores e informações sensíveis. Não usar conversas reais de terceiros sem autorização específica.

A composição pretendida é variada: explicativos, informativos, conversacionais e narrativos, com metadados de gênero, data, autoria/licença e variante regional. Nenhuma dessas fontes será baixada sem nova aprovação. Cada fonte deverá apresentar URL, licença, consentimento quando aplicável, hash, deduplicação e auditoria de dados pessoais antes de qualquer download.

### Custo para o futuro treinamento

O corpus experimental tem 578.207 tokens BPE, mas é pequeno demais para um pré-treinamento linguístico relevante. O piloto anterior de 10 etapas usou cerca de 1,03 s na GTX 1650, mas esse número não estima uma época real deste corpus nem deve ser extrapolado sem um piloto com a nova divisão e tokenizador. O próximo passo computacional deve medir tokens/s, VRAM, RAM, espaço em disco, acumulação e frequência de checkpoint com o corpus aprovado antes de definir duração. Nenhum treinamento principal foi iniciado nesta etapa.
