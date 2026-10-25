"""Train BPE from scratch on train only, export to Elysia and audit token stores."""
from __future__ import annotations

import argparse
from array import array
import hashlib
import json
from pathlib import Path
import sys

from tokenizers import Tokenizer, models, normalizers, pre_tokenizers, trainers

from brain.bpe_tokenizer import ByteBPETokenizer
from learning.portuguese_corpus import DEST, digest


def byte_alphabet():
    values = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    codes = values[:]
    count = 0
    for value in range(256):
        if value not in values:
            values.append(value)
            codes.append(256 + count)
            count += 1
    return {chr(code): value for value, code in zip(values, codes)}


def export_elysia(fast: Tokenizer, vocab_size: int):
    alphabet = byte_alphabet()
    payload = json.loads(fast.to_str())
    own = ByteBPETokenizer(vocab_size)
    by_bytes = {bytes([i]): i for i in range(256)}
    for pair in payload["model"]["merges"]:
        left, right = pair if isinstance(pair, list) else pair.split(" ")
        left_bytes = bytes(alphabet[c] for c in left)
        right_bytes = bytes(alphabet[c] for c in right)
        combined = left_bytes + right_bytes
        if combined in by_bytes:
            raise ValueError("Alternative merge for same bytes cannot be exported losslessly")
        own.merges.append((by_bytes[left_bytes], by_bytes[right_bytes]))
        by_bytes[combined] = len(own._token_bytes)
        own._token_bytes.append(combined)
    own._refresh_special_ids()
    own._validate()
    mapping = {index: by_bytes[bytes(alphabet[c] for c in token)] for token, index in fast.get_vocab().items()}
    return own, mapping


def rows(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def sha_file(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def prepare(corpus: Path = DEST, vocab_size=2048):
    target = corpus / "tokenizer"
    if target.exists():
        raise ValueError("Tokenizer already exists; refuse overwrite")
    if not 512 <= vocab_size <= 8192:
        raise ValueError("Vocabulary outside bounded corpus-preparation range")
    manifest = json.loads((corpus / "manifest.json").read_text())
    for split in ("train", "validation", "test"):
        if sha_file(corpus / f"{split}.jsonl") != manifest["partitions"][split]["sha256"]:
            raise ValueError("Corpus differs from audited manifest")
    target.mkdir()
    fast = Tokenizer(models.BPE())
    fast.normalizer = normalizers.NFC()
    fast.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=False)
    trainer = trainers.BpeTrainer(vocab_size=vocab_size - 3, min_frequency=5, show_progress=False,
                                 initial_alphabet=sorted(pre_tokenizers.ByteLevel.alphabet()))
    # No tokenization of validation/test participates in fitting the vocabulary.
    fast.train_from_iterator((r["text"] for r in rows(corpus / "train.jsonl")), trainer=trainer)
    fast.save(str(target / "fast-bpe.json"))
    own, mapping = export_elysia(fast, vocab_size)
    own.save(target / "elysia-bpe.json")
    (target / "fast-id-to-elysia-id.json").write_text(json.dumps(mapping, sort_keys=True), encoding="utf-8", newline='\n')
    totals, samples = {}, 0
    for split in ("train", "validation", "test"):
        index_rows = []
        count, family = 0, {}
        binary = target / f"tokens-{split}.bin"
        with binary.open("wb") as handle:
            for i, record in enumerate(rows(corpus / f"{split}.jsonl")):
                ids = [own.bos_id] + [mapping[t] for t in fast.encode(record["text"]).ids] + [own.eos_id]
                if own.decode(ids) != record["text"]:
                    raise ValueError("Lossy token round trip")
                # Verify rank/application equivalence as well, not only decoding.
                if split == "train" and i % 100 == 0:
                    sample = record["text"][:1200]
                    expected = [own.bos_id] + [mapping[t] for t in fast.encode(sample).ids] + [own.eos_id]
                    if own.encode(sample) != expected:
                        raise ValueError("Fast/custom merge application mismatch")
                    samples += 1
                packed = array("I", ids)
                if packed.itemsize != 4:
                    raise ValueError("uint32 storage unsupported")
                if sys.byteorder != "little":
                    packed.byteswap()
                packed.tofile(handle)
                index_rows.append({"id": record["id"], "group_id": record["group_id"], "offset_tokens": count,
                                   "length": len(ids), "family": record["family"], "text_sha256": record["sha256"]})
                count += len(ids)
                family[record["family"]] = family.get(record["family"], 0) + len(ids)
        (target / f"index-{split}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in index_rows), encoding="utf-8", newline='\n')
        totals[split] = {"tokens_including_bos_eos": count, "documents": len(index_rows), "by_family": family,
                         "store_sha256": sha_file(binary), "store_bytes": binary.stat().st_size,
                         "dtype": "uint32", "byteorder": "little"}
    result = {"trained_from_scratch": True, "fit_partition": "train only", "pretrained_artifacts_used": False,
              "implementation": "tokenizers Rust BPE trainer, byte-level with no regex segmentation; lossless export to project ByteBPETokenizer",
              "source_manifest_sha256": sha_file(corpus / "manifest.json"),
              "training_file_sha256": sha_file(corpus / "train.jsonl"), "vocab_size": own.vocab_size,
              "tokenizer": own.metadata(), "custom_fast_encoding_samples_checked": samples,
              "all_documents_round_trip_checked": True, "partitions": totals,
              "elysia_tokenizer_sha256": sha_file(target / "elysia-bpe.json"),
              "neural_weights_updated": False}
    (target / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8", newline='\n')
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEST)
    parser.add_argument("--vocab-size", type=int, default=2048)
    args = parser.parse_args()
    print(json.dumps(prepare(args.corpus, args.vocab_size), ensure_ascii=False, indent=2))
