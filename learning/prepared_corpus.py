"""Load audited preassigned token stores without silently recomputing splits."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from learning.corpus_tokenizer import sha_file
from learning.dataset import TokenStore
from learning.portuguese_corpus import DEST


def load_partition(split: str, *, corpus: Path = DEST, for_training: bool = False) -> TokenStore:
    if split not in {"train", "validation", "test"}:
        raise ValueError("Unknown partition")
    if for_training and split != "train":
        raise ValueError("Only train may be loaded for weight updates")
    if sys.byteorder != "little":
        raise ValueError("Legacy TokenStore reader requires little-endian host")
    metadata_path = corpus / "tokenizer/manifest.json"
    manifest = json.loads(metadata_path.read_text(encoding="utf-8"))
    source = json.loads((corpus / "manifest.json").read_text(encoding="utf-8"))
    if sha_file(corpus / "manifest.json") != manifest["source_manifest_sha256"]:
        raise ValueError("Source manifest changed")
    if sha_file(corpus / f"{split}.jsonl") != source["partitions"][split]["sha256"]:
        raise ValueError("Partition source changed")
    info = manifest["partitions"][split]
    path = corpus / f"tokenizer/tokens-{split}.bin"
    if path.stat().st_size != info["tokens_including_bos_eos"] * 4 or sha_file(path) != info["store_sha256"]:
        raise ValueError("Token store changed")
    return TokenStore(path=path, token_count=info["tokens_including_bos_eos"],
                      sha256=info["store_sha256"], metadata_path=metadata_path)
