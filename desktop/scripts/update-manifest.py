"""Emit fixed-repository update metadata for an already tested Windows installer."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re


def manifest(installer: Path, version: str, source: str, build: int) -> dict:
    if not re.fullmatch(r"[a-f0-9]{40}", source) or build <= 0:
        raise ValueError("A full source SHA and a positive native workflow build number are required.")
    if installer.name != "Elysia-Setup-x64.exe" or not 0 < installer.stat().st_size <= 1024**3:
        raise ValueError("Invalid native installer name or size.")
    tag = "native-" + source[:12]
    with installer.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {
        "format": "elysia-native-update-v1",
        "repository": "Lorran1690/elysia-2.0",
        "version": version,
        "build": build,
        "source_sha": source,
        "tag": tag,
        "installer": {
            "name": installer.name,
            "url": f"https://github.com/Lorran1690/elysia-2.0/releases/download/{tag}/{installer.name}",
            "bytes": installer.stat().st_size,
            "sha256": digest,
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("installer", type=Path)
    parser.add_argument("--output", type=Path, default=Path("elysia-update.json"))
    args = parser.parse_args()
    version = json.loads((Path(__file__).resolve().parents[1] / "package.json").read_text())["version"]
    value = manifest(args.installer, version, os.environ.get("GITHUB_SHA", ""), int(os.environ.get("GITHUB_RUN_NUMBER", "0")))
    args.output.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(value))
