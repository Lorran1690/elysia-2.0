"""Streaming corpus loading, grouped splits, and on-disk token storage."""

from __future__ import annotations

import hashlib
import json
import random
import unicodedata
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Protocol

import torch


class Tokenizer(Protocol):
    bos_id: int
    eos_id: int

    def encode(self, text: str, *, add_bos: bool = True, add_eos: bool = True) -> list[int]: ...

    def metadata(self) -> dict[str, str | int]: ...


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _normalized(text: str) -> str:
    return unicodedata.normalize("NFC", text).strip()


def _simhash(text: str) -> int:
    weights = [0] * 64
    _update_simhash(weights, text)
    return sum((1 << bit) for bit, weight in enumerate(weights) if weight >= 0)


def _update_simhash(weights: list[int], text: str) -> None:
    words = text.casefold().split()
    features = [" ".join(words[index : index + 3]) for index in range(max(0, len(words) - 2))]
    for feature in features or words or [text.casefold()]:
        number = int.from_bytes(hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest(), "big")
        for bit in range(64):
            weights[bit] += 1 if number & (1 << bit) else -1


def _hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_text_chunks(path: Path, size: int = 65_536) -> Iterator[str]:
    """Yield bounded NFC-normalized chunks, including content without line breaks."""
    with path.open("r", encoding="utf-8") as handle:
        while raw := handle.read(size):
            chunk = unicodedata.normalize("NFC", raw)
            if chunk:
                yield chunk


@dataclass(frozen=True)
class TextDocument:
    """One original work or a source-grouped JSONL work, without retaining its body."""

    path: Path
    text: str | None
    sha256: str
    line_number: int | None = None
    source_group: str | None = None
    group_id: str | None = None
    record_lines: tuple[int, ...] = ()
    byte_count: int = 0
    character_count: int = 0
    near_signature: int = 0

    @property
    def split_group(self) -> str:
        return self.group_id or self.source_group or self.sha256


@dataclass
class CorpusStats:
    files_seen: int = 0
    documents_loaded: int = 0
    duplicate_documents: int = 0
    invalid_documents: int = 0
    source_groups: int = 0
    near_duplicate_clusters: int = 0
    total_bytes: int = 0
    raw_files: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_seen": self.files_seen,
            "documents_loaded": self.documents_loaded,
            "duplicate_documents": self.duplicate_documents,
            "invalid_documents": self.invalid_documents,
            "source_groups": self.source_groups,
            "near_duplicate_clusters": self.near_duplicate_clusters,
            "total_bytes": self.total_bytes,
            "raw_files": self.raw_files,
        }


@dataclass(frozen=True)
class CorpusSplit:
    train: list[TextDocument]
    validation: list[TextDocument]
    test: list[TextDocument]
    seed: int
    validation_fraction: float
    test_fraction: float

    def metadata(self) -> dict[str, Any]:
        members = {
            name: [
                {"sha256": document.sha256, "group": document.split_group, "path": str(document.path)}
                for document in documents
            ]
            for name, documents in (("train", self.train), ("validation", self.validation), ("test", self.test))
        }
        base = {
            "seed": self.seed,
            "validation_fraction": self.validation_fraction,
            "test_fraction": self.test_fraction,
            "members": members,
        }
        return {**base, "fingerprint": _fingerprint(base)}


@dataclass(frozen=True)
class TokenStore:
    path: Path
    token_count: int
    sha256: str
    metadata_path: Path

    def numel(self) -> int:
        return self.token_count

    def read_slice(self, start: int, length: int) -> torch.Tensor:
        if start < 0 or length < 0 or start + length > self.token_count:
            raise ValueError("Faixa de tokens fora do armazenamento")
        with self.path.open("rb") as handle:
            handle.seek(start * 4)
            values = array("I")
            values.frombytes(handle.read(length * 4))
        return torch.tensor(values, dtype=torch.long)


def _txt_document(path: Path) -> TextDocument | None:
    digest = hashlib.sha256()
    characters = 0
    signature_weights = [0] * 64
    for chunk in _iter_text_chunks(path):
        if not chunk.strip():
            continue
        digest.update(chunk.encode("utf-8"))
        characters += len(chunk)
        _update_simhash(signature_weights, chunk)
    if not characters:
        return None
    return TextDocument(
        path=path,
        text=None,
        sha256=digest.hexdigest(),
        source_group=f"file:{path.name}",
        byte_count=path.stat().st_size,
        character_count=characters,
        near_signature=sum((1 << bit) for bit, weight in enumerate(signature_weights) if weight >= 0),
    )


def _record_text(payload: dict[str, Any]) -> str | None:
    value = payload.get("text")
    if isinstance(value, str):
        return _normalized(value)
    conversations = payload.get("conversations")
    if isinstance(conversations, list):
        parts = [item.get("content", "") for item in conversations if isinstance(item, dict) and isinstance(item.get("content"), str)]
        result = _normalized("\n".join(parts))
        return result or None
    return None


def _jsonl_documents(path: Path, stats: CorpusStats) -> list[TextDocument]:
    grouped: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                stats.invalid_documents += 1
                continue
            if not isinstance(payload, dict):
                stats.invalid_documents += 1
                continue
            text = _record_text(payload)
            if not text:
                stats.invalid_documents += 1
                continue
            source = next((str(payload[key]) for key in ("source_id", "source", "document_id", "id") if payload.get(key) is not None), f"line:{line_number}")
            entry = grouped.setdefault(source, {"lines": [], "digest": hashlib.sha256(), "characters": 0, "weights": [0] * 64})
            entry["lines"].append(line_number)
            entry["digest"].update(text.encode("utf-8"))
            entry["digest"].update(b"\n")
            entry["characters"] += len(text)
            _update_simhash(entry["weights"], text)
    documents: list[TextDocument] = []
    for source, entry in grouped.items():
        documents.append(
            TextDocument(
                path=path,
                text=None,
                sha256=entry["digest"].hexdigest(),
                line_number=entry["lines"][0],
                source_group=f"{path.name}:{source}",
                record_lines=tuple(entry["lines"]),
                byte_count=path.stat().st_size,
                character_count=entry["characters"],
                near_signature=sum((1 << bit) for bit, weight in enumerate(entry["weights"]) if weight >= 0),
            )
        )
    return documents


def _assign_near_duplicate_groups(documents: list[TextDocument], threshold: int = 5) -> list[TextDocument]:
    parents = list(range(len(documents)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left, right = find(left), find(right)
        if left != right:
            parents[right] = left

    for left in range(len(documents)):
        for right in range(left):
            if _hamming(documents[left].near_signature, documents[right].near_signature) <= threshold:
                union(left, right)
    return [
        TextDocument(**{**document.__dict__, "group_id": f"related:{find(index)}"})
        for index, document in enumerate(documents)
    ]


def load_corpus(data_dir: str | Path) -> tuple[list[TextDocument], CorpusStats]:
    root = Path(data_dir)
    stats = CorpusStats()
    documents: list[TextDocument] = []
    for path in sorted(root.glob("*")):
        if path.suffix.lower() not in {".txt", ".jsonl"}:
            continue
        stats.files_seen += 1
        stats.raw_files[str(path)] = _file_sha256(path)
        if path.suffix.lower() == ".txt":
            document = _txt_document(path)
            if document is None:
                stats.invalid_documents += 1
            else:
                documents.append(document)
        else:
            documents.extend(_jsonl_documents(path, stats))
    unique: list[TextDocument] = []
    hashes: set[str] = set()
    for document in documents:
        if document.sha256 in hashes:
            stats.duplicate_documents += 1
        else:
            hashes.add(document.sha256)
            unique.append(document)
    grouped = _assign_near_duplicate_groups(unique)
    stats.documents_loaded = len(grouped)
    stats.source_groups = len({document.source_group for document in grouped})
    stats.near_duplicate_clusters = len({document.split_group for document in grouped})
    stats.total_bytes = sum(document.byte_count for document in grouped)
    return grouped, stats


def iter_document_chunks(document: TextDocument) -> Iterator[str]:
    if document.text is not None:
        yield _normalized(document.text)
        return
    if document.path.suffix.lower() == ".txt":
        yield from _iter_text_chunks(document.path)
        return
    wanted = set(document.record_lines)
    with document.path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            if line_number not in wanted:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and (text := _record_text(payload)):
                yield text + "\n"


def split_documents(
    documents: list[TextDocument], *, validation_fraction: float = 0.15, test_fraction: float = 0.15, seed: int = 2026
) -> CorpusSplit:
    if not 0 < validation_fraction < 1 or not 0 < test_fraction < 1 or validation_fraction + test_fraction >= 1:
        raise ValueError("Frações de validação e teste inválidas")
    groups: dict[str, list[TextDocument]] = {}
    for document in documents:
        groups.setdefault(document.split_group, []).append(document)
    if len(groups) < 3:
        raise ValueError("São necessários ao menos três grupos de documentos para um split sem vazamento")
    keys = list(groups)
    random.Random(seed).shuffle(keys)
    test_count = max(1, round(len(keys) * test_fraction))
    validation_count = max(1, round(len(keys) * validation_fraction))
    if test_count + validation_count >= len(keys):
        raise ValueError("Não restaram grupos suficientes para treinamento")
    test_keys = set(keys[:test_count])
    validation_keys = set(keys[test_count : test_count + validation_count])
    train_keys = set(keys[test_count + validation_count :])
    return CorpusSplit(
        train=[document for key in train_keys for document in groups[key]],
        validation=[document for key in validation_keys for document in groups[key]],
        test=[document for key in test_keys for document in groups[key]],
        seed=seed,
        validation_fraction=validation_fraction,
        test_fraction=test_fraction,
    )


def tokenize_documents(documents: Iterable[TextDocument], tokenizer: Tokenizer) -> torch.Tensor:
    tokens: list[int] = []
    for document in documents:
        tokens.append(tokenizer.bos_id)
        for chunk in iter_document_chunks(document):
            tokens.extend(tokenizer.encode(chunk, add_bos=False, add_eos=False))
        tokens.append(tokenizer.eos_id)
    return torch.tensor(tokens, dtype=torch.long)


def prepare_token_store(
    documents: Iterable[TextDocument], tokenizer: Tokenizer, path: str | Path, *, split_metadata: dict[str, Any]
) -> TokenStore:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    count = 0
    document_hashes: list[str] = []
    with output.open("wb") as handle:
        for document in documents:
            document_hashes.append(document.sha256)
            for token_list in ([tokenizer.bos_id], *(tokenizer.encode(chunk, add_bos=False, add_eos=False) for chunk in iter_document_chunks(document)), [tokenizer.eos_id]):
                values = array("I", token_list)
                raw = values.tobytes()
                handle.write(raw)
                digest.update(raw)
                count += len(values)
    metadata_path = output.with_suffix(".json")
    metadata = {
        "schema_version": 1,
        "path": output.name,
        "token_count": count,
        "sha256": digest.hexdigest(),
        "documents": document_hashes,
        "tokenizer": tokenizer.metadata(),
        "split": split_metadata,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return TokenStore(output, count, digest.hexdigest(), metadata_path)


def make_batch(
    tokens: torch.Tensor | TokenStore, *, batch_size: int, block_size: int, device: torch.device, generator: torch.Generator
) -> tuple[torch.Tensor, torch.Tensor]:
    token_count = int(tokens.numel())
    if token_count <= block_size:
        raise ValueError("Tokens insuficientes para o tamanho de bloco")
    starts = torch.randint(token_count - block_size, (batch_size,), generator=generator)
    if isinstance(tokens, TokenStore):
        sequences = [tokens.read_slice(int(start), block_size + 1) for start in starts]
        batch = torch.stack(sequences)
    else:
        batch = torch.stack([tokens[int(start) : int(start) + block_size + 1] for start in starts])
    return batch[:, :-1].to(device), batch[:, 1:].to(device)


def write_source_manifest(documents: Iterable[TextDocument], path: str | Path, *, license_note: str, stats: CorpusStats) -> None:
    rows = ["# Fontes locais", "", license_note, "", "| Arquivo | SHA-256 | Grupo |", "| --- | --- | --- |"]
    rows.extend(f"| {document.path.name} | `{document.sha256}` | `{document.source_group}` |" for document in documents)
    rows.extend(["", "## Estatísticas", "", "```json", json.dumps(stats.to_dict(), ensure_ascii=False, indent=2), "```", ""])
    Path(path).write_text("\n".join(rows), encoding="utf-8")
