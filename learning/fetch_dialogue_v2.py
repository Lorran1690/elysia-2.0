"""Recover immutable conversational sources and committed book originals."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

from learning.dialogue_v2_data import DEST, OASST2_FILE, OASST2_REV, OASST2_SHA
from learning.download_oasst_pilot import download as fetch_oasst1


def fixed_file(url, path, expected, limit):
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Existing source differs; refuse overwrite")
        return
    temporary = path.with_suffix(path.suffix + ".part")
    size, digest = 0, hashlib.sha256()
    try:
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as handle:
            while chunk := response.read(65536):
                size += len(chunk)
                if size > limit:
                    raise ValueError("Source exceeds fixed byte limit")
                handle.write(chunk)
                digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ValueError("Downloaded source hash mismatch")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def fetch(cache):
    cache.mkdir(parents=True, exist_ok=True)
    fetch_oasst1(cache / "oasst1")
    second = cache / "oasst2"
    second.mkdir(exist_ok=True)
    for name, expected, limit in ((OASST2_FILE, OASST2_SHA, 64 * 1024 * 1024),
                                  ("README.md", "52bd472cf3cae04a4b21ecd5316f929741c47d991d4763b041c3a94de072dc31", 65536)):
        fixed_file(f"https://huggingface.co/datasets/OpenAssistant/oasst2/resolve/{OASST2_REV}/{name}", second / name, expected, limit)
    books = cache / "gutenberg-v2"
    books.mkdir(exist_ok=True)
    manifest = json.loads((DEST / "manifest.json").read_text())
    for source in (DEST / "sources").iterdir():
        destination = books / source.name
        if destination.exists() and destination.read_bytes() != source.read_bytes():
            raise ValueError("Existing book snapshot differs; refuse overwrite")
        if not destination.exists():
            shutil.copy2(source, destination)
    sources = list(manifest["books"].values())
    metadata = books / "sources.json"
    if metadata.exists() and json.loads(metadata.read_text()) != sources:
        raise ValueError("Existing book metadata differs; refuse overwrite")
    if not metadata.exists():
        metadata.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Pinned sources and full book/license snapshots verified.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    fetch(args.cache)
