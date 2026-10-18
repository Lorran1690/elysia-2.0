from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from learning.v05_collection_audit import CollectionAuditError
from learning.v05_corpus_consolidation import (
    ARTICLE_A_ID,
    ARTICLE_C_ID,
    _inline_quote_spans,
    _locate_redistribution_associations,
    _parse_modal_tables,
    _parse_scielo_html,
    _review_affectivity_inline_quotes,
    validate_phase2f_audit,
    validate_phase2f_local_artifacts,
)
from learning.v05_third_collection_audit import CONCI_DOCUMENT_ID, EMAG_DOCUMENT_ID


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "data" / "corpus-v0.5" / "collection-audit.json"
PHASE2E_PATH = ROOT / "data" / "corpus-v0.5" / "collection-audit.phase-2e.json"


def audit() -> dict[str, object]:
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def test_phase_2f_closes_the_four_document_quality_audit_without_collection() -> None:
    summary = validate_phase2f_audit(audit())

    assert summary == {
        "schema_version": 5,
        "documents": [
            {
                "id": EMAG_DOCUMENT_ID,
                "state": "approved_for_future_inclusion",
                "clean_characters": 135493,
                "clean_words": 19693,
            },
            {
                "id": CONCI_DOCUMENT_ID,
                "state": "approved_for_future_inclusion",
                "clean_characters": 34161,
                "clean_words": 5207,
            },
            {
                "id": ARTICLE_A_ID,
                "state": "approved_for_future_inclusion",
                "clean_characters": 35051,
                "clean_words": 5333,
            },
            {
                "id": ARTICLE_C_ID,
                "state": "approved_for_future_inclusion",
                "clean_characters": 60897,
                "clean_words": 8998,
            },
        ],
        "new_full_documents_collected": 0,
        "affectivity_inline_quote_spans_reviewed": 31,
        "affectivity_direct_quotes_redacted": 28,
        "redistribution_unambiguous_table_associations": 3,
        "redistribution_unresolved_table_associations": 1,
        "approved_for_future_inclusion": [EMAG_DOCUMENT_ID, CONCI_DOCUMENT_ID, ARTICLE_A_ID, ARTICLE_C_ID],
    }


def test_phase_2f_records_the_actual_frozen_phase_2e_hash() -> None:
    expected = hashlib.sha256(PHASE2E_PATH.read_bytes()).hexdigest()

    assert audit()["historical_phase_2e"]["sha256"] == expected


def test_phase_2f_rejects_missing_affectivity_quote_redaction() -> None:
    invalid = copy.deepcopy(audit())
    affectivity = next(document for document in invalid["documents"] if document["id"] == ARTICLE_A_ID)  # type: ignore[index]
    affectivity["phase2f_review"]["inline_quote_review"]["classification_counts"]["direct_third_party_quote"] = 27

    with pytest.raises(CollectionAuditError, match="classificacao de afetividade"):
        validate_phase2f_audit(invalid)


def test_phase_2f_rejects_forced_association_for_the_fourth_table() -> None:
    invalid = copy.deepcopy(audit())
    redistribution = next(document for document in invalid["documents"] if document["id"] == ARTICLE_C_ID)  # type: ignore[index]
    redistribution["phase2f_review"]["table_reference_review"]["associations"][3]["association"] = "unambiguous_exact_table_label"

    with pytest.raises(CollectionAuditError, match="quarta tabela"):
        validate_phase2f_audit(invalid)


def test_inline_quote_parser_preserves_nested_single_quotes() -> None:
    spans = _inline_quote_spans("Antes “termo com ‘simbolo’ interno”. Depois “outro trecho”.")

    assert [span[2] for span in spans] == ["“termo com ‘simbolo’ interno”", "“outro trecho”"]


def test_phase_2f_local_artifacts_match_when_available() -> None:
    original = ROOT / "data" / "corpus-v0.5" / "originals" / "scielo-rbeped-affectivity-2024.html"
    if not original.exists():
        pytest.skip("Artefatos de corpus sao locais e intencionalmente ignorados pelo Git")

    validate_phase2f_local_artifacts(audit(), ROOT)


def test_phase_2f_reviews_every_affectivity_inline_span_when_available() -> None:
    original = ROOT / "data" / "corpus-v0.5" / "originals" / "scielo-rbeped-affectivity-2024.html"
    if not original.exists():
        pytest.skip("HTML original permanece apenas no armazenamento local auditado")

    parsed = _parse_scielo_html(original.read_text(encoding="utf-8"))
    revised, rows, counts = _review_affectivity_inline_quotes(parsed.blocks)

    assert len(rows) == 31
    assert counts == {"direct_third_party_quote": 28, "orthographic_symbol": 1, "technical_expression": 2}
    assert "fenomenologia realista da afetividade" in revised[27].text
    assert revised[16].text.count("[citacao direta de terceiro removida]") == 2


def test_phase_2f_preserves_the_table_number_mismatch_when_available() -> None:
    original = ROOT / "data" / "corpus-v0.5" / "originals" / "scielo-rap-redistribution-2024.html"
    if not original.exists():
        pytest.skip("HTML original permanece apenas no armazenamento local auditado")

    html = original.read_text(encoding="utf-8")
    parsed = _parse_scielo_html(html)
    associations, anchors = _locate_redistribution_associations(parsed.blocks, _parse_modal_tables(html))

    assert set(anchors) == {"ModalTablet1", "ModalTablet2", "ModalTablet3"}
    assert associations["ModalTablet4"]["association"] == "not_proven_source_number_mismatch"
    assert associations["ModalTablet4"]["body_reference_candidate_label"] == "Tabela 6"
