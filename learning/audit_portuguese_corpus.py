"""Verify prepared corpus artifacts and report integrity separately from readiness."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re

from learning.corpus_tokenizer import rows, sha_file
from learning.portuguese_corpus import DEST, PII, ROOT, digest, normalize, portuguese_paragraph


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit(corpus=DEST):
    manifest = json.loads((corpus / "manifest.json").read_text())
    token_manifest = json.loads((corpus / "tokenizer/manifest.json").read_text())
    require(token_manifest["source_manifest_sha256"] == sha_file(corpus / "manifest.json"), "Source manifest hash mismatch")
    require(manifest["open_evaluation_sha256"] == sha_file(ROOT / "evaluation/portuguese-v1.json"), "Evaluation hash mismatch")
    paragraph_owners, group_owners, ids = {}, {}, set()
    overlaps, problems, count = [], [], 0
    for split in ("train", "validation", "test"):
        path = corpus / f"{split}.jsonl"
        require(sha_file(path) == manifest["partitions"][split]["sha256"], "Partition hash mismatch")
        indexes = list(rows(corpus / f"tokenizer/index-{split}.jsonl"))
        token_path = corpus / f"tokenizer/tokens-{split}.bin"
        metadata = token_manifest["partitions"][split]
        require(sha_file(token_path) == metadata["store_sha256"], "Token store hash mismatch")
        require(token_path.stat().st_size == 4 * metadata["tokens_including_bos_eos"], "Token store size mismatch")
        expected_offset = 0
        documents = list(rows(path))
        require(len(documents) == len(indexes) == manifest["partitions"][split]["documents"], "Document index count mismatch")
        for record, index in zip(documents, indexes):
            count += 1
            if record["id"] in ids:
                problems.append("duplicate_document_id")
            ids.add(record["id"])
            require(digest(record["text"].encode()) == record["sha256"], "Document hash mismatch")
            require(re.fullmatch(r"[a-f0-9]{64}", record["source_sha256"]), "Invalid source hash")
            require(record["license"] in {"PSF-2.0", "CC-BY-SA-2.5", "CC-BY-4.0"}, "Unknown license")
            require(record["attribution"] and record["changes"] and record["source_url"].startswith("https://"), "Missing attribution or provenance")
            require(index["id"] == record["id"] and index["text_sha256"] == record["sha256"], "Index identity mismatch")
            require(index["offset_tokens"] == expected_offset and index["length"] >= 2, "Index offset mismatch")
            expected_offset += index["length"]
            owner = group_owners.setdefault(record["group_id"], split)
            if owner != split:
                overlaps.append({"type": "group", "id": record["group_id"]})
            if PII.search(record["text"]):
                problems.append("identifier_pattern_remaining")
            for paragraph in record["text"].split("\n\n"):
                if not portuguese_paragraph(paragraph):
                    problems.append("language_heuristic_failed")
                key = digest(normalize(paragraph).casefold().encode())
                owner = paragraph_owners.setdefault(key, split)
                if owner != split:
                    overlaps.append({"type": "exact_paragraph", "sha256": key})
        require(expected_offset == metadata["tokens_including_bos_eos"], "Index total mismatch")
    require(not problems and not overlaps, f"Corpus problems: {problems[:5]}, overlaps: {overlaps[:5]}")
    train = token_manifest["partitions"]["train"]
    shares = {f: n / train["tokens_including_bos_eos"] for f, n in train["by_family"].items()}
    reviewed = json.loads((corpus / "dialogues/manifest.json").read_text())
    require(sha_file(corpus / "dialogues/reviewed-candidates.jsonl") == reviewed["candidate_file_sha256"], "Reviewed dialogue hash mismatch")
    accepted = list(rows(corpus / "dialogues/reviewed-candidates.jsonl"))
    review_log = json.loads((corpus / "dialogues/review-log.json").read_text())
    accepted_ids = {r["id"] for r in review_log if r["decision"] == "accepted_candidate"}
    require(len(accepted) == reviewed["accepted_candidates"] and {r["id"] for r in accepted} == accepted_ids, "Dialogue review decisions mismatch")
    # These are research-quality gates, not an inferred authorization workflow.
    readiness = {"at_least_four_source_families": len(shares) >= 4,
                 "largest_source_family_at_most_25_percent": max(shares.values()) <= 0.25,
                 "independent_human_dialogue_review": False,
                 "sufficient_diverse_conversation_curriculum": reviewed["eligible_as_broad_conversational_dataset"]}
    return {"integrity_checks_passed": True, "documents_verified": count,
            "cross_partition_group_overlap": 0, "cross_partition_exact_paragraph_overlap": 0,
            "identifier_pattern_hits_remaining": 0, "token_stores_verified": True,
            "all_document_round_trips_verified_during_tokenization": True,
            "neural_weights_updated": False, "open_evaluation_consumed": False,
            "total_bpe_tokens": sum(v["tokens_including_bos_eos"] for v in token_manifest["partitions"].values()),
            "train_bpe_tokens": train["tokens_including_bos_eos"], "train_source_token_shares": shares,
            "broad_conversation_readiness_gates": readiness,
            "ready_as_broad_conversation_corpus": all(readiness.values()),
            "domain_scope": "technical Portuguese prose; bounded research pretraining material",
            "caveats": manifest["limits"]}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEST)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/corpus-pt-v1/audit.json")
    args = parser.parse_args()
    report = audit(args.corpus)
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
