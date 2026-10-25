"""Prepare a licensed Portuguese prose corpus; never update neural weights."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import unicodedata

from markdown_it import MarkdownIt
import polib
import yaml

from learning.dataset import _simhash

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/corpus-pt-v1"
MDN_REV = "d2f749e082684aacee7be1de1c0586471be19844"
PYTHON_REV = "39154eb93cabd5b11f2d528b508897ed9552a156"
OMEKA_SHA = "33651a12f25521fbc4cffeaf373b872b842bb7db34736b5a8edbe47df9c76879"
OMEKA_URL = "https://repositorio.enap.gov.br/bitstream/1/3162/1/Guia%20do%20usu%C3%A1rio%20do%20Omeka%20-%20Ebook.pdf"
SEED = "elysia-corpus-pt-v1-2026-10-25"
WORDS = re.compile(r"[^\W\d_]+", re.UNICODE)
PT_WORDS = set("a o de da do das dos que não uma um para com você como se em é os as mais por são no na ao pode sua seu também este esta entre sobre quando foi ser pela pelo mas tem ou isso essa esse há até onde sem nas nos assim muito estão será qual pelo têm já porque aos elas eles às à pois cada são então através depois todos toda".split())
EN_WORDS = set("the and this that with from will not for to of is are be you your which an it on by can these when or its also used have has we such".split())
PII = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b(?:\+55\s*)?\(?\d{2}\)?[ -]?9\d{4}[ -]\d{4}\b|\bAKIA[A-Z0-9]{16}\b|\bsk-[A-Za-z0-9]{20,}", re.I)
PARSER = MarkdownIt("commonmark").enable("table")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", html.unescape(text)).split())


def language_ratio(text: str) -> float:
    words = WORDS.findall(text.casefold())
    return sum(w in PT_WORDS for w in words) / max(1, len(words))


def portuguese_paragraph(text: str) -> bool:
    words = WORDS.findall(text.casefold())
    pt = sum(w in PT_WORDS for w in words)
    en = sum(w in EN_WORDS for w in words)
    return pt / max(1, len(words)) >= 0.08 and pt >= en


def expand_reference(match):
    content = match[1]
    if re.match(r"(?:[\w]*xref|Glossary|HTTPHeader|HTTPMethod|HTTPStatus)\s*\(", content, re.I):
        names = re.findall(r'["\']([^"\']*)["\']', content)
        if names:
            return next((x for x in reversed(names) if x.strip()), "")
    return ""


def mdn_prose(raw: str) -> tuple[str, list[str]]:
    title = ""
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", raw, re.S)
    if match:
        metadata = yaml.safe_load(match[1]) or {}
        title = str(metadata.get("title", ""))
        raw = raw[match.end():]
    raw = re.sub(r"\{\{(.*?)\}\}", expand_reference, raw, flags=re.S)
    paragraphs = []
    for token in PARSER.parse(raw):
        if token.type != "inline":
            continue
        children = token.children or []
        # Keep short terminology such as Content-Type or null, avoiding holes in
        # prose. Reject paragraphs depending on substantive inline source code.
        if any(c.type == "code_inline" and (len(c.content) > 80 or re.search(r"[\n;{}=<>]", c.content)) for c in children):
            continue
        text = " ".join(child.content for child in children if child.type in {"text", "softbreak", "hardbreak", "code_inline"})
        text = normalize(text)
        if len(text) >= 60:
            paragraphs.append(text)
    return title, paragraphs


def rst_prose(text: str) -> str | None:
    if re.search(r"(^|\n)\s*(?:>>>|\.\. |[a-z_]+\s*\(.*\)\s*:?\s*$)", text, re.M):
        return None
    if re.search(r"::\s*\n|\n\s{4,}\S", text):
        return None
    literals = re.findall(r"``([^`]*)``", text)
    if any(len(value) > 80 or re.search(r"[\n;{}=<>]", value) for value in literals):
        return None
    text = re.sub(r"``([^`]*)``", r"\1", text)
    text = re.sub(r":[\w:]+:`([^`]+)`", lambda m: re.sub(r"\s*<[^>]+>", "", m[1]).lstrip("~!"), text)
    text = re.sub(r"`([^`]+)\s*<[^>]+>`_?", r"\1", text)
    text = re.sub(r"\|[^|]+\|", "", text)
    return normalize(text.replace("**", "").replace("*", ""))


def topic_group(family: str, relative: str) -> str:
    parts = Path(relative).parts
    if family == "python":
        section, name = (parts[0], Path(parts[-1]).stem) if len(parts) > 1 else ("misc", Path(relative).stem)
        if section in {"tutorial", "reference", "c-api", "using", "distributing"}:
            return f"python/{section}"
        return f"python/{section}/{name.split('.')[0].split('-')[0]}"
    if family == "mdn":
        parts = list(parts)
        if parts[-1] == "index.md":
            parts.pop()
        if parts[:2] == ["web", "api"]:
            return "mdn/" + "/".join(parts[:3])
        if parts[:4] == ["web", "javascript", "reference", "global_objects"]:
            return "mdn/" + "/".join(parts[:5])
        if parts[:3] == ["web", "javascript", "guide"]:
            return "mdn/web/javascript/guide"
        return "mdn/" + "/".join(parts[:min(4, len(parts))])
    return "enap/omeka-whole-book"


def input_documents(cache: Path, exclusions: Counter):
    py = cache / "python-docs-pt-br"
    mdn = cache / "mdn-translated"
    for repo, expected in ((py, PYTHON_REV), (mdn, MDN_REV)):
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        if revision != expected:
            raise ValueError(f"Source revision mismatch: {repo.name}")
        # Ignore no source modifications: hash the actual files and pin clean tracked source state.
        if subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip():
            raise ValueError(f"Source working tree modified: {repo.name}")
    for path in sorted(py.rglob("*.po")):
        relative = path.relative_to(py).as_posix()
        if Path(relative).parts[0] in {"whatsnew", "deprecations"}:
            exclusions["python_historical_changelog_or_deprecation_file"] += 1
            continue
        raw = path.read_bytes()
        po = polib.pofile(raw.decode("utf-8"))
        if "same license as the Python package" not in po.header or po.metadata.get("Language") != "pt_BR":
            exclusions["python_missing_license_or_locale"] += 1
            continue
        paragraphs = []
        for entry in po:
            if entry.obsolete or "fuzzy" in entry.flags or not entry.msgstr or entry.msgstr == entry.msgid:
                exclusions["python_untranslated_fuzzy_or_obsolete_entry"] += 1
                continue
            text = rst_prose(entry.msgstr)
            if text and len(text) >= 60:
                paragraphs.append(text)
        credits = [re.sub(r"<[^>]+>", "", s).strip() for s in po.header.splitlines() if s.strip() and not any(t in s for t in ["SOME DESCRIPTIVE", "FIRST AUTHOR", "Translators:"])]
        yield {"family": "python", "path": relative, "title": Path(relative).stem,
               "revision": PYTHON_REV, "source_sha256": digest(raw),
               "source_url": f"https://github.com/python/python-docs-pt-br/blob/{PYTHON_REV}/{relative}",
               "license": "PSF-2.0", "copyright_notices": credits,
               "attribution": "Python Software Foundation and pt-BR translation contributors; file credits retained",
               "changes": "Only non-fuzzy translated prose; code blocks/directives and substantive inline code removed; short terminology retained; NFC and whitespace normalization",
               "paragraphs": paragraphs}
    for path in sorted((mdn / "files/pt-br").rglob("index.md")):
        relative = path.relative_to(mdn / "files/pt-br").as_posix()
        raw = path.read_bytes()
        title, paragraphs = mdn_prose(raw.decode("utf-8"))
        yield {"family": "mdn", "path": relative, "title": title,
               "revision": MDN_REV, "source_sha256": digest(raw),
               "source_url": f"https://github.com/mdn/translated-content/blob/{MDN_REV}/files/pt-br/{relative}",
               "license": "CC-BY-SA-2.5", "license_url": "https://creativecommons.org/licenses/by-sa/2.5/",
               "attribution": "MDN contributors / Mozilla; original contributor history at source URL",
               "changes": "Prose adaptation under CC-BY-SA-2.5; code blocks, substantive inline code, images, HTML and navigation macros removed; short API terminology and reference labels retained; NFC and whitespace normalization",
               "paragraphs": paragraphs}
    pdf = cache / "enap-omeka.pdf"
    if digest(pdf.read_bytes()) != OMEKA_SHA:
        raise ValueError("Omeka PDF hash mismatch")
    extraction = subprocess.check_output(["pdftotext", "-layout", str(pdf), "-"], text=True)
    pages = extraction.split("\f")
    if "Creative Commons - Atribuição CC BY 4.0" not in pages[3]:
        raise ValueError("Omeka license declaration missing")
    paragraphs = []
    for page in pages[12:116]:
        page = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", page)
        lines = []
        for line in page.splitlines():
            clean = normalize(line)
            if not clean:
                lines.append("")
            elif len(clean) >= 30 and not re.search(r"Omeka: Serious|Guia do usuário do:|^(?:Figura|Fonte:|Parte [IVX]+)", clean):
                lines.append(clean)
        paragraphs.extend(normalize(p) for p in re.split(r"\n\s*\n", "\n".join(lines)) if len(normalize(p)) >= 80)
    yield {"family": "enap", "path": "omeka-body-pdf-pages-13-116", "title": "Guia do usuário do Omeka",
           "revision": "2018; original PDF identified by SHA-256", "source_sha256": OMEKA_SHA,
           "source_url": OMEKA_URL, "license": "CC-BY-4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
           "attribution": "© 2018 Ibict. Milton Shintaku, Rafael Fernandez Gomes, Ronnie Fagundes de Brito, Lucas Rodrigues, Vinícius Carvalho Pereira, Keicielle Schimidt",
           "changes": "PDF prose extraction; excludes front matter, references, author biographies, image captions and assets; dehyphenation and whitespace normalization",
           "paragraphs": paragraphs}


def prepare(cache: Path, output: Path = DEST):
    if output.exists():
        raise ValueError("Corpus already exists; refuse overwrite")
    spec = ROOT / "evaluation/portuguese-v1.json"
    prompts = [normalize(m["content"]).casefold() for c in json.loads(spec.read_text(encoding="utf-8"))["cases"] for m in c["messages"] if m["role"] == "user" and len(m["content"]) >= 45]
    exclusions, seen_paragraphs, seen_documents = Counter(), set(), set()
    candidates, inputs = [], []
    for document in input_documents(cache, exclusions):
        original = "\n\n".join(document.pop("paragraphs"))
        original_hash = digest(original.encode())
        index = {k: document[k] for k in ("family", "path", "source_url", "source_sha256")}
        reason = None
        if len(original) < 250:
            reason = "too_short"
        elif language_ratio(original) < 0.08:
            reason = "low_portuguese_marker_ratio"
        elif any(p in normalize(original).casefold() for p in prompts):
            reason = "evaluation_prompt_overlap"
        elif original_hash in seen_documents:
            reason = "exact_document_duplicate"
        if reason:
            exclusions[reason] += 1
            inputs.append({**index, "status": "excluded", "reason": reason})
            continue
        seen_documents.add(original_hash)
        paragraphs = []
        for text in original.split("\n\n"):
            if not portuguese_paragraph(text):
                exclusions["paragraph_not_confidently_portuguese"] += 1
                continue
            if PII.search(text):
                exclusions["identifier_pattern_paragraph"] += 1
                continue
            key = digest(normalize(text).casefold().encode())
            if key in seen_paragraphs:
                exclusions["duplicate_paragraph"] += 1
                continue
            seen_paragraphs.add(key)
            paragraphs.append(text)
        text = "\n\n".join(paragraphs)
        if len(text) < 250:
            exclusions["too_short_after_cleaning"] += 1
            inputs.append({**index, "status": "excluded", "reason": "too_short_after_cleaning"})
            continue
        document.update(text=text, sha256=digest(text.encode()), group_id=topic_group(document["family"], document["path"]),
                        id=digest((document["family"] + "/" + document["path"]).encode())[:24],
                        portuguese_marker_ratio=round(language_ratio(text), 6))
        candidates.append(document)
        inputs.append({**index, "status": "candidate", "id": document["id"]})
    # LSH pigeonhole: 4 x 16-bit bands find every SimHash pair within 3 bits.
    bands, retained, hashes, rejected = defaultdict(list), [], [], []
    for document in candidates:
        signature = _simhash(document["text"])
        possible = {i for b in range(4) for i in bands[(b, (signature >> (16 * b)) & 65535)]}
        duplicate = None
        for i in possible:
            if (signature ^ hashes[i]).bit_count() <= 3:
                a, b = set(WORDS.findall(document["text"].casefold())), set(WORDS.findall(retained[i]["text"].casefold()))
                if len(a & b) / max(1, len(a | b)) >= 0.85:
                    duplicate = retained[i]["id"]
                    break
        if duplicate:
            rejected.append({"id": document["id"], "source_url": document["source_url"], "canonical_id": duplicate})
            exclusions["near_document_duplicate"] += 1
            continue
        index = len(retained)
        retained.append(document)
        hashes.append(signature)
        for b in range(4):
            bands[(b, (signature >> (16 * b)) & 65535)].append(index)
    partitions = {s: [] for s in ("train", "validation", "test")}
    retained_ids = {r["id"] for r in retained}
    for item in inputs:
        if item["status"] == "candidate":
            item["status"] = "retained" if item["id"] in retained_ids else "excluded"
            if item["id"] not in retained_ids:
                item["reason"] = "near_document_duplicate"
    for document in retained:
        bucket = int(digest((SEED + document["group_id"]).encode())[:8], 16) % 10
        # One book is one indivisible training group; no chapters leak into eval.
        split = "train" if document["family"] == "enap" or bucket < 8 else "validation" if bucket == 8 else "test"
        partitions[split].append(document)
    output.mkdir(parents=True)
    for name, rows in partitions.items():
        (output / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    (output / "source-index.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in inputs), encoding="utf-8")
    (output / "near-duplicates.json").write_text(json.dumps(rejected, ensure_ascii=False, indent=2), encoding="utf-8")
    legal = output / "licenses"
    legal.mkdir()
    shutil.copy2(cache / "mdn-translated/LICENSE.md", legal / "MDN-LICENSE.md")
    shutil.copy2(cache / "preflight/python_html_license", legal / "PYTHON-LICENSE.html")
    shutil.copy2(cache / "preflight/python_translation_license", legal / "PYTHON-REPOSITORY-CC0.txt")
    (legal / "ENAP-NOTICE.txt").write_text(pages_notice(cache), encoding="utf-8")
    report = {"status": "prepared research corpus; not a claim of conversational competence", "seed": SEED,
              "neural_weights_updated": False, "open_evaluation_sha256": digest(spec.read_bytes()),
              "source_revisions": {"mdn": MDN_REV, "python": PYTHON_REV, "enap_pdf_sha256": OMEKA_SHA},
              "exclusions": dict(exclusions), "input_documents": len(inputs), "retained_documents": len(retained),
              "partitions": {s: {"documents": len(rows), "groups": len({r["group_id"] for r in rows}),
                                  "bytes_utf8": sum(len(r["text"].encode()) for r in rows),
                                  "words": sum(len(WORDS.findall(r["text"])) for r in rows),
                                  "sha256": digest((output / f"{s}.jsonl").read_bytes()),
                                  "by_family": {f: {"documents": sum(r["family"] == f for r in rows),
                                                     "bytes_utf8": sum(len(r["text"].encode()) for r in rows if r["family"] == f)}
                                                for f in ("mdn", "python", "enap")}} for s, rows in partitions.items()},
              "limits": ["Technical-domain concentration; not broad conversational data.",
                         "pt-BR source tags include mixed Portuguese variants; Brazilian usage is not independently certified.",
                         "Language-marker heuristics and PII regex are not a complete linguistic/privacy audit.",
                         "Near-duplicate detection is heuristic; semantic duplicates can remain.",
                         "Topic groups are disjoint; sources and authors are shared across partitions.",
                         "MDN derivative prose remains CC-BY-SA-2.5; other families retain their own licenses.",
                         "No neural training performed; no target token count inferred from byte or word counts."]}
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def pages_notice(cache):
    text = subprocess.check_output(["pdftotext", "-f", "4", "-l", "4", str(cache / "enap-omeka.pdf"), "-"], text=True)
    return "Source license declaration, extracted from original PDF page 4:\n" + text + "\nLicense: https://creativecommons.org/licenses/by/4.0/\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEST)
    args = parser.parse_args()
    print(json.dumps(prepare(args.cache, args.output), ensure_ascii=False, indent=2))
