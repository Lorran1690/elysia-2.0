"""Evaluation helpers for next-token loss."""

from __future__ import annotations

import torch

from .dataset import make_batch


@torch.no_grad()
def evaluate_loss(
    model: torch.nn.Module,
    tokens: torch.Tensor,
    *,
    batch_size: int,
    block_size: int,
    batches: int,
    device: torch.device,
    seed: int = 1337,
) -> float:
    model_was_training = model.training
    model.eval()
    generator = torch.Generator(device="cpu").manual_seed(seed)
    losses: list[float] = []
    try:
        for _ in range(batches):
            inputs, targets = make_batch(
                tokens,
                batch_size=batch_size,
                block_size=block_size,
                device=device,
                generator=generator,
            )
            _, loss = model(inputs, targets)
            losses.append(float(loss.item()))
    finally:
        model.train(model_was_training)
    return sum(losses) / len(losses)
