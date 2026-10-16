"""One-shot, test-only evaluation helpers for the frozen ELYSIA-Seed v0.4."""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from typing import Any

import psutil
import torch
from torch.nn import functional as F

from .dataset import TokenStore


def _fingerprint(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class FinalTestWindow:
    """One contiguous range of next-token targets in the final test work."""

    offset: int
    target_tokens: int

    def metadata(self) -> dict[str, int]:
        return {"offset": self.offset, "target_tokens": self.target_tokens}


@dataclass(frozen=True)
class FinalTestWindows:
    """A complete, deterministic partitioning of targets from the test work."""

    partition: str
    token_store_sha256: str
    token_count: int
    block_size: int
    windows: tuple[FinalTestWindow, ...]

    def metadata(self) -> dict[str, Any]:
        full_windows = sum(window.target_tokens == self.block_size for window in self.windows)
        trailing = self.windows[-1].target_tokens if self.windows else 0
        base = {
            "schema_version": 1,
            "partition": self.partition,
            "token_store_sha256": self.token_store_sha256,
            "token_count": self.token_count,
            "block_size": self.block_size,
            "window_count": len(self.windows),
            "evaluated_target_tokens": sum(window.target_tokens for window in self.windows),
            "full_window_count": full_windows,
            "trailing_window_target_tokens": trailing if trailing != self.block_size else 0,
            "windows": [window.metadata() for window in self.windows],
            "target_coverage": "Every next-token target from index 1 through token_count - 1 is scored exactly once.",
            "boundary_context": (
                "Each later window reuses only the preceding boundary token as unscored input context; "
                "target ranges never overlap and no target is counted twice."
            ),
            "tail_policy": "The final window is shorter when needed; no overlapping final window is added.",
            "mode": "complete_non_overlapping_target_coverage",
        }
        return {**base, "fingerprint": _fingerprint(base)}


def _validate_request(tokens: TokenStore, *, block_size: int, partition: str) -> None:
    if partition != "test":
        raise ValueError("A avaliação final só pode usar a partição test")
    if block_size < 1 or tokens.token_count < 2:
        raise ValueError("Tokens de teste insuficientes para avaliar próximo token")


def build_final_test_windows(
    tokens: TokenStore,
    *,
    block_size: int,
    partition: str = "test",
) -> FinalTestWindows:
    """Partition all next-token targets without a second, overlapping tail window."""
    _validate_request(tokens, block_size=block_size, partition=partition)
    windows = tuple(
        FinalTestWindow(
            offset=offset,
            target_tokens=min(block_size, tokens.token_count - offset - 1),
        )
        for offset in range(0, tokens.token_count - 1, block_size)
    )
    return FinalTestWindows(
        partition=partition,
        token_store_sha256=tokens.sha256,
        token_count=tokens.token_count,
        block_size=block_size,
        windows=windows,
    )


def _validate_windows(tokens: TokenStore, windows: FinalTestWindows) -> None:
    if windows.partition != "test":
        raise ValueError("A avaliação final aceita somente janelas de test")
    if windows.token_store_sha256 != tokens.sha256 or windows.token_count != tokens.token_count:
        raise ValueError("O armazenamento de teste não corresponde ao protocolo final")
    if not windows.windows:
        raise ValueError("O protocolo final não contém janelas")
    expected_offset = 0
    for window in windows.windows:
        expected_length = min(windows.block_size, tokens.token_count - expected_offset - 1)
        if window.offset != expected_offset or window.target_tokens != expected_length or window.target_tokens < 1:
            raise ValueError("As janelas finais não cobrem o teste de forma contínua")
        expected_offset += window.target_tokens
    if expected_offset != tokens.token_count - 1:
        raise ValueError("O protocolo final não cobre todos os alvos do teste")


def _runtime_snapshot(device: torch.device) -> dict[str, int]:
    snapshot = {"ram_bytes": int(psutil.Process().memory_info().rss)}
    if device.type == "cuda":
        snapshot["vram_allocated_bytes"] = int(torch.cuda.memory_allocated(device))
        snapshot["vram_reserved_bytes"] = int(torch.cuda.memory_reserved(device))
    return snapshot


def _batches(windows: tuple[FinalTestWindow, ...], batch_size: int) -> list[tuple[FinalTestWindow, ...]]:
    """Keep variable-length tail windows separate without padding or masking."""
    result: list[tuple[FinalTestWindow, ...]] = []
    index = 0
    while index < len(windows):
        length = windows[index].target_tokens
        current: list[FinalTestWindow] = []
        while index < len(windows) and windows[index].target_tokens == length and len(current) < batch_size:
            current.append(windows[index])
            index += 1
        result.append(tuple(current))
    return result


@torch.no_grad()
def evaluate_final_test(
    model: torch.nn.Module,
    tokens: TokenStore,
    windows: FinalTestWindows,
    *,
    batch_size: int,
    device: torch.device,
    text_bytes: int,
    special_token_ids: set[int],
) -> dict[str, Any]:
    """Run a read-only full test pass and return token- and byte-normalized metrics."""
    _validate_windows(tokens, windows)
    if batch_size < 1:
        raise ValueError("batch_size precisa ser positivo")
    if text_bytes < 1:
        raise ValueError("text_bytes precisa ser positivo")

    was_training = model.training
    model.eval()
    if device.type == "cuda":
        torch.cuda.synchronize(device)
        torch.cuda.reset_peak_memory_stats(device)

    started = time.perf_counter()
    before = _runtime_snapshot(device)
    peak_ram = before["ram_bytes"]
    total_nll = 0.0
    content_nll = 0.0
    evaluated_target_tokens = 0
    content_target_tokens = 0
    excluded_target_tokens = 0
    batch_count = 0
    try:
        for window_batch in _batches(windows.windows, batch_size):
            sequences = [tokens.read_slice(window.offset, window.target_tokens + 1) for window in window_batch]
            batch = torch.stack(sequences)
            inputs = batch[:, :-1].to(device)
            targets = batch[:, 1:].to(device)
            logits = model(inputs)
            if not isinstance(logits, torch.Tensor):
                raise ValueError("O modelo retornou uma saída de inferência inesperada")
            losses = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)),
                targets.reshape(-1),
                reduction="none",
            )
            total_nll += float(losses.sum().item())
            count = int(targets.numel())
            evaluated_target_tokens += count
            target_values = targets.reshape(-1)
            content_mask = torch.ones_like(target_values, dtype=torch.bool)
            for token_id in special_token_ids:
                content_mask &= target_values.ne(token_id)
            content_nll += float(losses[content_mask].sum().item())
            content_count = int(content_mask.sum().item())
            content_target_tokens += content_count
            excluded_target_tokens += count - content_count
            batch_count += 1
            peak_ram = max(peak_ram, int(psutil.Process().memory_info().rss))
    finally:
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        model.train(was_training)

    elapsed = time.perf_counter() - started
    after = _runtime_snapshot(device)
    peak_ram = max(peak_ram, after["ram_bytes"])
    if evaluated_target_tokens != tokens.token_count - 1:
        raise ValueError("A contagem de alvos avaliados diverge da cobertura total esperada")
    if content_target_tokens < 1:
        raise ValueError("A avaliação não encontrou tokens textuais para medir")

    loss = total_nll / evaluated_target_tokens
    content_loss = content_nll / content_target_tokens
    perplexity = math.exp(loss) if loss < math.log(float.fromhex("0x1.fffffffffffffp+1023")) else math.inf
    resources: dict[str, Any] = {
        "ram_before_bytes": before["ram_bytes"],
        "ram_after_bytes": after["ram_bytes"],
        "ram_peak_sampled_bytes": peak_ram,
    }
    if device.type == "cuda":
        resources.update(
            {
                "vram_before_allocated_bytes": before["vram_allocated_bytes"],
                "vram_after_allocated_bytes": after["vram_allocated_bytes"],
                "vram_peak_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
                "vram_before_reserved_bytes": before["vram_reserved_bytes"],
                "vram_after_reserved_bytes": after["vram_reserved_bytes"],
                "vram_peak_reserved_bytes": int(torch.cuda.max_memory_reserved(device)),
            }
        )
    return {
        "loss": loss,
        "content_token_loss": content_loss,
        "perplexity": perplexity,
        "bits_per_byte": content_nll / text_bytes / math.log(2),
        "evaluated_target_tokens": evaluated_target_tokens,
        "content_target_tokens": content_target_tokens,
        "excluded_special_target_tokens": excluded_target_tokens,
        "text_bytes": text_bytes,
        "window_count": len(windows.windows),
        "batch_count": batch_count,
        "seconds": elapsed,
        "resources": resources,
        "protocol": windows.metadata(),
        "metrics_definition": {
            "loss": "Média ponderada da entropia cruzada em todos os alvos de próximo token, incluindo o EOS final.",
            "perplexity": "exp(loss), calculada sobre a mesma média de loss.",
            "bits_per_byte": (
                "NLL dos tokens textuais, excluindo tokens especiais, dividida pelos bytes UTF-8 do texto limpo "
                "e por ln(2)."
            ),
        },
    }
