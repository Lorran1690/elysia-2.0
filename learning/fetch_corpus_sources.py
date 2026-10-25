"""Recover only the three fixed public sources used by corpus-pt-v1."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import urllib.request

from learning.portuguese_corpus import DEST, MDN_REV, OMEKA_SHA, OMEKA_URL, PYTHON_REV


def git_source(path, url, revision, sparse=None):
    if path.exists():
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
        if actual != revision or subprocess.check_output(["git", "status", "--porcelain"], cwd=path, text=True).strip():
            raise ValueError(f"Existing cache differs: {path}; will not overwrite")
        print(f"Verified source revision: {path.name}", flush=True)
        return
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "--quiet"], cwd=path, check=True)
    subprocess.run(["git", "remote", "add", "origin", url], cwd=path, check=True)
    subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=path, check=True)
    subprocess.run(["git", "fetch", "--quiet", "--depth", "1", "--filter=blob:none", "origin", revision], cwd=path, check=True)
    if sparse:
        subprocess.run(["git", "sparse-checkout", "init", "--cone"], cwd=path, check=True)
        subprocess.run(["git", "sparse-checkout", "set", "--skip-checks", sparse], cwd=path, check=True)
    subprocess.run(["git", "checkout", "--quiet", "--detach", revision], cwd=path, check=True)
    print(f"Recovered pinned source: {path.name}", flush=True)


def pdf_source(path):
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != OMEKA_SHA:
            raise ValueError("Existing PDF differs; will not overwrite")
        return
    temporary = path.with_suffix(".pdf.part")
    size, digest = 0, hashlib.sha256()
    try:
        with urllib.request.urlopen(OMEKA_URL, timeout=60) as response, temporary.open("wb") as handle:
            while chunk := response.read(65536):
                size += len(chunk)
                if size > 64 * 1024 * 1024:
                    raise ValueError("PDF exceeds fixed download bound")
                digest.update(chunk)
                handle.write(chunk)
        if digest.hexdigest() != OMEKA_SHA:
            raise ValueError("Downloaded PDF hash mismatch")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def fetch(cache):
    cache.mkdir(parents=True, exist_ok=True)
    git_source(cache / "python-docs-pt-br", "https://github.com/python/python-docs-pt-br.git", PYTHON_REV)
    git_source(cache / "mdn-translated", "https://github.com/mdn/translated-content.git", MDN_REV, "files/pt-br")
    pdf_source(cache / "enap-omeka.pdf")
    # Use the committed evidence snapshot, not a silently changing live license.
    preflight = cache / "preflight"
    preflight.mkdir(exist_ok=True)
    for original, name in (("PYTHON-LICENSE.html", "python_html_license"),
                           ("PYTHON-REPOSITORY-CC0.txt", "python_translation_license")):
        target = preflight / name
        source = DEST / "licenses" / original
        if target.exists() and target.read_bytes() != source.read_bytes():
            raise ValueError("Existing license snapshot differs; will not overwrite")
        if not target.exists():
            shutil.copy2(source, target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    fetch(args.cache)
