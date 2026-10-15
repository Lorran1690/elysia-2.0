import json
import tracemalloc
from pathlib import Path

import pytest
import torch

from brain.tokenizer import ByteTokenizer
from learning.dataset import TextDocument, iter_document_chunks, load_corpus, prepare_token_store, split_documents


def test_txt_is_one_work_and_jsonl_source_records_stay_grouped(tmp_path: Path) -> None:
    (tmp_path / "work.txt").write_text("Primeira parte\nSegunda parte\n", encoding="utf-8")
    (tmp_path / "records.jsonl").write_text(
        '{"source_id":"book-a","text":"Trecho um"}\n'
        '{"source_id":"book-a","text":"Trecho dois"}\n'
        '{"source_id":"book-b","text":"Outro texto"}\n'
        '{malformed}\n',
        encoding="utf-8",
    )
    documents, stats = load_corpus(tmp_path)
    assert stats.files_seen == 2
    assert stats.invalid_documents == 1
    assert len(documents) == 3
    txt = next(document for document in documents if document.path.name == "work.txt")
    book_a = next(document for document in documents if document.source_group == "records.jsonl:book-a")
    assert txt.text is None
    assert "Primeira parte" in "".join(iter_document_chunks(txt))
    assert book_a.record_lines == (1, 2)


def test_single_document_is_rejected_instead_of_leaking(tmp_path: Path) -> None:
    document = TextDocument(tmp_path / "one.txt", "texto", "hash")
    with pytest.raises(ValueError, match="três grupos"):
        split_documents([document])


def test_related_documents_remain_in_one_split() -> None:
    documents = [
        TextDocument(Path("a.txt"), "a", "a", group_id="related:0"),
        TextDocument(Path("b.txt"), "b", "b", group_id="related:0"),
        TextDocument(Path("c.txt"), "c", "c", group_id="related:1"),
        TextDocument(Path("d.txt"), "d", "d", group_id="related:2"),
        TextDocument(Path("e.txt"), "e", "e", group_id="related:3"),
    ]
    split = split_documents(documents, seed=4)
    partitions = [{document.sha256 for document in group} for group in (split.train, split.validation, split.test)]
    assert any({"a", "b"}.issubset(partition) for partition in partitions)


def test_split_is_disjoint_and_fingerprinted() -> None:
    documents = [TextDocument(Path(f"{index}.txt"), str(index), str(index)) for index in range(9)]
    split = split_documents(documents, seed=4)
    groups = [set(document.sha256 for document in group) for group in (split.train, split.validation, split.test)]
    assert not groups[0] & groups[1]
    assert not groups[0] & groups[2]
    assert not groups[1] & groups[2]
    assert len(split.metadata()["fingerprint"]) == 64
    assert split.metadata() == split_documents(documents, seed=4).metadata()


def test_token_store_is_bounded_for_large_source(tmp_path: Path) -> None:
    source = tmp_path / "large.txt"
    with source.open("w", encoding="utf-8") as handle:
        for _ in range(16):
            handle.write("elysia local " * 1024)
    tracemalloc.start()
    documents, _ = load_corpus(tmp_path)
    store = prepare_token_store(documents, ByteTokenizer(), tmp_path / "tokens.bin", split_metadata={"fingerprint": "test"})
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert documents[0].text is None
    assert peak < 6_000_000
    assert store.token_count > 200_000
    assert store.read_slice(0, 4).dtype == torch.long
    manifest = json.loads(store.metadata_path.read_text(encoding="utf-8"))
    assert manifest["sha256"] == store.sha256
