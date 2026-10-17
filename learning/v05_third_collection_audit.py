"""Build and validate the Phase 2D controlled collection audit.

This module is intentionally local-only. It never makes network requests. The
two authorized SciELO HTML files and their response snapshots must already be
present locally before this module is run. It preserves the Phase 2C manifest
and its derivatives, creates revised ConCI derivatives only when the audit
requires them, and records metadata without placing corpus text in Git.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from itertools import combinations
from pathlib import Path
from typing import Any

from learning.v05_collection_audit import (
    ALLOWED_LOCAL_PREFIXES,
    CollectionAuditError,
    TextBlock,
    _ascii_key,
    _deduplicate_consecutive_blocks,
    _estimate_tokens,
    _find_forbidden_content_fields,
    _invalid_control_characters,
    _is_read_only,
    _sha256_path,
    _text_stats,
    _write_json,
    render_blocks,
)
from learning.v05_second_collection_audit import (
    CONCI_DOCUMENT_ID,
    _decode_conci_html,
    _parse_conci_html,
    validate_phase2c_audit,
    validate_phase2c_local_artifacts,
)


SCHEMA_VERSION = 3
PHASE = "conci-consolidation-and-controlled-scielo-expansion"
PHASE2C_AUDIT_PATH = "data/corpus-v0.5/collection-audit.phase-2c.json"
CURRENT_AUDIT_PATH = "data/corpus-v0.5/collection-audit.json"
EMAG_DOCUMENT_ID = "emag-v3-1-html"
CONCI_DOCUMENT_ID = "conci-2021-alternative-licenses-html"
ARTICLE_A_ID = "scielo-rbeped-affectivity-2024"
ARTICLE_B_ID = "scielo-rbeped-triangles-2024"
ARTICLE_C_ID = "scielo-rap-redistribution-2024"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"


@dataclass(frozen=True)
class ArticleSpec:
    """The narrow metadata and local paths for one approved HTML collection."""

    identifier: str
    title: str
    authors: tuple[str, ...]
    institutions: tuple[str, ...]
    publication: str
    edition: str
    doi: str
    canonical_url: str
    original_path: str
    headers_path: str
    extracted_path: str
    clean_path: str


ARTICLE_A = ArticleSpec(
    identifier=ARTICLE_A_ID,
    title="A ideia de afetividade na filosofia e na educa\u00e7\u00e3o",
    authors=("Agostinho Morosini", "Maria Judith Sucupira da Costa Lins"),
    institutions=("Universidade Federal do Rio de Janeiro (UFRJ)",),
    publication="Revista Brasileira de Estudos Pedag\u00f3gicos",
    edition="v. 105, 2024",
    doi="10.24109/2176-6681.rbep.105.5844",
    canonical_url="https://www.scielo.br/j/rbeped/a/Yvgc3v3QyLL3nKYNSQvfkqy/?format=html&lang=pt",
    original_path="data/corpus-v0.5/originals/scielo-rbeped-affectivity-2024.html",
    headers_path="data/corpus-v0.5/originals/scielo-rbeped-affectivity-2024.headers.txt",
    extracted_path="data/corpus-v0.5/processed/scielo-rbeped-affectivity-2024.extracted.txt",
    clean_path="data/corpus-v0.5/clean/scielo-rbeped-affectivity-2024.clean.txt",
)

ARTICLE_C = ArticleSpec(
    identifier=ARTICLE_C_ID,
    title=(
        "An\u00e1lise do efeito redistributivo das transfer\u00eancias intergovernamentais "
        "sobre as receitas municipais no semi\u00e1rido brasileiro"
    ),
    authors=(
        "Luis Alberto da Costa",
        "Napi\u00ea Galv\u00ea Ara\u00fajo Silva",
        "Vilmar Antonio Gon\u00e7alves Tondolo",
        "Lauro Nogueira",
    ),
    institutions=(
        "Universidade Federal Rural do Semi\u00e1rido (UFERSA)",
        "Universidade Federal de Pelotas (UFPel)",
        "Universidade do Estado do Rio Grande do Norte (UERN)",
    ),
    publication="Revista de Administra\u00e7\u00e3o P\u00fablica",
    edition="v. 58, n. 5, 2024",
    doi="10.1590/0034-761220240010",
    canonical_url="https://www.scielo.br/j/rap/a/QpnmPNnQ8WmK8ckGFGgBv7w/?format=html&lang=pt",
    original_path="data/corpus-v0.5/originals/scielo-rap-redistribution-2024.html",
    headers_path="data/corpus-v0.5/originals/scielo-rap-redistribution-2024.headers.txt",
    extracted_path="data/corpus-v0.5/processed/scielo-rap-redistribution-2024.extracted.txt",
    clean_path="data/corpus-v0.5/clean/scielo-rap-redistribution-2024.clean.txt",
)

CONCI_REVISED_EXTRACTED = "data/corpus-v0.5/processed/conci-2021-licenses.phase-2d.extracted.txt"
CONCI_REVISED_CLEAN = "data/corpus-v0.5/clean/conci-2021-licenses.phase-2d.clean.txt"


@dataclass(frozen=True)
class ParsedSciELO:
    """The article body projected from the official SciELO HTML."""

    blocks: list[TextBlock]
    paragraphs: int
    table_rows: int
    blockquotes: int
    image_elements: int


class _SciELOArticleParser(HTMLParser):
    """Extract structural blocks only from article#articleText."""

    _VOID_TAGS = frozenset(
        {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    )
    _SKIP_TAGS = frozenset({"script", "style", "noscript"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[TextBlock] = []
        self.paragraphs = 0
        self.table_rows = 0
        self.blockquotes = 0
        self.image_elements = 0
        self._stack: list[str] = []
        self._article_depth: int | None = None
        self._skip_depth: int | None = None
        self._table_depth = 0
        self._active_tag: str | None = None
        self._active_kind: str | None = None
        self._active_level: int | None = None
        self._parts: list[str] = []

    @property
    def _inside_article(self) -> bool:
        return self._article_depth is not None

    def _flush(self) -> None:
        if self._active_kind is None:
            return
        text = unicodedata.normalize("NFC", "".join(self._parts)).replace("\u00a0", " ")
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            self.blocks.append(TextBlock(kind=self._active_kind, text=text, level=self._active_level))
        self._active_tag = None
        self._active_kind = None
        self._active_level = None
        self._parts = []

    def _begin(self, tag: str, kind: str, level: int | None = None) -> None:
        self._flush()
        self._active_tag = tag
        self._active_kind = kind
        self._active_level = level
        self._parts = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.casefold()
        attributes = {name.casefold(): value or "" for name, value in attrs}
        is_void = normalized in self._VOID_TAGS
        if not is_void:
            self._stack.append(normalized)
        depth = len(self._stack)

        if normalized == "article" and attributes.get("id", "").casefold() == "articletext":
            self._article_depth = depth
            return
        if not self._inside_article:
            return
        if self._skip_depth is not None:
            return
        if normalized in self._SKIP_TAGS:
            if not is_void:
                self._skip_depth = depth
            return
        if normalized == "img":
            self.image_elements += 1
            return
        if normalized == "table":
            self._table_depth += 1
            return
        if normalized == "blockquote":
            self._begin(normalized, "quote")
            self.blockquotes += 1
            return
        if normalized == "figcaption":
            self._begin(normalized, "figure_caption")
            return
        if normalized == "tr" and self._table_depth:
            self._begin(normalized, "table_row")
            self.table_rows += 1
            return
        if normalized in {"td", "th"} and self._active_kind == "table_row" and self._parts:
            self._parts.append(" | ")
            return
        if normalized == "p" and self._table_depth == 0 and self._active_kind != "quote":
            self._begin(normalized, "paragraph")
            self.paragraphs += 1
            return
        if normalized == "li" and self._table_depth == 0 and self._active_kind != "quote":
            self._begin(normalized, "list_item")
            return
        if normalized.startswith("h") and len(normalized) == 2 and normalized[1].isdigit() and self._table_depth == 0:
            self._begin(normalized, "heading", int(normalized[1]))
            return
        if normalized == "br" and self._active_kind is not None:
            self._parts.append(" ")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.casefold() not in self._VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._inside_article and self._skip_depth is None and self._active_kind is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        if normalized in self._VOID_TAGS or not self._stack:
            return
        if self._stack[-1] != normalized:
            return
        depth = len(self._stack)
        if self._inside_article:
            if self._skip_depth == depth:
                self._skip_depth = None
            elif self._active_tag == normalized:
                self._flush()
            if normalized == "table" and self._table_depth:
                self._table_depth -= 1
            if normalized == "article" and depth == self._article_depth:
                self._flush()
                self._article_depth = None
        self._stack.pop()


def _path(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else root / candidate


def _local_path(root: Path, path: Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise CollectionAuditError(f"Artefato fora do repositorio: {path}") from error
    result = relative.as_posix()
    if not result.startswith(ALLOWED_LOCAL_PREFIXES):
        raise CollectionAuditError(f"Artefato fora dos diretorios locais autorizados: {result}")
    return result


def _artifact_record(root: Path, path: Path, role: str, *, immutable: bool, format_name: str) -> dict[str, Any]:
    if not path.exists():
        raise CollectionAuditError(f"Artefato local ausente: {path}")
    return {
        "role": role,
        "local_path": _local_path(root, path),
        "git_ignored": True,
        "format": format_name,
        "bytes": path.stat().st_size,
        "sha256": _sha256_path(path),
        "immutable": immutable,
    }


def _parse_response_snapshot(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip().casefold()] = value.strip()
    if values.get("status") != "200":
        raise CollectionAuditError("A resposta preservada precisa registrar status HTTP 200")
    content_type = values.get("content-type", "").casefold()
    if not content_type.startswith("text/html") or "utf-8" not in content_type:
        raise CollectionAuditError("A resposta preservada precisa registrar HTML em UTF-8")
    if not values.get("requested-url") or not values.get("final-url"):
        raise CollectionAuditError("A resposta preservada precisa registrar URL solicitada e final")
    return values


def _parse_scielo_html(html_text: str) -> ParsedSciELO:
    parser = _SciELOArticleParser()
    parser.feed(html_text)
    parser.close()
    if parser._article_depth is not None or parser.paragraphs < 10:
        raise CollectionAuditError("O HTML SciELO nao contem a estrutura de artigo esperada")
    if not any(block.kind == "heading" for block in parser.blocks):
        raise CollectionAuditError("O HTML SciELO nao contem secoes textuais")
    return ParsedSciELO(
        blocks=parser.blocks,
        paragraphs=parser.paragraphs,
        table_rows=parser.table_rows,
        blockquotes=parser.blockquotes,
        image_elements=parser.image_elements,
    )


def _assert_scielo_identity(html_text: str, spec: ArticleSpec) -> None:
    visible_text = _ascii_key(unescape(re.sub(r"<[^>]+>", " ", html_text)))
    required = (_ascii_key(spec.title), *(_ascii_key(author) for author in spec.authors), spec.doi.casefold())
    if any(fragment not in visible_text for fragment in required):
        raise CollectionAuditError(f"O HTML nao confirma titulo, autores e DOI autorizados para {spec.identifier}")
    if LICENSE_URL not in html_text:
        raise CollectionAuditError(f"O HTML nao confirma CC BY 4.0 individualmente para {spec.identifier}")


def _article_preamble(spec: ArticleSpec) -> str:
    return "\n\n".join(
        (
            f"# {spec.title}",
            f"Autores: {', '.join(spec.authors)}",
            f"Publicacao: {spec.publication}, {spec.edition}",
            f"DOI: {spec.doi}",
            "Licenca: CC BY 4.0",
            f"Fonte oficial: {spec.canonical_url}",
        )
    )


def _is_body_start(block: TextBlock) -> bool:
    if block.kind != "heading":
        return False
    key = _ascii_key(block.text)
    return bool(re.match(r"^(?:\d+(?:\.\d+)*\.?\s+)?introducao\b", key))


def _is_references_heading(block: TextBlock) -> bool:
    return block.kind == "heading" and _ascii_key(block.text).startswith("referencias")


def _is_foreign_abstract_heading(block: TextBlock) -> bool:
    return block.kind == "heading" and _ascii_key(block.text).rstrip(":") in {"abstract", "resumen"}


def _is_portuguese_abstract_heading(block: TextBlock) -> bool:
    return block.kind == "heading" and _ascii_key(block.text).rstrip(":") == "resumo"


def _is_figure_caption(block: TextBlock) -> bool:
    key = _ascii_key(block.text)
    return block.kind == "figure_caption" or (
        block.kind in {"heading", "paragraph"} and bool(re.match(r"^(figura|grafico|quadro)\s+\d", key))
    )


_ELLIPSIS_QUOTE = re.compile(
    r"[\"\u201c]\s*\[\.\.\.\].*?[\"\u201d](?:\s*\([^)]*(?:19|20)\d{2}[^)]*\))?",
    flags=re.DOTALL,
)


def _redact_ellipsis_quotes(text: str) -> tuple[str, int]:
    redacted, count = _ELLIPSIS_QUOTE.subn("[citacao direta de terceiro removida]", text)
    return re.sub(r"\s+", " ", redacted).strip(), count


def _clean_scielo_blocks(blocks: list[TextBlock]) -> tuple[list[TextBlock], dict[str, int]]:
    """Keep the Portuguese article and remove third-party or portal material."""

    cleaned: list[TextBlock] = []
    counters = Counter(
        {
            "front_matter_blocks_removed": 0,
            "foreign_abstract_blocks_removed": 0,
            "references_blocks_removed": 0,
            "figure_caption_blocks_removed": 0,
            "direct_quote_blocks_redacted": 0,
            "inline_direct_quote_spans_redacted": 0,
        }
    )
    stage = "front_matter"
    for index, block in enumerate(blocks):
        if stage == "front_matter":
            if _is_portuguese_abstract_heading(block):
                stage = "portuguese_abstract"
                cleaned.append(block)
            else:
                counters["front_matter_blocks_removed"] += 1
            continue
        if stage == "portuguese_abstract":
            if _is_foreign_abstract_heading(block):
                stage = "foreign_abstract"
                counters["foreign_abstract_blocks_removed"] += 1
            elif _is_body_start(block):
                stage = "article"
                cleaned.append(block)
            else:
                cleaned.append(block)
            continue
        if stage == "foreign_abstract":
            if _is_body_start(block):
                stage = "article"
                cleaned.append(block)
            else:
                counters["foreign_abstract_blocks_removed"] += 1
            continue
        if _is_references_heading(block):
            counters["references_blocks_removed"] += len(blocks) - index
            break
        if _is_figure_caption(block):
            counters["figure_caption_blocks_removed"] += 1
            continue
        if block.kind == "quote":
            cleaned.append(TextBlock(kind="paragraph", text="[citacao direta de terceiro removida]"))
            counters["direct_quote_blocks_redacted"] += 1
            continue
        if block.kind == "paragraph":
            text, redactions = _redact_ellipsis_quotes(block.text)
            counters["inline_direct_quote_spans_redacted"] += redactions
            cleaned.append(TextBlock(kind=block.kind, text=text, level=block.level))
            continue
        cleaned.append(block)
    if stage != "article":
        raise CollectionAuditError("Nao foi possivel localizar o corpo em portugues do artigo SciELO")
    if not cleaned or not any(_is_body_start(block) for block in cleaned):
        raise CollectionAuditError("A limpeza SciELO nao preservou a introducao")
    deduplicated, consecutive = _deduplicate_consecutive_blocks(cleaned)
    counters["consecutive_blocks_removed"] = consecutive
    return deduplicated, dict(counters)


def _personal_data_counts(text: str) -> dict[str, int]:
    phone = r"(?<!\d)(?:\+55\s*)?(?:\(\d{2}\)\s*|\d{2}\s+)\d{4,5}-\d{4}(?!\d)"
    return {
        "email_matches": len(re.findall(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", text)),
        "cpf_matches": len(re.findall(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", text)),
        "phone_matches": len(re.findall(phone, text)),
    }


def _sample_headings(blocks: list[TextBlock]) -> dict[str, str]:
    headings = [block.text for block in blocks if block.kind == "heading"]
    if len(headings) < 3:
        raise CollectionAuditError("O texto limpo precisa conter ao menos tres secoes para amostragem")
    return {"start": headings[0], "middle": headings[len(headings) // 2], "end": headings[-1]}


def _make_scielo_document(root: Path, spec: ArticleSpec) -> tuple[dict[str, Any], str]:
    original_path = _path(root, spec.original_path)
    headers_path = _path(root, spec.headers_path)
    extracted_path = _path(root, spec.extracted_path)
    clean_path = _path(root, spec.clean_path)
    if not _is_read_only(original_path):
        raise CollectionAuditError(f"O HTML original de {spec.identifier} precisa permanecer somente leitura")
    headers = _parse_response_snapshot(headers_path)
    original_bytes = original_path.read_bytes()
    try:
        html_text = original_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CollectionAuditError(f"O HTML de {spec.identifier} nao e UTF-8 valido") from error
    _assert_scielo_identity(html_text, spec)
    parsed = _parse_scielo_html(html_text)
    clean_blocks, cleaning = _clean_scielo_blocks(parsed.blocks)

    extracted_text = unicodedata.normalize("NFC", _article_preamble(spec) + "\n\n" + render_blocks(parsed.blocks))
    clean_text = unicodedata.normalize("NFC", _article_preamble(spec) + "\n\n" + render_blocks(clean_blocks))
    for path, text in ((extracted_path, extracted_text), (clean_path, clean_text)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    clean_personal = _personal_data_counts(clean_text)
    if any(clean_personal.values()):
        raise CollectionAuditError(f"A versao limpa de {spec.identifier} reteve dados pessoais detectados")

    original_artifact = _artifact_record(root, original_path, "original_html", immutable=True, format_name="text/html; charset=UTF-8")
    headers_artifact = _artifact_record(root, headers_path, "response_headers", immutable=False, format_name="text/plain; HTTP response snapshot")
    extracted_artifact = _artifact_record(root, extracted_path, "extracted_text", immutable=False, format_name="text/plain; charset=UTF-8")
    clean_artifact = _artifact_record(root, clean_path, "clean_text", immutable=False, format_name="text/plain; charset=UTF-8")
    clean_stats = _text_stats(clean_text)
    extracted_stats = _text_stats(extracted_text)
    source_personal = _personal_data_counts(html_text)

    document = {
        "id": spec.identifier,
        "states": {
            "candidate": True,
            "collection_authorized": True,
            "collected": True,
            "audited": True,
            "approved_for_future_inclusion": False,
            "rejected": False,
            "current_state": "audited",
        },
        "identity": {
            "title": spec.title,
            "authors": list(spec.authors),
            "institutions": list(spec.institutions),
            "publication": spec.publication,
            "edition": spec.edition,
            "doi": spec.doi,
        },
        "source": {
            "canonical_page_url": spec.canonical_url,
            "requested_url": headers["requested-url"],
            "final_url": headers["final-url"],
            "host": "www.scielo.br",
            "preflight_checked_at": headers["collected-at"],
            "collected_at": headers["collected-at"],
            "http_status": 200,
            "redirect_detected": headers["requested-url"] != headers["final-url"],
            "content_type": headers["content-type"],
            "http_date": headers.get("date"),
            "relevant_headers_artifact": headers_artifact["local_path"],
            "selected_representation": "HTML",
            "other_representations_downloaded": False,
        },
        "license": {
            "name": "CC BY 4.0",
            "evidence_url": spec.canonical_url,
            "evidence_in_original_html": LICENSE_URL,
            "attribution_obligations": (
                "Creditar autores, publicacao inicial, URL da fonte e CC BY 4.0; "
                "incluir o link da licenca e indicar as alteracoes nos derivados."
            ),
        },
        "local_artifacts": [original_artifact, headers_artifact, extracted_artifact, clean_artifact],
        "quality": {
            "original_html": {
                "bytes": original_artifact["bytes"],
                "sha256": original_artifact["sha256"],
                "utf8_valid": True,
                "http_declared_content_type": headers["content-type"],
            },
            "normalization": "Unicode NFC",
            "extracted_text_statistics": extracted_stats,
            "clean_text_statistics": clean_stats,
            "paragraphs_extracted": parsed.paragraphs,
            "table_rows_extracted": parsed.table_rows,
            "blockquotes_extracted": parsed.blockquotes,
            "image_elements_omitted": parsed.image_elements,
            "sections_extracted": len([block for block in clean_blocks if block.kind == "heading"]),
            "sampled_sections": _sample_headings(clean_blocks),
            "invalid_control_characters": _invalid_control_characters(clean_text),
            "replacement_character_count": clean_text.count("\ufffd"),
            "personal_data_scan": {
                "source": source_personal,
                "clean": clean_personal,
                "note": "Autoria para atribuicao fica no preambulo; contatos e elementos posteriores a referencias nao seguem para a versao limpa.",
            },
            "estimated_tokens": _estimate_tokens(clean_stats["words"]),
            "deduplication": {
                "strategy": "Somente blocos consecutivos exatamente iguais sao removidos apos a limpeza dirigida.",
                "consecutive_blocks_removed": cleaning["consecutive_blocks_removed"],
            },
        },
        "cleaning": {
            "rules": [
                "Preservar o HTML oficial imutavel e produzir derivados em UTF-8 normalizado em NFC.",
                "Extrair somente o conteudo de article#articleText e conservar resumo em portugues, secoes, listas e tabelas textuais.",
                "Excluir resumos estrangeiros, navegacao, referencias, elementos editoriais posteriores, imagens e legendas de figuras.",
                "Redigir blocos de citacao direta de terceiros e somente spans de citacao identificados com reticencias, preservando a analise autoral ao redor.",
                "Remover apenas duplicacoes consecutivas exatamente iguais; nao resumir nem reescrever o texto dos autores.",
            ],
            "excluded_elements": cleaning,
            "third_party_handling": (
                "Nenhum recurso citado, PDF, XML, imagem ou anexo foi baixado. "
                "Referencias, figuras e citacoes diretas de terceiros foram deixadas fora do texto limpo."
            ),
        },
        "future_inclusion_decision": "pending_explicit_approval",
        "future_inclusion_reason": (
            "A coleta e auditoria autorizadas nesta fase nao constituem inclusao automatica "
            "em corpus, tokenizacao, split ou treinamento."
        ),
    }
    return document, clean_text


def _conci_preamble(document: dict[str, Any]) -> str:
    identity = document["identity"]
    return "\n\n".join(
        (
            f"# {identity['title']}",
            f"Autores: {', '.join(identity['authors'])}",
            f"Publicacao: {identity['publication']}, {identity['edition']}",
            f"DOI: {identity['doi']}",
            f"Licenca: {document['license']['name']}",
            f"Fonte oficial: {document['license']['evidence_url']}",
        )
    )


def _is_conci_article_start(block: TextBlock) -> bool:
    return block.kind == "heading" and _ascii_key(block.text).startswith("1 introducao")


def _is_conci_figure_caption(block: TextBlock) -> bool:
    return block.kind == "paragraph" and _ascii_key(block.text).startswith("figura ")


def _clean_conci_phase2d_blocks(blocks: list[TextBlock]) -> tuple[list[TextBlock], dict[str, int]]:
    """Correct Phase 2C false positives without changing the preserved source."""

    result: list[TextBlock] = []
    counters = Counter(
        {
            "front_matter_blocks_removed": 0,
            "foreign_abstract_blocks_removed": 0,
            "references_blocks_removed": 0,
            "figure_caption_blocks_removed": 0,
            "figure_source_blocks_removed": 0,
            "direct_quote_blocks_redacted": 0,
            "inline_direct_quote_spans_redacted": 0,
        }
    )
    stage = "front_matter"
    previous_figure = False
    for index, block in enumerate(blocks):
        key = _ascii_key(block.text)
        if stage == "front_matter":
            if key == "resumo":
                stage = "portuguese_abstract"
                result.append(block)
            else:
                counters["front_matter_blocks_removed"] += 1
            continue
        if stage == "portuguese_abstract":
            if key in {"abstract", "resumen"}:
                stage = "foreign_abstract"
                counters["foreign_abstract_blocks_removed"] += 1
            elif _is_conci_article_start(block):
                stage = "article"
                result.append(block)
            else:
                result.append(block)
            continue
        if stage == "foreign_abstract":
            if _is_conci_article_start(block):
                stage = "article"
                result.append(block)
            else:
                counters["foreign_abstract_blocks_removed"] += 1
            continue
        if key == "referencias":
            counters["references_blocks_removed"] += len(blocks) - index
            break
        if _is_conci_figure_caption(block):
            previous_figure = True
            counters["figure_caption_blocks_removed"] += 1
            continue
        if previous_figure and block.kind == "paragraph" and key.startswith("fonte:"):
            previous_figure = False
            counters["figure_source_blocks_removed"] += 1
            continue
        previous_figure = False
        if block.kind == "paragraph" and block.text.lstrip().startswith("[...]"):
            result.append(TextBlock(kind="paragraph", text="[citacao direta de terceiro removida]"))
            counters["direct_quote_blocks_redacted"] += 1
            continue
        if block.kind == "paragraph":
            text, redactions = _redact_ellipsis_quotes(block.text)
            counters["inline_direct_quote_spans_redacted"] += redactions
            result.append(TextBlock(kind=block.kind, text=text, level=block.level))
            continue
        result.append(block)
    if stage != "article":
        raise CollectionAuditError("A revisao ConCI nao localizou o artigo em portugues")
    deduplicated, consecutive = _deduplicate_consecutive_blocks(result)
    counters["consecutive_blocks_removed"] = consecutive
    return deduplicated, dict(counters)


def _artifact_by_role(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = document.get("local_artifacts")
    if not isinstance(artifacts, list):
        raise CollectionAuditError("Documento sem artefatos locais")
    return {artifact["role"]: artifact for artifact in artifacts if isinstance(artifact, dict)}


def _make_revised_conci_document(root: Path, historic_document: dict[str, Any]) -> tuple[dict[str, Any], str]:
    artifact_by_role = _artifact_by_role(historic_document)
    original_path = _path(root, artifact_by_role["original_html"]["local_path"])
    headers_path = _path(root, artifact_by_role["response_headers"]["local_path"])
    extracted_path = _path(root, CONCI_REVISED_EXTRACTED)
    clean_path = _path(root, CONCI_REVISED_CLEAN)
    if not _is_read_only(original_path):
        raise CollectionAuditError("O HTML original ConCI precisa permanecer somente leitura")
    for role, artifact in artifact_by_role.items():
        artifact_path = _path(root, artifact["local_path"])
        if not artifact_path.exists() or _sha256_path(artifact_path) != artifact["sha256"]:
            raise CollectionAuditError(f"O artefato historico ConCI diverge: {role}")
    original_bytes = original_path.read_bytes()
    html_text, encoding = _decode_conci_html(original_bytes)
    parsed = _parse_conci_html(html_text)
    clean_blocks, cleaning = _clean_conci_phase2d_blocks(parsed.blocks)
    extracted_text = unicodedata.normalize("NFC", _conci_preamble(historic_document) + "\n\n" + render_blocks(parsed.blocks))
    clean_text = unicodedata.normalize("NFC", _conci_preamble(historic_document) + "\n\n" + render_blocks(clean_blocks))
    for path, text in ((extracted_path, extracted_text), (clean_path, clean_text)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    clean_personal = _personal_data_counts(clean_text)
    if any(clean_personal.values()):
        raise CollectionAuditError("A revisao ConCI reteve dados pessoais detectados")

    document = copy.deepcopy(historic_document)
    document["states"] = {
        "candidate": True,
        "collection_authorized": True,
        "collected": True,
        "audited": True,
        "approved_for_future_inclusion": True,
        "rejected": False,
        "current_state": "approved_for_future_inclusion",
    }
    document["future_inclusion_decision"] = "approved_for_future_inclusion"
    document["future_inclusion_reason"] = (
        "A auditoria final da Fase 2D confirmou a qualidade dos derivados revisados. "
        "A decisao permite somente futura inclusao formalmente autorizada; nao permite tokenizacao, split ou treinamento."
    )
    original_artifact = _artifact_record(
        root,
        original_path,
        "original_html",
        immutable=True,
        format_name="text/html; embedded charset=windows-1252; HTTP header declared UTF-8",
    )
    headers_artifact = _artifact_record(root, headers_path, "response_headers", immutable=False, format_name="text/plain; HTTP headers")
    extracted_artifact = _artifact_record(root, extracted_path, "extracted_text", immutable=False, format_name="text/plain; charset=UTF-8")
    clean_artifact = _artifact_record(root, clean_path, "clean_text", immutable=False, format_name="text/plain; charset=UTF-8")
    document["local_artifacts"] = [original_artifact, headers_artifact, extracted_artifact, clean_artifact]
    document["quality"] = {
        "original_html": {
            "bytes": original_artifact["bytes"],
            "sha256": original_artifact["sha256"],
            "http_declared_content_type": historic_document["source"]["content_type"],
            "embedded_charset": encoding["embedded_charset"],
            "utf8_valid": encoding["utf8_valid"],
            "encoding_mismatch_recorded": True,
        },
        "derived_text_encoding": encoding["derived_text_encoding"],
        "normalization": "Unicode NFC",
        "extracted_text_statistics": _text_stats(extracted_text),
        "clean_text_statistics": _text_stats(clean_text),
        "paragraphs_extracted": parsed.paragraphs,
        "table_rows_extracted": parsed.table_rows,
        "image_elements_omitted": parsed.image_elements,
        "sections_extracted": len([block for block in clean_blocks if block.kind == "heading"]),
        "sampled_sections": _sample_headings(clean_blocks),
        "invalid_control_characters": _invalid_control_characters(clean_text),
        "replacement_character_count": clean_text.count("\ufffd"),
        "personal_data_scan": {
            "source": _personal_data_counts(html_text),
            "clean": clean_personal,
            "note": "Dados de contato da materia preliminar permanecem apenas no HTML original; o preambulo retem somente a atribuicao necessaria.",
        },
        "estimated_tokens": _estimate_tokens(_text_stats(clean_text)["words"]),
        "deduplication": {
            "strategy": "Somente blocos consecutivos exatamente iguais sao removidos apos a limpeza dirigida.",
            "consecutive_blocks_removed": cleaning["consecutive_blocks_removed"],
        },
    }
    document["cleaning"] = {
        "rules": [
            "Preservar o HTML original em Windows-1252 e converter somente derivados para UTF-8 normalizado em NFC.",
            "Preservar resumo, secoes, listas e tabelas textuais do artigo em portugues.",
            "Excluir capa, contatos, resumos estrangeiros, figuras, legendas, referencias e material posterior ao artigo.",
            "Redigir somente citacoes diretas de terceiros claramente delimitadas; preservar a analise autoral que as contextualiza.",
            "Remover somente blocos consecutivos exatamente iguais; nao resumir nem reescrever a argumentacao dos autores.",
        ],
        "excluded_elements": cleaning,
        "third_party_handling": (
            "Quatro blocos compostos apenas por citacao direta foram redigidos. Quatro spans de citacao em blocos mistos foram redigidos "
            "sem apagar a analise autoral. Quatro redacoes amplas da Fase 2C foram restauradas por nao conterem citacao direta."
        ),
    }
    document["phase2d_review"] = {
        "historical_phase2c_clean_artifact": artifact_by_role["clean_text"]["local_path"],
        "historical_phase2c_clean_sha256": artifact_by_role["clean_text"]["sha256"],
        "historical_phase2c_derivatives_preserved": True,
        "original_hash_rechecked": True,
        "windows_1252_to_utf8_nfc_rechecked": True,
        "eight_prior_redactions_individually_inspected": True,
        "reviewed_prior_redactions": [
            {"source_block_index": 20, "outcome": "restored", "reason": "Aspas enfaticas e citacao indireta; nenhuma citacao direta identificada."},
            {"source_block_index": 30, "outcome": "restored", "reason": "Aspas em termo dos autores; nenhuma citacao direta identificada."},
            {"source_block_index": 62, "outcome": "kept_redacted", "reason": "Bloco composto por citacao direta de terceiro."},
            {"source_block_index": 63, "outcome": "surgically_redacted", "reason": "Analise autoral preservada; tres spans de citacao direta redigidos."},
            {"source_block_index": 66, "outcome": "restored", "reason": "Descricao autoral com expressao entre aspas, sem citacao direta."},
            {"source_block_index": 68, "outcome": "kept_redacted", "reason": "Bloco composto por citacao direta de terceiro."},
            {"source_block_index": 75, "outcome": "restored", "reason": "Descricao autoral de obra citada, sem citacao direta."},
            {"source_block_index": 116, "outcome": "kept_redacted", "reason": "Bloco composto por citacao direta de terceiro."},
        ],
        "newly_identified_direct_quote_findings": [
            {"source_block_index": 21, "outcome": "surgically_redacted", "reason": "Citacao direta dentro de analise autoral; contexto preservado."},
            {"source_block_index": 60, "outcome": "redacted", "reason": "Bloco composto apenas por citacao direta de terceiro."},
        ],
        "sampled_start_middle_end_and_tables": True,
        "clean_corrections_applied": [
            "Restauracao de quatro blocos autorais indevidamente redigidos.",
            "Redacao interna de tres citacoes diretas no bloco misto de direitos autorais.",
            "Redacao de uma citacao interna e de um bloco completo identificados na nova auditoria.",
        ],
    }
    return document, clean_text


def _preflight_records() -> list[dict[str, Any]]:
    return [
        {
            "id": ARTICLE_A_ID,
            "status": "passed",
            "title_and_doi_confirmed": True,
            "canonical_page_url": ARTICLE_A.canonical_url,
            "license": {"name": "CC BY 4.0", "evidence_url": ARTICLE_A.canonical_url, "covers_selected_html_representation": True},
            "third_party_risks": ["citacoes diretas", "referencias", "figura e legenda"],
            "personal_data_risks": ["e-mails e afiliacoes na materia preliminar"],
            "duplicate_risk": "Pagina HTML, PDF e versoes de resumo existem; somente o HTML em portugues foi selecionado.",
            "content_downloaded": True,
        },
        {
            "id": ARTICLE_B_ID,
            "status": "blocked_license_not_cc_by_4_0",
            "title": "Tecnologias digitais e o ensino de tri\u00e2ngulos: uma revis\u00e3o sistem\u00e1tica da literatura",
            "doi": "10.24109/2176-6681.rbep.105.5980",
            "authors": ["B\u00e1rbara Silva Gumiero", "Vin\u00edcius Pazuch"],
            "canonical_page_url": "https://www.scielo.br/j/rbeped/a/9HwMzH7xZBLqnRTS33df56K/?format=html&lang=pt",
            "license": {
                "name": "CC BY-NC 4.0",
                "evidence_url": "https://www.scielo.br/j/rbeped/a/9HwMzH7xZBLqnRTS33df56K/?format=html&lang=pt",
                "covers_selected_html_representation": False,
            },
            "reason": "A fase exige verificacao individual de CC BY 4.0; a pagina oficial aponta CC BY-NC 4.0.",
            "content_downloaded": False,
            "local_artifacts_created": False,
        },
        {
            "id": ARTICLE_C_ID,
            "status": "passed",
            "title_and_doi_confirmed": True,
            "canonical_page_url": ARTICLE_C.canonical_url,
            "license": {"name": "CC BY 4.0", "evidence_url": ARTICLE_C.canonical_url, "covers_selected_html_representation": True},
            "third_party_risks": ["referencias", "graficos e fontes externas", "dados citados"],
            "personal_data_risks": ["e-mails de correspondencia e nomes editoriais apos as referencias"],
            "duplicate_risk": "Pagina HTML, PDF e versao em outro idioma existem; somente o HTML em portugues foi selecionado.",
            "content_downloaded": True,
        },
    ]


def _identity_value(document: dict[str, Any], key: str) -> str | None:
    identity = document.get("identity", {})
    if not isinstance(identity, dict):
        return None
    value = identity.get(key)
    if isinstance(value, str):
        return _ascii_key(value)
    if isinstance(value, list) and value:
        return _ascii_key(str(value[0]))
    return None


def _same_identity_value(left: dict[str, Any], right: dict[str, Any], key: str) -> bool:
    left_value = _identity_value(left, key)
    right_value = _identity_value(right, key)
    return left_value is not None and left_value == right_value


def _deduplication_report(documents: list[dict[str, Any]], clean_texts: dict[str, str]) -> dict[str, Any]:
    pairs: list[dict[str, Any]] = []
    for left, right in combinations(documents, 2):
        left_id = left["id"]
        right_id = right["id"]
        left_words = set(re.findall(r"[\w-]+", _ascii_key(clean_texts[left_id])))
        right_words = set(re.findall(r"[\w-]+", _ascii_key(clean_texts[right_id])))
        union = left_words | right_words
        similarity = len(left_words & right_words) / len(union) if union else 0.0
        left_quality = left["quality"]["clean_text_statistics"]
        right_quality = right["quality"]["clean_text_statistics"]
        pairs.append(
            {
                "documents": [left_id, right_id],
                "same_doi": _same_identity_value(left, right, "doi"),
                "same_title": _same_identity_value(left, right, "title"),
                "same_first_author": _same_identity_value(left, right, "authors"),
                "same_institution": _same_identity_value(left, right, "institutions"),
                "same_clean_text_hash": left_quality["sha256"] == right_quality["sha256"],
                "word_set_jaccard": round(similarity, 6),
                "action": "report_only_no_automatic_removal",
            }
        )
    return {
        "method": "Comparacao por DOI, titulo, primeiro autor, instituicao, hashes e Jaccard de conjuntos de palavras normalizadas.",
        "pairs": pairs,
        "automatic_content_removal": False,
        "potential_duplicate_pairs": [pair["documents"] for pair in pairs if pair["same_doi"] or pair["same_clean_text_hash"]],
    }


def _validate_artifacts(document: dict[str, Any]) -> None:
    artifacts = document.get("local_artifacts")
    expected_roles = {"original_html", "response_headers", "extracted_text", "clean_text"}
    if not isinstance(artifacts, list) or {artifact.get("role") for artifact in artifacts if isinstance(artifact, dict)} != expected_roles:
        raise CollectionAuditError("Cada documento coletado precisa ter quatro artefatos locais")
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise CollectionAuditError("Artefato invalido")
        if artifact.get("git_ignored") is not True:
            raise CollectionAuditError("O conteudo de corpus precisa continuar fora do Git")
        if not isinstance(artifact.get("local_path"), str) or not artifact["local_path"].startswith(ALLOWED_LOCAL_PREFIXES):
            raise CollectionAuditError("Artefato fora dos diretorios locais permitidos")
        if not isinstance(artifact.get("bytes"), int) or artifact["bytes"] <= 0:
            raise CollectionAuditError("Artefato sem tamanho valido")
        if not isinstance(artifact.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]):
            raise CollectionAuditError("Artefato sem SHA-256 valido")


def summarize_phase2d_audit(audit: dict[str, Any]) -> dict[str, Any]:
    documents = []
    for document in audit["documents"]:
        quality = document["quality"]["clean_text_statistics"]
        documents.append(
            {
                "id": document["id"],
                "state": document["states"]["current_state"],
                "clean_characters": quality["characters"],
                "clean_words": quality["words"],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "documents": documents,
        "new_full_documents_collected": 2,
        "blocked_candidates": [ARTICLE_B_ID],
        "approved_for_future_inclusion": [EMAG_DOCUMENT_ID, CONCI_DOCUMENT_ID],
    }


def validate_phase2d_audit(audit: dict[str, Any]) -> dict[str, Any]:
    """Validate the metadata-only Phase 2D manifest without opening corpus files."""

    if audit.get("schema_version") != SCHEMA_VERSION or audit.get("phase") != PHASE:
        raise CollectionAuditError("O manifesto precisa registrar a Fase 2D e o schema 3")
    historical = audit.get("historical_phase_2c")
    if not isinstance(historical, dict) or historical.get("path") != PHASE2C_AUDIT_PATH or historical.get("schema_version") != 2:
        raise CollectionAuditError("O manifesto historico da Fase 2C precisa permanecer referenciado")
    if historical.get("preserved") is not True or not re.fullmatch(r"[0-9a-f]{64}", str(historical.get("sha256", ""))):
        raise CollectionAuditError("O manifesto historico da Fase 2C precisa permanecer imutavel e hasheado")
    authorization = audit.get("authorization")
    expected_authorization = {
        "conci_final_review": [CONCI_DOCUMENT_ID],
        "approved_scielo_html_collection": [ARTICLE_A_ID, ARTICLE_C_ID],
        "blocked_without_download": [ARTICLE_B_ID],
        "other_full_documents_authorized": 0,
    }
    if authorization != expected_authorization:
        raise CollectionAuditError("A autorizacao da Fase 2D foi ampliada ou alterada")
    safeguards = audit.get("safeguards")
    expected_safeguards = {
        "ollama_used",
        "external_model_or_weights_used",
        "ai_api_used",
        "bpe_trained",
        "final_split_created",
        "neural_training_started",
        "v04_weights_or_checkpoints_modified",
        "desktop_interface_branch_modified",
        "pdf_downloaded",
        "xml_downloaded",
        "external_link_content_downloaded",
        "documents_outside_authorized_list_collected",
    }
    if not isinstance(safeguards, dict) or set(safeguards) != expected_safeguards or any(value is not False for value in safeguards.values()):
        raise CollectionAuditError("Uma salvaguarda obrigatoria foi alterada")
    documents = audit.get("documents")
    if not isinstance(documents, list) or len(documents) != 4:
        raise CollectionAuditError("A Fase 2D precisa registrar exatamente quatro documentos locais")
    documents_by_id = {document.get("id"): document for document in documents if isinstance(document, dict)}
    expected_ids = {EMAG_DOCUMENT_ID, CONCI_DOCUMENT_ID, ARTICLE_A_ID, ARTICLE_C_ID}
    if set(documents_by_id) != expected_ids:
        raise CollectionAuditError("O manifesto contem documento local nao autorizado")
    for document in documents_by_id.values():
        _validate_artifacts(document)
        quality = document.get("quality", {})
        scan = quality.get("personal_data_scan", {}) if isinstance(quality, dict) else {}
        personal = scan.get("clean", scan) if isinstance(scan, dict) else {}
        if any(personal.get(key) != 0 for key in ("email_matches", "cpf_matches", "phone_matches")):
            raise CollectionAuditError("Texto limpo com dados pessoais detectados")
        if quality.get("replacement_character_count") != 0 or quality.get("invalid_control_characters") != []:
            raise CollectionAuditError("Texto limpo com problema de codificacao")
    conci = documents_by_id[CONCI_DOCUMENT_ID]
    if conci["states"]["current_state"] != "approved_for_future_inclusion" or not conci["states"]["approved_for_future_inclusion"]:
        raise CollectionAuditError("A auditoria final do ConCI precisa registrar somente a aprovacao limitada")
    review = conci.get("phase2d_review")
    if not isinstance(review, dict) or review.get("eight_prior_redactions_individually_inspected") is not True:
        raise CollectionAuditError("A revisao individual das oito redacoes ConCI esta ausente")
    if len(review.get("reviewed_prior_redactions", [])) != 8 or review.get("historical_phase2c_derivatives_preserved") is not True:
        raise CollectionAuditError("O historico e a revisao das redacoes ConCI precisam ser preservados")
    for identifier in (ARTICLE_A_ID, ARTICLE_C_ID):
        document = documents_by_id[identifier]
        if document["states"]["current_state"] != "audited" or document["license"]["name"] != "CC BY 4.0":
            raise CollectionAuditError("Somente artigos CC BY 4.0 podem aparecer como coletados")
        if document["source"]["selected_representation"] != "HTML" or document["source"]["other_representations_downloaded"] is not False:
            raise CollectionAuditError("Cada artigo SciELO precisa registrar somente uma representacao HTML")
    preflight = audit.get("preflight")
    if not isinstance(preflight, list) or {item.get("id") for item in preflight if isinstance(item, dict)} != {ARTICLE_A_ID, ARTICLE_B_ID, ARTICLE_C_ID}:
        raise CollectionAuditError("A pre-verificacao precisa registrar somente os tres artigos autorizados")
    blocked = next(item for item in preflight if item["id"] == ARTICLE_B_ID)
    if blocked.get("status") != "blocked_license_not_cc_by_4_0" or blocked.get("content_downloaded") is not False:
        raise CollectionAuditError("O artigo B precisa permanecer bloqueado sem download")
    duplicate_report = audit.get("deduplication_report")
    if not isinstance(duplicate_report, dict) or duplicate_report.get("automatic_content_removal") is not False:
        raise CollectionAuditError("A deduplicacao deve somente relatar, nunca remover automaticamente")
    if len(duplicate_report.get("pairs", [])) != 6:
        raise CollectionAuditError("O relatorio de similaridade precisa cobrir todos os pares de documentos")
    forbidden = _find_forbidden_content_fields(audit)
    if forbidden:
        raise CollectionAuditError(f"O manifesto nao pode conter conteudo integral: {', '.join(forbidden)}")
    return summarize_phase2d_audit(audit)


def validate_phase2d_local_artifacts(audit: dict[str, Any], root: str | Path = ".") -> None:
    """Verify locally ignored Phase 2D artifacts and the preserved Phase 2C audit."""

    validate_phase2d_audit(audit)
    root_path = Path(root)
    historical = audit["historical_phase_2c"]
    history_path = _path(root_path, historical["path"])
    if not history_path.exists() or _sha256_path(history_path) != historical["sha256"]:
        raise CollectionAuditError("O manifesto historico da Fase 2C diverge do hash registrado")
    phase2c = json.loads(history_path.read_text(encoding="utf-8"))
    validate_phase2c_audit(phase2c)
    validate_phase2c_local_artifacts(phase2c, root_path)
    for document in audit["documents"]:
        for artifact in document["local_artifacts"]:
            artifact_path = _path(root_path, artifact["local_path"])
            if not artifact_path.exists() or artifact_path.stat().st_size != artifact["bytes"]:
                raise CollectionAuditError(f"Artefato local ausente ou com tamanho divergente: {artifact_path}")
            if _sha256_path(artifact_path) != artifact["sha256"]:
                raise CollectionAuditError(f"SHA-256 divergente: {artifact_path}")
            if artifact["role"] in {"extracted_text", "clean_text"}:
                text = artifact_path.read_text(encoding="utf-8")
                if unicodedata.normalize("NFC", text) != text:
                    raise CollectionAuditError(f"Texto fora de NFC: {artifact_path}")
        original = next(artifact for artifact in document["local_artifacts"] if artifact["role"] == "original_html")
        if not _is_read_only(_path(root_path, original["local_path"])):
            raise CollectionAuditError("Um HTML original deixou de estar somente leitura")


def build_phase2d_audit(root: str | Path = ".") -> dict[str, Any]:
    """Create the v3 metadata audit from already-authorized local artifacts."""

    root_path = Path(root)
    phase2c_path = _path(root_path, PHASE2C_AUDIT_PATH)
    phase2c = json.loads(phase2c_path.read_text(encoding="utf-8"))
    validate_phase2c_audit(phase2c)
    validate_phase2c_local_artifacts(phase2c, root_path)
    phase2c_documents = {document["id"]: document for document in phase2c["documents"]}
    emag = copy.deepcopy(phase2c_documents[EMAG_DOCUMENT_ID])
    conci, conci_text = _make_revised_conci_document(root_path, phase2c_documents[CONCI_DOCUMENT_ID])
    article_a, article_a_text = _make_scielo_document(root_path, ARTICLE_A)
    article_c, article_c_text = _make_scielo_document(root_path, ARTICLE_C)
    documents = [emag, conci, article_a, article_c]
    emag_clean = _path(root_path, _artifact_by_role(emag)["clean_text"]["local_path"]).read_text(encoding="utf-8")
    audit = {
        "schema_version": SCHEMA_VERSION,
        "project": "ELYSIA-Seed v0.5",
        "phase": PHASE,
        "historical_phase_2b": copy.deepcopy(phase2c["historical_phase_2b"]),
        "historical_phase_2c": {
            "path": PHASE2C_AUDIT_PATH,
            "schema_version": 2,
            "sha256": _sha256_path(phase2c_path),
            "preserved": True,
        },
        "historical_research_manifest": copy.deepcopy(phase2c["historical_research_manifest"]),
        "authorization": {
            "conci_final_review": [CONCI_DOCUMENT_ID],
            "approved_scielo_html_collection": [ARTICLE_A_ID, ARTICLE_C_ID],
            "blocked_without_download": [ARTICLE_B_ID],
            "other_full_documents_authorized": 0,
        },
        "safeguards": {
            "ollama_used": False,
            "external_model_or_weights_used": False,
            "ai_api_used": False,
            "bpe_trained": False,
            "final_split_created": False,
            "neural_training_started": False,
            "v04_weights_or_checkpoints_modified": False,
            "desktop_interface_branch_modified": False,
            "pdf_downloaded": False,
            "xml_downloaded": False,
            "external_link_content_downloaded": False,
            "documents_outside_authorized_list_collected": False,
        },
        "preflight": _preflight_records(),
        "documents": documents,
        "deduplication_report": _deduplication_report(
            documents,
            {
                EMAG_DOCUMENT_ID: emag_clean,
                CONCI_DOCUMENT_ID: conci_text,
                ARTICLE_A_ID: article_a_text,
                ARTICLE_C_ID: article_c_text,
            },
        ),
    }
    validate_phase2d_audit(audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--audit", default=CURRENT_AUDIT_PATH)
    args = parser.parse_args()

    root = Path(args.root)
    audit = build_phase2d_audit(root)
    _write_json(_path(root, args.audit), audit)
    validate_phase2d_local_artifacts(audit, root)
    print(json.dumps(summarize_phase2d_audit(audit), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
