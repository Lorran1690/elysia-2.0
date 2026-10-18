# ELYSIA-Seed v0.5 - Phase 2G expansion readiness

Date: 2026-10-18
Branch: `codex/elysia-seed-v0.5`
Approved base: `cabdb1010280df2f4ef24112841d790f9bee8311`

## Scope and stop point

Phase 2G is a research and planning artifact only. It preserves the historical Phase 2F audit and does not download a new corpus, extract text, tokenize, train BPE, create splits, run neural training, change weights or checkpoints, use Ollama, use an external model, modify v0.4, modify `feature/elysia-desktop-orb`, or modify `voice-command-life`.

The machine-readable source of truth is `data/corpus-v0.5/expansion-readiness-candidates.json`. It contains only metadata: official URL, author or institution, genre, language, license evidence, available format, volume basis, rights/privacy/duplication risks, language-quality assessment, ELYSIA utility, state, future scope, and `group_id` rule. It contains no corpus text, content hash, downloaded path, or derived dataset.

The catalog state has 22 specific sources: six candidates for a future bounded preflight, 13 pending item-level verification, and three deliberately rejected. A `candidate` is not collection approval.

## Source catalog

The catalog does not infer an article license from a portal. Wherever a portal or journal policy is the only evidence, the source remains pending until a later audit captures the selected item's own license, version, and third-party-content result.

| Source | Genre and language | License evidence | Planning volume | State |
| --- | --- | --- | --- | --- |
| [ELYSIA original everyday dialogues](https://github.com/Lorran1690/elysia-2.0) | Human-authored everyday dialogue, pt-BR | License not yet assigned; future signed contribution record required | 40k-180k tokens | Pending |
| [ELYSIA original support and explanations](https://github.com/Lorran1690/elysia-2.0) | Human-authored support and instructional prose, pt-BR | License not yet assigned; future signed contribution record required | 80k-350k | Pending |
| [IBICT/ENAP Omeka guide](https://repositorio.enap.gov.br/bitstream/1/3162/1/Guia%20do%20usu%C3%A1rio%20do%20Omeka%20-%20Ebook.pdf) | Technical educational guide, pt-BR | Reported CC BY 4.0 on the official item | 35k-70k | Candidate |
| [SGB OGC API](https://geoservicos.sgb.gov.br/ogcapi?f=html) | Technical service documentation, pt-BR | CC BY 4.0 notice on the official service | 50k-180k | Candidate |
| [Padrao Digital de Governo guides](https://www.gov.br/ds/guias/wai-aria) | Accessibility and service-writing guides, pt-BR | [CC0/MIT policy](https://www.gov.br/ds/downloads/legislacao); scope must be verified per artifact | 20k-80k | Candidate |
| [GitHub Docs Portuguese](https://docs.github.com/pt) | Technical docs, FAQ, and troubleshooting | [CC BY 4.0 documentation license](https://github.com/github/docs/blob/main/LICENSE); code/assets excluded | 100k-400k | Candidate |
| [Python docs pt-BR](https://docs.python.org/pt-br/3/) | Programming tutorial and FAQ, pt-BR | [PSF License Version 2](https://docs.python.org/pt-br/3/license.html); examples classified separately | 80k-300k | Candidate |
| [Microsoft Learn Edge pt-BR](https://learn.microsoft.com/pt-br/microsoft-edge/devtools/css/) | Developer instructions and support, pt-BR | Page-level [CC BY 4.0 notice](https://learn.microsoft.com/pt-br/microsoft-edge/devtools/css/) | 60k-220k | Candidate |
| [Android Developers pt-BR](https://developer.android.com/?hl=pt-br) | Technical documentation, pt-BR | [Mixed source terms](https://developer.android.com/license); page-level classification required | 75k-350k | Pending |
| [MDN Web Docs pt-BR](https://developer.mozilla.org/pt-BR/docs/Web) | Web tutorials and reference, pt-BR | [CC BY-SA guidance](https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Attrib_copyright_license); code handled separately | 120k-600k | Pending |
| [FastAPI Portuguese docs](https://fastapi.tiangolo.com/pt/) | Programming documentation | Official page discloses AI and human translation | 120k-450k | Rejected |
| [Mozilla Support pt-BR](https://support.mozilla.org/pt-BR/) | User support and FAQ, pt-BR | Official source known, but exact reuse license and translation provenance unresolved | 100k-500k | Pending |
| [LibreOffice Help pt-BR](https://help.libreoffice.org/latest/pt-BR/) | Office help and procedures, pt-BR | Official source known, but documentation-license scope unresolved | 300k-2M | Pending |
| [Mozilla Common Voice Portuguese text](https://commonvoice.mozilla.org/pt/datasets) | Short prompted sentences and metadata | [CC0 contribution policy](https://commonvoice.mozilla.org/pt/guidelines) must be checked by exact release and locale | 500k-5M | Pending |
| [SciELO RAP](https://www.scielo.br/j/rap/) | Public-administration research, pt-BR | [SciELO open-access policy](https://www.scielo.org/pt-br/sobre-o-scielo/declaracao-de-acesso-aberto/) is discovery context only; verify each article | 250k-1.5M | Pending |
| [SciELO RBEP](https://www.scielo.br/j/rbeped/) | Educational research, pt-BR | [SciELO open-access policy](https://www.scielo.org/pt-br/sobre-o-scielo/declaracao-de-acesso-aberto/) is discovery context only; verify each article | 250k-1.2M | Pending |
| [SciELO RESS](https://www.scielo.br/j/ress/) | Public-health information, pt-BR | [Journal CC BY 4.0 policy](https://www.scielo.br/journal/ress/about/?ilang=pt_BR), then verify article, table, and figure rights | 180k-800k | Pending |
| [Em Aberto](https://emaberto.inep.gov.br/ojs3/index.php/emaberto) | Educational-policy articles, pt-BR | [Journal policy](https://emaberto.inep.gov.br/ojs3/index.php/emaberto/about/submissions) needs article-level confirmation | 300k-2M | Pending |
| [eduCAPES: licencas e ciencia da informacao](https://educapes.capes.gov.br/handle/capes/1140501?mode=full) | Open-science article, pt-BR | CC BY 4.0 metadata only; canonical file is unresolved | 6k-18k | Pending |
| [eduCAPES: ciencia aberta no CNPq](https://educapes.capes.gov.br/handle/capes/1023510?mode=full) | Institutional open-science article, pt-BR | CC BY 4.0 metadata only; canonical file is unresolved | 4.5k-15k | Pending |
| [Portuguese Wikipedia](https://pt.wikipedia.org/wiki/Wikip%C3%A9dia:P%C3%A1gina_principal) | Collaborative encyclopedia, mixed Portuguese variants | [CC BY-SA and historical GFDL obligations](https://pt.wikipedia.org/wiki/Wikip%C3%A9dia:Direitos_de_autor) | 50M-2B | Rejected |
| [eMAG 3.1 historical record](https://emag.governoeletronico.gov.br/) | Accessibility technical guidance, pt-BR | CC BY 4.0 was audited in the preserved history | 37.5k-75k | Rejected for new acquisition |

Expected volume is a planning range, not a measured token count. It was derived from page or document counts, stated editions, and bounded future scopes. The JSON catalog records the source-specific calculation basis, risk notes, expected quality, and ELYSIA value for every row.

## Original conversational-data protocol

The project should keep two future data tracks separate:

| Track | Purpose | Unit and exclusions |
| --- | --- | --- |
| Linguistic pretraining | Build broad exposure to licensed Brazilian Portuguese prose and reviewed original instructional texts. | One document or section with author, license, source version, provenance, and `group_id`. Excludes private conversations, unconsented personal stories, unverified translations, model-generated text, and unreviewed support logs. |
| Conversational tuning | Teach response behavior only after a separate authorization. | A human-authored, multi-turn scenario record with intent, difficulty, roles, reviewer, factual-source notes, safety notes, provenance, and `group_id`. Excludes automatically generated dialogues, Ollama/API output, private messages, and unlicensed tickets. |

Any future original dialogue program must be human authored and reviewed. It must deliberately cover everyday conversations; questions and answers; simple, intermediate, and advanced explanations; step-by-step instructions; multi-turn exchange; ambiguous requests; correction of errors; admission of uncertainty; local-tool interactions; and technical support. Contributors need an explicit license and consent record outside the training text. Personal data must be redacted before a derived file exists. The project must not automatically manufacture a large synthetic dialogue set.

## Scale planning

The following is a capacity-planning range only. It does not tokenize current material or start a tokenizer.

| Scenario | Clean UTF-8 planning volume | Expected documents | Source families | Human cleaning and audit | Main duplication risks |
| --- | --- | --- | --- | --- | --- |
| Initial 5M tokens | 20-27.5 MB | 1,200-5,000 | 7-12 | 80-200 hours | Mirrors, localization variants, templates, API-generated fragments, citations |
| Expanded 20M tokens | 80-110 MB | 4,800-20,000 | 12-20 | 280-700 hours | Scaled repeats, author self-reuse, translations, syndicated pages, copied or synthetic support text |

No family should exceed 25 percent of a future corpus. Author, journal, website-template, and translation concentration must be measured before any training decision.

The frozen v0.4 architecture is small and its historical corpus was very limited. Five or 20 million tokens can support narrow experiments, but cannot by themselves demonstrate general language competence, dependable instruction following, factual grounding, tool reliability, reasoning, or natural conversation. A conversational assistant also needs a separate, carefully authored and evaluated behavior dataset. More volume is not a substitute for provenance, diversity, evaluation, and safety controls.

## Proposed batch-ingestion architecture

Only an explicitly approved source list can enter a future batch. An unlisted URL, mirror, attachment, or source substitution is rejected before download.

1. Create a versioned batch manifest containing `batch_id`, `source_id`, `document_id`, `group_id`, canonical URL, retrieval time, source version, author or institution, license, attribution, approval record, original SHA-256, derived SHA-256, and state.
2. Preserve the original immutably, calculate SHA-256, then create separate UTF-8 and NFC derivatives.
3. Run personal-data scanning, exact and near-duplicate checks, third-party quotation review, and cleaning-artifact detection before an individual acceptance decision.
4. Emit an audit report per document and per batch. States are: proposed, approved for preflight, preflight passed, original preserved, extracted, cleaned, audited, accepted for future split, or rejected.
5. Assign `group_id` before any future split. Every version, translation, mirror, author-related revision, and derived document of one underlying work stays in the same group. No group may cross a future training, validation, or test boundary.

No split has been created in Phase 2G. A future split proposal must follow source approval and `group_id` assignment, and must keep final test groups untouched until one final evaluation.

## Recommended first authorization lot

This is a recommendation for a future explicit collection authorization only. Collection has not started. The four named sources below cannot be replaced by other sources without a new approval.

### 1. IBICT/ENAP Omeka guide

- Justification: one named technical guide, identifiable edition, and reported CC BY 4.0 notice.
- Evidence: [official item](https://repositorio.enap.gov.br/bitstream/1/3162/1/Guia%20do%20usu%C3%A1rio%20do%20Omeka%20-%20Ebook.pdf).
- Expected volume: 35k-70k tokens.
- Risks: PDF extraction, screenshots, citations, product references, and third-party examples.
- Accept only when the named official edition is available, the CC BY 4.0 notice is retained, the text layer is usable, third-party assets can be excluded or documented, and no unresolved personal data remains.
- Reject when the official item is unavailable, the notice is missing or incompatible, protected material cannot be separated, or extraction is materially corrupt.

### 2. SGB OGC API documentation

- Justification: technical instructions with an official CC BY 4.0 notice and a naturally bounded endpoint list.
- Evidence: [official service](https://geoservicos.sgb.gov.br/ogcapi?f=html).
- Expected volume: 50k-180k tokens.
- Risks: repeated schema text, external standards, and map/data attributions.
- Accept only with a finite approved endpoint list, page-level provenance, measurable duplicate filtering, and exclusion of external standards and visual assets.
- Reject when scope expands, the notice is absent, near-duplicate rate prevents useful prose recovery, or required text depends on unlicensed external material.

### 3. GitHub Docs Portuguese

- Justification: edited help and troubleshooting language from source-controlled documentation.
- Evidence: [official documentation license](https://github.com/github/docs/blob/main/LICENSE).
- Expected volume: 100k-400k tokens.
- Risks: code, product marks, reusable fragments, locale/source mismatch, and localized duplicates.
- Accept only when every approved page maps to a CC BY 4.0 documentation source, code and branded assets are separated, language variant is recorded, and all versions are grouped.
- Reject when page-to-source or license mapping is missing, content is user generated, code/assets cannot be separated, or locale provenance is unclear.

### 4. Python documentation pt-BR

- Justification: bounded tutorial and FAQ pages add step-by-step programming explanations in Portuguese (Brazil).
- Evidence: [official pt-BR license page](https://docs.python.org/pt-br/3/license.html).
- Expected volume: 80k-300k tokens.
- Risks: version overlap, prose/code distinctions, upstream quotations, and incomplete localization.
- Accept only for named pt-BR tutorial and FAQ pages with retained PSF notice, separated code, assigned version/translation groups, and no unapproved external traversal.
- Reject when license scope is incompatible, the page is not pt-BR, translation/version provenance is unclear, or generated index text dominates.

The four-source lot is intentionally small. It provides a controlled test of provenance, extraction, normalization, attribution, and deduplication before the project considers larger or more sensitive material.

## Validation and stop point

`learning/v05_expansion_readiness.py` validates all Phase 2G gates: exact base commit, metadata-only catalog, 15-25 source limit, candidate-status licensing, no collection/tokenization/training, the ten conversational scenario families, 5M and 20M planning targets, required ingestion controls, `group_id`, and the non-substitutable first lot. `tests/test_v05_expansion_readiness.py` adds regression coverage for those gates.

The local Windows environment does not currently expose a usable Python interpreter through `python`, so focused pytest and the validator could not run locally. The repository CI installs Python 3.12 and will be the complete test verification after publication. Static repository checks and JSON parsing were run separately before commit.

Phase 2G stops here. No source is authorized for collection, no tokenizer or split exists, and no neural training may begin without explicit user approval.
