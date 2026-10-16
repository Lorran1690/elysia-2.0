"""Build and validate the Phase 2C, metadata-only collection audit.

The module is deliberately local-only. Network preflight and the one authorized
ConCI HTML download happen outside this code. This script reads those preserved
files, creates derived local UTF-8 text, and records hashes and transformations
without embedding corpus text in Git.
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
    _artifact,
    _ascii_key,
    _deduplicate_consecutive_blocks,
    _document_preamble,
    _estimate_tokens,
    _find_forbidden_content_fields,
    _invalid_control_characters,
    _is_read_only,
    _normalize_inline,
    _parse_headers,
    _sha256_path,
    _text_stats,
    _write_json,
    extract_blocks,
    render_blocks,
    validate_collection_audit as validate_phase2b_audit,
    validate_local_artifacts as validate_phase2b_local_artifacts,
)


SCHEMA_VERSION = 2
PHASE = "controlled-multi-document-collection"
PHASE2B_AUDIT_PATH = "data/corpus-v0.5/collection-audit.phase-2b.json"
EMAG_DOCUMENT_ID = "emag-v3-1-html"
CONCI_DOCUMENT_ID = "conci-2021-alternative-licenses-html"
CONCI_TITLE = (
    "Licencas alternativas de protecao intelectual atribuidas a periodicos "
    "tecnicos e/ou cientificos da area da Ciencia da Informacao no contexto "
    "da Ciencia Aberta"
)
CONCI_AUTHORS = [
    "Natalia Rodrigues Silva",
    "Nivaldo Calixto Ribeiro",
    "Dalgiza Andrade Oliveira",
]
CONCI_DOI = "10.33467/conci.v4i.15670"
CONCI_LANDING_URL = "https://periodicos.ufs.br/conci/article/view/15670"
CONCI_HTML_URL = "https://periodicos.ufs.br/conci/article/download/15670/12129?inline=1"
CONCI_HOST = "periodicos.ufs.br"
CONCI_LICENSE = "CC BY 4.0"
REQUIRED_ARTIFACT_ROLES = {
    "original_html",
    "response_headers",
    "extracted_text",
    "clean_text",
}
FORBIDDEN_SAFEGAURDS = {
    "ollama_used",
    "external_model_or_weights_used",
    "ai_api_used",
    "additional_dataset_downloaded",
    "scielo_content_collected",
    "bpe_trained",
    "final_split_created",
    "neural_training_started",
    "v04_weights_or_checkpoints_modified",
    "pdf_a_downloaded",
    "xml_downloaded",
    "other_conci_representation_downloaded",
}


@dataclass(frozen=True)
class ConciParseResult:
    """Text blocks projected from the publisher-provided Word HTML."""

    blocks: list[TextBlock]
    paragraphs: int
    table_rows: int
    image_elements: int


class _ConciHtmlParser(HTMLParser):
    """Extract paragraph and table-row text from the selected ConCI HTML."""

    _SKIP_TAGS = frozenset({"head", "script", "style", "noscript"})
    _VOID_TAGS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[TextBlock] = []
        self.paragraphs = 0
        self.table_rows = 0
        self.image_elements = 0
        self._skip_depth = 0
        self._table_depth = 0
        self._paragraph_parts: list[str] | None = None
        self._row_cells: list[str] | None = None
        self._cell_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.casefold()
        if normalized_tag in self._SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if normalized_tag == "img":
            self.image_elements += 1
            return
        if normalized_tag == "table":
            self._table_depth += 1
            return
        if normalized_tag == "tr" and self._table_depth == 1:
            self._row_cells = []
            return
        if normalized_tag in {"td", "th"} and self._row_cells is not None:
            self._cell_parts = []
            return
        if normalized_tag == "p" and self._table_depth == 0:
            self._paragraph_parts = []

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.casefold() not in self._VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._cell_parts is not None:
            self._cell_parts.append(data)
        elif self._paragraph_parts is not None:
            self._paragraph_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.casefold()
        if normalized_tag in self._SKIP_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if normalized_tag == "p" and self._table_depth == 0 and self._paragraph_parts is not None:
            text = _normalize_inline("".join(self._paragraph_parts))
            self._paragraph_parts = None
            if text:
                self.blocks.append(_classify_conci_paragraph(text))
                self.paragraphs += 1
            return
        if normalized_tag in {"td", "th"} and self._cell_parts is not None and self._row_cells is not None:
            text = _normalize_inline("".join(self._cell_parts))
            self._cell_parts = None
            self._row_cells.append(text)
            return
        if normalized_tag == "tr" and self._table_depth == 1 and self._row_cells is not None:
            cells = [cell for cell in self._row_cells if cell]
            self._row_cells = None
            if cells:
                self.blocks.append(TextBlock(kind="table_row", text=" | ".join(cells)))
                self.table_rows += 1
            return
        if normalized_tag == "table" and self._table_depth:
            self._table_depth -= 1


def _classify_conci_paragraph(text: str) -> TextBlock:
    if _is_conci_heading(text):
        return TextBlock(kind="heading", text=text, level=2)
    if re.match(r"^[\u2022\u2023\u25e6\-*]\s+", text):
        return TextBlock(kind="list_item", text=re.sub(r"^[\u2022\u2023\u25e6\-*]\s+", "", text))
    return TextBlock(kind="paragraph", text=text)


def _is_conci_heading(text: str) -> bool:
    key = _ascii_key(text)
    if key in {"resumo", "abstract", "resumen", "referencias"}:
        return True
    return bool(re.match(r"^\d+(?:\.\d+)?\.?\s+", key))


def _parse_conci_html(html_text: str) -> ConciParseResult:
    parser = _ConciHtmlParser()
    parser.feed(html_text)
    parser.close()
    if parser.paragraphs < 100 or parser.table_rows < 1:
        raise CollectionAuditError("O HTML ConCI nao contem a estrutura textual esperada")
    return ConciParseResult(
        blocks=parser.blocks,
        paragraphs=parser.paragraphs,
        table_rows=parser.table_rows,
        image_elements=parser.image_elements,
    )


def _detect_embedded_charset(original_bytes: bytes) -> str:
    match = re.search(
        rb"charset\s*=\s*[\"']?([A-Za-z0-9_-]+)",
        original_bytes[:8192],
        flags=re.IGNORECASE,
    )
    if not match:
        raise CollectionAuditError("O HTML ConCI nao declara um charset interno")
    return match.group(1).decode("ascii").casefold()


def _decode_conci_html(original_bytes: bytes) -> tuple[str, dict[str, Any]]:
    embedded_charset = _detect_embedded_charset(original_bytes)
    if embedded_charset not in {"windows-1252", "cp1252"}:
        raise CollectionAuditError("O HTML ConCI nao declarou o charset Windows-1252 esperado")
    try:
        original_bytes.decode("utf-8")
    except UnicodeDecodeError:
        utf8_valid = False
    else:
        utf8_valid = True
    try:
        html_text = original_bytes.decode("windows-1252")
    except UnicodeDecodeError as error:
        raise CollectionAuditError("O HTML ConCI nao pode ser decodificado como Windows-1252") from error
    return html_text, {
        "embedded_charset": "windows-1252",
        "utf8_valid": utf8_valid,
        "derived_text_encoding": "UTF-8",
    }


def _assert_conci_identity(html_text: str) -> None:
    # Word can split a visible author name across formatting tags. Validate the
    # rendered text rather than relying on adjacent bytes in the HTML markup.
    key = _ascii_key(re.sub(r"<[^>]+>", " ", html_text))
    required_fragments = (
        _ascii_key(CONCI_TITLE),
        _ascii_key(CONCI_AUTHORS[0]),
        _ascii_key(CONCI_AUTHORS[1]),
        _ascii_key(CONCI_AUTHORS[2]),
        "resumo",
        "1 introducao",
        "referencias",
    )
    missing = [fragment for fragment in required_fragments if fragment not in key]
    if missing:
        raise CollectionAuditError("O HTML ConCI nao confirma identidade, autoria e corpo do artigo autorizados")


def _is_article_start(block: TextBlock) -> bool:
    return block.kind == "heading" and _ascii_key(block.text).startswith("1 introducao")


def _is_figure_caption(block: TextBlock) -> bool:
    return block.kind == "paragraph" and _ascii_key(block.text).startswith("figura ")


def _looks_like_direct_third_party_quote(text: str) -> bool:
    quote_marker = any(marker in text for marker in ("[...]", "\u201c", "\u201d", '"'))
    citation = re.search(r"\([A-ZÀ-Ý][A-Za-zÀ-ÿ .;,&-]*(?:19|20)\d{2}[^)]*\)", text)
    return quote_marker and citation is not None


def _clean_conci_blocks(blocks: list[TextBlock]) -> tuple[list[TextBlock], dict[str, int]]:
    """Keep the Portuguese article, leaving aside portal-independent extras."""
    result: list[TextBlock] = []
    stage = "front_matter"
    counters = {
        "front_matter_blocks_removed": 0,
        "foreign_abstract_blocks_removed": 0,
        "references_blocks_removed": 0,
        "figure_caption_blocks_removed": 0,
        "figure_source_blocks_removed": 0,
        "direct_quote_blocks_redacted": 0,
    }
    previous_was_figure_caption = False

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
            elif _is_article_start(block):
                stage = "article"
                result.append(block)
            else:
                result.append(block)
            continue
        if stage == "foreign_abstract":
            if _is_article_start(block):
                stage = "article"
                result.append(block)
            else:
                counters["foreign_abstract_blocks_removed"] += 1
            continue

        if key == "referencias":
            counters["references_blocks_removed"] += len(blocks) - index
            break
        if _is_figure_caption(block):
            previous_was_figure_caption = True
            counters["figure_caption_blocks_removed"] += 1
            continue
        if previous_was_figure_caption and block.kind == "paragraph" and key.startswith("fonte:"):
            previous_was_figure_caption = False
            counters["figure_source_blocks_removed"] += 1
            continue
        previous_was_figure_caption = False
        if block.kind == "paragraph" and _looks_like_direct_third_party_quote(block.text):
            result.append(TextBlock(kind="paragraph", text="[citacao direta de terceiro removida]"))
            counters["direct_quote_blocks_redacted"] += 1
            continue
        result.append(block)

    if stage != "article":
        raise CollectionAuditError("Nao foi possivel localizar o artigo em portugues apos os resumos")
    if not result or not any(_is_article_start(block) for block in result):
        raise CollectionAuditError("A limpeza ConCI removeu o inicio do artigo")
    return _deduplicate_consecutive_blocks(result)[0], counters


def _conci_preamble() -> str:
    return "\n\n".join(
        (
            f"# {CONCI_TITLE}",
            f"Autores: {', '.join(CONCI_AUTHORS)}",
            "Publicacao: ConCI: Convergencias em Ciencia da Informacao, v. 4, 2021, p. 1-30",
            f"DOI: {CONCI_DOI}",
            f"Licenca: {CONCI_LICENSE}",
            f"Fonte oficial: {CONCI_LANDING_URL}",
        )
    )


def _sample_headings(blocks: list[TextBlock]) -> dict[str, str]:
    headings = [block.text for block in blocks if block.kind == "heading"]
    if len(headings) < 3:
        raise CollectionAuditError("O texto ConCI limpo nao possui secoes suficientes para amostragem")
    return {
        "start": headings[0],
        "middle": headings[len(headings) // 2],
        "end": headings[-1],
    }


def _count_personal_data(text: str) -> dict[str, int]:
    # A bare 4-4 number is commonly an ISSN in this article, not a telephone.
    phone_pattern = r"(?<!\d)(?:\+55\s*)?(?:\(\d{2}\)\s*|\d{2}\s+)\d{4,5}-\d{4}(?!\d)"
    return {
        "email_matches": len(re.findall(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", text)),
        "cpf_matches": len(re.findall(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", text)),
        "phone_matches": len(re.findall(phone_pattern, text)),
    }


def _make_conci_document(
    *,
    original_path: Path,
    headers_path: Path,
    extracted_path: Path,
    clean_path: Path,
    preflight_at: str,
    collected_at: str,
) -> dict[str, Any]:
    if not _is_read_only(original_path):
        raise CollectionAuditError("O HTML original ConCI precisa permanecer marcado como somente leitura")
    headers = _parse_headers(headers_path)
    original_bytes = original_path.read_bytes()
    html_text, encoding = _decode_conci_html(original_bytes)
    _assert_conci_identity(html_text)
    parsed = _parse_conci_html(html_text)
    clean_blocks, cleaning_counts = _clean_conci_blocks(parsed.blocks)
    clean_blocks, duplicate_blocks_removed = _deduplicate_consecutive_blocks(clean_blocks)

    extracted_text = unicodedata.normalize("NFC", _conci_preamble() + "\n\n" + render_blocks(parsed.blocks))
    clean_text = unicodedata.normalize("NFC", _conci_preamble() + "\n\n" + render_blocks(clean_blocks))
    extracted_path.parent.mkdir(parents=True, exist_ok=True)
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    extracted_path.write_text(extracted_text, encoding="utf-8", newline="\n")
    clean_path.write_text(clean_text, encoding="utf-8", newline="\n")

    original_artifact = _artifact(
        original_path,
        "original_html",
        immutable=True,
        format_name="text/html; embedded charset=windows-1252; HTTP header declared UTF-8",
    )
    headers_artifact = _artifact(headers_path, "response_headers", immutable=False, format_name="text/plain; HTTP headers")
    extracted_artifact = _artifact(extracted_path, "extracted_text", immutable=False, format_name="text/plain; charset=UTF-8")
    clean_artifact = _artifact(clean_path, "clean_text", immutable=False, format_name="text/plain; charset=UTF-8")
    clean_stats = _text_stats(clean_text)
    extracted_stats = _text_stats(extracted_text)
    original_personal_data = _count_personal_data(html_text)
    clean_personal_data = _count_personal_data(clean_text)

    return {
        "id": CONCI_DOCUMENT_ID,
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
            "title": CONCI_TITLE,
            "authors": CONCI_AUTHORS,
            "publication": "ConCI: Convergencias em Ciencia da Informacao",
            "edition": "v. 4, 2021, artigo original, p. 1-30",
            "doi": CONCI_DOI,
        },
        "source": {
            "landing_page_url": CONCI_LANDING_URL,
            "requested_url": CONCI_HTML_URL,
            "final_url": CONCI_HTML_URL,
            "host": CONCI_HOST,
            "preflight_checked_at": preflight_at,
            "collected_at": collected_at,
            "http_status": 200,
            "redirect_detected": False,
            "content_type": headers["content-type"],
            "http_date": headers.get("date"),
            "relevant_headers_artifact": headers_artifact["local_path"],
            "available_representations": [
                {"format": "HTML", "selected": True, "downloaded": True},
                {"format": "XML", "selected": False, "downloaded": False},
                {"format": "PDF-A", "selected": False, "downloaded": False},
            ],
        },
        "license": {
            "name": CONCI_LICENSE,
            "declared_on_landing_page": True,
            "evidence_url": CONCI_LANDING_URL,
            "attribution_obligations": "Creditar Natalia Rodrigues Silva, Nivaldo Calixto Ribeiro, Dalgiza Andrade Oliveira e a publicacao inicial na ConCI; indicar a licenca CC BY 4.0 e alteracoes em derivados.",
        },
        "local_artifacts": [original_artifact, headers_artifact, extracted_artifact, clean_artifact],
        "quality": {
            "original_html": {
                "bytes": original_artifact["bytes"],
                "sha256": original_artifact["sha256"],
                "http_declared_content_type": headers["content-type"],
                "embedded_charset": encoding["embedded_charset"],
                "utf8_valid": encoding["utf8_valid"],
                "encoding_mismatch_recorded": True,
            },
            "derived_text_encoding": encoding["derived_text_encoding"],
            "normalization": "Unicode NFC",
            "extracted_text_statistics": extracted_stats,
            "clean_text_statistics": clean_stats,
            "paragraphs_extracted": parsed.paragraphs,
            "table_rows_extracted": parsed.table_rows,
            "image_elements_omitted": parsed.image_elements,
            "sections_extracted": len([block for block in clean_blocks if block.kind == "heading"]),
            "sampled_sections": _sample_headings(clean_blocks),
            "invalid_control_characters": _invalid_control_characters(clean_text),
            "replacement_character_count": clean_text.count("\ufffd"),
            "deduplication": {
                "strategy": "Somente blocos consecutivos exatamente iguais sao removidos apos a limpeza dirigida.",
                "consecutive_blocks_removed": duplicate_blocks_removed,
            },
            "personal_data_scan": {
                "source": original_personal_data,
                "clean": clean_personal_data,
                "note": "Identificadores de autoria necessarios para atribuicao permanecem apenas no preambulo. Dados de contato da materia preliminar nao seguem para a versao limpa.",
            },
            "estimated_tokens": _estimate_tokens(clean_stats["words"]),
        },
        "cleaning": {
            "rules": [
                "Preservar o HTML original em Windows-1252 e converter somente textos derivados para UTF-8 normalizado em NFC.",
                "Extrair paragrafos e linhas de tabela do HTML Word fornecido pela revista, preservando o resumo em portugues, as secoes do artigo, listas e tabelas textuais.",
                "Excluir capa, autores, afiliacoes e contato da materia preliminar, pois a atribuicao estruturada permanece no preambulo local.",
                "Excluir resumos em ingles e espanhol para manter a colecao linguistica em portugues brasileiro.",
                "Excluir figura, legenda e fonte imediatamente associada quando a imagem nao e preservada.",
                "Excluir referencias e bibliografia para evitar material repetitivo e conteudo de terceiros sem auditoria individual.",
                "Redigir blocos que aparentam conter citacao direta de terceiros, preservando somente uma marcacao de remocao.",
                "Remover somente blocos consecutivos exatamente iguais; nao resumir nem reescrever a argumentacao dos autores.",
            ],
            "excluded_elements": {**cleaning_counts, "consecutive_blocks_removed": duplicate_blocks_removed},
            "third_party_handling": "Nenhuma referencia externa, imagem ou anexo foi baixado. Bibliografia, legendas de figura e blocos identificados como citacao direta de terceiro foram retirados da versao limpa.",
        },
        "future_inclusion_decision": "pending_explicit_approval",
        "future_inclusion_reason": "A coleta e auditoria desta representacao nao autorizam tokenizacao, split, treinamento ou inclusao automatica no futuro corpus.",
    }


def _emag_section_samples(headings: list[str]) -> list[dict[str, Any]]:
    if len(headings) < 10:
        raise CollectionAuditError("O eMAG nao possui secoes suficientes para a revisao final solicitada")
    positions = [round(index * (len(headings) - 1) / 9) for index in range(10)]
    return [{"heading": headings[position], "heading_index": position + 1} for position in positions]


def _review_emag(phase2b_audit: dict[str, Any], root: Path, reviewed_at: str) -> dict[str, Any]:
    """Verify the existing phase 2B artifacts without rewriting them."""
    validate_phase2b_audit(phase2b_audit)
    validate_phase2b_local_artifacts(phase2b_audit, root)
    document = phase2b_audit["documents"][0]
    artifact_by_role = {artifact["role"]: artifact for artifact in document["local_artifacts"]}
    original_path = root / artifact_by_role["original_html"]["local_path"]
    extracted_path = root / artifact_by_role["extracted_text"]["local_path"]
    clean_path = root / artifact_by_role["clean_text"]["local_path"]
    html_text = original_path.read_text(encoding="utf-8")

    full_blocks, _, _ = extract_blocks(html_text, technical_column_only=False, clean=False)
    clean_blocks, exclusions, _ = extract_blocks(html_text, technical_column_only=True, clean=True)
    from learning.v05_collection_audit import (
        _redact_third_party_quotes_in_code,
        _remove_acknowledgements,
        _remove_inline_urls,
    )

    clean_blocks, acknowledgement_blocks_removed = _remove_acknowledgements(clean_blocks)
    clean_blocks, third_party_redactions = _redact_third_party_quotes_in_code(clean_blocks)
    clean_blocks, inline_urls_removed = _remove_inline_urls(clean_blocks)
    clean_blocks, duplicate_blocks_removed = _deduplicate_consecutive_blocks(clean_blocks)
    expected_extracted = unicodedata.normalize("NFC", _document_preamble() + "\n\n" + render_blocks(full_blocks))
    expected_clean = unicodedata.normalize("NFC", _document_preamble() + "\n\n" + render_blocks(clean_blocks))
    if extracted_path.read_text(encoding="utf-8") != expected_extracted:
        raise CollectionAuditError("O texto extraido do eMAG diverge da projecao reproduzivel do HTML original")
    if clean_path.read_text(encoding="utf-8") != expected_clean:
        raise CollectionAuditError("O texto limpo do eMAG diverge da projecao reproduzivel do HTML original")

    headings = [block.text for block in clean_blocks if block.kind == "heading"]
    samples = _emag_section_samples(headings)
    full_headings = {block.text for block in full_blocks if block.kind == "heading"}
    extracted_text = extracted_path.read_text(encoding="utf-8")
    clean_text = clean_path.read_text(encoding="utf-8")
    for sample in samples:
        heading = sample["heading"]
        sample["present_in_original"] = heading in full_headings
        sample["present_in_extracted"] = heading in extracted_text
        sample["present_in_clean"] = heading in clean_text
        if not all(sample[key] for key in ("present_in_original", "present_in_extracted", "present_in_clean")):
            raise CollectionAuditError("Uma secao amostrada do eMAG nao foi preservada durante a revisao")

    comparison = {
        "titles_preserved": bool(headings),
        "recommendation_headings_preserved": sum(
            1 for heading in headings if _ascii_key(heading).startswith("recomendacao")
        ),
        "list_items_preserved": sum(block.kind == "list_item" for block in clean_blocks),
        "technical_examples_preserved": sum(block.kind == "code" for block in clean_blocks),
        "technical_table_rows_preserved": sum(block.kind == "table_row" for block in clean_blocks),
        "clean_projection_matches_original": True,
    }
    if not all(
        (
            comparison["titles_preserved"],
            comparison["recommendation_headings_preserved"] > 0,
            comparison["list_items_preserved"] > 0,
            comparison["technical_examples_preserved"] > 0,
            comparison["technical_table_rows_preserved"] > 0,
        )
    ):
        raise CollectionAuditError("A revisao do eMAG nao confirmou todas as estruturas tecnicas obrigatorias")
    prior_redactions = document["quality"]["third_party_code_redactions"]
    if third_party_redactions != prior_redactions:
        raise CollectionAuditError("As redacoes de citacao de terceiros do eMAG nao correspondem ao registro da Fase 2B")

    return {
        "reviewed_at": reviewed_at,
        "all_phase_2b_hashes_confirmed": True,
        "original_unchanged": True,
        "sampled_sections": samples,
        "structural_comparison": comparison,
        "cleaning_recheck": {
            "excluded_elements_match": dict(sorted(exclusions.items())) == document["cleaning"]["excluded_elements"],
            "acknowledgement_blocks_removed": acknowledgement_blocks_removed,
            "inline_urls_removed": inline_urls_removed,
            "consecutive_blocks_removed": duplicate_blocks_removed,
            "third_party_code_redactions_confirmed": third_party_redactions,
            "third_party_code_redactions_adequate": third_party_redactions == prior_redactions,
        },
        "clean_corrections_applied": [],
    }


def _build_emag_document(phase2b_audit: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(phase2b_audit["documents"][0])
    if document["id"] != EMAG_DOCUMENT_ID:
        raise CollectionAuditError("O manifesto historico nao contem o eMAG esperado")
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
        "A revisao final da Fase 2C aprovou somente a inclusao posterior em um corpus "
        "ainda sujeito a autorizacao explicita. Nao autoriza tokenizacao, split ou treinamento."
    )
    document["final_review"] = review
    return document


def build_phase2c_audit(
    *,
    root: str | Path,
    phase2b_audit_path: Path,
    conci_original_path: Path,
    conci_headers_path: Path,
    conci_extracted_path: Path,
    conci_clean_path: Path,
    emag_reviewed_at: str,
    conci_preflight_at: str,
    conci_collected_at: str,
) -> dict[str, Any]:
    """Create the v2 manifest from only the two activities authorized in Phase 2C."""
    root_path = Path(root)
    phase2b_bytes = phase2b_audit_path.read_bytes()
    phase2b_audit = json.loads(phase2b_bytes.decode("utf-8"))
    review = _review_emag(phase2b_audit, root_path, emag_reviewed_at)
    emag_document = _build_emag_document(phase2b_audit, review)
    conci_document = _make_conci_document(
        original_path=conci_original_path,
        headers_path=conci_headers_path,
        extracted_path=conci_extracted_path,
        clean_path=conci_clean_path,
        preflight_at=conci_preflight_at,
        collected_at=conci_collected_at,
    )
    audit = {
        "schema_version": SCHEMA_VERSION,
        "project": "ELYSIA-Seed v0.5",
        "phase": PHASE,
        "created_at": conci_collected_at,
        "historical_phase_2b": {
            "path": PHASE2B_AUDIT_PATH,
            "schema_version": 1,
            "sha256": _sha256_path(phase2b_audit_path),
            "preserved": True,
            "original_document_state": "audited",
            "original_future_inclusion_decision": "pending_explicit_approval",
        },
        "historical_research_manifest": {
            "path": "data/corpus-v0.5/source-candidates.json",
            "phase": "research-and-corpus-plan-only",
            "preserved_without_relaxing_its_zero-download_validation": True,
        },
        "authorization": {
            "existing_documents_reauthorized_for_final_review": [EMAG_DOCUMENT_ID],
            "new_full_document_collection": [CONCI_DOCUMENT_ID],
            "other_full_documents_authorized": 0,
            "alternative_conci_representations_downloaded": False,
            "external_links_followed": False,
        },
        "safeguards": {key: False for key in sorted(FORBIDDEN_SAFEGAURDS)},
        "documents": [emag_document, conci_document],
    }
    validate_phase2c_audit(audit)
    return audit


def _validate_document_artifacts(document: dict[str, Any]) -> None:
    artifacts = document.get("local_artifacts")
    if not isinstance(artifacts, list):
        raise CollectionAuditError("Cada documento precisa registrar seus artefatos locais")
    roles = {artifact.get("role") for artifact in artifacts if isinstance(artifact, dict)}
    if roles != REQUIRED_ARTIFACT_ROLES:
        raise CollectionAuditError("Cada documento precisa ter os quatro artefatos locais obrigatorios")
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise CollectionAuditError("Cada artefato precisa ser um objeto")
        path = artifact.get("local_path")
        if not isinstance(path, str) or not path.startswith(ALLOWED_LOCAL_PREFIXES):
            raise CollectionAuditError("Um artefato esta fora dos diretorios locais autorizados")
        if artifact.get("git_ignored") is not True:
            raise CollectionAuditError("Conteudo de corpus precisa continuar fora do GitHub")
        if not isinstance(artifact.get("bytes"), int) or artifact["bytes"] <= 0:
            raise CollectionAuditError("Todo artefato precisa registrar tamanho positivo")
        if not isinstance(artifact.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]):
            raise CollectionAuditError("Todo artefato precisa registrar SHA-256 hexadecimal")


def validate_phase2c_audit(audit: dict[str, Any]) -> dict[str, Any]:
    """Validate the v2 metadata-only manifest without opening local corpus files."""
    if audit.get("schema_version") != SCHEMA_VERSION:
        raise CollectionAuditError("schema_version precisa ser 2")
    if audit.get("phase") != PHASE:
        raise CollectionAuditError("A fase precisa registrar a colecao controlada de multiplos documentos")
    historical = audit.get("historical_phase_2b")
    if not isinstance(historical, dict) or historical.get("path") != PHASE2B_AUDIT_PATH:
        raise CollectionAuditError("O manifesto historico da Fase 2B precisa permanecer referenciado")
    if historical.get("schema_version") != 1 or historical.get("preserved") is not True:
        raise CollectionAuditError("O historico da Fase 2B precisa manter sua versao e decisao originais")
    if not isinstance(historical.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", historical["sha256"]):
        raise CollectionAuditError("O manifesto historico precisa registrar SHA-256")
    research_manifest = audit.get("historical_research_manifest")
    if not isinstance(research_manifest, dict) or research_manifest.get("preserved_without_relaxing_its_zero-download_validation") is not True:
        raise CollectionAuditError("O manifesto historico de pesquisa precisa permanecer separado e restritivo")
    authorization = audit.get("authorization")
    expected_authorization = {
        "existing_documents_reauthorized_for_final_review": [EMAG_DOCUMENT_ID],
        "new_full_document_collection": [CONCI_DOCUMENT_ID],
        "other_full_documents_authorized": 0,
        "alternative_conci_representations_downloaded": False,
        "external_links_followed": False,
    }
    if authorization != expected_authorization:
        raise CollectionAuditError("A autorizacao da Fase 2C foi ampliada ou alterada")
    safeguards = audit.get("safeguards")
    if not isinstance(safeguards, dict) or set(safeguards) != FORBIDDEN_SAFEGAURDS or any(value is not False for value in safeguards.values()):
        raise CollectionAuditError("Uma salvaguarda proibida foi alterada")
    documents = audit.get("documents")
    if not isinstance(documents, list) or len(documents) != 2:
        raise CollectionAuditError("A Fase 2C precisa registrar exatamente os dois documentos autorizados")
    documents_by_id = {document.get("id"): document for document in documents if isinstance(document, dict)}
    if set(documents_by_id) != {EMAG_DOCUMENT_ID, CONCI_DOCUMENT_ID}:
        raise CollectionAuditError("O manifesto contem um documento nao autorizado")

    emag = documents_by_id[EMAG_DOCUMENT_ID]
    expected_emag_state = {
        "candidate": True,
        "collection_authorized": True,
        "collected": True,
        "audited": True,
        "approved_for_future_inclusion": True,
        "rejected": False,
        "current_state": "approved_for_future_inclusion",
    }
    if emag.get("states") != expected_emag_state or emag.get("future_inclusion_decision") != "approved_for_future_inclusion":
        raise CollectionAuditError("O eMAG precisa refletir a aprovacao limitada da revisao final")
    if not isinstance(emag.get("final_review"), dict) or len(emag["final_review"].get("sampled_sections", [])) < 10:
        raise CollectionAuditError("A revisao final do eMAG precisa registrar ao menos dez secoes amostradas")
    _validate_document_artifacts(emag)

    conci = documents_by_id[CONCI_DOCUMENT_ID]
    expected_conci_state = {
        "candidate": True,
        "collection_authorized": True,
        "collected": True,
        "audited": True,
        "approved_for_future_inclusion": False,
        "rejected": False,
        "current_state": "audited",
    }
    if conci.get("states") != expected_conci_state:
        raise CollectionAuditError("O artigo ConCI nao pode receber aprovacao futura automaticamente")
    if conci.get("future_inclusion_decision") != "pending_explicit_approval":
        raise CollectionAuditError("A inclusao futura do artigo ConCI precisa continuar pendente")
    if conci.get("identity", {}).get("doi") != CONCI_DOI or conci.get("license", {}).get("name") != CONCI_LICENSE:
        raise CollectionAuditError("DOI ou licenca do artigo ConCI nao conferem")
    source = conci.get("source")
    if not isinstance(source, dict) or source.get("requested_url") != CONCI_HTML_URL or source.get("final_url") != CONCI_HTML_URL:
        raise CollectionAuditError("O HTML ConCI final nao corresponde a representacao autorizada")
    if source.get("host") != CONCI_HOST or source.get("http_status") != 200 or source.get("redirect_detected") is not False:
        raise CollectionAuditError("A resposta HTTP ConCI registrada nao atende a coleta autorizada")
    if not str(source.get("content_type", "")).casefold().startswith("text/html"):
        raise CollectionAuditError("A coleta ConCI precisa registrar HTML")
    representations = source.get("available_representations")
    if not isinstance(representations, list) or representations != [
        {"format": "HTML", "selected": True, "downloaded": True},
        {"format": "XML", "selected": False, "downloaded": False},
        {"format": "PDF-A", "selected": False, "downloaded": False},
    ]:
        raise CollectionAuditError("As representacoes ConCI registradas nao correspondem a coleta unica autorizada")
    quality = conci.get("quality")
    if not isinstance(quality, dict) or quality.get("original_html", {}).get("embedded_charset") != "windows-1252":
        raise CollectionAuditError("A divergencia de codificacao do HTML ConCI precisa permanecer registrada")
    if quality.get("derived_text_encoding") != "UTF-8" or quality.get("replacement_character_count") != 0:
        raise CollectionAuditError("Os textos derivados ConCI precisam estar em UTF-8 sem caractere de substituicao")
    personal_data_scan = quality.get("personal_data_scan")
    clean_personal_data = personal_data_scan.get("clean") if isinstance(personal_data_scan, dict) else None
    if not isinstance(clean_personal_data, dict) or any(clean_personal_data.get(key) != 0 for key in ("email_matches", "cpf_matches", "phone_matches")):
        raise CollectionAuditError("A versao limpa ConCI nao pode reter dados pessoais detectados")
    token_estimate = quality.get("estimated_tokens")
    if not isinstance(token_estimate, dict) or token_estimate.get("minimum", 0) <= 0 or token_estimate.get("maximum", 0) < token_estimate.get("minimum", 0):
        raise CollectionAuditError("A estimativa preliminar de tokens ConCI e invalida")
    _validate_document_artifacts(conci)

    forbidden = _find_forbidden_content_fields(audit)
    if forbidden:
        raise CollectionAuditError(f"O manifesto de coleta nao pode conter conteudo integral: {', '.join(forbidden)}")
    return summarize_phase2c_audit(audit)


def validate_phase2c_local_artifacts(audit: dict[str, Any], root: str | Path = ".") -> None:
    """Verify all local, Git-ignored Phase 2C artifacts on the collection machine."""
    validate_phase2c_audit(audit)
    root_path = Path(root)
    historical = audit["historical_phase_2b"]
    historical_path = root_path / historical["path"]
    if not historical_path.exists() or _sha256_path(historical_path) != historical["sha256"]:
        raise CollectionAuditError("O manifesto historico local da Fase 2B diverge do hash registrado")
    phase2b_audit = json.loads(historical_path.read_text(encoding="utf-8"))
    validate_phase2b_local_artifacts(phase2b_audit, root_path)
    for document in audit["documents"]:
        for artifact in document["local_artifacts"]:
            artifact_path = root_path / artifact["local_path"]
            if not artifact_path.exists():
                raise CollectionAuditError(f"Artefato local ausente: {artifact_path}")
            if artifact_path.stat().st_size != artifact["bytes"]:
                raise CollectionAuditError(f"Tamanho divergente: {artifact_path}")
            if _sha256_path(artifact_path) != artifact["sha256"]:
                raise CollectionAuditError(f"SHA-256 divergente: {artifact_path}")
            if artifact["role"] in {"extracted_text", "clean_text"}:
                text = artifact_path.read_text(encoding="utf-8")
                if unicodedata.normalize("NFC", text) != text:
                    raise CollectionAuditError(f"Texto fora de NFC: {artifact_path}")
        original = next(artifact for artifact in document["local_artifacts"] if artifact["role"] == "original_html")
        if not _is_read_only(root_path / original["local_path"]):
            raise CollectionAuditError("Um HTML original local deixou de estar somente leitura")


def summarize_phase2c_audit(audit: dict[str, Any]) -> dict[str, Any]:
    documents = []
    for document in audit["documents"]:
        quality = document["quality"]
        documents.append(
            {
                "id": document["id"],
                "state": document["states"]["current_state"],
                "clean_characters": quality["clean_text_statistics"]["characters"],
                "clean_words": quality["clean_text_statistics"]["words"],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "documents": documents,
        "new_full_documents_collected": 1,
        "approved_for_future_inclusion": [EMAG_DOCUMENT_ID],
        "conci_future_inclusion_decision": "pending_explicit_approval",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--phase2b-audit", default=PHASE2B_AUDIT_PATH)
    parser.add_argument("--conci-original", default="data/corpus-v0.5/originals/conci-2021-licenses.html")
    parser.add_argument("--conci-headers", default="data/corpus-v0.5/originals/conci-2021-licenses.headers.txt")
    parser.add_argument("--conci-extracted", default="data/corpus-v0.5/processed/conci-2021-licenses.extracted.txt")
    parser.add_argument("--conci-clean", default="data/corpus-v0.5/clean/conci-2021-licenses.clean.txt")
    parser.add_argument("--audit", default="data/corpus-v0.5/collection-audit.json")
    parser.add_argument("--emag-reviewed-at", required=True)
    parser.add_argument("--conci-preflight-at", required=True)
    parser.add_argument("--conci-collected-at", required=True)
    args = parser.parse_args()

    audit = build_phase2c_audit(
        root=Path(args.root),
        phase2b_audit_path=Path(args.phase2b_audit),
        conci_original_path=Path(args.conci_original),
        conci_headers_path=Path(args.conci_headers),
        conci_extracted_path=Path(args.conci_extracted),
        conci_clean_path=Path(args.conci_clean),
        emag_reviewed_at=args.emag_reviewed_at,
        conci_preflight_at=args.conci_preflight_at,
        conci_collected_at=args.conci_collected_at,
    )
    _write_json(Path(args.audit), audit)
    validate_phase2c_local_artifacts(audit, Path(args.root))
    print(json.dumps(summarize_phase2c_audit(audit), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
