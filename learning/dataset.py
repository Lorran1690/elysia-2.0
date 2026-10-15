"""Local text loading, document-level splitting and next-token batches."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from pathlib import Path

import torch

from brain.tokenizer import ByteTokenizer


@dataclass(frozen=True)
class TextDocument:
    path: Path
    text: str
    sha256: str


@dataclass(frozen=True)
class CorpusSplit:
    train: tuple[TextDocument, ...]
    validation: tuple[TextDocument, ...]


def load_text_documents(directory: str | Path) -> list[TextDocument]:
    root = Path(directory)
    documents: list[TextDocument] = []
    for path in sorted(root.rglob("*.txt")):
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            continue
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        documents.append(TextDocument(path=path, text=text, sha256=digest))
    if not documents:
        raise FileNotFoundError(f"Nenhum arquivo .txt encontrado em {root}")
    return documents


def split_documents(
    documents: list[TextDocument],
    *,
    validation_fraction: float = 0.25,
    seed: int = 1337,
) -> CorpusSplit:
    if not 0.0 < validation_fraction < 1.0:
        raise ValueError("validation_fraction precisa estar entre 0 e 1")
    shuffled = list(documents)
    random.Random(seed).shuffle(shuffled)
    if len(shuffled) == 1:
        # A corpus real deve ter mais de um documento; this fallback keeps the loader useful for smoke tests.
        return CorpusSplit(train=tuple(shuffled), validation=tuple(shuffled))
    validation_count = max(1, round(len(shuffled) * validation_fraction))
    validation_count = min(validation_count, len(shuffled) - 1)
    return CorpusSplit(
        train=tuple(shuffled[validation_count:]),
        validation=tuple(shuffled[:validation_count]),
    )


def tokenize_documents(documents: tuple[TextDocument, ...], tokenizer: ByteTokenizer) -> torch.Tensor:
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
    starts = torch.randint(
        maximum_start + 1,
        (batch_size,),
        generator=generator,
        device="cpu",
    )
    inputs = torch.stack([tokens[start : start + block_size] for start in starts.tolist()])
    targets = torch.stack([tokens[start + 1 : start + block_size + 1] for start in starts.tolist()])
    return inputs.to(device), targets.to(device)


def write_source_manifest(
    documents: list[TextDocument],
    output_path: str | Path,
    *,
    license_note: str,
) -> None:
    output = Path(output_path)
    lines = [
        "# Manifesto de dados",
        "",
        "Os arquivos abaixo são locais e foram criados especificamente para testes do pipeline.",
        f"Nota de licença/origem: {license_note}",
        "",
        "| Arquivo | SHA-256 |",
        "|---|---|",
    ]
    lines.extend(f"| `{document.path.as_posix()}` | `{document.sha256}` |" for document in documents)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
