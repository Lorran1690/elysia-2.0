"""A deliberately small tokenizer built directly on UTF-8 bytes."""

from __future__ import annotations


class ByteTokenizer:
    """Maps every UTF-8 byte to one token and reserves three special tokens."""

    PAD_ID = 256
    BOS_ID = 257
    EOS_ID = 258

    @property
    def vocab_size(self) -> int:
        return 259

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

    def decode(self, tokens: list[int] | tuple[int, ...]) -> str:
        raw = bytearray()
        for token in tokens:
            if token in (self.PAD_ID, self.BOS_ID, self.EOS_ID):
                continue
            if not 0 <= token <= 255:
                raise ValueError(f"Token fora do vocabulário de bytes: {token}")
            raw.append(token)
        return raw.decode("utf-8")
