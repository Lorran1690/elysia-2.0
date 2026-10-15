"""Causal self-attention used by the decoder-only Transformer."""

from __future__ import annotations

import torch
from torch import nn


def causal_mask(sequence_length: int, *, device: torch.device | None = None) -> torch.Tensor:
    """Return a boolean mask where True marks positions that must be hidden."""
    return torch.triu(
        torch.ones((sequence_length, sequence_length), dtype=torch.bool, device=device),
        diagonal=1,
    )


class CausalSelfAttention(nn.Module):
    def __init__(self, embedding_dim: int, num_heads: int, dropout: float = 0.0) -> None:
        super().__init__()
        if embedding_dim % num_heads != 0:
            raise ValueError("embedding_dim precisa ser divisível por num_heads")
        self.embedding_dim = embedding_dim
        self.num_heads = num_heads
        self.head_dim = embedding_dim // num_heads
        self.qkv = nn.Linear(embedding_dim, 3 * embedding_dim)
        self.output = nn.Linear(embedding_dim, embedding_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        batch_size, sequence_length, _ = hidden_states.shape
        qkv = self.qkv(hidden_states)
        query, key, value = qkv.chunk(3, dim=-1)
        shape = (batch_size, sequence_length, self.num_heads, self.head_dim)
        query = query.view(shape).transpose(1, 2)
        key = key.view(shape).transpose(1, 2)
        value = value.view(shape).transpose(1, 2)

        scores = (query @ key.transpose(-2, -1)) / (self.head_dim**0.5)
        scores = scores.masked_fill(causal_mask(sequence_length, device=hidden_states.device), float("-inf"))
        weights = torch.softmax(scores, dim=-1)
        weights = self.dropout(weights)
        attended = weights @ value
        attended = attended.transpose(1, 2).contiguous().view(batch_size, sequence_length, self.embedding_dim)
        return self.output(attended)
