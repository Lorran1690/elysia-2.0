from brain.tokenizer import ByteTokenizer


def test_utf8_round_trip_and_special_tokens() -> None:
    tokenizer = ByteTokenizer()
    text = "Olá, E.L.Y.S.I.A. 2.0!\n日本語"
    tokens = tokenizer.encode(text)
    assert tokens[0] == tokenizer.BOS_ID
    assert tokens[-1] == tokenizer.EOS_ID
    assert tokenizer.decode(tokens) == text
    assert tokenizer.vocab_size == 259


def test_padding_is_ignored_on_decode() -> None:
    tokenizer = ByteTokenizer()
    assert tokenizer.decode([tokenizer.PAD_ID, *tokenizer.encode("ok")]) == "ok"
