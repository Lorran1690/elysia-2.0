from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from learning.v05_collection_audit import CollectionAuditError, TextBlock
from learning.v05_second_collection_audit import (
    CONCI_DOCUMENT_ID,
    EMAG_DOCUMENT_ID,
    _clean_conci_blocks,
    _decode_conci_html,
    validate_phase2c_audit,
    validate_phase2c_local_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "data" / "corpus-v0.5" / "collection-audit.phase-2c.json"


def audit() -> dict[str, object]:
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def test_phase_2c_audit_records_only_the_authorized_review_and_one_new_collection() -> None:
    summary = validate_phase2c_audit(audit())

    assert summary == {
        "schema_version": 2,
        "documents": [
            {
                "id": EMAG_DOCUMENT_ID,
                "state": "approved_for_future_inclusion",
                "clean_characters": 135493,
                "clean_words": 19693,
            },
            {
                "id": CONCI_DOCUMENT_ID,
                "state": "audited",
                "clean_characters": 31130,
                "clean_words": 4742,
            },
        ],
        "new_full_documents_collected": 1,
        "approved_for_future_inclusion": [EMAG_DOCUMENT_ID],
        "conci_future_inclusion_decision": "pending_explicit_approval",
    }


def test_phase_2c_audit_rejects_any_extra_document() -> None:
    invalid = copy.deepcopy(audit())
    invalid["documents"].append(copy.deepcopy(invalid["documents"][1]))  # type: ignore[index]

    with pytest.raises(CollectionAuditError, match="exatamente os dois documentos"):
        validate_phase2c_audit(invalid)


def test_phase_2c_audit_rejects_automatic_conci_future_approval() -> None:
    invalid = copy.deepcopy(audit())
    conci = next(document for document in invalid["documents"] if document["id"] == CONCI_DOCUMENT_ID)  # type: ignore[index]
    conci["states"]["approved_for_future_inclusion"] = True

    with pytest.raises(CollectionAuditError, match="nao pode receber aprovacao futura automaticamente"):
        validate_phase2c_audit(invalid)


def test_phase_2c_audit_rejects_detected_personal_data_in_clean_conci_text() -> None:
    invalid = copy.deepcopy(audit())
    conci = next(document for document in invalid["documents"] if document["id"] == CONCI_DOCUMENT_ID)  # type: ignore[index]
    conci["quality"]["personal_data_scan"]["clean"]["email_matches"] = 1

    with pytest.raises(CollectionAuditError, match="dados pessoais detectados"):
        validate_phase2c_audit(invalid)


def test_phase_2c_audit_rejects_changed_phase_2b_history() -> None:
    invalid = copy.deepcopy(audit())
    invalid["historical_phase_2b"]["path"] = "data/corpus-v0.5/collection-audit.json"  # type: ignore[index]

    with pytest.raises(CollectionAuditError, match="Fase 2B"):
        validate_phase2c_audit(invalid)


def test_conci_cleaning_keeps_portuguese_article_and_removes_unneeded_material() -> None:
    blocks = [
        TextBlock(kind="paragraph", text="Capa e contato"),
        TextBlock(kind="heading", text="RESUMO"),
        TextBlock(kind="paragraph", text="Resumo em portugues."),
        TextBlock(kind="paragraph", text="Palavras-chave: teste."),
        TextBlock(kind="heading", text="ABSTRACT"),
        TextBlock(kind="paragraph", text="English abstract."),
        TextBlock(kind="heading", text="RESUMEN"),
        TextBlock(kind="paragraph", text="Resumen en espanol."),
        TextBlock(kind="heading", text="1 INTRODUCAO"),
        TextBlock(kind="paragraph", text="Argumento dos autores."),
        TextBlock(kind="paragraph", text="\u201cCitacao externa\u201d (AUTOR, 2020)."),
        TextBlock(kind="paragraph", text="Figura 1 - Artefato visual"),
        TextBlock(kind="paragraph", text="Fonte: Terceiro."),
        TextBlock(kind="table_row", text="Dado | Valor"),
        TextBlock(kind="heading", text="5 CONSIDERACOES FINAIS"),
        TextBlock(kind="paragraph", text="Conclusao dos autores."),
        TextBlock(kind="heading", text="REFERENCIAS"),
        TextBlock(kind="paragraph", text="Referencia de terceiro."),
    ]

    cleaned, counters = _clean_conci_blocks(blocks)
    rendered = "\n".join(block.text for block in cleaned)

    assert "Capa e contato" not in rendered
    assert "English abstract" not in rendered
    assert "Resumen en espanol" not in rendered
    assert "Citacao externa" not in rendered
    assert "[citacao direta de terceiro removida]" in rendered
    assert "Figura 1" not in rendered
    assert "Fonte: Terceiro" not in rendered
    assert "Dado | Valor" in rendered
    assert "Referencia de terceiro" not in rendered
    assert counters == {
        "front_matter_blocks_removed": 1,
        "foreign_abstract_blocks_removed": 4,
        "references_blocks_removed": 2,
        "figure_caption_blocks_removed": 1,
        "figure_source_blocks_removed": 1,
        "direct_quote_blocks_redacted": 1,
    }


def test_conci_decoder_honors_the_embedded_windows_1252_declaration() -> None:
    original = b'<meta http-equiv="Content-Type" content="text/html; charset=windows-1252"><p>Licen\xe7as</p>'

    text, encoding = _decode_conci_html(original)

    assert "Licenças" in text
    assert encoding == {
        "embedded_charset": "windows-1252",
        "utf8_valid": False,
        "derived_text_encoding": "UTF-8",
    }


def test_phase_2c_local_artifacts_match_when_available() -> None:
    original = ROOT / "data" / "corpus-v0.5" / "originals" / "conci-2021-licenses.html"
    if not original.exists():
        pytest.skip("Artefatos de corpus sao locais e intencionalmente ignorados pelo Git")

    validate_phase2c_local_artifacts(audit(), ROOT)
