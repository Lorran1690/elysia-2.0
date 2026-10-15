import unicodedata
from pathlib import Path

import pytest

from learning.dataset import TextDocument, load_corpus, split_documents


def test_streaming_loader_reads_txt_jsonl_normalizes_and_deduplicates(tmp_path: Path) -> None:
    (tmp_path / "one.txt").write_text("Cafe\u0301 com ação\nCafe\u0301 com ação\n", encoding="utf-8")
    (tmp_path / "two.jsonl").write_text(
        '{"text":"Uma linha válida"}\n'
        '{"conversations":[{"role":"user","content":"Outra linha"}]}\n'
        '{malformed}\n',
        encoding="utf-8",
    )
    documents, stats = load_corpus(tmp_path)
    assert stats.files_seen == 2
    assert stats.duplicate_documents == 1
    assert stats.invalid_documents == 1
    assert all(unicodedata.is_normalized("NFC", document.text) for document in documents)
    assert len(documents) == 3


def test_single_document_is_rejected_instead_of_leaking(tmp_path: Path) -> None:
    document = TextDocument(tmp_path / "one.txt", "texto", "hash")
    with pytest.raises(ValueError, match="três documentos"):
        split_documents([document])


def test_document_splits_are_disjoint() -> None:
    documents = [TextDocument(Path(f"{index}.txt"), str(index), str(index)) for index in range(9)]
    split = split_documents(documents, seed=4)
    groups = [set(document.sha256 for document in group) for group in (split.train, split.validation, split.test)]
    assert not groups[0] & groups[1]
    assert not groups[0] & groups[2]
    assert not groups[1] & groups[2]
