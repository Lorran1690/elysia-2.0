from pathlib import Path

import pytest

from brain.bpe_tokenizer import ByteBPETokenizer
from brain.tokenizer import ByteTokenizer
from learning.tokenizer_metrics import compare_tokenizers


def trained_bpe() -> ByteBPETokenizer:
    return ByteBPETokenizer(320).train(
        [
            "A E.L.Y.S.I.A. aprende padrões em português brasileiro. " * 8,
            "Atenção causal preserva a ordem dos tokens e os acentos. " * 8,
        ]
    )


def test_bpe_round_trip_unicode_and_persistence(tmp_path: Path) -> None:
    tokenizer = trained_bpe()
    text = "Olá, ação, coração e informação."
    encoded = tokenizer.encode(text)
    assert tokenizer.decode(encoded) == text
    path = tmp_path / "tokenizer.json"
    tokenizer.save(path)
    restored = ByteBPETokenizer.load(path)
    assert restored.decode(restored.encode(text)) == text
    assert restored.metadata() == tokenizer.metadata()


def test_bpe_has_configurable_vocabulary_and_special_tokens() -> None:
    tokenizer = trained_bpe()
    assert tokenizer.vocab_size <= 320
    assert len({tokenizer.pad_id, tokenizer.bos_id, tokenizer.eos_id}) == 3
    assert tokenizer.encode("x")[0] == tokenizer.bos_id


def test_incomplete_utf8_is_safe_during_generation() -> None:
    tokenizer = trained_bpe()
    assert tokenizer.decode_incremental([0xC3]) == ""
    assert ByteTokenizer().decode_incremental([0xC3]) == ""


def test_tokenizer_comparison_uses_byte_aware_metrics() -> None:
    texts = ["ação e café", "E.L.Y.S.I.A. local"]
    byte_metrics = compare_tokenizers(
        texts,
        encode=lambda text: ByteTokenizer().encode(text, add_bos=False, add_eos=False),
        vocab_size=259,
    )
    bpe = trained_bpe()
    bpe_metrics = compare_tokenizers(
        texts,
        encode=lambda text: bpe.encode(text, add_bos=False, add_eos=False),
        vocab_size=bpe.vocab_size,
    )
    assert byte_metrics["bytes_per_token"] == 1.0
    assert bpe_metrics["bytes"] == byte_metrics["bytes"]
    assert bpe_metrics["uniform_bits_per_byte_upper_bound"] > 0


def test_incompatible_vocabulary_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "tokenizer.json"
    trained_bpe().save(path)
    payload = path.read_text(encoding="utf-8").replace('"schema_version": 1', '"schema_version": 999')
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="incompatível"):
        ByteBPETokenizer.load(path)


def test_disk_training_never_learns_held_out_phrase(tmp_path: Path) -> None:
    train_documents = [["treino local repetido " * 30]]
    held_out_phrase = "UNSEEN_QZ_991"
    tokenizer = ByteBPETokenizer(320).train_documents(train_documents, work_dir=tmp_path)
    frozen = tokenizer.metadata()
    tokenizer.encode(held_out_phrase, add_bos=False, add_eos=False)
    assert tokenizer.metadata() == frozen
    assert held_out_phrase.encode("utf-8") not in tokenizer._token_bytes
