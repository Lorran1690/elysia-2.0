"""Small, local architecture benchmark for the v0.3 ablations."""

from __future__ import annotations

import time
from typing import Any

import psutil
import torch

from brain.generate import generate
from brain.model import ElysiaTransformer


def _sync(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def cache_nbytes(cache: list[tuple[torch.Tensor, torch.Tensor]]) -> int:
    return sum(key.numel() * key.element_size() + value.numel() * value.element_size() for key, value in cache)


@torch.no_grad()
def benchmark_generation(model: ElysiaTransformer, *, device: torch.device, tokens: int = 32) -> dict[str, float]:
    prompt = torch.randint(0, model.config.vocab_size, (1, min(16, model.config.block_size)), device=device)
    results: dict[str, float] = {}
    for cached in (False, True):
        _sync(device)
        started = time.perf_counter()
        output = generate(model, prompt, max_new_tokens=tokens, temperature=0.0, use_cache=cached)
        _sync(device)
        elapsed = time.perf_counter() - started
        label = "cached" if cached else "uncached"
        results[f"generation_{label}_seconds"] = elapsed
        results[f"generation_{label}_tokens_per_second"] = tokens / elapsed
        assert output.size(1) >= prompt.size(1)
    _, cache = model(prompt, use_cache=True)
    results["kv_cache_bytes_for_prompt"] = float(cache_nbytes(cache))
    return results


def benchmark_model(model: ElysiaTransformer, *, device: torch.device, steps: int = 5) -> dict[str, Any]:
    model = model.to(device)
    model.train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
    batch_size = 2
    sequence = min(64, model.config.block_size)
    inputs = torch.randint(0, model.config.vocab_size, (batch_size, sequence), device=device)
    targets = torch.randint(0, model.config.vocab_size, (batch_size, sequence), device=device)
    process = psutil.Process()
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    _sync(device)
    started = time.perf_counter()
    losses: list[float] = []
    for _ in range(steps):
        optimizer.zero_grad(set_to_none=True)
        _, loss = model(inputs, targets)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.item()))
    _sync(device)
    elapsed = time.perf_counter() - started
    model.eval()
    generation = benchmark_generation(model, device=device)
    return {
        "parameters": model.num_parameters(),
        "train_seconds": elapsed,
        "train_step_seconds": elapsed / steps,
        "tokens_per_second": (batch_size * sequence * steps) / elapsed,
        "last_loss": losses[-1],
        "rss_bytes": process.memory_info().rss,
        "peak_vram_bytes": torch.cuda.max_memory_allocated(device) if device.type == "cuda" else 0,
        **generation,
    }
