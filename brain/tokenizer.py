"""A deliberately small tokenizer built directly on UTF-8 bytes."""

from __future__ import annotations

import codecs
import hashlib
import json

class ByteTokenizer:
    """Maps every UTF-8 byte to one token and reserves three special tokens."""

    PAD_ID = 256
    BOS_ID = 257
    EOS_ID = 258

    @property
    def vocab_size(self) -> int:
        return 259

    @property
    def bos_id(self) -> int:
        return self.BOS_ID

    @property
    def eos_id(self) -> int:
        return self.EOS_ID

    def encode(
        self,
        text: str,
        *,
        add_bos: bool = True,
        add_eos: bool = True,
    ) -> list[int]:
        tokens: list[int] = []
        if add_bos:
            tokens.append(self.BOS_ID)
        tokens.extend(text.encode("utf-8"))
        if add_eos:
            tokens.append(self.EOS_ID)
        return tokens

    def _bytes_from_tokens(self, tokens: list[int] | tuple[int, ...]) -> bytes:
        raw = bytearray()
        for token in tokens:
            if token in (self.PAD_ID, self.BOS_ID, self.EOS_ID):
                continue
            if not 0 <= token <= 255:
                raise ValueError(f"Token fora do vocabulário de bytes: {token}")
            raw.append(token)
        return bytes(raw)

    def decode(
        self,
        tokens: list[int] | tuple[int, ...],
        *,
        errors: str = "strict",
    ) -> str:
        return self._bytes_from_tokens(tokens).decode("utf-8", errors=errors)

    def decode_incremental(self, tokens: list[int] | tuple[int, ...]) -> str:
        """Decode a generation prefix without crashing on a partial UTF-8 byte."""
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        return decoder.decode(self._bytes_from_tokens(tokens), final=False)

    def decode_for_generation(self, tokens: list[int] | tuple[int, ...]) -> str:
        return self.decode_incremental(tokens)

    def metadata(self) -> dict[str, str | int]:
        payload = {
            "type": "byte_utf8",
            "vocab_size": self.vocab_size,
            "special_tokens": {
                "pad": self.PAD_ID,
                "bos": self.BOS_ID,
                "eos": self.EOS_ID,
            },
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return {**payload, "fingerprint": fingerprint}
