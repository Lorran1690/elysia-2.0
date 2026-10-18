"""Build and validate the Phase 2E final SciELO quality review.

The module operates exclusively on the two already-authorized local SciELO
HTML files.  It does not fetch content, create splits, train a tokenizer, or
touch neural weights.  Phase 2D is retained as an immutable historical audit;
only the redistribution article receives new local derivatives because the
official HTML contains text tables outside ``article#articleText``.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from learning.v05_collection_audit import (
    ALLOWED_LOCAL_PREFIXES,
    CollectionAuditError,
    TextBlock,
    _estimate_tokens,
    _find_forbidden_content_fields,
    _invalid_control_characters,
    _is_read_only,
    _sha256_path,
    _text_stats,
    _write_json,
    render_blocks,
)
from learning.v05_third_collection_audit import (
    ARTICLE_A,
    ARTICLE_A_ID,
    ARTICLE_C,
    ARTICLE_C_ID,
    CONCI_DOCUMENT_ID,
    EMAG_DOCUMENT_ID,
    ArticleSpec,
    _article_preamble,
    _artifact_by_role,
    _artifact_record,
    _assert_scielo_identity,
    _clean_scielo_blocks,
    _deduplication_report,
    _parse_response_snapshot,
    _parse_scielo_html,
    _path,
    _personal_data_counts,
    _sample_headings,
    validate_phase2d_audit,
    validate_phase2d_local_artifacts,
)


SCHEMA_VERSION = 4
PHASE = "final-scielo-quality-review-and-corpus-planning"
PHASE2D_AUDIT_PATH = "data/corpus-v0.5/collection-audit.phase-2d.json"
CURRENT_AUDIT_PATH = "data/corpus-v0.5/collection-audit.phase-2e.json"
REDISTRIBUTION_REVISED_EXTRACTED = "data/corpus-v0.5/processed/scielo-rap-redistribution-2024.phase-2e.extracted.txt"
REDISTRIBUTION_REVISED_CLEAN = "data/corpus-v0.5/clean/scielo-rap-redistribution-2024.phase-2e.clean.txt"

_AFFECTIVITY_QUOTE_SOURCES = (
    "Platao, 1980",
    "Aristoteles, 2014",
    "Maritain, 1959",
    "Macedo, 1980",
    "Rates e Sucupira Lins, 2021",
    "Von Hildebrand, 2007",
    "Maritain, 2006",
    "Mounier, 2004",
    "Piaget, 1973",
    "Von Hildebrand, 2007",
    "Sucupira Lins, 2022b",
    "Von Hildebrand, 2020",
)

_REDISTRIBUTION_DIRECT_QUOTE = re.compile(
    r"\u201ca federa\u00e7\u00e3o \u00e9, em \u00faltima inst\u00e2ncia, um arranjo "
    r"pol\u00edtico-institucional que deve, necessariamente, emular de alguma forma "
    r"o Estado unit\u00e1rio\u201d",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class ModalTableCell:
    """One textual table cell, keeping explicit structural spans when present."""

    text: str
    colspan: int | None
    rowspan: int | None


@dataclass(frozen=True)
class ModalTable:
    """A table rendered in an official SciELO modal outside the article body."""

    identifier: str
    title: str
    rows: tuple[tuple[ModalTableCell, ...], ...]


class _SciELOModalTableParser(HTMLParser):
    """Read only ``ModalTablet*`` text tables; images and external links stay out."""

    _VOID_TAGS = frozenset(
        {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[ModalTable] = []
        self._stack: list[str] = []
        self._modal_identifier: str | None = None
        self._modal_depth: int | None = None
        self._title_active = False
        self._title_parts: list[str] = []
        self._table_depth = 0
        self._rows: list[tuple[ModalTableCell, ...]] = []
        self._row: list[ModalTableCell] | None = None
        self._cell_tag: str | None = None
        self._cell_parts: list[str] = []
        self._cell_colspan: int | None = None
        self._cell_rowspan: int | None = None

    @staticmethod
    def _span(value: str | None) -> int | None:
        if value is None or not value.isdigit():
            return None
        result = int(value)
        return result if result > 1 else None

    @staticmethod
    def _compact(parts: list[str]) -> str:
        return re.sub(r"\s+", " ", "".join(parts)).strip()

    def _begin_modal(self, identifier: str, depth: int) -> None:
        self._modal_identifier = identifier
        self._modal_depth = depth
        self._title_active = False
        self._title_parts = []
        self._table_depth = 0
        self._rows = []
        self._row = None
        self._cell_tag = None
        self._cell_parts = []
        self._cell_colspan = None
        self._cell_rowspan = None

    def _finish_cell(self) -> None:
        if self._cell_tag is None or self._row is None:
            return
        self._row.append(
            ModalTableCell(
                text=self._compact(self._cell_parts),
                colspan=self._cell_colspan,
                rowspan=self._cell_rowspan,
            )
        )
        self._cell_tag = None
        self._cell_parts = []
        self._cell_colspan = None
        self._cell_rowspan = None

    def _finish_modal(self) -> None:
        if self._modal_identifier is None:
            return
        title = self._compact(self._title_parts)
        title = re.sub(r"^table_chart\s*", "", title, flags=re.IGNORECASE).strip()
        if self._rows and title:
            self.tables.append(ModalTable(self._modal_identifier, title, tuple(self._rows)))
        self._modal_identifier = None
        self._modal_depth = None
        self._title_active = False
        self._title_parts = []
        self._table_depth = 0
        self._rows = []
        self._row = None
        self._cell_tag = None
        self._cell_parts = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.casefold()
        attributes = {name.casefold(): value for name, value in attrs}
        is_void = normalized in self._VOID_TAGS
        if not is_void:
            self._stack.append(normalized)
        depth = len(self._stack)

        identifier = attributes.get("id") or ""
        if normalized == "div" and re.fullmatch(r"ModalTablet\d+", identifier):
            self._begin_modal(identifier, depth)
            return
        if self._modal_identifier is None:
            return
        if normalized == "h5":
            self._title_active = True
            self._title_parts = []
        elif normalized == "table":
            self._table_depth += 1
        elif normalized == "tr" and self._table_depth:
            self._row = []
        elif normalized in {"th", "td"} and self._table_depth and self._row is not None:
            self._cell_tag = normalized
            self._cell_parts = []
            self._cell_colspan = self._span(attributes.get("colspan"))
            self._cell_rowspan = self._span(attributes.get("rowspan"))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.casefold() not in self._VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._modal_identifier is None:
            return
        if self._title_active:
            self._title_parts.append(data)
        if self._cell_tag is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        if normalized in self._VOID_TAGS or not self._stack or self._stack[-1] != normalized:
            return
        depth = len(self._stack)
        if self._modal_identifier is not None:
            if normalized == "h5":
                self._title_active = False
            elif normalized in {"th", "td"}:
                self._finish_cell()
            elif normalized == "tr" and self._row is not None:
                self._rows.append(tuple(self._row))
                self._row = None
            elif normalized == "table" and self._table_depth:
                self._table_depth -= 1
            elif normalized == "div" and depth == self._modal_depth:
                self._finish_modal()
        self._stack.pop()


def _parse_modal_tables(html_text: str) -> list[ModalTable]:
    parser = _SciELOModalTableParser()
    parser.feed(html_text)
    parser.close()
    expected_ids = [f"ModalTablet{number}" for number in range(1, 5)]
    actual_ids = [table.identifier for table in parser.tables]
    if actual_ids != expected_ids:
        raise CollectionAuditError("O HTML de redistribuicao precisa conter exatamente quatro tabelas textuais oficiais")
    if any(not table.rows for table in parser.tables):
        raise CollectionAuditError("Uma tabela textual oficial foi extraida sem linhas")
    return parser.tables


def _render_modal_table_blocks(tables: list[ModalTable]) -> list[TextBlock]:
    result = [TextBlock(kind="heading", text="Tabelas textuais disponiveis no HTML oficial", level=2)]
    for table in tables:
        result.append(TextBlock(kind="heading", text=table.title, level=3))
        for row in table.rows:
            cells: list[str] = []
            for cell in row:
                value = cell.text
                spans: list[str] = []
                if cell.colspan is not None:
                    spans.append(f"colspan={cell.colspan}")
                if cell.rowspan is not None:
                    spans.append(f"rowspan={cell.rowspan}")
                if spans:
                    value = f"{value} [{' '.join(spans)}]".strip()
                cells.append(value)
            result.append(TextBlock(kind="table_row", text=" | ".join(cells)))
    return result


def _redact_redistribution_direct_quote(blocks: list[TextBlock]) -> tuple[list[TextBlock], int]:
    """Remove the one reviewed substantive quotation while retaining the analysis."""

    result: list[TextBlock] = []
    count = 0
    for block in blocks:
        if block.kind != "paragraph":
            result.append(block)
            continue
        text, replacements = _REDISTRIBUTION_DIRECT_QUOTE.subn("[citacao direta de terceiro removida]", block.text)
        result.append(TextBlock(kind=block.kind, text=text, level=block.level))
        count += replacements
    if count != 1:
        raise CollectionAuditError("A revisao de redistribuicao esperava uma unica citacao direta substantiva")
    return result, count


def _assert_artifact_set(document: dict[str, Any]) -> None:
    artifacts = document.get("local_artifacts")
    expected = {"original_html", "response_headers", "extracted_text", "clean_text"}
    if not isinstance(artifacts, list):
        raise CollectionAuditError("Documento sem artefatos locais")
    roles = {artifact.get("role") for artifact in artifacts if isinstance(artifact, dict)}
    if roles != expected:
        raise CollectionAuditError("Cada documento precisa manter exatamente quatro artefatos locais atuais")
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise CollectionAuditError("Artefato local invalido")
        if artifact.get("git_ignored") is not True:
            raise CollectionAuditError("Conteudo local de corpus nao pode entrar no Git")
        path = artifact.get("local_path")
        if not isinstance(path, str) or not path.startswith(ALLOWED_LOCAL_PREFIXES):
            raise CollectionAuditError("Artefato local fora do diretorio de corpus permitido")
        if not isinstance(artifact.get("bytes"), int) or artifact["bytes"] <= 0:
            raise CollectionAuditError("Artefato local sem tamanho valido")
        if not re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("sha256", ""))):
            raise CollectionAuditError("Artefato local sem SHA-256 valido")


def _phase2e_safeguards() -> dict[str, bool]:
    return {
        "additional_dataset_downloaded": False,
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
    }


def _future_corpus_plan() -> dict[str, Any]:
    """Metadata-only planning; candidates remain uncollected until explicit approval."""

    return {
        "status": "proposal_only_no_collection_authorized",
        "collection_or_tokenization_started": False,
        "split_policy": {
            "unit": "whole-document-author-origin-and-derivation-group",
            "rule": "A group_id remains entirely in one future partition; no BPE or split is created in this phase.",
        },
        "candidate_families": [
            {
                "id": "elysia-original-dialogues-and-guides",
                "genre": "original dialogues, support instructions, and explanatory prose",
                "rights_basis": "signed contributor authorization with CC0 1.0 preferred",
                "status": "requires_authoring_protocol_and_explicit_collection_approval",
                "risks": ["synthetic or copied content", "personal data in examples"],
            },
            {
                "id": "ibict-omeka-guide-2018",
                "genre": "technical documentation",
                "source_url": "https://repositorio.enap.gov.br/bitstream/1/3162/1/Guia%20do%20usu%C3%A1rio%20do%20Omeka%20-%20Ebook.pdf",
                "rights_basis": "CC BY 4.0 stated in the official repository record",
                "status": "metadata-reviewed_only",
                "risks": ["PDF extraction quality", "third-party screenshots and references"],
            },
            {
                "id": "individual-scielo-cc-by-articles",
                "genre": "informative and explanatory academic prose",
                "rights_basis": "license must be confirmed on the selected item, not inferred from the portal",
                "status": "requires_individual_preflight_and_explicit_collection_approval",
                "risks": ["quotations", "figures", "references", "near-duplicate editions"],
            },
            {
                "id": "educapes-individual-cc-by-records",
                "genre": "educational material",
                "rights_basis": "canonical file and individual rights metadata must match before collection",
                "status": "requires_canonical_version_audit_and_explicit_collection_approval",
                "risks": ["repository metadata/version mismatch", "third-party material in attachments"],
            },
            {
                "id": "brazilian-official-acts",
                "genre": "institutional and legal texts",
                "source_url": "https://www.planalto.gov.br/ccivil_03/leis/l9610.htm",
                "rights_basis": "Brazilian Copyright Law, art. 8 IV, excludes official acts from copyright protection",
                "status": "requires_scope_and_currency_protocol_before_collection",
                "risks": ["highly formal register", "outdated versions", "politically sensitive material"],
            },
        ],
        "rejected_license_families": [
            "CC BY-NC, CC BY-NC-SA, CC BY-ND, unknown licenses, and portal-level claims without file-level evidence",
        ],
    }


def _make_affectivity_review(root: Path, prior: dict[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(prior)
    artifacts = _artifact_by_role(document)
    original_path = _path(root, artifacts["original_html"]["local_path"])
    if not _is_read_only(original_path):
        raise CollectionAuditError("O HTML original de afetividade precisa permanecer somente leitura")
    html_text = original_path.read_text(encoding="utf-8")
    _assert_scielo_identity(html_text, ARTICLE_A)
    parsed = _parse_scielo_html(html_text)
    direct_blocks = [block for block in parsed.blocks if block.kind == "quote"]
    if len(direct_blocks) != len(_AFFECTIVITY_QUOTE_SOURCES):
        raise CollectionAuditError("A revisao de afetividade precisa encontrar os doze blocos de citacao")
    clean_path = _path(root, artifacts["clean_text"]["local_path"])
    clean_text = clean_path.read_text(encoding="utf-8")
    review_rows = [
        {
            "ordinal": ordinal,
            "attribution": attribution,
            "classification": "direct_third_party_quote",
            "action": "prior_redaction_retained",
            "authorial_context_before_and_after_preserved": True,
        }
        for ordinal, attribution in enumerate(_AFFECTIVITY_QUOTE_SOURCES, start=1)
    ]
    document["phase2e_review"] = {
        "reviewed_blockquote_count": len(review_rows),
        "reviewed_blockquotes": review_rows,
        "all_reviewed_blocks_are_direct_third_party_quotes": True,
        "prior_clean_derivative_reused_without_change": True,
        "prior_clean_sha256": artifacts["clean_text"]["sha256"],
        "paragraph_continuity_review": {
            "distributed_sections_reviewed": ["Resumo", "Introducao", "desenvolvimento", "Consideracoes finais"],
            "context_before_and_after_each_redaction_checked": True,
            "authorial_commentary_restored": False,
        },
        "remaining_limitation": (
            "The text retains many inline quotations mixed with authorial paragraphs. "
            "They require a separate, semantic quote-by-quote rights review before promotion."
        ),
    }
    document["quality"]["phase2e_utf8_and_nfc_checked"] = {
        "clean_utf8": True,
        "clean_nfc": unicodedata.normalize("NFC", clean_text) == clean_text,
        "clean_replacement_character_count": clean_text.count("\ufffd"),
        "clean_invalid_control_characters": _invalid_control_characters(clean_text),
    }
    document["states"].update(
        {
            "audited": True,
            "approved_for_future_inclusion": False,
            "current_state": "audited",
        }
    )
    document["future_inclusion_decision"] = "audited_pending_inline_quote_rights_review"
    document["future_inclusion_reason"] = (
        "The twelve standalone quotations were confirmed as third-party material and remain redacted, "
        "but inline quotation rights review remains incomplete."
    )
    return document


def _make_redistribution_review(root: Path, prior: dict[str, Any]) -> tuple[dict[str, Any], str]:
    document = copy.deepcopy(prior)
    prior_artifacts = _artifact_by_role(prior)
    original_path = _path(root, prior_artifacts["original_html"]["local_path"])
    headers_path = _path(root, prior_artifacts["response_headers"]["local_path"])
    extracted_path = _path(root, REDISTRIBUTION_REVISED_EXTRACTED)
    clean_path = _path(root, REDISTRIBUTION_REVISED_CLEAN)
    if not _is_read_only(original_path):
        raise CollectionAuditError("O HTML original de redistribuicao precisa permanecer somente leitura")
    headers = _parse_response_snapshot(headers_path)
    original_bytes = original_path.read_bytes()
    try:
        html_text = original_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CollectionAuditError("O HTML de redistribuicao nao e UTF-8 valido") from error
    _assert_scielo_identity(html_text, ARTICLE_C)
    parsed = _parse_scielo_html(html_text)
    tables = _parse_modal_tables(html_text)
    clean_blocks, cleaning = _clean_scielo_blocks(parsed.blocks)
    clean_blocks, quoted_spans = _redact_redistribution_direct_quote(clean_blocks)
    table_blocks = _render_modal_table_blocks(tables)
    extracted_blocks = [*parsed.blocks, *table_blocks]
    clean_blocks = [*clean_blocks, *table_blocks]
    extracted_text = unicodedata.normalize("NFC", _article_preamble(ARTICLE_C) + "\n\n" + render_blocks(extracted_blocks))
    clean_text = unicodedata.normalize("NFC", _article_preamble(ARTICLE_C) + "\n\n" + render_blocks(clean_blocks))
    for path, text in ((extracted_path, extracted_text), (clean_path, clean_text)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    clean_personal = _personal_data_counts(clean_text)
    if any(clean_personal.values()):
        raise CollectionAuditError("A revisao de redistribuicao reteve dados pessoais detectados")

    original_artifact = _artifact_record(root, original_path, "original_html", immutable=True, format_name="text/html; charset=UTF-8")
    headers_artifact = _artifact_record(root, headers_path, "response_headers", immutable=False, format_name="text/plain; HTTP response snapshot")
    extracted_artifact = _artifact_record(root, extracted_path, "extracted_text", immutable=False, format_name="text/plain; charset=UTF-8")
    clean_artifact = _artifact_record(root, clean_path, "clean_text", immutable=False, format_name="text/plain; charset=UTF-8")
    extracted_stats = _text_stats(extracted_text)
    clean_stats = _text_stats(clean_text)
    table_rows = sum(len(table.rows) for table in tables)
    numeric_cells = sum(
        1
        for table in tables
        for row in table.rows
        for cell in row
        if re.fullmatch(r"-?\d+(?:[.,]\d+)?", cell.text)
    )
    cleaning["inline_direct_quote_spans_redacted"] += quoted_spans
    document["local_artifacts"] = [original_artifact, headers_artifact, extracted_artifact, clean_artifact]
    document["quality"] = {
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
        "table_rows_extracted": table_rows,
        "table_modal_count": len(tables),
        "table_numeric_cells_preserved": numeric_cells,
        "blockquotes_extracted": parsed.blockquotes,
        "image_elements_omitted": parsed.image_elements,
        "sections_extracted": len([block for block in clean_blocks if block.kind == "heading"]),
        "sampled_sections": _sample_headings(clean_blocks),
        "invalid_control_characters": _invalid_control_characters(clean_text),
        "replacement_character_count": clean_text.count("\ufffd"),
        "personal_data_scan": {
            "source": _personal_data_counts(html_text),
            "clean": clean_personal,
            "note": "Contact material remains outside the cleaned article and table transcription.",
        },
        "estimated_tokens": _estimate_tokens(clean_stats["words"]),
        "deduplication": {
            "strategy": "Only exactly equal consecutive blocks are removed; table rows are preserved in source order.",
            "consecutive_blocks_removed": cleaning["consecutive_blocks_removed"],
        },
    }
    document["cleaning"] = {
        "rules": [
            "Preserve the immutable official HTML and make only UTF-8 NFC derivatives.",
            "Retain the Portuguese article body and the four text tables available in official HTML modals.",
            "Represent each table cell in official HTML order and expose colspan or rowspan when present; do not infer missing cells or values.",
            "Remove foreign abstracts, references, editorial material, figures, and graph captions from the cleaned derivative.",
            "Redact the one reviewed substantive direct quotation while keeping its surrounding authorial analysis.",
        ],
        "excluded_elements": cleaning,
        "third_party_handling": (
            "No PDF, XML, image, attachment, or external link was downloaded. Graph-only information remains omitted; "
            "HTML text tables and authorial interpretation are preserved."
        ),
    }
    document["phase2e_review"] = {
        "prior_derivatives": {
            "extracted_derivative_artifact": prior_artifacts["extracted_text"],
            "clean_derivative_artifact": prior_artifacts["clean_text"],
        },
        "html_comparison": {
            "article_body_tables_detected": 0,
            "modal_tables_detected_outside_article_body": len(tables),
            "modal_table_identifiers": [table.identifier for table in tables],
            "table_rows_preserved": table_rows,
            "numeric_cells_preserved_without_reconstruction": numeric_cells,
            "table_text_source": "official HTML modal tables",
            "graph_only_information_not_reconstructed": True,
        },
        "inline_direct_quote_review": {
            "substantive_spans_redacted": quoted_spans,
            "short_notational_quotation_marks_retained": True,
        },
        "clean_revision_changed": True,
        "quality_decision": "approved_for_future_inclusion",
    }
    document["states"].update(
        {
            "audited": True,
            "approved_for_future_inclusion": True,
            "current_state": "approved_for_future_inclusion",
        }
    )
    document["future_inclusion_decision"] = "approved_for_future_inclusion"
    document["future_inclusion_reason"] = (
        "The official HTML, attribution, CC BY 4.0 evidence, UTF-8/NFC derivatives, table completeness, "
        "and no-data-personal scan passed the bounded Phase 2E audit. This does not authorize training."
    )
    return document, clean_text


def _load_phase2d(root: Path) -> tuple[dict[str, Any], Path]:
    path = _path(root, PHASE2D_AUDIT_PATH)
    if not path.exists():
        raise CollectionAuditError("O manifesto congelado da Fase 2D esta ausente")
    phase2d = json.loads(path.read_text(encoding="utf-8"))
    validate_phase2d_audit(phase2d)
    return phase2d, path


def _documents_by_id(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    documents = audit.get("documents")
    if not isinstance(documents, list):
        raise CollectionAuditError("Manifesto sem documentos")
    indexed = {document.get("id"): document for document in documents if isinstance(document, dict)}
    expected = {EMAG_DOCUMENT_ID, CONCI_DOCUMENT_ID, ARTICLE_A_ID, ARTICLE_C_ID}
    if set(indexed) != expected:
        raise CollectionAuditError("Manifesto com conjunto inesperado de documentos")
    return indexed


def summarize_phase2e_audit(audit: dict[str, Any]) -> dict[str, Any]:
    documents = audit["documents"]
    affectivity = next(document for document in documents if document["id"] == ARTICLE_A_ID)
    redistribution = next(document for document in documents if document["id"] == ARTICLE_C_ID)
    return {
        "schema_version": SCHEMA_VERSION,
        "documents": [
            {
                "id": document["id"],
                "state": document["states"]["current_state"],
                "clean_characters": document["quality"]["clean_text_statistics"]["characters"],
                "clean_words": document["quality"]["clean_text_statistics"]["words"],
            }
            for document in documents
        ],
        "new_full_documents_collected": 0,
        "affectivity_quote_blocks_reviewed": affectivity["phase2e_review"]["reviewed_blockquote_count"],
        "redistribution_modal_tables_preserved": redistribution["phase2e_review"]["html_comparison"]["modal_tables_detected_outside_article_body"],
        "approved_for_future_inclusion": [
            document["id"] for document in documents if document["states"]["approved_for_future_inclusion"]
        ],
    }


def validate_phase2e_audit(audit: dict[str, Any]) -> dict[str, Any]:
    """Validate the metadata-only Phase 2E manifest without opening corpus files."""

    if audit.get("schema_version") != SCHEMA_VERSION or audit.get("phase") != PHASE:
        raise CollectionAuditError("O manifesto precisa registrar Fase 2E e schema 4")
    historical = audit.get("historical_phase_2d")
    if not isinstance(historical, dict) or historical.get("path") != PHASE2D_AUDIT_PATH:
        raise CollectionAuditError("A Fase 2D precisa permanecer referenciada como historica")
    if historical.get("schema_version") != 3 or historical.get("preserved") is not True:
        raise CollectionAuditError("A referencia historica da Fase 2D esta incompleta")
    if not re.fullmatch(r"[0-9a-f]{64}", str(historical.get("sha256", ""))):
        raise CollectionAuditError("A Fase 2D historica precisa ter SHA-256")
    safeguards = audit.get("safeguards")
    if safeguards != _phase2e_safeguards():
        raise CollectionAuditError("Uma salvaguarda obrigatoria da Fase 2E foi alterada")
    authorization = audit.get("authorization")
    if authorization != {
        "documents_reviewed": [ARTICLE_A_ID, ARTICLE_C_ID],
        "new_full_documents_authorized": 0,
        "new_full_documents_collected": 0,
    }:
        raise CollectionAuditError("A autorizacao da Fase 2E foi ampliada")
    documents = _documents_by_id(audit)
    for document in documents.values():
        _assert_artifact_set(document)
        quality = document.get("quality", {})
        scan = quality.get("personal_data_scan", {}) if isinstance(quality, dict) else {}
        clean_scan = scan.get("clean", scan) if isinstance(scan, dict) else {}
        if any(clean_scan.get(key) != 0 for key in ("email_matches", "cpf_matches", "phone_matches")):
            raise CollectionAuditError("Texto limpo com dados pessoais detectados")
        if quality.get("replacement_character_count") != 0 or quality.get("invalid_control_characters") != []:
            raise CollectionAuditError("Texto limpo com problema de codificacao")
    affectivity = documents[ARTICLE_A_ID]
    affectivity_review = affectivity.get("phase2e_review")
    if not isinstance(affectivity_review, dict) or affectivity_review.get("reviewed_blockquote_count") != 12:
        raise CollectionAuditError("Os doze blocos de afetividade precisam ser revisados individualmente")
    entries = affectivity_review.get("reviewed_blockquotes")
    if not isinstance(entries, list) or len(entries) != 12:
        raise CollectionAuditError("A revisao individual de afetividade esta incompleta")
    if any(entry.get("classification") != "direct_third_party_quote" for entry in entries if isinstance(entry, dict)):
        raise CollectionAuditError("A classificacao das citacoes de afetividade diverge da auditoria")
    if affectivity["states"]["current_state"] != "audited" or affectivity["states"]["approved_for_future_inclusion"]:
        raise CollectionAuditError("Afetividade deve permanecer audited enquanto houver citacoes inline pendentes")
    redistribution = documents[ARTICLE_C_ID]
    redistribution_review = redistribution.get("phase2e_review")
    if not isinstance(redistribution_review, dict):
        raise CollectionAuditError("A revisao de redistribuicao esta ausente")
    comparison = redistribution_review.get("html_comparison")
    if not isinstance(comparison, dict) or comparison.get("modal_tables_detected_outside_article_body") != 4:
        raise CollectionAuditError("A revisao precisa preservar as quatro tabelas do HTML oficial")
    if comparison.get("table_rows_preserved") != 35 or comparison.get("graph_only_information_not_reconstructed") is not True:
        raise CollectionAuditError("A representacao das tabelas ou o limite visual esta incorreto")
    if redistribution_review.get("inline_direct_quote_review", {}).get("substantive_spans_redacted") != 1:
        raise CollectionAuditError("A citacao direta substantiva de redistribuicao precisa ser redigida")
    if redistribution["states"]["current_state"] != "approved_for_future_inclusion" or not redistribution["states"]["approved_for_future_inclusion"]:
        raise CollectionAuditError("Redistribuicao precisa registrar a decisao limitada de aprovacao")
    redistributions_artifacts = _artifact_by_role(redistribution)
    if not redistributions_artifacts["clean_text"]["local_path"].endswith(".phase-2e.clean.txt"):
        raise CollectionAuditError("Redistribuicao precisa apontar para o derivado revisado da Fase 2E")
    duplicate_report = audit.get("deduplication_report")
    if not isinstance(duplicate_report, dict) or duplicate_report.get("automatic_content_removal") is not False:
        raise CollectionAuditError("Deduplicacao deve continuar somente informativa")
    if len(duplicate_report.get("pairs", [])) != 6:
        raise CollectionAuditError("Relatorio de duplicacao precisa cobrir todos os pares")
    future_plan = audit.get("future_corpus_plan")
    if not isinstance(future_plan, dict) or future_plan.get("status") != "proposal_only_no_collection_authorized":
        raise CollectionAuditError("O plano futuro nao pode autorizar coleta")
    if future_plan.get("collection_or_tokenization_started") is not False:
        raise CollectionAuditError("O plano futuro nao pode iniciar coleta ou tokenizacao")
    forbidden = _find_forbidden_content_fields(audit)
    if forbidden:
        raise CollectionAuditError(f"O manifesto nao pode conter conteudo integral: {', '.join(forbidden)}")
    return summarize_phase2e_audit(audit)


def validate_phase2e_local_artifacts(audit: dict[str, Any], root: str | Path = ".") -> None:
    """Validate hashes, read-only originals, and UTF-8 NFC derivatives locally."""

    validate_phase2e_audit(audit)
    root_path = Path(root)
    historical = audit["historical_phase_2d"]
    phase2d_path = _path(root_path, historical["path"])
    if not phase2d_path.exists() or _sha256_path(phase2d_path) != historical["sha256"]:
        raise CollectionAuditError("O manifesto historico da Fase 2D diverge do hash registrado")
    phase2d = json.loads(phase2d_path.read_text(encoding="utf-8"))
    validate_phase2d_local_artifacts(phase2d, root_path)
    for document in audit["documents"]:
        artifacts = _artifact_by_role(document)
        for artifact in artifacts.values():
            path = _path(root_path, artifact["local_path"])
            if not path.exists() or path.stat().st_size != artifact["bytes"]:
                raise CollectionAuditError(f"Artefato local ausente ou com tamanho divergente: {path}")
            if _sha256_path(path) != artifact["sha256"]:
                raise CollectionAuditError(f"SHA-256 divergente: {path}")
            if artifact["role"] in {"extracted_text", "clean_text"}:
                text = path.read_text(encoding="utf-8")
                if unicodedata.normalize("NFC", text) != text:
                    raise CollectionAuditError(f"Texto fora de NFC: {path}")
        original = _path(root_path, artifacts["original_html"]["local_path"])
        if not _is_read_only(original):
            raise CollectionAuditError("Um HTML original deixou de estar somente leitura")


def build_phase2e_audit(root: str | Path = ".") -> dict[str, Any]:
    """Create the Phase 2E metadata audit from already-present local artifacts."""

    root_path = Path(root)
    phase2d, phase2d_path = _load_phase2d(root_path)
    validate_phase2d_local_artifacts(phase2d, root_path)
    previous = _documents_by_id(phase2d)
    emag = copy.deepcopy(previous[EMAG_DOCUMENT_ID])
    conci = copy.deepcopy(previous[CONCI_DOCUMENT_ID])
    affectivity = _make_affectivity_review(root_path, previous[ARTICLE_A_ID])
    redistribution, redistribution_clean = _make_redistribution_review(root_path, previous[ARTICLE_C_ID])
    documents = [emag, conci, affectivity, redistribution]
    clean_texts = {
        document_id: _path(root_path, _artifact_by_role(document)["clean_text"]["local_path"]).read_text(encoding="utf-8")
        for document_id, document in ((EMAG_DOCUMENT_ID, emag), (CONCI_DOCUMENT_ID, conci), (ARTICLE_A_ID, affectivity))
    }
    clean_texts[ARTICLE_C_ID] = redistribution_clean
    audit = {
        "schema_version": SCHEMA_VERSION,
        "project": "ELYSIA-Seed v0.5",
        "phase": PHASE,
        "historical_phase_2b": copy.deepcopy(phase2d["historical_phase_2b"]),
        "historical_phase_2c": copy.deepcopy(phase2d["historical_phase_2c"]),
        "historical_phase_2d": {
            "path": PHASE2D_AUDIT_PATH,
            "schema_version": 3,
            "sha256": _sha256_path(phase2d_path),
            "preserved": True,
        },
        "historical_research_manifest": copy.deepcopy(phase2d["historical_research_manifest"]),
        "authorization": {
            "documents_reviewed": [ARTICLE_A_ID, ARTICLE_C_ID],
            "new_full_documents_authorized": 0,
            "new_full_documents_collected": 0,
        },
        "safeguards": _phase2e_safeguards(),
        "documents": documents,
        "deduplication_report": _deduplication_report(documents, clean_texts),
        "future_corpus_plan": _future_corpus_plan(),
    }
    validate_phase2e_audit(audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--audit", default=CURRENT_AUDIT_PATH)
    args = parser.parse_args()

    root = Path(args.root)
    audit = build_phase2e_audit(root)
    _write_json(_path(root, args.audit), audit)
    validate_phase2e_local_artifacts(audit, root)
    print(json.dumps(summarize_phase2e_audit(audit), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
