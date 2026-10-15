"""Autoregressive token generation utilities."""

from __future__ import annotations

import torch

from .model import ElysiaTransformer


@torch.no_grad()
def generate(
    model: ElysiaTransformer,
    input_ids: torch.Tensor,
    *,
    max_new_tokens: int,
    temperature: float = 1.0,
    top_k: int | None = 50,
    eos_id: int | None = None,
) -> torch.Tensor:
    if input_ids.ndim != 2:
        raise ValueError("input_ids precisa ter o formato [batch, sequência]")
    if temperature < 0:
        raise ValueError("temperature não pode ser negativa")
    was_training = model.training
    model.eval()
    generated = input_ids
    try:
        for _ in range(max_new_tokens):
            context = generated[:, -model.config.block_size :]
            logits = model(context)[:, -1, :]
            if temperature == 0:
                next_token = logits.argmax(dim=-1, keepdim=True)
            else:
                logits = logits / temperature
                if top_k is not None:
                    top_k = min(top_k, logits.size(-1))
                    values, _ = torch.topk(logits, top_k)
                    logits = logits.masked_fill(logits < values[:, [-1]], float("-inf"))
                probabilities = torch.softmax(logits, dim=-1)
                next_token = torch.multinomial(probabilities, num_samples=1)
            generated = torch.cat((generated, next_token), dim=1)
            if eos_id is not None and torch.all(next_token == eos_id):
                break
    finally:
        model.train(was_training)
    return generated
