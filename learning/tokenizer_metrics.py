"""Comparable, model-independent tokenizer measurements."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable


def compare_tokenizers(
    texts: Iterable[str],
    *,
    encode: Callable[[str], list[int]],
    vocab_size: int,
) -> dict[str, float]:
    byte_count = 0
    token_count = 0
    for text in texts:
        byte_count += len(text.encode("utf-8"))
        token_count += len(encode(text))
    if byte_count == 0 or token_count == 0:
        raise ValueError("É necessário texto não vazio para medir o tokenizador")
    return {
        "bytes": float(byte_count),
        "tokens": float(token_count),
        "bytes_per_token": byte_count / token_count,
        "uniform_bits_per_byte_upper_bound": (token_count * math.log2(vocab_size)) / byte_count,
    }
