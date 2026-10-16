"""Clean and audit the three approved Machado de Assis Gutenberg works."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import time
from pathlib import Path
from typing import Any

from learning.dataset import load_corpus, split_documents
from learning.dataset import iter_document_chunks, prepare_token_store
from brain.bpe_tokenizer import ByteBPETokenizer


WORKS = {
    "dom-casmurro": {
        "id": "55752",
        "title": "Dom Casmurro",
        "author": "Machado de Assis",
        "landing_url": "https://www.gutenberg.org/ebooks/55752",
        "download_url": "https://www.gutenberg.org/cache/epub/55752/pg55752.txt",
        "release_date": "2017-10-15",
    },
    "memorias-postumas-de-bras-cubas": {
        "id": "54829",
        "title": "Memorias Posthumas de Braz Cubas",
        "author": "Machado de Assis",
        "landing_url": "https://www.gutenberg.org/ebooks/54829",
        "download_url": "https://www.gutenberg.org/cache/epub/54829/pg54829.txt",
        "release_date": "2017-06-02",
    },
    "quincas-borba": {
        "id": "55682",
        "title": "Quincas Borba",
        "author": "Machado de Assis",
        "landing_url": "https://www.gutenberg.org/ebooks/55682",
        "download_url": "https://www.gutenberg.org/cache/epub/55682/pg55682.txt",
        "release_date": "2017-10-05",
    },
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clean_gutenberg_text(raw: str) -> str:
    normalized = unicodedata.normalize("NFC", raw.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff"))
    start = re.search(r"^\*\*\* START OF THE PROJECT GUTENBERG EBOOK .*? \*\*\*$", normalized, re.MULTILINE)
    end = re.search(r"^\*\*\* END OF THE PROJECT GUTENBERG EBOOK .*? \*\*\*$", normalized, re.MULTILINE)
    if start is None or end is None or end.start() <= start.end():
        raise ValueError("Marcadores técnicos do Gutenberg não foram encontrados na ordem esperada")
    body = normalized[start.end() : end.start()]
    lines = [line.rstrip() for line in body.split("\n")]
    output: list[str] = []
    blank_count = 0
    for line in lines:
        if not line.strip():
            blank_count += 1
            if blank_count <= 2:
                output.append("")
        else:
            blank_count = 0
            output.append(line)
    return "\n".join(output).strip() + "\n"


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\wÀ-ÖØ-öø-ÿ]+\b", text, flags=re.UNICODE))


def _stable_fingerprint(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _quality_audit(text: str) -> dict[str, Any]:
    """Sample the beginning, middle and end so front matter is not checked only once."""
    markers = re.compile(r"(?i)\b(introduction|translator|tradução|tradutor|project gutenberg)\b")
    offsets = sorted({0, len(text) // 4, len(text) // 2, (len(text) * 3) // 4, max(0, len(text) - 5000)})
    samples = []
    for offset in offsets:
        window = text[offset : offset + 5000]
        samples.append({"offset": offset, "marker_hits": sorted(set(markers.findall(window)))})
    return {
        "sample_count": len(samples),
        "samples": samples,
        "modern_front_matter_detected": any(sample["marker_hits"] for sample in samples),
    }


def prepare(root: str | Path, *, skip_tokenizer: bool = False) -> dict[str, Any]:
    base = Path(root)
    originals = base / "originals"
    clean = base / "clean"
    clean.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for slug, work in WORKS.items():
        original_path = originals / f"{slug}.txt"
        if not original_path.exists():
            raise FileNotFoundError(f"Arquivo aprovado ausente: {original_path}")
        original_bytes = original_path.read_bytes()
        original_text = original_bytes.decode("utf-8")
        cleaned_text = clean_gutenberg_text(original_text)
        clean_path = clean / f"{slug}.txt"
        clean_path.write_text(cleaned_text, encoding="utf-8", newline="\n")
        clean_bytes = cleaned_text.encode("utf-8")
        quality = _quality_audit(cleaned_text)
        records.append(
            {
                **work,
                "format": "UTF-8 plain text",
                "accessed_at": "2026-10-15",
                "source_status": "Project Gutenberg declara public domain in the USA; confirmação brasileira fornecida pelo solicitante.",
                "source_conditions": "Preservar atribuição e avisos; a política do Project Gutenberg exige verificar a lei local e regula o uso da marca.",
                "original_path": str(original_path),
                "clean_path": str(clean_path),
                "original_bytes": len(original_bytes),
                "clean_bytes": len(clean_bytes),
                "original_sha256": _sha256(original_bytes),
                "clean_sha256": _sha256(clean_bytes),
                "characters": len(cleaned_text),
                "words": _word_count(cleaned_text),
                "start_marker_removed": True,
                "end_marker_removed": True,
                "modern_front_matter_detected": quality["modern_front_matter_detected"],
                "quality_audit": quality,
            }
        )
    documents, stats = load_corpus(clean)
    split = split_documents(documents, validation_fraction=0.15, test_fraction=0.15, seed=2026)
    record_by_name = {Path(item["clean_path"]).name: item for item in records}
    for partition, partition_documents in (("train", split.train), ("validation", split.validation), ("test", split.test)):
        for document in partition_documents:
            record_by_name[document.path.name]["split"] = partition
    processed = base / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    tokenizer_path = processed / "tokenizer-v0.4-machado.json"
    tokenizer_manifest_path = processed / "tokenizer-v0.4-machado.manifest.json"
    if skip_tokenizer:
        previous_manifest_path = base / "audit-manifest.json"
        if not previous_manifest_path.exists() or not tokenizer_path.exists() or not tokenizer_manifest_path.exists():
            raise FileNotFoundError("--skip-tokenizer exige manifesto e tokenizador já existentes")
        previous_manifest = json.loads(previous_manifest_path.read_text(encoding="utf-8"))
        token_audit = previous_manifest["tokenizer_audit"]
        tokenizer = ByteBPETokenizer.load(tokenizer_path)
    else:
        tokenizer_started = time.perf_counter()
        tokenizer = ByteBPETokenizer(512)
        tokenizer.train_documents(
            (iter_document_chunks(document) for document in split.train),
            min_pair_frequency=2,
            work_dir=processed / "bpe-work",
        )
        tokenizer.save(tokenizer_path)
        split_fingerprint = split.metadata()["fingerprint"]
        tokenizer_manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "training_split_fingerprint": split_fingerprint,
                    "training_partition_fingerprint": _stable_fingerprint({"split": split.metadata(), "partition": "train"}),
                    "tokenizer": tokenizer.metadata(),
                    "training_seconds": time.perf_counter() - tokenizer_started,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        token_audit = {"type": "byte_bpe", "tokenizer": tokenizer.metadata(), "splits": {}}
        for partition, partition_documents in (("train", split.train), ("validation", split.validation), ("test", split.test)):
            token_path = processed / f"tokens-{partition}.bin"
            store = prepare_token_store(partition_documents, tokenizer, token_path, split_metadata=split.metadata())
            byte_count = sum(len(chunk.encode("utf-8")) for document in partition_documents for chunk in iter_document_chunks(document))
            token_audit["splits"][partition] = {
                "bytes": byte_count,
                "tokens": store.token_count,
                "bytes_per_token": byte_count / store.token_count,
                "token_store": {"path": str(store.path), "sha256": store.sha256, "metadata_path": str(store.metadata_path)},
            }
    manifest = {
        "schema_version": 1,
        "status": "local-only-audit",
        "source_policy": "Somente as três obras aprovadas; nenhum outro corpus foi baixado.",
        "legal_note": "O Project Gutenberg declara domínio público nos EUA; a situação brasileira foi aprovada pelo solicitante, mas a página, licença e atribuição foram preservadas para auditoria.",
        "works": records,
        "stats": stats.to_dict(),
        "split": split.metadata(),
        "deduplication": {"exact_duplicates": stats.duplicate_documents, "near_duplicate_clusters": stats.near_duplicate_clusters},
        "tokenizer_audit": token_audit,
    }
    (base / "audit-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="data/corpus-v0.4")
    parser.add_argument("--skip-tokenizer", action="store_true", help="Reaudita amostras mantendo BPE e token stores existentes")
    args = parser.parse_args()
    print(json.dumps(prepare(args.root, skip_tokenizer=args.skip_tokenizer), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
