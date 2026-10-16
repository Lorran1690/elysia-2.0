"""Deterministic, validation-only windows for comparable language-model loss."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

import torch

from .dataset import TokenStore


def _fingerprint(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class FixedValidationWindows:
    """A stable selection of next-token windows from the validation partition."""

    partition: str
    token_store_sha256: str
    token_count: int
    block_size: int
    offsets: tuple[int, ...]
    mode: str

    def metadata(self) -> dict[str, Any]:
        base = {
            "schema_version": 1,
            "partition": self.partition,
            "token_store_sha256": self.token_store_sha256,
            "token_count": self.token_count,
            "block_size": self.block_size,
            "window_count": len(self.offsets),
            "evaluated_tokens": len(self.offsets) * self.block_size,
            "offsets": list(self.offsets),
            "mode": self.mode,
        }
        return {**base, "fingerprint": _fingerprint(base)}


def _validate_window_request(tokens: TokenStore, *, block_size: int, partition: str) -> int:
    if partition != "validation":
        raise ValueError("Janelas de seleção de checkpoint só podem usar a partição validation")
    if block_size < 1 or tokens.token_count <= block_size:
        raise ValueError("Tokens de validação insuficientes para o tamanho de bloco")
    return tokens.token_count - block_size - 1


def build_fixed_validation_windows(
    tokens: TokenStore,
    *,
    block_size: int,
    window_count: int,
    partition: str = "validation",
) -> FixedValidationWindows:
    """Distribute a fixed number of non-random windows across a whole work."""
    max_offset = _validate_window_request(tokens, block_size=block_size, partition=partition)
    if window_count < 1:
        raise ValueError("window_count precisa ser positivo")
    available = max_offset + 1
    if window_count >= available:
        offsets = tuple(range(available))
    elif window_count == 1:
        offsets = (max_offset // 2,)
    else:
        offsets = tuple(round(index * max_offset / (window_count - 1)) for index in range(window_count))
    if len(set(offsets)) != len(offsets):
        raise ValueError("As janelas de validação precisam ter offsets únicos")
    return FixedValidationWindows(
        partition=partition,
        token_store_sha256=tokens.sha256,
        token_count=tokens.token_count,
        block_size=block_size,
        offsets=offsets,
        mode="fixed_distributed",
    )


def build_full_validation_windows(
    tokens: TokenStore,
    *,
    block_size: int,
    partition: str = "validation",
) -> FixedValidationWindows:
    """Create a bounded-memory full pass over validation, available only on request."""
    max_offset = _validate_window_request(tokens, block_size=block_size, partition=partition)
    offsets = list(range(0, max_offset + 1, block_size))
    if offsets[-1] != max_offset:
        offsets.append(max_offset)
    return FixedValidationWindows(
        partition=partition,
        token_store_sha256=tokens.sha256,
        token_count=tokens.token_count,
        block_size=block_size,
        offsets=tuple(offsets),
        mode="full_non_overlapping",
    )


@torch.no_grad()
def evaluate_fixed_validation(
    model: torch.nn.Module,
    tokens: TokenStore,
    windows: FixedValidationWindows,
    *,
    batch_size: int,
    device: torch.device,
) -> dict[str, Any]:
    """Evaluate exactly the preselected windows, without random sampling."""
    if windows.partition != "validation":
        raise ValueError("A avaliação fixa aceita somente janelas de validation")
    if windows.token_store_sha256 != tokens.sha256 or windows.token_count != tokens.token_count:
        raise ValueError("O armazenamento de validação não corresponde ao protocolo fixo")
    if batch_size < 1:
        raise ValueError("batch_size precisa ser positivo")

    was_training = model.training
    model.eval()
    started = time.perf_counter()
    weighted_loss = 0.0
    evaluated_tokens = 0
    try:
        for first in range(0, len(windows.offsets), batch_size):
            offsets = windows.offsets[first : first + batch_size]
            sequences = [tokens.read_slice(offset, windows.block_size + 1) for offset in offsets]
            batch = torch.stack(sequences)
            inputs = batch[:, :-1].to(device)
            targets = batch[:, 1:].to(device)
            _, loss = model(inputs, targets)
            count = int(targets.numel())
            weighted_loss += float(loss.item()) * count
            evaluated_tokens += count
    finally:
        model.train(was_training)
    return {
        "loss": weighted_loss / evaluated_tokens,
        "evaluated_tokens": evaluated_tokens,
        "window_count": len(windows.offsets),
        "block_size": windows.block_size,
        "seconds": time.perf_counter() - started,
        "protocol": windows.metadata(),
    }
