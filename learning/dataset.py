"""Streaming corpus loading, document-level splits and next-token batches."""

from __future__ import annotations

import hashlib
import json
import random
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import torch


@dataclass(frozen=True)
class TextDocument:
    path: Path
    text: str
    sha256: str
    line_number: int = 1


@dataclass
class CorpusStats:
    files_seen: int = 0
    documents_seen: int = 0
    duplicate_documents: int = 0
    invalid_documents: int = 0
    total_characters: int = 0
    total_bytes: int = 0
    invalid_records: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_seen": self.files_seen,
            "documents_seen": self.documents_seen,
            "duplicate_documents": self.duplicate_documents,
            "invalid_documents": self.invalid_documents,
            "total_characters": self.total_characters,
            "total_bytes": self.total_bytes,
            "invalid_records": self.invalid_records,
        }


@dataclass(frozen=True)
class CorpusSplit:
    train: tuple[TextDocument, ...]
    validation: tuple[TextDocument, ...]
    test: tuple[TextDocument, ...]


def _candidate_paths(source: str | Path) -> list[Path]:
    root = Path(source)
    if root.is_file():
        return [root]
    if not root.is_dir():
        raise FileNotFoundError(f"Caminho de corpus não encontrado: {root}")
    return sorted(path for path in root.rglob("*") if path.suffix.lower() in {".txt", ".jsonl"})


def _normalise(text: str) -> str:
    return unicodedata.normalize("NFC", text).strip()


def _jsonl_text(record: object) -> str:
    if not isinstance(record, dict):
        raise ValueError("registro JSONL não é um objeto")
    if isinstance(record.get("text"), str):
        return record["text"]
    conversations = record.get("conversations")
    if isinstance(conversations, list):
        contents = [
            item.get("content")
            for item in conversations
            if isinstance(item, dict) and isinstance(item.get("content"), str)
        ]
        if contents:
            return "\n".join(contents)
    raise ValueError("JSONL precisa de text ou conversations[].content")


def load_corpus(source: str | Path) -> tuple[list[TextDocument], CorpusStats]:
    """Read TXT/JSONL incrementally, normalize Unicode and remove duplicates."""
    documents: list[TextDocument] = []
    stats = CorpusStats()
    seen_hashes: set[str] = set()
    for path in _candidate_paths(source):
        stats.files_seen += 1
        try:
            with path.open("r", encoding="utf-8", errors="strict") as handle:
                for line_number, raw_line in enumerate(handle, start=1):
                    if not raw_line.strip():
                        continue
                    try:
                        text = _jsonl_text(json.loads(raw_line)) if path.suffix.lower() == ".jsonl" else raw_line
                        text = _normalise(text)
                        if not text:
                            raise ValueError("documento vazio")
                    except (json.JSONDecodeError, TypeError, ValueError) as error:
                        stats.invalid_documents += 1
                        stats.invalid_records.append(f"{path}:{line_number}: {error}")
                        continue
                    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    if digest in seen_hashes:
                        stats.duplicate_documents += 1
                        continue
                    seen_hashes.add(digest)
                    document = TextDocument(path=path, text=text, sha256=digest, line_number=line_number)
                    documents.append(document)
                    stats.documents_seen += 1
                    stats.total_characters += len(text)
                    stats.total_bytes += len(text.encode("utf-8"))
        except UnicodeDecodeError as error:
            stats.invalid_documents += 1
            stats.invalid_records.append(f"{path}: UTF-8 inválido: {error}")
    if not documents:
        raise ValueError(f"Nenhum documento válido encontrado em {source}")
    return documents, stats


def load_text_documents(directory: str | Path) -> list[TextDocument]:
    """Compatibility wrapper retained for the v0.1 training API."""
    return load_corpus(directory)[0]


def split_documents(
    documents: list[TextDocument],
    *,
    validation_fraction: float = 0.15,
    test_fraction: float = 0.15,
    seed: int = 1337,
) -> CorpusSplit:
    """Split by document and refuse the one-document leakage case."""
    if len(documents) < 3:
        raise ValueError("São necessários pelo menos três documentos para treino/validação/teste sem contaminação")
    if not 0.0 < validation_fraction < 1.0 or not 0.0 < test_fraction < 1.0:
        raise ValueError("As frações de validação e teste precisam estar entre 0 e 1")
    shuffled = list(documents)
    random.Random(seed).shuffle(shuffled)
    test_count = max(1, round(len(shuffled) * test_fraction))
    validation_count = max(1, round(len(shuffled) * validation_fraction))
    if test_count + validation_count >= len(shuffled):
        test_count = 1
        validation_count = 1
    test_documents = tuple(shuffled[:test_count])
    validation_documents = tuple(shuffled[test_count : test_count + validation_count])
    train_documents = tuple(shuffled[test_count + validation_count :])
    return CorpusSplit(train=train_documents, validation=validation_documents, test=test_documents)


def tokenize_documents(documents: Iterable[TextDocument], tokenizer: Any) -> torch.Tensor:
    token_ids: list[int] = []
    for document in documents:
        token_ids.extend(tokenizer.encode(document.text))
    if len(token_ids) < 2:
        raise ValueError("São necessários pelo menos dois tokens")
    return torch.tensor(token_ids, dtype=torch.long)


def make_batch(
    tokens: torch.Tensor,
    *,
    batch_size: int,
    block_size: int,
    device: torch.device,
    generator: torch.Generator | None = None,
) -> tuple[torch.Tensor, torch.Tensor]:
    if tokens.ndim != 1:
        raise ValueError("tokens precisa ser um vetor unidimensional")
    maximum_start = tokens.numel() - block_size - 1
    if maximum_start < 0:
        raise ValueError("Corpus menor que block_size + 1")
    starts = torch.randint(maximum_start + 1, (batch_size,), generator=generator, device="cpu")
    inputs = torch.stack([tokens[start : start + block_size] for start in starts.tolist()])
    targets = torch.stack([tokens[start + 1 : start + block_size + 1] for start in starts.tolist()])
    return inputs.to(device), targets.to(device)


def write_source_manifest(
    documents: Iterable[TextDocument],
    output_path: str | Path,
    *,
    license_note: str,
    stats: CorpusStats | None = None,
) -> None:
    output = Path(output_path)
    lines = [
        "# Manifesto de dados",
        "",
        f"Nota de licença/origem: {license_note}",
        "",
        "| Arquivo | Linha | SHA-256 |",
        "|---|---:|---|",
    ]
    lines.extend(
        f"| `{document.path.as_posix()}` | {document.line_number} | `{document.sha256}` |"
        for document in documents
    )
    if stats is not None:
        lines.extend(["", "## Estatísticas", "", "```json", json.dumps(stats.to_dict(), ensure_ascii=False, indent=2), "```"])
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
