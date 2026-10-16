"""Build and validate the local-only audit for the authorized eMAG HTML collection.

This module never fetches a URL. Network verification and the one authorized
HTML download are performed separately, so this code only transforms the
preserved local source and records reproducible audit metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import stat
import unicodedata
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


AUTHORIZED_URL = "https://emag.governoeletronico.gov.br/"
AUTHORIZED_HOST = "emag.governoeletronico.gov.br"
DOCUMENT_ID = "emag-v3-1-html"
DISPLAY_TITLE = "eMAG - Modelo de Acessibilidade em Governo Eletr\u00f4nico"
VERSION = "Vers\u00e3o 3.1 - Abril 2014"
LICENSE_NAME = "CC BY 4.0"
INSTITUTIONAL_AUTHOR = "Equipe do DGE - Departamento de Governo Eletronico"
ALLOWED_LOCAL_PREFIXES = (
    "data/corpus-v0.5/originals/",
    "data/corpus-v0.5/processed/",
    "data/corpus-v0.5/clean/",
)
FORBIDDEN_CONTENT_FIELDS = frozenset(
    {
        "full_text",
        "raw_text",
        "clean_text",
        "text_content",
        "html_content",
        "document_body",
        "token_ids",
        "token_store",
    }
)
REQUIRED_SECTION_FRAGMENTS = (
    "1. introducao",
    "2 . o processo para desenvolver um sitio acessivel",
    "3. recomendacoes de acessibilidade",
    "4. elementos padronizados de acessibilidade digital no governo federal",
    "5. praticas desaconselhadas",
    "6. glossario",
    "anexo 1",
)


class CollectionAuditError(ValueError):
    """Raised when a collection audit violates its narrow authorization."""


@dataclass(frozen=True)
class TextBlock:
    """A small structural unit projected from the preserved HTML."""

    kind: str
    text: str
    level: int | None = None


def _ascii_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_marks).strip().casefold()


def _normalize_inline(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", normalized).strip()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _word_count(text: str) -> int:
    return len(re.findall(r"[^\W_]+(?:[\-'\u2019][^\W_]+)*", text, flags=re.UNICODE))


def _text_stats(text: str) -> dict[str, int]:
    encoded = text.encode("utf-8")
    return {
        "bytes": len(encoded),
        "characters": len(text),
        "words": _word_count(text),
        "sha256": _sha256_bytes(encoded),
    }


def _invalid_control_characters(text: str) -> list[str]:
    return sorted(
        {
            f"U+{ord(char):04X}"
            for char in text
            if unicodedata.category(char) == "Cc" and char not in {"\n", "\r", "\t"}
        }
    )


def _estimate_tokens(word_count: int) -> dict[str, Any]:
    return {
        "minimum": math.ceil(word_count * 1.25),
        "maximum": math.ceil(word_count * 1.55),
        "method": "Faixa heuristica de 1,25 a 1,55 unidades sublexicais por palavra em portugues; nenhum tokenizador foi treinado ou executado.",
    }


def _is_read_only(path: Path) -> bool:
    metadata = path.stat()
    attributes = getattr(metadata, "st_file_attributes", 0)
    readonly_attribute = getattr(stat, "FILE_ATTRIBUTE_READONLY", 0)
    if readonly_attribute:
        return bool(attributes & readonly_attribute)
    return not bool(metadata.st_mode & stat.S_IWRITE)


class _MainContentParser(HTMLParser):
    """Project either the full principal area or only the technical left column."""

    _BLOCK_TAGS = {
        "p": ("paragraph", None),
        "li": ("list_item", None),
        "dt": ("list_item", None),
        "dd": ("paragraph", None),
        "pre": ("code", None),
        "textarea": ("code", None),
        "tr": ("table_row", None),
    }
    _ALWAYS_SKIP_TAGS = frozenset(
        {"script", "style", "noscript", "svg", "img", "form", "input", "button", "select", "option"}
    )
    _VOID_TAGS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})
    _CLEAN_SKIP_TAGS = frozenset({"blockquote", "cite"})
    _CLEAN_SKIP_CLASSES = frozenset({"voltar", "recomendacao", "topo", "img", "l-voltar", "l-recomendacao"})

    def __init__(self, *, technical_column_only: bool, clean: bool) -> None:
        super().__init__(convert_charrefs=True)
        self.technical_column_only = technical_column_only
        self.clean = clean
        self.blocks: list[TextBlock] = []
        self.excluded_elements: Counter[str] = Counter()
        self._stack: list[tuple[str, dict[str, str]]] = []
        self._principal_depth: int | None = None
        self._main_depth: int | None = None
        self._skip_depth: int | None = None
        self._active_tag: str | None = None
        self._active_kind: str | None = None
        self._active_level: int | None = None
        self._parts: list[str] = []
        self.saw_principal = False
        self.saw_main_column = False

    def _capturing(self) -> bool:
        if self._principal_depth is None:
            return False
        return not self.technical_column_only or self._main_depth is not None

    def _class_names(self, attrs: dict[str, str]) -> set[str]:
        return {name.casefold() for name in attrs.get("class", "").split() if name}

    def _skip_reason(self, tag: str, attrs: dict[str, str]) -> str | None:
        if tag in self._ALWAYS_SKIP_TAGS:
            return f"tag:{tag}"
        if not self.clean:
            return None
        if tag in self._CLEAN_SKIP_TAGS:
            return f"third_party_tag:{tag}"
        matching_classes = self._class_names(attrs) & self._CLEAN_SKIP_CLASSES
        if matching_classes:
            return f"class:{sorted(matching_classes)[0]}"
        return None

    def _flush(self) -> None:
        if self._active_kind is None:
            return
        if self._active_kind == "code":
            text = unicodedata.normalize("NFC", "".join(self._parts)).replace("\r\n", "\n").strip()
        else:
            text = _normalize_inline("".join(self._parts))
        if text:
            self.blocks.append(TextBlock(kind=self._active_kind, text=text, level=self._active_level))
        self._active_tag = None
        self._active_kind = None
        self._active_level = None
        self._parts = []

    def _begin_block(self, tag: str, kind: str, level: int | None) -> None:
        self._flush()
        self._active_tag = tag
        self._active_kind = kind
        self._active_level = level
        self._parts = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.casefold()
        attributes = {key.casefold(): value or "" for key, value in attrs}
        is_void = normalized_tag in self._VOID_TAGS
        if not is_void:
            self._stack.append((normalized_tag, attributes))
        depth = len(self._stack)

        if normalized_tag == "div" and attributes.get("id", "").casefold() == "principal":
            self._principal_depth = depth
            self.saw_principal = True
        elif self._principal_depth is not None and normalized_tag == "div" and "p-esquerda" in self._class_names(attributes):
            self._main_depth = depth
            self.saw_main_column = True

        if not self._capturing():
            return
        if self._skip_depth is not None:
            return
        reason = self._skip_reason(normalized_tag, attributes)
        if reason:
            self._flush()
            self.excluded_elements[reason] += 1
            if not is_void:
                self._skip_depth = depth
            return

        if normalized_tag in self._BLOCK_TAGS:
            kind, level = self._BLOCK_TAGS[normalized_tag]
            self._begin_block(normalized_tag, kind, level)
        elif normalized_tag.startswith("h") and len(normalized_tag) == 2 and normalized_tag[1].isdigit():
            self._begin_block(normalized_tag, "heading", int(normalized_tag[1]))
        elif normalized_tag in {"td", "th"} and self._active_kind == "table_row" and self._parts:
            self._parts.append(" | ")
        elif normalized_tag == "br" and self._active_kind is not None:
            self._parts.append(" ")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if not self._capturing() or self._skip_depth is not None or not data.strip():
            return
        if self._active_kind is None:
            self._begin_block("implicit", "paragraph", None)
        self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.casefold()
        if normalized_tag in self._VOID_TAGS:
            return
        if not self._stack or self._stack[-1][0] != normalized_tag:
            return
        depth = len(self._stack)
        if self._skip_depth is not None and depth == self._skip_depth:
            self._skip_depth = None
        elif self._active_tag == normalized_tag:
            self._flush()

        if depth == self._main_depth and normalized_tag == "div":
            self._flush()
            self._main_depth = None
        if depth == self._principal_depth and normalized_tag == "div":
            self._flush()
            self._principal_depth = None
        self._stack.pop()

    def close(self) -> None:
        super().close()
        self._flush()


def _repair_known_html_issue(html_text: str) -> tuple[str, int]:
    repaired, count = re.subn(r"</p\s*(?=<h[1-6]\b)", "</p>\n", html_text, flags=re.IGNORECASE)
    return repaired, count


def extract_blocks(html_text: str, *, technical_column_only: bool, clean: bool) -> tuple[list[TextBlock], Counter[str], int]:
    repaired_html, repair_count = _repair_known_html_issue(html_text)
    parser = _MainContentParser(technical_column_only=technical_column_only, clean=clean)
    parser.feed(repaired_html)
    parser.close()
    if not parser.saw_principal:
        raise CollectionAuditError("O HTML nao contem a area principal esperada")
    if technical_column_only and not parser.saw_main_column:
        raise CollectionAuditError("O HTML nao contem a coluna tecnica p-esquerda esperada")
    return parser.blocks, parser.excluded_elements, repair_count


def _remove_acknowledgements(blocks: list[TextBlock]) -> tuple[list[TextBlock], int]:
    result: list[TextBlock] = []
    removing = False
    removed = 0
    found = False
    for block in blocks:
        key = _ascii_key(block.text)
        if block.kind == "heading" and key == "agradecimentos":
            removing = True
            found = True
            removed += 1
            continue
        if removing and block.kind == "heading" and key.startswith("1. introducao"):
            removing = False
        if removing:
            removed += 1
            continue
        result.append(block)
    if not found:
        raise CollectionAuditError("A secao Agradecimentos esperada nao foi encontrada")
    if not result:
        raise CollectionAuditError("A limpeza removeu todo o conteudo tecnico")
    return result, removed


def _deduplicate_consecutive_blocks(blocks: list[TextBlock]) -> tuple[list[TextBlock], int]:
    result: list[TextBlock] = []
    previous_key: tuple[str, str] | None = None
    removed = 0
    for block in blocks:
        key = (block.kind, _ascii_key(block.text))
        if key == previous_key:
            removed += 1
            continue
        result.append(block)
        previous_key = key
    return result, removed


def _remove_inline_urls(blocks: list[TextBlock]) -> tuple[list[TextBlock], int]:
    pattern = re.compile(r"https?://[^\s)>,]+", flags=re.IGNORECASE)
    cleaned: list[TextBlock] = []
    removed = 0
    for block in blocks:
        if block.kind == "code":
            cleaned.append(block)
            continue
        text, count = pattern.subn("", block.text)
        removed += count
        cleaned.append(TextBlock(kind=block.kind, text=_normalize_inline(text), level=block.level))
    return cleaned, removed


def _redact_third_party_quotes_in_code(blocks: list[TextBlock]) -> tuple[list[TextBlock], int]:
    cleaned: list[TextBlock] = []
    redacted = 0
    blockquote_pattern = re.compile(r"(<blockquote\b[^>]*>).*?(</blockquote>)", flags=re.IGNORECASE | re.DOTALL)
    cite_pattern = re.compile(r"<cite\b[^>]*>.*?</cite>", flags=re.IGNORECASE | re.DOTALL)
    for block in blocks:
        if block.kind != "code":
            cleaned.append(block)
            continue
        text, blockquote_count = blockquote_pattern.subn(r"\1[conteudo citacional de terceiro removido]\2", block.text)
        text, cite_count = cite_pattern.subn("[atribuicao de terceiro removida]", text)
        redacted += blockquote_count + cite_count
        cleaned.append(TextBlock(kind=block.kind, text=text, level=block.level))
    return cleaned, redacted


def render_blocks(blocks: list[TextBlock]) -> str:
    lines: list[str] = []
    for block in blocks:
        if block.kind == "heading":
            level = block.level or 2
            lines.append(f"{'#' * max(1, min(level, 6))} {block.text}")
        elif block.kind == "list_item":
            lines.append(f"- {block.text}")
        elif block.kind == "table_row":
            lines.append(f"| {block.text} |")
        elif block.kind == "code":
            lines.append(f"```html\n{block.text}\n```")
        else:
            lines.append(block.text)
    return "\n\n".join(lines).strip() + "\n"


def _document_preamble() -> str:
    return "\n\n".join(
        (
            f"# {DISPLAY_TITLE}",
            f"Versao: {VERSION}",
            f"Licenca: {LICENSE_NAME}",
            f"Autoria institucional: {INSTITUTIONAL_AUTHOR}",
            f"Fonte oficial: {AUTHORIZED_URL}",
        )
    )


def _assert_document_identity(html_text: str) -> None:
    key = _ascii_key(html_text)
    required_fragments = (
        _ascii_key(DISPLAY_TITLE),
        _ascii_key(VERSION),
        "creative commons - atribuicao 4.0 internacional (cc by 4.0)",
        "modelo de acessibilidade em governo eletronico",
    )
    missing = [fragment for fragment in required_fragments if fragment not in key]
    if missing:
        raise CollectionAuditError("O HTML nao confirma titulo, versao, licenca e corpo do eMAG autorizados")


def _assert_required_sections(blocks: list[TextBlock]) -> list[str]:
    headings = [block.text for block in blocks if block.kind == "heading"]
    normalized_headings = [_ascii_key(heading) for heading in headings]
    missing = [fragment for fragment in REQUIRED_SECTION_FRAGMENTS if not any(fragment in heading for heading in normalized_headings)]
    if missing:
        raise CollectionAuditError(f"Secoes obrigatorias ausentes apos extracao: {', '.join(missing)}")
    return headings


def _sample_sections(headings: list[str]) -> dict[str, str]:
    if len(headings) < 3:
        raise CollectionAuditError("A extracao nao possui secoes suficientes para a amostragem")
    return {
        "start": headings[0],
        "middle": headings[len(headings) // 2],
        "end": headings[-1],
    }


def _parse_headers(headers_path: Path) -> dict[str, str]:
    lines = headers_path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("HTTP/"):
        raise CollectionAuditError("O snapshot de cabecalhos nao inicia com uma resposta HTTP")
    headers = {"status_line": lines[0]}
    for line in lines[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().casefold()] = value.strip()
    if not headers["status_line"].startswith("HTTP/1.1 200"):
        raise CollectionAuditError("A coleta HTML precisa registrar resposta HTTP 200")
    content_type = headers.get("content-type", "").casefold()
    if not content_type.startswith("text/html") or "charset=utf-8" not in content_type:
        raise CollectionAuditError("A coleta HTML precisa registrar text/html; charset=UTF-8")
    return headers


def _artifact(path: Path, role: str, *, immutable: bool, format_name: str) -> dict[str, Any]:
    if not path.exists():
        raise CollectionAuditError(f"Artefato local ausente: {path}")
    relative_path = path.as_posix()
    if not relative_path.startswith(ALLOWED_LOCAL_PREFIXES):
        raise CollectionAuditError(f"Artefato fora dos diretorios locais autorizados: {relative_path}")
    return {
        "role": role,
        "local_path": relative_path,
        "git_ignored": True,
        "format": format_name,
        "bytes": path.stat().st_size,
        "sha256": _sha256_path(path),
        "immutable": immutable,
    }


def _find_forbidden_content_fields(value: Any, location: str = "audit") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}"
            if key in FORBIDDEN_CONTENT_FIELDS:
                findings.append(child_location)
            findings.extend(_find_forbidden_content_fields(child, child_location))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_find_forbidden_content_fields(child, f"{location}[{index}]"))
    return findings


def _metadata_only_reviews() -> list[dict[str, Any]]:
    return [
        {
            "id": "educapes-licencas-ciencia-informacao",
            "metadata_url": "https://educapes.capes.gov.br/handle/capes/1140501?mode=full",
            "title": "Licencas alternativas de protecao intelectual atribuidas a periodicos tecnicos e/ou cientificos da area da Ciencia da Informacao no contexto da Ciencia Aberta",
            "authors": ["Natalia Rodrigues Silva", "Nivaldo Calixto Ribeiro", "Dalgiza Andrade Oliveira"],
            "persistent_identifier": "https://doi.org/10.33467/conci.v4i.15670",
            "canonical_origin_url": "https://periodicos.ufs.br/conci/article/view/15670",
            "canonical_version": "ConCI, v. 4, 2021, artigo original, p. 1-30",
            "license": {
                "name": "CC BY 4.0",
                "evidence_url": "https://periodicos.ufs.br/conci/article/view/15670",
                "obligations": "Atribuir autores e a publicacao inicial; indicar a licenca e alteracoes em eventual derivado.",
            },
            "file_reference": {
                "direct_file_url": None,
                "landing_page_lists": ["PDF-A", "HTML", "XML"],
                "reason": "A pagina oficial lista representacoes, mas nenhum arquivo foi requisitado ou baixado nesta revisao somente de metadados.",
            },
            "restrictions": "O artigo contem referencias e possiveis citacoes de terceiros; uma auditoria do arquivo final continua obrigatoria.",
            "future_collection_status": "pending",
            "content_downloaded": False,
        },
        {
            "id": "educapes-ciencia-aberta-cnpq",
            "metadata_url": "https://educapes.capes.gov.br/handle/capes/1023510?mode=full",
            "title": "A ciencia aberta no CNPq: acesso aberto aos dados e resultados de pesquisas",
            "authors": ["Adriana Maria Tonini", "Paulo Henrique de Assis Santana", "Thais Machado Scherrer"],
            "persistent_identifier": "https://doi.org/10.21452/978-85-93910-04-3.cap16",
            "canonical_origin_url": "https://www.repositorio.ufop.br/handle/123456789/19961",
            "canonical_version": "Capitulo 16 de Topicos sobre dados abertos para editores cientificos, ABEC, 2020, p. 203-214",
            "license": {
                "name": "CC BY 4.0",
                "evidence_url": "https://www.abecbrasil.org.br/arquivos/Topicos_dados_abertos_editores_cientificos.pdf",
                "obligations": "Mencionar a fonte em qualquer reproducao parcial ou total e indicar alteracoes em eventual derivado.",
            },
            "file_reference": {
                "direct_file_url": "https://www.repositorio.ufop.br/bitstreams/5c15a935-8e70-41b7-8565-fe3c30613d72/download",
                "publisher_book_url": "https://www.abecbrasil.org.br/arquivos/Topicos_dados_abertos_editores_cientificos.pdf",
                "reason": "URLs identificados somente como metadados; nenhum PDF, livro ou capitulo foi baixado.",
            },
            "restrictions": "A licenca do livro precisa ser conferida no arquivo selecionado e o capitulo exige auditoria de referencias e de eventuais materiais de terceiros.",
            "future_collection_status": "pending",
            "content_downloaded": False,
        },
    ]


def build_collection_audit(
    *,
    original_path: Path,
    headers_path: Path,
    extracted_path: Path,
    clean_path: Path,
    preflight_at: str,
    collected_at: str,
) -> dict[str, Any]:
    """Create derived local text and return a metadata-only audit manifest."""
    if not _is_read_only(original_path):
        raise CollectionAuditError("O HTML original precisa permanecer marcado como somente leitura")
    headers = _parse_headers(headers_path)
    original_bytes = original_path.read_bytes()
    try:
        html_text = original_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CollectionAuditError("O HTML original nao esta em UTF-8 valido") from error
    _assert_document_identity(html_text)

    extracted_blocks, _, repair_count = extract_blocks(html_text, technical_column_only=False, clean=False)
    clean_blocks, exclusions, clean_repair_count = extract_blocks(html_text, technical_column_only=True, clean=True)
    clean_blocks, acknowledgement_blocks_removed = _remove_acknowledgements(clean_blocks)
    clean_blocks, third_party_code_redactions = _redact_third_party_quotes_in_code(clean_blocks)
    clean_blocks, inline_urls_removed = _remove_inline_urls(clean_blocks)
    clean_blocks, duplicate_blocks_removed = _deduplicate_consecutive_blocks(clean_blocks)
    headings = _assert_required_sections(clean_blocks)

    extracted_text = _document_preamble() + "\n\n" + render_blocks(extracted_blocks)
    clean_text = _document_preamble() + "\n\n" + render_blocks(clean_blocks)
    extracted_text = unicodedata.normalize("NFC", extracted_text)
    clean_text = unicodedata.normalize("NFC", clean_text)
    extracted_path.parent.mkdir(parents=True, exist_ok=True)
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    extracted_path.write_text(extracted_text, encoding="utf-8", newline="\n")
    clean_path.write_text(clean_text, encoding="utf-8", newline="\n")

    clean_stats = _text_stats(clean_text)
    extracted_stats = _text_stats(extracted_text)
    invalid_characters = _invalid_control_characters(clean_text)
    personal_data_scan = {
        "email_matches": len(re.findall(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", clean_text)),
        "cpf_matches": len(re.findall(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", clean_text)),
        "phone_matches": len(re.findall(r"\b(?:\+55\s*)?(?:\(?\d{2}\)?\s*)?\d{4,5}-\d{4}\b", clean_text)),
        "acknowledgement_blocks_removed": acknowledgement_blocks_removed,
        "note": "A verificacao automatica cobre e-mail, CPF e telefone. A secao de agradecimentos com nomes de pessoas foi excluida por nao ser conteudo tecnico.",
    }

    original_artifact = _artifact(original_path, "original_html", immutable=True, format_name="text/html; charset=UTF-8")
    headers_artifact = _artifact(headers_path, "response_headers", immutable=False, format_name="text/plain; HTTP headers")
    extracted_artifact = _artifact(extracted_path, "extracted_text", immutable=False, format_name="text/plain; charset=UTF-8")
    clean_artifact = _artifact(clean_path, "clean_text", immutable=False, format_name="text/plain; charset=UTF-8")
    if original_artifact["bytes"] != len(original_bytes):
        raise CollectionAuditError("O tamanho registrado do HTML original nao confere")

    audit = {
        "schema_version": 1,
        "project": "ELYSIA-Seed v0.5",
        "phase": "first-controlled-html-collection",
        "created_at": collected_at,
        "historical_research_manifest": {
            "path": "data/corpus-v0.5/source-candidates.json",
            "phase": "research-and-corpus-plan-only",
            "preserved_without_relaxing_its_zero-download_validation": True,
        },
        "authorization": {
            "authorized_document_id": DOCUMENT_ID,
            "authorized_url": AUTHORIZED_URL,
            "authorized_format": "HTML only",
            "other_full_documents_authorized": 0,
            "followed_external_links": False,
        },
        "safeguards": {
            "ollama_used": False,
            "external_model_or_weights_used": False,
            "ai_api_used": False,
            "additional_dataset_downloaded": False,
            "scielo_content_collected": False,
            "bpe_trained": False,
            "final_split_created": False,
            "neural_training_started": False,
            "v04_weights_or_checkpoints_modified": False,
        },
        "documents": [
            {
                "id": DOCUMENT_ID,
                "states": {
                    "selected": True,
                    "collected": True,
                    "audited": True,
                    "approved_for_future_inclusion": False,
                    "rejected": False,
                    "current_state": "audited",
                },
                "identity": {
                    "title": DISPLAY_TITLE,
                    "version": VERSION,
                    "institutional_author": INSTITUTIONAL_AUTHOR,
                },
                "source": {
                    "requested_url": AUTHORIZED_URL,
                    "final_url": AUTHORIZED_URL,
                    "host": AUTHORIZED_HOST,
                    "preflight_checked_at": preflight_at,
                    "collected_at": collected_at,
                    "http_status": 200,
                    "redirect_detected": False,
                    "content_type": headers["content-type"],
                    "http_date": headers.get("date"),
                    "relevant_headers_artifact": headers_artifact["local_path"],
                },
                "license": {
                    "name": LICENSE_NAME,
                    "declared_on_document": True,
                    "attribution_obligations": "Creditar a Equipe do DGE - Departamento de Governo Eletronico, a fonte oficial, a licenca CC BY 4.0 e indicar alteracoes em derivados.",
                },
                "local_artifacts": [original_artifact, headers_artifact, extracted_artifact, clean_artifact],
                "quality": {
                    "original_html": {
                        "bytes": original_artifact["bytes"],
                        "sha256": original_artifact["sha256"],
                        "utf8_valid": True,
                    },
                    "extracted_text_statistics": extracted_stats,
                    "clean_text_statistics": clean_stats,
                    "sections_extracted": len(headings),
                    "sampled_sections": _sample_sections(headings),
                    "normalization": "Unicode NFC",
                    "invalid_control_characters": invalid_characters,
                    "replacement_character_count": clean_text.count("\ufffd"),
                    "html_repairs_in_memory": {
                        "malformed_paragraph_closures_before_headings": max(repair_count, clean_repair_count),
                        "original_html_modified": False,
                    },
                    "deduplication": {
                        "strategy": "Somente blocos tecnicos consecutivos exatamente iguais sao removidos; navegacao repetida e removida por seletor de interface.",
                        "consecutive_blocks_removed": duplicate_blocks_removed,
                    },
                    "inline_urls_removed": inline_urls_removed,
                    "third_party_code_redactions": third_party_code_redactions,
                    "personal_data_scan": personal_data_scan,
                    "estimated_tokens": _estimate_tokens(clean_stats["words"]),
                },
                "cleaning": {
                    "rules": [
                        "Decodificar o HTML original estritamente como UTF-8 e normalizar o texto resultante para Unicode NFC.",
                        "Extrair a coluna tecnica p-esquerda para a versao limpa e manter titulos, subtitulos, listas, recomendacoes, explicacoes, glossario e anexo textual.",
                        "Excluir navegacao, controles, sumario lateral, links Voltar ao sumario, botoes Topo e links de exemplos navegaveis.",
                        "Excluir scripts, estilos, formularios, imagens, legendas visuais e blocos citacionais de terceiros sem auditoria propria; textareas de exemplos sao preservados como codigo tecnico.",
                        "Remover URLs externas soltas do texto corrido e redigir citacoes diretas de terceiros em exemplos de codigo, preservando a estrutura do exemplo.",
                        "Excluir a secao Agradecimentos, que contem nomes de pessoas e nao e conteudo tecnico do modelo.",
                        "Remover somente duplicacoes tecnicas consecutivas exatamente iguais; nao deduplicar prosa nao consecutiva.",
                    ],
                    "excluded_elements": dict(sorted(exclusions.items())),
                    "third_party_handling": "Nenhum recurso externo foi baixado. URLs externas soltas foram removidas do texto corrido e citacoes diretas em exemplos de codigo foram redigidas.",
                },
                "future_inclusion_decision": "pending_explicit_approval",
                "future_inclusion_reason": "A coleta e auditoria local nao constituem aprovacao para tokenizacao, split ou treinamento.",
            }
        ],
        "educapes_metadata_reviews": _metadata_only_reviews(),
    }
    validate_collection_audit(audit)
    return audit


def validate_collection_audit(audit: dict[str, Any]) -> dict[str, Any]:
    """Validate the collection-only manifest without opening any local source file."""
    if audit.get("schema_version") != 1:
        raise CollectionAuditError("schema_version precisa ser 1")
    if audit.get("phase") != "first-controlled-html-collection":
        raise CollectionAuditError("A fase precisa ser first-controlled-html-collection")
    historical = audit.get("historical_research_manifest")
    if not isinstance(historical, dict) or historical.get("preserved_without_relaxing_its_zero-download_validation") is not True:
        raise CollectionAuditError("O manifesto historico de pesquisa precisa permanecer separado e restritivo")
    authorization = audit.get("authorization")
    if not isinstance(authorization, dict) or authorization.get("authorized_document_id") != DOCUMENT_ID:
        raise CollectionAuditError("A auditoria so pode autorizar o HTML do eMAG 3.1")
    if authorization.get("authorized_url") != AUTHORIZED_URL or authorization.get("authorized_format") != "HTML only":
        raise CollectionAuditError("A URL ou o formato autorizado foi alterado")
    if authorization.get("other_full_documents_authorized") != 0 or authorization.get("followed_external_links") is not False:
        raise CollectionAuditError("A auditoria nao pode incluir outros documentos ou links externos")
    safeguards = audit.get("safeguards")
    if not isinstance(safeguards, dict) or any(value is not False for value in safeguards.values()):
        raise CollectionAuditError("Uma salvaguarda proibida foi alterada")
    documents = audit.get("documents")
    if not isinstance(documents, list) or len(documents) != 1:
        raise CollectionAuditError("A fase de coleta precisa registrar exatamente um documento")
    document = documents[0]
    if not isinstance(document, dict) or document.get("id") != DOCUMENT_ID:
        raise CollectionAuditError("O documento coletado nao corresponde ao eMAG HTML autorizado")
    expected_states = {
        "selected": True,
        "collected": True,
        "audited": True,
        "approved_for_future_inclusion": False,
        "rejected": False,
        "current_state": "audited",
    }
    if document.get("states") != expected_states:
        raise CollectionAuditError("Os estados da coleta nao distinguem selecao, coleta, auditoria e aprovacao futura")
    source = document.get("source")
    if not isinstance(source, dict):
        raise CollectionAuditError("source precisa ser um objeto")
    if source.get("requested_url") != AUTHORIZED_URL or source.get("final_url") != AUTHORIZED_URL:
        raise CollectionAuditError("A auditoria precisa manter o URL oficial final sem substituicao")
    if source.get("host") != AUTHORIZED_HOST or source.get("http_status") != 200 or source.get("redirect_detected") is not False:
        raise CollectionAuditError("A resposta HTTP registrada nao atende a coleta autorizada")
    if not str(source.get("content_type", "")).casefold().startswith("text/html"):
        raise CollectionAuditError("O documento coletado precisa ser HTML")
    if document.get("license", {}).get("name") != LICENSE_NAME:
        raise CollectionAuditError("A licenca CC BY 4.0 precisa permanecer registrada")
    artifacts = document.get("local_artifacts")
    if not isinstance(artifacts, list) or {item.get("role") for item in artifacts if isinstance(item, dict)} != {
        "original_html",
        "response_headers",
        "extracted_text",
        "clean_text",
    }:
        raise CollectionAuditError("Os quatro artefatos locais obrigatorios estao ausentes")
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise CollectionAuditError("Cada artefato precisa ser um objeto")
        path = artifact.get("local_path")
        if not isinstance(path, str) or not path.startswith(ALLOWED_LOCAL_PREFIXES):
            raise CollectionAuditError("Um artefato esta fora dos diretorios locais ignorados")
        if artifact.get("git_ignored") is not True:
            raise CollectionAuditError("Conteudo de corpus deve continuar fora do GitHub")
        if not isinstance(artifact.get("bytes"), int) or artifact["bytes"] <= 0:
            raise CollectionAuditError("Cada artefato precisa registrar tamanho positivo")
        if not isinstance(artifact.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]):
            raise CollectionAuditError("Cada artefato precisa registrar SHA-256 em hexadecimal")
    quality = document.get("quality")
    if not isinstance(quality, dict) or quality.get("sections_extracted", 0) < len(REQUIRED_SECTION_FRAGMENTS):
        raise CollectionAuditError("A auditoria precisa registrar as secoes tecnicas extraidas")
    token_estimate = quality.get("estimated_tokens")
    if not isinstance(token_estimate, dict) or token_estimate.get("minimum", 0) <= 0 or token_estimate.get("maximum", 0) < token_estimate.get("minimum", 0):
        raise CollectionAuditError("A estimativa preliminar de tokens e invalida")
    if document.get("future_inclusion_decision") != "pending_explicit_approval":
        raise CollectionAuditError("A coleta nao pode aprovar treinamento futuro automaticamente")
    reviews = audit.get("educapes_metadata_reviews")
    if not isinstance(reviews, list) or len(reviews) != 2:
        raise CollectionAuditError("Os dois registros eduCAPES precisam permanecer como revisoes de metadados")
    for review in reviews:
        if not isinstance(review, dict) or review.get("content_downloaded") is not False or review.get("future_collection_status") != "pending":
            raise CollectionAuditError("Registros eduCAPES nao podem ser promovidos ou baixados nesta fase")
    forbidden = _find_forbidden_content_fields(audit)
    if forbidden:
        raise CollectionAuditError(f"O manifesto de coleta nao pode conter conteudo integral: {', '.join(forbidden)}")
    return summarize_collection_audit(audit)


def validate_local_artifacts(audit: dict[str, Any], root: str | Path = ".") -> None:
    """Verify local ignored files when they are present on the collection machine."""
    root_path = Path(root)
    document = audit["documents"][0]
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
    original = next(item for item in document["local_artifacts"] if item["role"] == "original_html")
    if not _is_read_only(root_path / original["local_path"]):
        raise CollectionAuditError("O HTML original local deixou de estar somente leitura")


def summarize_collection_audit(audit: dict[str, Any]) -> dict[str, Any]:
    document = audit["documents"][0]
    quality = document["quality"]
    return {
        "document_id": document["id"],
        "state": document["states"]["current_state"],
        "original_html_bytes": quality["original_html"]["bytes"],
        "clean_characters": quality["clean_text_statistics"]["characters"],
        "clean_words": quality["clean_text_statistics"]["words"],
        "sections_extracted": quality["sections_extracted"],
        "future_inclusion_decision": document["future_inclusion_decision"],
        "educapes_reviews": len(audit["educapes_metadata_reviews"]),
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", default="data/corpus-v0.5/originals/emag-v3-1.html")
    parser.add_argument("--headers", default="data/corpus-v0.5/originals/emag-v3-1.headers.txt")
    parser.add_argument("--extracted", default="data/corpus-v0.5/processed/emag-v3-1.extracted.txt")
    parser.add_argument("--clean", default="data/corpus-v0.5/clean/emag-v3-1.clean.txt")
    parser.add_argument("--audit", default="data/corpus-v0.5/collection-audit.phase-2b.json")
    parser.add_argument("--preflight-at", required=True)
    parser.add_argument("--collected-at", required=True)
    args = parser.parse_args()

    audit = build_collection_audit(
        original_path=Path(args.original),
        headers_path=Path(args.headers),
        extracted_path=Path(args.extracted),
        clean_path=Path(args.clean),
        preflight_at=args.preflight_at,
        collected_at=args.collected_at,
    )
    _write_json(Path(args.audit), audit)
    validate_local_artifacts(audit)
    print(json.dumps(summarize_collection_audit(audit), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
