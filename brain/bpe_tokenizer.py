"""A small Byte-Level BPE tokenizer trained from local text only.

This implementation intentionally keeps the algorithm visible and has no
dependency on a pretrained vocabulary or tokenizer package.
"""

from __future__ import annotations

import base64
import codecs
import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterable


class ByteBPETokenizer:
    SCHEMA_VERSION = 1
    PAD_TOKEN = "<|pad|>"
    BOS_TOKEN = "<|bos|>"
    EOS_TOKEN = "<|eos|>"

    def __init__(self, requested_vocab_size: int = 512) -> None:
        if requested_vocab_size < 259:
            raise ValueError("O vocabulário BPE precisa comportar bytes e tokens especiais")
        self.requested_vocab_size = requested_vocab_size
        self._token_bytes: list[bytes] = [bytes([value]) for value in range(256)]
        self.merges: list[tuple[int, int]] = []
        self.special_tokens = {
            "pad": self.PAD_TOKEN,
            "bos": self.BOS_TOKEN,
            "eos": self.EOS_TOKEN,
        }
        self.special_ids: dict[str, int] = {}
        self._refresh_special_ids()

    @property
    def vocab_size(self) -> int:
        return len(self._token_bytes) + len(self.special_ids)

    @property
    def pad_id(self) -> int:
        return self.special_ids["pad"]

    @property
    def bos_id(self) -> int:
        return self.special_ids["bos"]

    @property
    def eos_id(self) -> int:
        return self.special_ids["eos"]

    @staticmethod
    def _merge_pair(sequence: list[int], left: int, right: int, merged: int) -> list[int]:
        output: list[int] = []
        index = 0
        while index < len(sequence):
            if index + 1 < len(sequence) and sequence[index] == left and sequence[index + 1] == right:
                output.append(merged)
                index += 2
            else:
                output.append(sequence[index])
                index += 1
        return output

    def _refresh_special_ids(self) -> None:
        start = len(self._token_bytes)
        self.special_ids = {name: start + offset for offset, name in enumerate(self.special_tokens)}

    def train(self, texts: Iterable[str], *, min_pair_frequency: int = 2) -> "ByteBPETokenizer":
        sequences = [
            list(unicodedata.normalize("NFC", text).encode("utf-8"))
            for text in texts
            if text
        ]
        if not sequences:
            raise ValueError("Não há textos válidos para treinar o BPE")

        maximum_merges = self.requested_vocab_size - 256 - len(self.special_tokens)
        while len(self.merges) < maximum_merges:
            counts: Counter[tuple[int, int]] = Counter()
            for sequence in sequences:
                counts.update(zip(sequence, sequence[1:]))
            if not counts:
                break
            pair, frequency = counts.most_common(1)[0]
            if frequency < min_pair_frequency:
                break
            left, right = pair
            merged_id = len(self._token_bytes)
            self._token_bytes.append(self._token_bytes[left] + self._token_bytes[right])
            self.merges.append(pair)
            sequences = [self._merge_pair(sequence, left, right, merged_id) for sequence in sequences]
        self._refresh_special_ids()
        return self

    def encode(
        self,
        text: str,
        *,
        add_bos: bool = True,
        add_eos: bool = True,
    ) -> list[int]:
        sequence = list(unicodedata.normalize("NFC", text).encode("utf-8"))
        for merge_index, (left, right) in enumerate(self.merges):
            sequence = self._merge_pair(sequence, left, right, 256 + merge_index)
        if add_bos:
            sequence.insert(0, self.bos_id)
        if add_eos:
            sequence.append(self.eos_id)
        return sequence

    def _bytes_from_tokens(self, tokens: Iterable[int]) -> bytes:
        raw = bytearray()
        for token in tokens:
            if token in self.special_ids.values():
                continue
            if not 0 <= token < len(self._token_bytes):
                raise ValueError(f"Token BPE fora do vocabulário: {token}")
            raw.extend(self._token_bytes[token])
        return bytes(raw)

    def decode(self, tokens: Iterable[int], *, errors: str = "strict") -> str:
        return self._bytes_from_tokens(tokens).decode("utf-8", errors=errors)

    def decode_incremental(self, tokens: Iterable[int]) -> str:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        return decoder.decode(self._bytes_from_tokens(tokens), final=False)

    def decode_for_generation(self, tokens: Iterable[int]) -> str:
        return self.decode_incremental(tokens)

    def metadata(self) -> dict[str, str | int]:
        payload: dict[str, str | int] = {
            "type": "byte_bpe",
            "schema_version": self.SCHEMA_VERSION,
            "vocab_size": self.vocab_size,
            "requested_vocab_size": self.requested_vocab_size,
        }
        encoded = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return {**payload, "fingerprint": hashlib.sha256(encoded).hexdigest()}

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "requested_vocab_size": self.requested_vocab_size,
            "tokens": [base64.b64encode(value).decode("ascii") for value in self._token_bytes],
            "merges": [[left, right] for left, right in self.merges],
            "special_tokens": self.special_tokens,
            "special_ids": self.special_ids,
        }

    def save(self, path: str | Path) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "ByteBPETokenizer":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("Versão de vocabulário BPE incompatível")
        tokenizer = cls(int(payload["requested_vocab_size"]))
        tokenizer._token_bytes = [base64.b64decode(value) for value in payload["tokens"]]
        tokenizer.merges = [tuple(pair) for pair in payload["merges"]]
        tokenizer.special_tokens = dict(payload["special_tokens"])
        tokenizer.special_ids = {name: int(value) for name, value in payload["special_ids"].items()}
        tokenizer._validate()
        return tokenizer

    def _validate(self) -> None:
        if len(self._token_bytes) < 256:
            raise ValueError("Vocabulário BPE sem todos os tokens de bytes")
        if self.vocab_size > self.requested_vocab_size:
            raise ValueError("Vocabulário BPE excede o limite configurado")
        if set(self.special_ids) != {"pad", "bos", "eos"}:
            raise ValueError("Tokens especiais BPE incompletos")
        expected_ids = {
            "pad": len(self._token_bytes),
            "bos": len(self._token_bytes) + 1,
            "eos": len(self._token_bytes) + 2,
        }
        if self.special_ids != expected_ids:
            raise ValueError("IDs de tokens especiais BPE inconsistentes")
