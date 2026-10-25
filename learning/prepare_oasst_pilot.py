"""Prepare a pinned, filtered pt-BR OASST1 research pilot with grouped splits."""
from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import random
import re
import shutil
import unicodedata

REVISION = "fdf72ae0827c1cda404aff25b6603abec9e3399b"
ARCHIVE = "2023-04-12_oasst_ready.messages.jsonl.gz"
SOURCE_HASH = "286a6e9a5a413b3272ae9c0b5a20d327983dea1c24342ae28cb244a6da65185c"
LICENSE_HASH = "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/language-pilot"
SEED = 25102026
BLOCKED = re.compile(r"https?://|[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b|\b\d{8,}\b", re.I)
LABELS = ("pii", "spam", "lang_mismatch", "not_appropriate", "hate_speech", "sexual_content", "violence")
MANUAL_EXCLUSIONS = {
    "6f9c020e-6f3c-4e1c-91ca-6598dae7d6d5": "Answers about billiards when the source question asks about poker; observed during source quality review."
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rejection(row: dict) -> str | None:
    if row.get("message_id") in MANUAL_EXCLUSIONS:
        return "manual_topic_mismatch"
    if row.get("lang") != "pt-BR":
        return "not_pt_br"
    if row.get("synthetic") is not False or row.get("model_name"):
        return "source_marks_synthetic"
    if row.get("deleted") or row.get("review_result") is not True:
        return "not_positively_reviewed"
    for key in LABELS:
        label = row.get("labels", {}).get(key, {})
        if label.get("count", 0) < 2 or label.get("value", 1) > 0:
            return "source_label_" + key
    if row.get("labels", {}).get("quality", {}).get("value", 0) < 0.6:
        return "low_source_quality"
    text = row["text"]
    if not 20 <= len(text) <= 4000:
        return "length"
    if BLOCKED.search(text):
        return "identifier_or_link_pattern"
    # Preserve only explanatory/support material in this first bounded lot.
    if re.search(r"poema|letra de|música|musica|fernando pessoa|whatsapp|chatgpt|openassistant|open assistant", text, re.I):
        return "excluded_scope_or_identity"
    return None


def group_split(records: list[dict]) -> dict[str, list[dict]]:
    """Unify whole trees and long exact duplicate messages before splitting."""
    parent = {r["tree_id"]: r["tree_id"] for r in records}

    def find(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    known = {}
    for record in records:
        for msg in record["messages"]:
            normalized = " ".join(msg["content"].casefold().split())
            if len(normalized) < 80:
                continue
            if normalized in known:
                a, b = find(record["tree_id"]), find(known[normalized])
                parent[max(a, b)] = min(a, b)
            known[normalized] = record["tree_id"]
    # Merge near-duplicate initial prompts as well, using word-shingle Jaccard.
    roots = {r["tree_id"]: r["messages"][0]["content"].casefold().split() for r in records}
    roots = {k: {tuple(v[i:i + 3]) for i in range(len(v) - 2)} for k, v in roots.items()}
    keys = sorted(roots)
    for i, left in enumerate(keys):
        for right in keys[i + 1:]:
            a, b = roots[left], roots[right]
            if min(len(a), len(b)) >= 10 and len(a & b) / len(a | b) >= 0.8:
                x, y = find(left), find(right)
                parent[max(x, y)] = min(x, y)
    groups = sorted({find(k) for k in parent})
    if len(groups) < 20:
        raise ValueError("Insufficient independent conversation groups for this pilot")
    random.Random(SEED).shuffle(groups)
    n = max(2, len(groups) // 10)
    assignments = {g: "test" if i < n else "validation" if i < 2 * n else "train" for i, g in enumerate(groups)}
    result = {s: [] for s in ("train", "validation", "test")}
    for record in records:
        record = {**record, "group_id": find(record["tree_id"])}
        result[assignments[record["group_id"]]].append(record)
    return result


def prepare(cache: Path, output: Path = DEST) -> dict:
    if output.exists():
        raise ValueError("Output already exists; refuse to replace the audited lot")
    if sha(cache / ARCHIVE) != SOURCE_HASH or sha(cache / "LICENSE") != LICENSE_HASH:
        raise ValueError("Source or license hash mismatch")
    rows = [json.loads(line) for line in gzip.open(cache / ARCHIVE, "rt", encoding="utf-8")]
    excluded = Counter()
    accepted = {}
    for row in rows:
        reason = rejection(row)
        if reason:
            excluded[reason] += 1
        else:
            accepted[row["message_id"]] = row
    records = []
    for row in accepted.values():
        if row["role"] != "assistant":
            continue
        chain, current, visited = [], row, set()
        while current is not None:
            key = current["message_id"]
            if key in visited:
                raise ValueError("Cycle in source conversation")
            visited.add(key)
            chain.append(current)
            parent_id = current.get("parent_id")
            if parent_id and parent_id not in accepted:
                excluded["incomplete_filtered_path"] += 1
                break
            current = accepted.get(parent_id)
        else:
            chain.reverse()
            if any(r["role"] != ("prompter" if i % 2 == 0 else "assistant") for i, r in enumerate(chain)):
                excluded["role_order"] += 1
                continue
            if len(chain) > 8 or sum(len(r["text"]) for r in chain) > 6000:
                excluded["path_too_long"] += 1
                continue
            records.append({"id": row["message_id"], "tree_id": row["message_tree_id"],
                            "source_message_ids": [r["message_id"] for r in chain],
                            "messages": [{"role": "user" if r["role"] == "prompter" else "assistant",
                                          "content": unicodedata.normalize("NFC", r["text"]).strip()} for r in chain]})
    splits = group_split(records)
    output.mkdir(parents=True)
    for name, items in splits.items():
        (output / f"{name}.json").write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(cache / "LICENSE", output / "LICENSE-APACHE-2.0.txt")
    shutil.copy2(cache / "README.md", output / "UPSTREAM-DATASET-CARD.md")
    report = {"source": "OpenAssistant/oasst1", "revision": REVISION,
              "url": f"https://huggingface.co/datasets/OpenAssistant/oasst1/resolve/{REVISION}/{ARCHIVE}",
              "license": "Apache-2.0 (dataset publisher declaration and LICENSE verified)",
              "attribution": "OpenAssistant contributors / LAION-AI, OASST1, 2023",
              "original_sha256": SOURCE_HASH, "license_sha256": LICENSE_HASH,
              "language": "pt-BR according to source tags", "seed": SEED,
              "excluded": dict(excluded), "accepted_messages_before_path_filter": len(accepted),
              "manual_exclusions": MANUAL_EXCLUSIONS,
              "records": len(records), "trees": len({r["tree_id"] for r in records}),
              "splits": {s: {"records": len(items), "groups": len({r["group_id"] for r in items}),
                              "sha256": sha(output / f"{s}.json")} for s, items in splits.items()},
              "limitations": ["Source flags are not proof of human authorship or factual correctness.",
                              "PII label and regex filtering are incomplete; not a complete manual privacy review.",
                              "No user IDs, timestamps or other account metadata retained in derivatives.",
                              "Repeated prefixes within one conversation tree remain within one split.",
                              "Near-duplicate checks cover initial prompts; semantic duplicates can remain."]}
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.cache), ensure_ascii=False, indent=2))
