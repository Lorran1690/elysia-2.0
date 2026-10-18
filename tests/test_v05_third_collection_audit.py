from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from learning.v05_collection_audit import CollectionAuditError, TextBlock, render_blocks
from learning.v05_third_collection_audit import (
    ARTICLE_A_ID,
    ARTICLE_B_ID,
    ARTICLE_C_ID,
    CONCI_DOCUMENT_ID,
    EMAG_DOCUMENT_ID,
    _clean_conci_phase2d_blocks,
    _clean_scielo_blocks,
    _parse_scielo_html,
    validate_phase2d_audit,
    validate_phase2d_local_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "data" / "corpus-v0.5" / "collection-audit.phase-2d.json"


def audit() -> dict[str, object]:
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def test_phase_2d_audit_records_only_the_two_approved_html_downloads() -> None:
    summary = validate_phase2d_audit(audit())

    assert summary == {
        "schema_version": 3,
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
                "state": "audited",
                "clean_characters": 57456,
                "clean_words": 8449,
            },
        ],
        "new_full_documents_collected": 2,
        "blocked_candidates": [ARTICLE_B_ID],
        "approved_for_future_inclusion": [EMAG_DOCUMENT_ID, CONCI_DOCUMENT_ID],
    }


def test_phase_2d_rejects_collection_of_article_b_under_cc_by_nc() -> None:
    invalid = copy.deepcopy(audit())
    blocked = next(item for item in invalid["preflight"] if item["id"] == ARTICLE_B_ID)  # type: ignore[index]
    blocked["content_downloaded"] = True

    with pytest.raises(CollectionAuditError, match="artigo B"):
        validate_phase2d_audit(invalid)


def test_phase_2d_rejects_automatic_future_approval_of_new_scielo_article() -> None:
    invalid = copy.deepcopy(audit())
    article = next(document for document in invalid["documents"] if document["id"] == ARTICLE_A_ID)  # type: ignore[index]
    article["states"]["current_state"] = "approved_for_future_inclusion"
    article["states"]["approved_for_future_inclusion"] = True

    with pytest.raises(CollectionAuditError, match="CC BY 4.0"):
        validate_phase2d_audit(invalid)


def test_phase_2d_rejects_missing_conci_redaction_review() -> None:
    invalid = copy.deepcopy(audit())
    conci = next(document for document in invalid["documents"] if document["id"] == CONCI_DOCUMENT_ID)  # type: ignore[index]
    conci["phase2d_review"]["reviewed_prior_redactions"].pop()

    with pytest.raises(CollectionAuditError, match="historico e a revisao"):
        validate_phase2d_audit(invalid)


def test_scielo_cleaning_preserves_authorial_context_and_removes_quote_and_references() -> None:
    html = """
    <article id="articleText">
      <div class="articleSection"><h2>Resumo</h2><p>Resumo em portugues.</p></div>
      <div class="articleSection"><h2>Abstract</h2><p>English abstract.</p></div>
      <div class="articleSection"><h2>Resumen</h2><p>Resumen en espanol.</p></div>
      <div class="articleSection">
        <h2>1. Introducao</h2>
        <p>Analise dos autores "[...] citacao externa" (AUTOR, 2020) continua depois da citacao.</p>
        <p>Primeiro paragrafo do desenvolvimento.</p>
        <p>Segundo paragrafo do desenvolvimento.</p>
        <p>Terceiro paragrafo do desenvolvimento.</p>
        <p>Quarto paragrafo do desenvolvimento.</p>
        <p>Quinto paragrafo do desenvolvimento.</p>
        <blockquote>Citacao direta de terceiro.</blockquote>
        <table><tr><th>Coluna</th><th>Valor</th></tr></table>
        <figcaption>Figura 1 Conteudo visual</figcaption>
        <h2>Referencias</h2><p>Referencia de terceiro.</p>
      </div>
    </article>
    """

    parsed = _parse_scielo_html(html)
    cleaned, counters = _clean_scielo_blocks(parsed.blocks)
    rendered = render_blocks(cleaned)

    assert parsed.blockquotes == 1
    assert parsed.table_rows == 1
    assert "English abstract" not in rendered
    assert "Resumen en espanol" not in rendered
    assert "Referencia de terceiro" not in rendered
    assert "Conteudo visual" not in rendered
    assert "Analise dos autores" in rendered
    assert "continua depois da citacao" in rendered
    assert "citacao externa" not in rendered
    assert rendered.count("[citacao direta de terceiro removida]") == 2
    assert "| Coluna | Valor |" in rendered
    assert counters == {
        "front_matter_blocks_removed": 0,
        "foreign_abstract_blocks_removed": 4,
        "references_blocks_removed": 2,
        "figure_caption_blocks_removed": 1,
        "direct_quote_blocks_redacted": 1,
        "inline_direct_quote_spans_redacted": 1,
        "consecutive_blocks_removed": 0,
    }


def test_conci_review_restores_false_positives_and_redacts_only_direct_quotes() -> None:
    blocks = [
        TextBlock(kind="paragraph", text="Capa e contato"),
        TextBlock(kind="heading", text="RESUMO"),
        TextBlock(kind="paragraph", text="Resumo em portugues."),
        TextBlock(kind="heading", text="ABSTRACT"),
        TextBlock(kind="paragraph", text="English abstract."),
        TextBlock(kind="heading", text="1 INTRODUCAO"),
        TextBlock(kind="paragraph", text='Uso autoral de "termo" (AUTOR, 2020) permanece.'),
        TextBlock(kind="paragraph", text="[ ... ]"),
        TextBlock(kind="paragraph", text="[...] citacao direta de terceiro (AUTOR, 2020)."),
        TextBlock(
            kind="paragraph",
            text='Analise dos autores "[...] citacao direta" (AUTOR, 2020) permanece depois.',
        ),
        TextBlock(kind="heading", text="REFERENCIAS"),
        TextBlock(kind="paragraph", text="Referencia externa."),
    ]

    cleaned, counters = _clean_conci_phase2d_blocks(blocks)
    rendered = render_blocks(cleaned)

    assert 'Uso autoral de "termo"' in rendered
    assert "Referencia externa" not in rendered
    assert "[...] citacao direta de terceiro (AUTOR, 2020)." not in rendered
    assert "Analise dos autores" in rendered
    assert "permanece depois" in rendered
    assert counters["direct_quote_blocks_redacted"] == 1
    assert counters["inline_direct_quote_spans_redacted"] == 1
    assert rendered.count("[citacao direta de terceiro removida]") == 2


def test_phase_2d_local_artifacts_match_when_available() -> None:
    original = ROOT / "data" / "corpus-v0.5" / "originals" / "scielo-rbeped-affectivity-2024.html"
    if not original.exists():
        pytest.skip("Artefatos de corpus sao locais e intencionalmente ignorados pelo Git")

    validate_phase2d_local_artifacts(audit(), ROOT)
