"""Close the bounded Phase 2F textual-quality review for ELYSIA-Seed v0.5.

Only the four local documents already present in the corpus are inspected.
The module never fetches a source, trains a tokenizer, creates a data split, or
updates neural weights.  It freezes Phase 2E as an historical manifest and
builds Phase 2F derivatives only from the preserved SciELO HTML files.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from learning.v05_collection_audit import (
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
from learning.v05_final_quality_review import (
    ModalTable,
    _parse_modal_tables,
    _redact_redistribution_direct_quote,
    validate_phase2e_audit,
    validate_phase2e_local_artifacts,
)
from learning.v05_third_collection_audit import (
    ARTICLE_A,
    ARTICLE_A_ID,
    ARTICLE_C,
    ARTICLE_C_ID,
    CONCI_DOCUMENT_ID,
    EMAG_DOCUMENT_ID,
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
)


SCHEMA_VERSION = 5
PHASE = "corpus-consolidation-and-textual-quality-closure"
PHASE2E_AUDIT_PATH = "data/corpus-v0.5/collection-audit.phase-2e.json"
CURRENT_AUDIT_PATH = "data/corpus-v0.5/collection-audit.json"
AFFECTIVITY_REVISED_CLEAN = "data/corpus-v0.5/clean/scielo-rbeped-affectivity-2024.phase-2f.clean.txt"
REDISTRIBUTION_REVISED_EXTRACTED = "data/corpus-v0.5/processed/scielo-rap-redistribution-2024.phase-2f.extracted.txt"
REDISTRIBUTION_REVISED_CLEAN = "data/corpus-v0.5/clean/scielo-rap-redistribution-2024.phase-2f.clean.txt"


@dataclass(frozen=True)
class InlineQuoteDecision:
    """A manual semantic decision for one top-level inline quotation mark span."""

    paragraph_block_ordinal: int
    inline_quote_ordinal: int
    source_attribution: str | None
    classification: str
    action: str


# This map is intentionally explicit.  It distinguishes literal third-party
# quotations from quoted conceptual labels and an authorial pronunciation mark.
_AFFECTIVITY_INLINE_DECISIONS = (
    InlineQuoteDecision(16, 1, "Aristoteles, 2014", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(16, 2, "Aristoteles, 2014", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(17, 1, "Maritain, 1985", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(18, 1, "Maritain, 1985", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(18, 2, "Maritain, 1985", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(27, 1, None, "technical_expression", "retain_term"),
    InlineQuoteDecision(28, 1, "von Hildebrand, 2007", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(39, 1, "von Hildebrand, 2007", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(43, 1, "Maritain, 1984", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(45, 1, "Maritain, 1959", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(46, 1, "Maritain, 1959", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(48, 1, "Sucupira Lins, 2013", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(49, 1, "Sucupira Lins, 2018", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(49, 2, None, "technical_expression", "retain_term"),
    InlineQuoteDecision(52, 1, "Saltini, 2022", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(52, 2, "Saltini, 2022", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(57, 1, "Simmel, 2006", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(62, 1, "Sucupira Lins, 2005", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(63, 1, "Maritain, 1959", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(73, 1, "Nascentes, 1932", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(73, 2, "Lalande, 1993", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(73, 3, "Lewis, 2017", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(73, 4, None, "orthographic_symbol", "retain_symbol"),
    InlineQuoteDecision(75, 1, "Aristoteles, 2011", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(82, 1, "Aquino, 2015", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(82, 2, "Aquino, 2015", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(83, 1, "Piaget, 2014", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(85, 1, "Piaget, 2014", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(86, 1, "Piaget, 2014", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(93, 1, "von Hildebrand, 2007", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
    InlineQuoteDecision(94, 1, "von Hildebrand, 1996", "direct_third_party_quote", "redact_span_preserve_authorial_context"),
)

_REDISTRIBUTION_TABLE_REFERENCES = (
    ("ModalTablet1", "Tabela 1"),
    ("ModalTablet2", "Tabela 2"),
    ("ModalTablet3", "Tabela 3"),
)
_REDISTRIBUTION_UNRESOLVED_REFERENCE = "tabela 6"


def _phase2f_safeguards() -> dict[str, bool]:
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


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _documents_by_id(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    documents = audit.get("documents")
    if not isinstance(documents, list):
        raise CollectionAuditError("Manifesto sem documentos")
    indexed = {document.get("id"): document for document in documents if isinstance(document, dict)}
    expected = {EMAG_DOCUMENT_ID, CONCI_DOCUMENT_ID, ARTICLE_A_ID, ARTICLE_C_ID}
    if set(indexed) != expected:
        raise CollectionAuditError("Manifesto com conjunto inesperado de documentos")
    return indexed


def _inline_quote_spans(text: str) -> list[tuple[int, int, str]]:
    """Return top-level curly-quote spans and reject unbalanced source punctuation."""

    spans: list[tuple[int, int, str]] = []
    start: int | None = None
    depth = 0
    for index, character in enumerate(text):
        if character == "“":
            if depth == 0:
                start = index
            depth += 1
        elif character == "”" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                spans.append((start, index + 1, text[start : index + 1]))
                start = None
    if depth or start is not None:
        raise CollectionAuditError("Citacao inline com pontuacao de aspas desbalanceada no HTML original")
    return spans


def _review_affectivity_inline_quotes(blocks: list[TextBlock]) -> tuple[list[TextBlock], list[dict[str, Any]], dict[str, int]]:
    """Apply documented, span-level decisions while retaining authorial prose."""

    decisions = {
        (item.paragraph_block_ordinal, item.inline_quote_ordinal): item for item in _AFFECTIVITY_INLINE_DECISIONS
    }
    found: set[tuple[int, int]] = set()
    revised: list[TextBlock] = []
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()

    for block_ordinal, block in enumerate(blocks):
        if block.kind != "paragraph":
            revised.append(block)
            continue
        spans = _inline_quote_spans(block.text)
        if not spans:
            revised.append(block)
            continue
        parts: list[str] = []
        cursor = 0
        for quote_ordinal, (start, end, quote_text) in enumerate(spans, start=1):
            decision = decisions.get((block_ordinal, quote_ordinal))
            if decision is None:
                raise CollectionAuditError("Uma citacao inline de afetividade nao possui decisao individual registrada")
            found.add((block_ordinal, quote_ordinal))
            parts.append(block.text[cursor:start])
            replacement = quote_text
            if decision.classification == "direct_third_party_quote":
                replacement = "[citacao direta de terceiro removida]"
            parts.append(replacement)
            cursor = end
            counts[decision.classification] += 1
            rows.append(
                {
                    "paragraph_block_ordinal": block_ordinal,
                    "inline_quote_ordinal": quote_ordinal,
                    "span_characters": len(quote_text),
                    "span_sha256": _text_sha256(quote_text),
                    "source_attribution": decision.source_attribution,
                    "classification": decision.classification,
                    "action": decision.action,
                    "surrounding_authorial_analysis_or_paraphrase_preserved": True,
                }
            )
        parts.append(block.text[cursor:])
        revised.append(TextBlock(kind=block.kind, text="".join(parts), level=block.level))

    if found != set(decisions):
        missing = sorted(set(decisions) - found)
        unexpected = sorted(found - set(decisions))
        raise CollectionAuditError(f"Mapa de citacoes inline de afetividade divergente: faltam={missing}, extras={unexpected}")
    if counts != Counter({"direct_third_party_quote": 28, "technical_expression": 2, "orthographic_symbol": 1}):
        raise CollectionAuditError("A classificacao semantica das citacoes inline de afetividade diverge da auditoria")
    return revised, rows, dict(sorted(counts.items()))


def _make_affectivity_document(root: Path, prior: dict[str, Any]) -> tuple[dict[str, Any], str]:
    document = copy.deepcopy(prior)
    artifacts = _artifact_by_role(document)
    original_path = _path(root, artifacts["original_html"]["local_path"])
    headers_path = _path(root, artifacts["response_headers"]["local_path"])
    clean_path = _path(root, AFFECTIVITY_REVISED_CLEAN)
    if not _is_read_only(original_path):
        raise CollectionAuditError("O HTML original de afetividade precisa permanecer somente leitura")
    headers = _parse_response_snapshot(headers_path)
    html_text = original_path.read_text(encoding="utf-8")
    _assert_scielo_identity(html_text, ARTICLE_A)
    parsed = _parse_scielo_html(html_text)
    revised_blocks, review_rows, classifications = _review_affectivity_inline_quotes(parsed.blocks)
    clean_blocks, cleaning = _clean_scielo_blocks(revised_blocks)
    clean_text = unicodedata.normalize("NFC", _article_preamble(ARTICLE_A) + "\n\n" + render_blocks(clean_blocks))
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    clean_path.write_text(clean_text, encoding="utf-8", newline="\n")
    clean_personal = _personal_data_counts(clean_text)
    if any(clean_personal.values()):
        raise CollectionAuditError("A versao consolidada de afetividade reteve dados pessoais detectados")

    clean_artifact = _artifact_record(root, clean_path, "clean_text", immutable=False, format_name="text/plain; charset=UTF-8")
    document["local_artifacts"] = [
        copy.deepcopy(artifacts["original_html"]),
        copy.deepcopy(artifacts["response_headers"]),
        copy.deepcopy(artifacts["extracted_text"]),
        clean_artifact,
    ]
    quality = copy.deepcopy(document["quality"])
    quality.update(
        {
            "normalization": "Unicode NFC",
            "clean_text_statistics": _text_stats(clean_text),
            "sections_extracted": len([block for block in clean_blocks if block.kind == "heading"]),
            "sampled_sections": _sample_headings(clean_blocks),
            "invalid_control_characters": _invalid_control_characters(clean_text),
            "replacement_character_count": clean_text.count("\ufffd"),
            "personal_data_scan": {
                "source": _personal_data_counts(html_text),
                "clean": clean_personal,
                "note": "Contact material remains outside the cleaned article.",
            },
            "estimated_tokens": _estimate_tokens(_text_stats(clean_text)["words"]),
        }
    )
    document["quality"] = quality
    document["cleaning"] = {
        "rules": [
            "Preserve the read-only official HTML and build only UTF-8 NFC derivatives.",
            "Keep the Portuguese article body, quoted technical expressions, paraphrases, and authorial analysis.",
            "Replace each reviewed inline third-party direct quotation with a neutral marker while retaining surrounding paragraph context.",
            "Retain the twelve standalone quotation redactions inherited from the prior audit.",
            "Remove foreign abstracts, references, editorial material, and figure captions from the clean derivative.",
        ],
        "excluded_elements": cleaning,
        "third_party_handling": "Twenty-eight inline third-party quotation spans and twelve standalone quotation blocks are redacted in the clean derivative.",
    }
    document["phase2f_review"] = {
        "source_basis": "preserved_local_original_html_only",
        "inline_quote_review": {
            "inline_quote_marked_spans_reviewed": len(review_rows),
            "classification_counts": classifications,
            "reviewed_spans": review_rows,
            "third_party_direct_quotes_redacted": classifications["direct_third_party_quote"],
            "technical_expressions_retained": classifications["technical_expression"],
            "orthographic_symbols_retained": classifications["orthographic_symbol"],
            "citation_without_a_delimited_direct_quote_treated_as_paraphrase_or_authorial_analysis": True,
            "all_surrounding_authorial_context_preserved": True,
        },
        "historical_standalone_quote_blocks": {
            "reviewed_in_phase_2e": 12,
            "redaction_retained": True,
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
        "The preserved official HTML was reviewed at inline-span level; third-party direct quotations were redacted, "
        "while technical terms, paraphrases, and surrounding authorial analysis were retained. This does not authorize training."
    )
    if quality["original_html"]["http_declared_content_type"] != headers["content-type"]:
        raise CollectionAuditError("Metadado HTTP de afetividade diverge do cabecalho preservado")
    return document, clean_text


def _render_one_table(table: ModalTable) -> list[TextBlock]:
    blocks = [TextBlock(kind="heading", text=table.title, level=3)]
    for row in table.rows:
        cells: list[str] = []
        for cell in row:
            spans: list[str] = []
            if cell.colspan is not None:
                spans.append(f"colspan={cell.colspan}")
            if cell.rowspan is not None:
                spans.append(f"rowspan={cell.rowspan}")
            value = cell.text
            if spans:
                value = f"{value} [{' '.join(spans)}]".strip()
            cells.append(value)
        blocks.append(TextBlock(kind="table_row", text=" | ".join(cells)))
    return blocks


def _locate_redistribution_associations(parsed_blocks: list[TextBlock], tables: list[ModalTable]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    table_by_id = {table.identifier: table for table in tables}
    if set(table_by_id) != {"ModalTablet1", "ModalTablet2", "ModalTablet3", "ModalTablet4"}:
        raise CollectionAuditError("As quatro tabelas oficiais de redistribuicao precisam permanecer identificadas")
    anchors: dict[str, str] = {}
    associations: dict[str, dict[str, Any]] = {}
    for modal_id, label in _REDISTRIBUTION_TABLE_REFERENCES:
        candidates = [
            (ordinal, block)
            for ordinal, block in enumerate(parsed_blocks)
            if block.kind == "paragraph" and label.casefold() in block.text.casefold()
        ]
        if len(candidates) != 1:
            raise CollectionAuditError(f"A referencia corporal de {label} precisa ser unica no HTML original")
        ordinal, block = candidates[0]
        anchors[modal_id] = block.text
        associations[modal_id] = {
            "modal_table_identifier": modal_id,
            "official_title": table_by_id[modal_id].title,
            "source_table_label": label,
            "body_reference_block_ordinal": ordinal,
            "body_reference_sha256": _text_sha256(block.text),
            "association": "unambiguous_exact_table_label",
            "rendering_decision": "insert_after_original_body_reference",
        }

    unresolved = [
        (ordinal, block)
        for ordinal, block in enumerate(parsed_blocks)
        if block.kind == "paragraph" and _REDISTRIBUTION_UNRESOLVED_REFERENCE in block.text.casefold()
    ]
    if len(unresolved) != 1:
        raise CollectionAuditError("A mencao numericamente divergente de tabela em redistribuicao precisa permanecer documentada")
    ordinal, block = unresolved[0]
    associations["ModalTablet4"] = {
        "modal_table_identifier": "ModalTablet4",
        "official_title": table_by_id["ModalTablet4"].title,
        "source_table_label": "Tabela 4",
        "body_reference_candidate_label": "Tabela 6",
        "body_reference_candidate_block_ordinal": ordinal,
        "body_reference_candidate_sha256": _text_sha256(block.text),
        "association": "not_proven_source_number_mismatch",
        "rendering_decision": "retain_in_unmatched_tables_appendix",
    }
    return associations, anchors


def _insert_redistribution_tables(
    blocks: list[TextBlock], tables: list[ModalTable], anchors: dict[str, str]
) -> list[TextBlock]:
    table_by_id = {table.identifier: table for table in tables}
    inserted: Counter[str] = Counter()
    output: list[TextBlock] = []
    for block in blocks:
        output.append(block)
        for modal_id, anchor_text in anchors.items():
            if block.kind == "paragraph" and block.text == anchor_text:
                output.extend(_render_one_table(table_by_id[modal_id]))
                inserted[modal_id] += 1
    expected = {modal_id for modal_id, _ in _REDISTRIBUTION_TABLE_REFERENCES}
    if set(inserted) != expected or any(count != 1 for count in inserted.values()):
        raise CollectionAuditError("As tabelas com associacao inequivoca precisam ser inseridas uma unica vez")
    output.append(TextBlock(kind="heading", text="Tabela textual preservada sem associacao inequivoca no corpo", level=2))
    output.extend(_render_one_table(table_by_id["ModalTablet4"]))
    return output


def _make_redistribution_document(root: Path, prior: dict[str, Any]) -> tuple[dict[str, Any], str]:
    document = copy.deepcopy(prior)
    prior_artifacts = _artifact_by_role(prior)
    original_path = _path(root, prior_artifacts["original_html"]["local_path"])
    headers_path = _path(root, prior_artifacts["response_headers"]["local_path"])
    extracted_path = _path(root, REDISTRIBUTION_REVISED_EXTRACTED)
    clean_path = _path(root, REDISTRIBUTION_REVISED_CLEAN)
    if not _is_read_only(original_path):
        raise CollectionAuditError("O HTML original de redistribuicao precisa permanecer somente leitura")
    headers = _parse_response_snapshot(headers_path)
    html_text = original_path.read_text(encoding="utf-8")
    _assert_scielo_identity(html_text, ARTICLE_C)
    parsed = _parse_scielo_html(html_text)
    tables = _parse_modal_tables(html_text)
    associations, anchors = _locate_redistribution_associations(parsed.blocks, tables)
    clean_blocks, cleaning = _clean_scielo_blocks(parsed.blocks)
    clean_blocks, quoted_spans = _redact_redistribution_direct_quote(clean_blocks)
    extracted_blocks = _insert_redistribution_tables(parsed.blocks, tables, anchors)
    clean_blocks = _insert_redistribution_tables(clean_blocks, tables, anchors)
    extracted_text = unicodedata.normalize("NFC", _article_preamble(ARTICLE_C) + "\n\n" + render_blocks(extracted_blocks))
    clean_text = unicodedata.normalize("NFC", _article_preamble(ARTICLE_C) + "\n\n" + render_blocks(clean_blocks))
    for path, text in ((extracted_path, extracted_text), (clean_path, clean_text)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    clean_personal = _personal_data_counts(clean_text)
    if any(clean_personal.values()):
        raise CollectionAuditError("A versao consolidada de redistribuicao reteve dados pessoais detectados")
    table_rows = sum(len(table.rows) for table in tables)
    numeric_cells = sum(
        1
        for table in tables
        for row in table.rows
        for cell in row
        if re.fullmatch(r"-?\d+(?:[.,]\d+)?", cell.text)
    )
    phase2e_comparison = prior["phase2e_review"]["html_comparison"]
    if table_rows != phase2e_comparison["table_rows_preserved"] or numeric_cells != phase2e_comparison["numeric_cells_preserved_without_reconstruction"]:
        raise CollectionAuditError("A consolidacao de redistribuicao alterou dados tabulares recuperados")

    extracted_artifact = _artifact_record(root, extracted_path, "extracted_text", immutable=False, format_name="text/plain; charset=UTF-8")
    clean_artifact = _artifact_record(root, clean_path, "clean_text", immutable=False, format_name="text/plain; charset=UTF-8")
    document["local_artifacts"] = [
        copy.deepcopy(prior_artifacts["original_html"]),
        copy.deepcopy(prior_artifacts["response_headers"]),
        extracted_artifact,
        clean_artifact,
    ]
    quality = copy.deepcopy(document["quality"])
    quality.update(
        {
            "normalization": "Unicode NFC",
            "extracted_text_statistics": _text_stats(extracted_text),
            "clean_text_statistics": _text_stats(clean_text),
            "table_rows_extracted": table_rows,
            "table_modal_count": len(tables),
            "table_numeric_cells_preserved": numeric_cells,
            "sections_extracted": len([block for block in clean_blocks if block.kind == "heading"]),
            "sampled_sections": _sample_headings(clean_blocks),
            "invalid_control_characters": _invalid_control_characters(clean_text),
            "replacement_character_count": clean_text.count("\ufffd"),
            "personal_data_scan": {
                "source": _personal_data_counts(html_text),
                "clean": clean_personal,
                "note": "Contact material remains outside the cleaned article and table transcription.",
            },
            "estimated_tokens": _estimate_tokens(_text_stats(clean_text)["words"]),
        }
    )
    document["quality"] = quality
    cleaning["inline_direct_quote_spans_redacted"] += quoted_spans
    document["cleaning"] = {
        "rules": [
            "Preserve the read-only official HTML and make only UTF-8 NFC derivatives.",
            "Keep the four official text tables in source row and cell order without reconstructing values.",
            "Place tables 1, 2, and 3 directly after their unique original body references.",
            "Keep table 4 in a distinct appendix because the body references Tabela 6 while the official modal labels it Tabela 4.",
            "Remove foreign abstracts, references, editorial material, figures, and graph captions from the cleaned derivative.",
            "Redact the one reviewed substantive direct quotation while keeping surrounding authorial analysis.",
        ],
        "excluded_elements": cleaning,
        "third_party_handling": "No PDF, XML, image, attachment, or external link was downloaded; graph-only information remains unavailable.",
    }
    document["phase2f_review"] = {
        "source_basis": "preserved_local_original_html_only",
        "table_reference_review": {
            "official_modal_tables_reviewed": len(tables),
            "table_rows_preserved_without_value_reconstruction": table_rows,
            "numeric_cells_preserved_without_value_reconstruction": numeric_cells,
            "associations": [associations[f"ModalTablet{ordinal}"] for ordinal in range(1, 5)],
            "unambiguous_associations_rendered_near_body_reference": 3,
            "unresolved_association_retained_without_forced_relocation": 1,
        },
        "inline_direct_quote_review": {
            "substantive_spans_redacted": quoted_spans,
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
        "The official HTML tables remain complete and unchanged. Three are rendered next to unique body references; "
        "the fourth remains separately preserved because a source numbering mismatch prevents a proven relocation."
    )
    if quality["original_html"]["http_declared_content_type"] != headers["content-type"]:
        raise CollectionAuditError("Metadado HTTP de redistribuicao diverge do cabecalho preservado")
    return document, clean_text


def _future_expansion_plan() -> dict[str, Any]:
    """A metadata-only proposal; every candidate still needs a separate preflight."""

    return {
        "status": "proposal_only_no_collection_authorized",
        "new_documents_downloaded": 0,
        "tokenizer_or_bpe_trained": False,
        "training_started": False,
        "target_scale": {
            "minimum_tokens_for_bounded_experiments": 5_000_000,
            "preferred_tokens_before_claiming_broader_language_coverage": 20_000_000,
            "note": "These are collection planning targets, not a claim that either volume is sufficient for a capable general-purpose language model.",
        },
        "candidate_families": [
            {
                "id": "elysia-original-conversations",
                "genre": "original conversational Portuguese from consenting contributors",
                "language_variant": "Portuguese Brasileiro contemporaneo",
                "source_url": None,
                "license": "CC0 1.0 preferred; alternatively CC BY 4.0 with a signed contributor authorization",
                "estimated_tokens": {"minimum": 600_000, "maximum": 1_500_000},
                "status": "requires_authorship_protocol_and_explicit_collection_approval",
                "risks": ["personal data", "copied prompts", "synthetic dialogue", "speaker imbalance"],
            },
            {
                "id": "elysia-original-explanatory-and-support-texts",
                "genre": "commissioned explanatory, instructional, and support prose",
                "language_variant": "Portuguese Brasileiro contemporaneo",
                "source_url": None,
                "license": "CC BY 4.0 or CC0 1.0 under a documented project authorship agreement",
                "estimated_tokens": {"minimum": 800_000, "maximum": 2_000_000},
                "status": "requires_authorship_protocol_and_explicit_collection_approval",
                "risks": ["templated duplication", "synthetic content", "narrow domain coverage"],
            },
            {
                "id": "ibict-enap-omeka-guide",
                "genre": "technical documentation",
                "language_variant": "Portuguese Brasileiro contemporaneo",
                "source_url": "https://repositorio.enap.gov.br/bitstream/1/3162/1/Guia%20do%20usu%C3%A1rio%20do%20Omeka%20-%20Ebook.pdf",
                "license": "CC BY 4.0 stated by the official item",
                "estimated_tokens": {"minimum": 35_000, "maximum": 70_000},
                "status": "requires_item_level_preflight_and_explicit_collection_approval",
                "risks": ["PDF extraction", "third-party screenshots", "references", "small volume"],
            },
            {
                "id": "scielo-rac-item-level-articles",
                "genre": "informative and explanatory academic prose",
                "language_variant": "Portuguese Brasileiro contemporary articles selected individually",
                "source_url": "https://www.scielo.br/journal/rac/about/?ilang=pt_BR",
                "license": "CC BY 4.0 at journal level; each selected article must confirm its own license and third-party handling",
                "estimated_tokens": {"minimum": 1_500_000, "maximum": 4_500_000},
                "status": "requires_per_article_license_audit_and_explicit_collection_approval",
                "risks": ["quotations", "references", "figures", "author and topic concentration"],
            },
            {
                "id": "inep-em-aberto-item-level-articles",
                "genre": "educational and policy-oriented explanatory prose",
                "language_variant": "Portuguese Brasileiro contemporary articles selected individually",
                "source_url": "https://emaberto.inep.gov.br/ojs3/index.php/emaberto/about/submissions",
                "license": "CC BY 4.0 reuse statement; verify every canonical article representation before collection",
                "estimated_tokens": {"minimum": 500_000, "maximum": 1_800_000},
                "status": "requires_per_article_license_audit_and_explicit_collection_approval",
                "risks": ["article-level license exceptions", "citations", "PDF-only layouts", "academic-register bias"],
            },
            {
                "id": "sgb-open-api-documentation",
                "genre": "technical API documentation and structured explanatory text",
                "language_variant": "Portuguese Brasileiro contemporaneo",
                "source_url": "https://geoservicos.sgb.gov.br/ogcapi?f=html",
                "license": "CC BY 4.0 stated by the official service",
                "estimated_tokens": {"minimum": 80_000, "maximum": 300_000},
                "status": "requires_endpoint_scope_review_and_explicit_collection_approval",
                "risks": ["generated schema repetition", "structured-data dominance", "low conversational value"],
            },
        ],
        "future_split_isolation_policy": {
            "unit": "whole document, author group, source family, and derivation group",
            "rule": "No source, author group, translated version, near duplicate, or conversation contributor may cross train, validation, and final test partitions.",
            "reserved_final_test": "Hold out approved, never-inspected documents from at least two genres and separate authors until one final evaluation.",
        },
        "collection_sequence": [
            "Write and audit the original-dialogue authorship and privacy protocol.",
            "Select small, diverse, item-level samples with license and provenance preflight records.",
            "Audit text quality, third-party quotations, personal data, and duplication before any corpus inclusion decision.",
            "Only after a separately approved corpus composition, define splits and train a tokenizer from training text alone.",
        ],
    }


def summarize_phase2f_audit(audit: dict[str, Any]) -> dict[str, Any]:
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
        "affectivity_inline_quote_spans_reviewed": affectivity["phase2f_review"]["inline_quote_review"]["inline_quote_marked_spans_reviewed"],
        "affectivity_direct_quotes_redacted": affectivity["phase2f_review"]["inline_quote_review"]["third_party_direct_quotes_redacted"],
        "redistribution_unambiguous_table_associations": redistribution["phase2f_review"]["table_reference_review"]["unambiguous_associations_rendered_near_body_reference"],
        "redistribution_unresolved_table_associations": redistribution["phase2f_review"]["table_reference_review"]["unresolved_association_retained_without_forced_relocation"],
        "approved_for_future_inclusion": [
            document["id"] for document in documents if document["states"]["approved_for_future_inclusion"]
        ],
    }


def _assert_document_quality(document: dict[str, Any]) -> None:
    artifacts = _artifact_by_role(document)
    if set(artifacts) != {"original_html", "response_headers", "extracted_text", "clean_text"}:
        raise CollectionAuditError("Cada documento consolidado precisa manter quatro artefatos locais")
    for artifact in artifacts.values():
        if artifact.get("git_ignored") is not True:
            raise CollectionAuditError("Conteudo integral do corpus nao pode entrar no Git")
        if not re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("sha256", ""))):
            raise CollectionAuditError("Artefato local sem SHA-256")
    quality = document.get("quality")
    if not isinstance(quality, dict):
        raise CollectionAuditError("Documento sem metadados de qualidade")
    scan = quality.get("personal_data_scan", {})
    clean_scan = scan.get("clean", scan) if isinstance(scan, dict) else {}
    if any(clean_scan.get(key) != 0 for key in ("email_matches", "cpf_matches", "phone_matches")):
        raise CollectionAuditError("Texto limpo consolidado reteve dados pessoais detectados")
    if quality.get("replacement_character_count") != 0 or quality.get("invalid_control_characters") != []:
        raise CollectionAuditError("Texto limpo consolidado tem problema de codificacao")


def validate_phase2f_audit(audit: dict[str, Any]) -> dict[str, Any]:
    """Validate tracked Phase 2F metadata without opening local corpus files."""

    if audit.get("schema_version") != SCHEMA_VERSION or audit.get("phase") != PHASE:
        raise CollectionAuditError("O manifesto precisa registrar Fase 2F e schema 5")
    historical = audit.get("historical_phase_2e")
    if not isinstance(historical, dict) or historical.get("path") != PHASE2E_AUDIT_PATH:
        raise CollectionAuditError("A Fase 2E precisa permanecer congelada como historica")
    if historical.get("schema_version") != 4 or historical.get("preserved") is not True:
        raise CollectionAuditError("A referencia historica da Fase 2E esta incompleta")
    if not re.fullmatch(r"[0-9a-f]{64}", str(historical.get("sha256", ""))):
        raise CollectionAuditError("A Fase 2E historica precisa ter SHA-256")
    if audit.get("safeguards") != _phase2f_safeguards():
        raise CollectionAuditError("Uma salvaguarda obrigatoria da Fase 2F foi alterada")
    if audit.get("authorization") != {
        "documents_reviewed": [EMAG_DOCUMENT_ID, CONCI_DOCUMENT_ID, ARTICLE_A_ID, ARTICLE_C_ID],
        "documents_with_new_local_derivatives": [ARTICLE_A_ID, ARTICLE_C_ID],
        "new_full_documents_authorized": 0,
        "new_full_documents_collected": 0,
    }:
        raise CollectionAuditError("A autorizacao da Fase 2F foi ampliada")

    documents = _documents_by_id(audit)
    if any(document["states"].get("current_state") != "approved_for_future_inclusion" for document in documents.values()):
        raise CollectionAuditError("Todos os quatro documentos precisam de uma decisao explicita apos a consolidacao")
    for document in documents.values():
        _assert_document_quality(document)
    affectivity = documents[ARTICLE_A_ID]
    affectivity_review = affectivity.get("phase2f_review", {}).get("inline_quote_review", {})
    if affectivity_review.get("inline_quote_marked_spans_reviewed") != 31:
        raise CollectionAuditError("A revisao inline de afetividade precisa cobrir 31 trechos")
    if affectivity_review.get("classification_counts") != {
        "direct_third_party_quote": 28,
        "orthographic_symbol": 1,
        "technical_expression": 2,
    }:
        raise CollectionAuditError("A classificacao de afetividade nao corresponde a revisao individual")
    rows = affectivity_review.get("reviewed_spans")
    if not isinstance(rows, list) or len(rows) != 31:
        raise CollectionAuditError("Os trechos inline de afetividade precisam permanecer individualmente registrados")
    if affectivity_review.get("all_surrounding_authorial_context_preserved") is not True:
        raise CollectionAuditError("O contexto autoral de afetividade precisa ser preservado")
    if not _artifact_by_role(affectivity)["clean_text"]["local_path"].endswith(".phase-2f.clean.txt"):
        raise CollectionAuditError("Afetividade precisa apontar para o derivado consolidado da Fase 2F")

    redistribution = documents[ARTICLE_C_ID]
    table_review = redistribution.get("phase2f_review", {}).get("table_reference_review", {})
    if table_review.get("official_modal_tables_reviewed") != 4 or table_review.get("table_rows_preserved_without_value_reconstruction") != 35:
        raise CollectionAuditError("As quatro tabelas de redistribuicao precisam permanecer completas")
    if table_review.get("unambiguous_associations_rendered_near_body_reference") != 3:
        raise CollectionAuditError("Tres tabelas de redistribuicao precisam ficar junto a referencias inequivocas")
    if table_review.get("unresolved_association_retained_without_forced_relocation") != 1:
        raise CollectionAuditError("A limitacao numerica da quarta tabela precisa permanecer explicitamente registrada")
    associations = table_review.get("associations")
    if not isinstance(associations, list) or len(associations) != 4:
        raise CollectionAuditError("As associacoes das quatro tabelas precisam ser registradas")
    if [entry.get("association") for entry in associations[:3]] != ["unambiguous_exact_table_label"] * 3:
        raise CollectionAuditError("As tres primeiras tabelas precisam ter associacao inequivoca")
    if associations[3].get("association") != "not_proven_source_number_mismatch":
        raise CollectionAuditError("A quarta tabela nao pode ser associada por inferencia")
    redistribution_artifacts = _artifact_by_role(redistribution)
    if not redistribution_artifacts["clean_text"]["local_path"].endswith(".phase-2f.clean.txt") or not redistribution_artifacts["extracted_text"]["local_path"].endswith(".phase-2f.extracted.txt"):
        raise CollectionAuditError("Redistribuicao precisa apontar para derivados consolidados da Fase 2F")

    duplicate_report = audit.get("deduplication_report")
    if not isinstance(duplicate_report, dict) or duplicate_report.get("automatic_content_removal") is not False:
        raise CollectionAuditError("Deduplicacao precisa continuar somente informativa")
    if len(duplicate_report.get("pairs", [])) != 6:
        raise CollectionAuditError("Relatorio de duplicacao precisa cobrir todos os pares")
    plan = audit.get("future_corpus_expansion_plan")
    if not isinstance(plan, dict) or plan.get("status") != "proposal_only_no_collection_authorized":
        raise CollectionAuditError("O plano de expansao nao pode autorizar coleta")
    if plan.get("new_documents_downloaded") != 0 or plan.get("tokenizer_or_bpe_trained") is not False or plan.get("training_started") is not False:
        raise CollectionAuditError("O plano de expansao nao pode iniciar coleta, tokenizacao ou treinamento")
    candidates = plan.get("candidate_families")
    if not isinstance(candidates, list) or len(candidates) < 5:
        raise CollectionAuditError("O plano de expansao precisa propor fontes diversas")
    forbidden = _find_forbidden_content_fields(audit)
    if forbidden:
        raise CollectionAuditError(f"O manifesto nao pode conter conteudo integral: {', '.join(forbidden)}")
    return summarize_phase2f_audit(audit)


def validate_phase2f_local_artifacts(audit: dict[str, Any], root: str | Path = ".") -> None:
    """Validate local hashes, NFC text, provenance, and immutable originals."""

    validate_phase2f_audit(audit)
    root_path = Path(root)
    historical = audit["historical_phase_2e"]
    phase2e_path = _path(root_path, historical["path"])
    if not phase2e_path.exists() or _sha256_path(phase2e_path) != historical["sha256"]:
        raise CollectionAuditError("O snapshot historico da Fase 2E diverge do hash registrado")
    phase2e = json.loads(phase2e_path.read_text(encoding="utf-8"))
    validate_phase2e_local_artifacts(phase2e, root_path)
    prior_documents = _documents_by_id(phase2e)
    for document in audit["documents"]:
        artifacts = _artifact_by_role(document)
        prior_artifacts = _artifact_by_role(prior_documents[document["id"]])
        for role, artifact in artifacts.items():
            path = _path(root_path, artifact["local_path"])
            if not path.exists() or path.stat().st_size != artifact["bytes"]:
                raise CollectionAuditError(f"Artefato local ausente ou com tamanho divergente: {path}")
            if _sha256_path(path) != artifact["sha256"]:
                raise CollectionAuditError(f"SHA-256 divergente: {path}")
            if role in {"extracted_text", "clean_text"}:
                text = path.read_text(encoding="utf-8")
                if unicodedata.normalize("NFC", text) != text:
                    raise CollectionAuditError(f"Texto fora de NFC: {path}")
        if artifacts["original_html"] != prior_artifacts["original_html"] or artifacts["response_headers"] != prior_artifacts["response_headers"]:
            raise CollectionAuditError("A consolidacao nao pode alterar a proveniencia dos originais")
        original = _path(root_path, artifacts["original_html"]["local_path"])
        if not _is_read_only(original):
            raise CollectionAuditError("Um HTML original deixou de estar somente leitura")


def _load_phase2e(root: Path) -> tuple[dict[str, Any], Path]:
    path = _path(root, PHASE2E_AUDIT_PATH)
    if not path.exists():
        raise CollectionAuditError("O snapshot congelado da Fase 2E esta ausente")
    audit = json.loads(path.read_text(encoding="utf-8"))
    validate_phase2e_audit(audit)
    return audit, path


def build_phase2f_audit(root: str | Path = ".") -> dict[str, Any]:
    """Create the Phase 2F metadata audit from the preserved local artifacts."""

    root_path = Path(root)
    phase2e, phase2e_path = _load_phase2e(root_path)
    validate_phase2e_local_artifacts(phase2e, root_path)
    prior = _documents_by_id(phase2e)
    emag = copy.deepcopy(prior[EMAG_DOCUMENT_ID])
    conci = copy.deepcopy(prior[CONCI_DOCUMENT_ID])
    affectivity, affectivity_clean = _make_affectivity_document(root_path, prior[ARTICLE_A_ID])
    redistribution, redistribution_clean = _make_redistribution_document(root_path, prior[ARTICLE_C_ID])
    documents = [emag, conci, affectivity, redistribution]
    clean_texts = {
        EMAG_DOCUMENT_ID: _path(root_path, _artifact_by_role(emag)["clean_text"]["local_path"]).read_text(encoding="utf-8"),
        CONCI_DOCUMENT_ID: _path(root_path, _artifact_by_role(conci)["clean_text"]["local_path"]).read_text(encoding="utf-8"),
        ARTICLE_A_ID: affectivity_clean,
        ARTICLE_C_ID: redistribution_clean,
    }
    audit = {
        "schema_version": SCHEMA_VERSION,
        "project": "ELYSIA-Seed v0.5",
        "phase": PHASE,
        "historical_phase_2b": copy.deepcopy(phase2e["historical_phase_2b"]),
        "historical_phase_2c": copy.deepcopy(phase2e["historical_phase_2c"]),
        "historical_phase_2d": copy.deepcopy(phase2e["historical_phase_2d"]),
        "historical_phase_2e": {
            "path": PHASE2E_AUDIT_PATH,
            "schema_version": 4,
            "sha256": _sha256_path(phase2e_path),
            "preserved": True,
        },
        "historical_research_manifest": copy.deepcopy(phase2e["historical_research_manifest"]),
        "authorization": {
            "documents_reviewed": [EMAG_DOCUMENT_ID, CONCI_DOCUMENT_ID, ARTICLE_A_ID, ARTICLE_C_ID],
            "documents_with_new_local_derivatives": [ARTICLE_A_ID, ARTICLE_C_ID],
            "new_full_documents_authorized": 0,
            "new_full_documents_collected": 0,
        },
        "safeguards": _phase2f_safeguards(),
        "documents": documents,
        "deduplication_report": _deduplication_report(documents, clean_texts),
        "future_corpus_expansion_plan": _future_expansion_plan(),
    }
    validate_phase2f_audit(audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--audit", default=CURRENT_AUDIT_PATH)
    args = parser.parse_args()
    root = Path(args.root)
    audit = build_phase2f_audit(root)
    _write_json(_path(root, args.audit), audit)
    validate_phase2f_local_artifacts(audit, root)
    print(json.dumps(summarize_phase2f_audit(audit), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
