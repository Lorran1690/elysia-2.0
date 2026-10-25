"""Download only the three pinned public source files for the OASST1 pilot."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import urllib.request

from learning.prepare_oasst_pilot import ARCHIVE, LICENSE_HASH, REVISION, SOURCE_HASH, sha

FILES = {
    ARCHIVE: (SOURCE_HASH, 40 * 1024 * 1024),
    "LICENSE": (LICENSE_HASH, 32 * 1024),
    "README.md": ("68483ac2fcc2f3f7779f453352363827678070ef35b6d746ccb2ca6958540fff", 64 * 1024),
}


def download(cache: Path):
    cache.mkdir(parents=True, exist_ok=True)
    for name, (expected, limit) in FILES.items():
        destination = cache / name
        if destination.exists():
            if sha(destination) != expected:
                raise ValueError(f"Existing source differs: {name}; will not overwrite")
            print(f"Verified existing {name}", flush=True)
            continue
        temporary = destination.with_suffix(destination.suffix + ".part")
        digest, size = hashlib.sha256(), 0
        url = f"https://huggingface.co/datasets/OpenAssistant/oasst1/resolve/{REVISION}/{name}"
        try:
            with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as handle:
                while chunk := response.read(65536):
                    size += len(chunk)
                    if size > limit:
                        raise ValueError(f"Source exceeds bound: {name}")
                    digest.update(chunk)
                    handle.write(chunk)
            if digest.hexdigest() != expected:
                raise ValueError(f"Source hash mismatch: {name}")
            temporary.replace(destination)
            print(f"Downloaded and verified {name}: {size} bytes", flush=True)
        finally:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    download(args.cache)
