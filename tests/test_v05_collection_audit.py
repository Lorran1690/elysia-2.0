from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from learning.v05_collection_audit import (
    CollectionAuditError,
    _redact_third_party_quotes_in_code,
    _remove_acknowledgements,
    _remove_inline_urls,
    extract_blocks,
    render_blocks,
    validate_collection_audit,
    validate_local_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "data" / "corpus-v0.5" / "collection-audit.phase-2b.json"


def audit() -> dict[str, object]:
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def test_collection_audit_has_one_audited_html_document_and_two_metadata_reviews() -> None:
    summary = validate_collection_audit(audit())

    assert summary == {
        "document_id": "emag-v3-1-html",
        "state": "audited",
        "original_html_bytes": 245543,
        "clean_characters": 135493,
        "clean_words": 19693,
        "sections_extracted": 72,
        "future_inclusion_decision": "pending_explicit_approval",
        "educapes_reviews": 2,
    }


def test_collection_audit_rejects_embedded_source_content() -> None:
    invalid = copy.deepcopy(audit())
    invalid["documents"][0]["full_text"] = "texto que nao pertence ao manifesto"  # type: ignore[index]

    with pytest.raises(CollectionAuditError, match="conteudo integral"):
        validate_collection_audit(invalid)


def test_collection_audit_rejects_automatic_approval_for_future_inclusion() -> None:
    invalid = copy.deepcopy(audit())
    invalid["documents"][0]["states"]["approved_for_future_inclusion"] = True  # type: ignore[index]

    with pytest.raises(CollectionAuditError, match="estados da coleta"):
        validate_collection_audit(invalid)


def test_collection_audit_rejects_a_second_collected_document() -> None:
    invalid = copy.deepcopy(audit())
    invalid["documents"].append(copy.deepcopy(invalid["documents"][0]))  # type: ignore[index]

    with pytest.raises(CollectionAuditError, match="exatamente um documento"):
        validate_collection_audit(invalid)


def test_clean_projection_removes_ui_and_acknowledgements_but_keeps_technical_examples() -> None:
    html = """
    <html><body><div id="principal"><div class="p-esquerda">
      <h2>Agradecimentos</h2><p>Ana Pessoa</p>
      <h2>1. Introducao</h2><p>Conteudo tecnico https://example.test/redundant.</p>
      <p class="voltar">Voltar ao sumario</p>
      <div class="recomendacao">Ir ao exemplo navegavel</div>
      <label>Exemplo<textarea>&lt;blockquote&gt;Citacao externa&lt;/blockquote&gt;</textarea></label>
    </div><div class="p-direita"><h3>Sumario</h3></div></div></body></html>
    """

    blocks, exclusions, _ = extract_blocks(html, technical_column_only=True, clean=True)
    blocks, acknowledgement_blocks_removed = _remove_acknowledgements(blocks)
    blocks, third_party_redactions = _redact_third_party_quotes_in_code(blocks)
    blocks, urls_removed = _remove_inline_urls(blocks)
    rendered = render_blocks(blocks)

    assert acknowledgement_blocks_removed == 2
    assert third_party_redactions == 1
    assert urls_removed == 1
    assert exclusions["class:voltar"] == 1
    assert exclusions["class:recomendacao"] == 1
    assert "Ana Pessoa" not in rendered
    assert "Voltar ao sumario" not in rendered
    assert "Ir ao exemplo navegavel" not in rendered
    assert "https://example.test/redundant" not in rendered
    assert "[conteudo citacional de terceiro removido]" in rendered


def test_local_artifacts_match_the_audit_when_they_are_available() -> None:
    original = ROOT / "data" / "corpus-v0.5" / "originals" / "emag-v3-1.html"
    if not original.exists():
        pytest.skip("Artefatos de corpus sao locais e intencionalmente ignorados pelo Git")

    validate_local_artifacts(audit(), ROOT)
