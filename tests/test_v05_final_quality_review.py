from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from learning.v05_collection_audit import CollectionAuditError, TextBlock
from learning.v05_final_quality_review import (
    ARTICLE_A_ID,
    ARTICLE_C_ID,
    _parse_modal_tables,
    _redact_redistribution_direct_quote,
    validate_phase2e_audit,
    validate_phase2e_local_artifacts,
)
from learning.v05_third_collection_audit import CONCI_DOCUMENT_ID, EMAG_DOCUMENT_ID


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "data" / "corpus-v0.5" / "collection-audit.phase-2e.json"
PHASE2D_PATH = ROOT / "data" / "corpus-v0.5" / "collection-audit.phase-2d.json"


def audit() -> dict[str, object]:
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def test_phase_2e_freezes_phase_2d_and_records_no_new_collection() -> None:
    summary = validate_phase2e_audit(audit())

    assert summary == {
        "schema_version": 4,
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
                "state": "audited",
                "clean_characters": 38377,
                "clean_words": 5883,
            },
            {
                "id": ARTICLE_C_ID,
                "state": "approved_for_future_inclusion",
                "clean_characters": 60881,
                "clean_words": 8996,
            },
        ],
        "new_full_documents_collected": 0,
        "affectivity_quote_blocks_reviewed": 12,
        "redistribution_modal_tables_preserved": 4,
        "approved_for_future_inclusion": [EMAG_DOCUMENT_ID, CONCI_DOCUMENT_ID, ARTICLE_C_ID],
    }


def test_phase_2e_records_the_actual_phase_2d_manifest_hash() -> None:
    expected = hashlib.sha256(PHASE2D_PATH.read_bytes()).hexdigest()

    assert audit()["historical_phase_2d"]["sha256"] == expected


def test_phase_2e_keeps_affectivity_audited_until_inline_quote_review_is_complete() -> None:
    document = next(document for document in audit()["documents"] if document["id"] == ARTICLE_A_ID)  # type: ignore[index]
    review = document["phase2e_review"]

    assert review["reviewed_blockquote_count"] == 12
    assert len(review["reviewed_blockquotes"]) == 12
    assert all(item["classification"] == "direct_third_party_quote" for item in review["reviewed_blockquotes"])
    assert all(item["authorial_context_before_and_after_preserved"] for item in review["reviewed_blockquotes"])
    assert document["states"]["current_state"] == "audited"
    assert document["states"]["approved_for_future_inclusion"] is False


def test_phase_2e_rejects_lost_redistribution_table_rows() -> None:
    invalid = copy.deepcopy(audit())
    redistribution = next(document for document in invalid["documents"] if document["id"] == ARTICLE_C_ID)  # type: ignore[index]
    redistribution["phase2e_review"]["html_comparison"]["table_rows_preserved"] = 34

    with pytest.raises(CollectionAuditError, match="representacao das tabelas"):
        validate_phase2e_audit(invalid)


def test_modal_table_parser_preserves_text_order_and_structural_spans() -> None:
    tables = _parse_modal_tables(
        """
        <div id="ModalTablet1"><h5>Tabela 1</h5><table><tr><th>Ano</th><th>Valor</th></tr><tr><td>2022</td><td>8,85</td></tr></table></div>
        <div id="ModalTablet2"><h5>Tabela 2</h5><table><tr><td>Faixa</td></tr></table></div>
        <div id="ModalTablet3"><h5>Tabela 3</h5><table><tr><th colspan="4">BRASIL</th></tr></table></div>
        <div id="ModalTablet4"><h5>Tabela 4</h5><table><tr><td rowspan="2">RecPr</td></tr></table></div>
        """
    )

    assert [table.identifier for table in tables] == ["ModalTablet1", "ModalTablet2", "ModalTablet3", "ModalTablet4"]
    assert tables[0].rows[1][1].text == "8,85"
    assert tables[2].rows[0][0].colspan == 4
    assert tables[3].rows[0][0].rowspan == 2


def test_redistribution_quote_redaction_keeps_surrounding_analysis() -> None:
    blocks, count = _redact_redistribution_direct_quote(
        [
            TextBlock(
                kind="paragraph",
                text=(
                    "Prado afirma que \u201ca federa\u00e7\u00e3o \u00e9, em \u00faltima inst\u00e2ncia, um arranjo pol\u00edtico-institucional "
                    "que deve, necessariamente, emular de alguma forma o Estado unit\u00e1rio\u201d, e os autores analisam o efeito."
                ),
            )
        ]
    )

    assert count == 1
    assert "citacao direta de terceiro removida" in blocks[0].text
    assert "autores analisam o efeito" in blocks[0].text


def test_phase_2e_local_artifacts_match_when_available() -> None:
    original = ROOT / "data" / "corpus-v0.5" / "originals" / "scielo-rap-redistribution-2024.html"
    if not original.exists():
        pytest.skip("Artefatos de corpus sao locais e intencionalmente ignorados pelo Git")

    validate_phase2e_local_artifacts(audit(), ROOT)
