"""Prepare fresh OASST2 trees and separately licensed historical prose."""
from __future__ import annotations

from array import array
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import unicodedata

from tokenizers import Tokenizer

from brain.bpe_tokenizer import ByteBPETokenizer
from learning.corpus_tokenizer import sha_file
from learning.language_pilot import encode_messages
from learning.portuguese_corpus import ROOT
from learning.prepare_oasst_pilot import group_split, rejection

DEST = ROOT / "data/neural-dialogue-v2"
OASST2_REV = "179dd21fc55192153d94adb0e0ce8f69e222bf75"
OASST2_FILE = "2023-11-05_oasst2_ready.messages.jsonl.gz"
OASST2_SHA = "a9f240c4c77aa1378364f70d37e753c07ba284e247b019d700e1947a0e5da751"
BOOKS = {
    67535: ("train", 1922, "7898e07218e1431f00d6e6aa1d5ebe364bb6d770afaab865868a11df6da07350"),
    69187: ("train", 1913, "f17560b8cc8b260e61251090e62c6ed7794d1e1e57c5a573910bcbf726e169e5"),
    69229: ("train", 1934, "61378dca26a39184a8b2d68b4378bc4fd878f5e577bdc2a8526eaa99614a271c"),
    67740: ("validation", 1877, "e19bbd57aa2fff7715832b52e1c28562d8bdc4a908515609a6f638799d916bac"),
    68541: ("test", 1895, "6823430573966358842c539f23d951dbc55c26eba9c484a6f6713c8dadf5efe1"),
}
IDENTITY = re.compile(r"chatgpt|openassistant|openai|laion|gpt[- ]?[34]|finja que|atue como|finja ser", re.I)


class FastProjectTokenizer:
    """Same existing project vocabulary/IDs, with the verified fast encoder."""
    def __init__(self):
        folder = ROOT / "data/corpus-pt-v1/tokenizer"
        self.own = ByteBPETokenizer.load(folder / "elysia-bpe.json")
        self.fast = Tokenizer.from_file(str(folder / "fast-bpe.json"))
        self.mapping = {int(k): v for k, v in json.loads((folder / "fast-id-to-elysia-id.json").read_text(encoding='utf-8')).items()}
        self.bos_id, self.eos_id = self.own.bos_id, self.own.eos_id
        self.vocab_size = self.own.vocab_size

    def encode(self, text, *, add_bos=True, add_eos=True):
        ids = [self.mapping[t] for t in self.fast.encode(unicodedata.normalize("NFC", text)).ids]
        return ([self.bos_id] if add_bos else []) + ids + ([self.eos_id] if add_eos else [])

    def decode(self, ids, *, errors="strict"):
        return self.own.decode(ids, errors=errors)

    def metadata(self):
        return self.own.metadata()


def strip_book(raw: str) -> str:
    start = re.search(r"\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK .*?\*\*\*", raw, re.I)
    end = re.search(r"\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK .*?\*\*\*", raw, re.I)
    if not start or not end or start.end() >= end.start():
        raise ValueError("Missing book boundaries")
    text = raw[start.end():end.start()]
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n"))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 100000:
        raise ValueError("Unexpectedly short book")
    return text


def prepare(cache: Path, output: Path = DEST):
    if output.exists():
        raise ValueError("Prepared v2 data exists; refuse overwrite")
    if sha_file(cache / "oasst2" / OASST2_FILE) != OASST2_SHA:
        raise ValueError("OASST2 source hash mismatch")
    old_trees, old_text = set(), set()
    for line in gzip.open(cache / "oasst1/2023-04-12_oasst_ready.messages.jsonl.gz", "rt", encoding="utf-8"):
        row = json.loads(line)
        if row.get("lang", "").startswith("pt"):
            old_trees.add(row["message_tree_id"])
            if len(row["text"]) >= 40:
                old_text.add(" ".join(row["text"].casefold().split()))
    accepted, excluded = {}, Counter()
    for line in gzip.open(cache / "oasst2" / OASST2_FILE, "rt", encoding="utf-8"):
        row = json.loads(line)
        if row.get("lang") != "pt-BR":
            continue
        reason = rejection(row)
        if row["message_tree_id"] in old_trees:
            reason = "historical_tree_excluded"
        elif " ".join(row["text"].casefold().split()) in old_text:
            reason = "historical_text_duplicate"
        elif IDENTITY.search(row["text"]):
            reason = "external_identity_or_impersonation"
        if reason:
            excluded[reason] += 1
        else:
            accepted[row["message_id"]] = row
    paths = []
    for row in accepted.values():
        if row["role"] != "assistant":
            continue
        chain, current, seen = [], row, set()
        while current:
            if current["message_id"] in seen:
                raise ValueError("Cycle in source tree")
            seen.add(current["message_id"])
            chain.append(current)
            parent = current.get("parent_id")
            if parent and parent not in accepted:
                excluded["incomplete_filtered_path"] += 1
                break
            current = accepted.get(parent)
        else:
            chain.reverse()
            if len(chain) > 8 or sum(len(r["text"]) for r in chain) > 8000:
                excluded["path_budget"] += 1
                continue
            if any(r["role"] != ("prompter" if i % 2 == 0 else "assistant") for i, r in enumerate(chain)):
                excluded["role_order"] += 1
                continue
            paths.append({"id": row["message_id"], "tree_id": row["message_tree_id"],
                          "messages": [{"role": "user" if r["role"] == "prompter" else "assistant",
                                        "content": unicodedata.normalize("NFC", r["text"])} for r in chain],
                          "source_message_ids": [r["message_id"] for r in chain],
                          "minimum_source_quality": min(r["labels"]["quality"]["value"] for r in chain),
                          "source": "OpenAssistant/oasst2", "license": "Apache-2.0", "synthetic": False,
                          "authorship": "Source marks nonsynthetic; not independently verified"})
    splits = group_split(paths)
    tokenizer = FastProjectTokenizer()
    output.mkdir(parents=True)
    (output / "dialogues").mkdir()
    for split, records in splits.items():
        (output / f"dialogues/{split}.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline='\n')
    supplements = []
    for record in json.loads((ROOT / "data/context-words/train.json").read_text(encoding='utf-8'))["records"]:
        supplements.append({"id": record["id"], "group_id": record["group_id"], "synthetic": True,
                            "source": "preexisting diagnostic curriculum, before the 24-case evaluation",
                            "messages": record["messages"] + [{"role": "assistant", "content": record["answer"]}]})
    (output / "dialogues/legacy-synthetic-train.json").write_text(json.dumps(supplements, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline='\n')
    shutil.copy2(ROOT / "data/language-pilot/LICENSE-APACHE-2.0.txt", output / "dialogues/LICENSE-APACHE-2.0.txt")
    shutil.copy2(cache / "oasst2/README.md", output / "dialogues/UPSTREAM-CARD.md")
    originals = output / "sources"
    originals.mkdir()
    literature = {s: [] for s in splits}
    books_metadata = {r["id"]: r for r in json.loads((cache / "gutenberg-v2/sources.json").read_text(encoding='utf-8'))}
    for book_id, (split, death, expected) in BOOKS.items():
        raw = cache / f"gutenberg-v2/{book_id}.txt"
        page = cache / f"gutenberg-v2/{book_id}.html"
        if sha_file(raw) != expected:
            raise ValueError("Book source hash mismatch")
        page_text = page.read_text(encoding='utf-8')
        if 'Public domain in the USA.' not in page_text or str(death) not in page_text or death > 1955:
            raise ValueError("Book rights evidence missing")
        body = strip_book(raw.read_text(encoding="utf-8-sig"))
        # Retain the complete original text, including Gutenberg notices/license.
        shutil.copy2(raw, originals / raw.name)
        shutil.copy2(page, originals / page.name)
        metadata = books_metadata[book_id]
        literature[split].append({"id": f"pg-{book_id}", "group_id": "author/" + metadata["authors"][0],
                                  "text": body, "source_url": metadata["url"], "source_sha256": expected,
                                  "attribution": metadata["authors"], "rights": metadata["rights"],
                                  "brazil_term_basis": {"author_death_year": death, "over_70_years_elapsed": True},
                                  "scope": "historical prose only, not conversational behavior; contains archaic usage and dated prejudices"})
    (output / "literature").mkdir()
    stores = {}
    for split, records in literature.items():
        path = output / f"literature/{split}.jsonl"
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8", newline='\n')
        count = 0
        with (output / f"literature/tokens-{split}.bin").open("wb") as handle:
            for record in records:
                ids = tokenizer.encode(record["text"])
                if tokenizer.decode(ids) != record["text"]:
                    raise ValueError("Book tokenization lost text")
                values = array("I", ids)
                values.tofile(handle)
                count += len(ids)
        stores[split] = {"tokens": count, "sha256": sha_file(output / f"literature/tokens-{split}.bin"), "authors": len(records)}
    report = {"oasst2_revision": OASST2_REV, "oasst2_sha256": OASST2_SHA, "old_portuguese_trees_excluded": len(old_trees),
              "exclusions": dict(excluded), "dialogue_splits": {s: {"paths": len(v), "trees": len({r['tree_id'] for r in v}),
              "sha256": sha_file(output / f"dialogues/{s}.json")} for s, v in splits.items()},
              "synthetic_supplement_records": len(supplements), "literature_stores": stores,
              "books": books_metadata, "tokenizer": tokenizer.metadata(), "evaluation_sha256": sha_file(ROOT / "evaluation/portuguese-v1.json"),
              "caveats": ["OASST flags and moderation votes are not independent factual verification.",
                          "Historical fiction is not contemporary conversation or a source of factual answers.",
                          "The synthetic supplement is explicitly separate and predates the frozen open evaluation.",
                          "This is a bounded research dataset, not a broad-conversation readiness claim."]}
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline='\n')
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEST)
    args = parser.parse_args()
    print(json.dumps(prepare(args.cache, args.output), ensure_ascii=False, indent=2))
