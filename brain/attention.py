"""Causal attention with optional RoPE, SDPA, and KV cache."""

from __future__ import annotations

import math
from typing import TypeAlias

import torch
from torch import nn
from torch.nn import functional as F

KVCache: TypeAlias = tuple[torch.Tensor, torch.Tensor]


def causal_mask(sequence_length: int, *, device: torch.device | None = None) -> torch.Tensor:
    """Return a mask where True means a future position must be hidden."""
    return torch.triu(torch.ones((sequence_length, sequence_length), dtype=torch.bool, device=device), diagonal=1)


def _cache_mask(query_length: int, key_length: int, *, device: torch.device) -> torch.Tensor:
    """Boolean SDPA mask where True means an attention edge is permitted."""
    past_length = key_length - query_length
    query_positions = torch.arange(query_length, device=device) + past_length
    key_positions = torch.arange(key_length, device=device)
    return key_positions.unsqueeze(0) <= query_positions.unsqueeze(1)


def rotate_half(hidden_states: torch.Tensor) -> torch.Tensor:
    left, right = hidden_states.chunk(2, dim=-1)
    return torch.cat((-right, left), dim=-1)


def apply_rope(hidden_states: torch.Tensor, *, position_offset: int = 0, theta: float = 10_000.0) -> torch.Tensor:
    """Apply half-rotation RoPE to [batch, heads, sequence, head_dim] Q or K."""
    if hidden_states.ndim != 4:
        raise ValueError("RoPE espera [batch, cabeças, sequência, dimensão]")
    head_dim = hidden_states.size(-1)
    if head_dim % 2:
        raise ValueError("RoPE exige dimensão de cabeça par")
    positions = torch.arange(position_offset, position_offset + hidden_states.size(-2), device=hidden_states.device)
    inverse_frequency = 1.0 / (theta ** (torch.arange(0, head_dim, 2, device=hidden_states.device, dtype=torch.float32) / head_dim))
    angles = torch.outer(positions.to(torch.float32), inverse_frequency)
    angles = torch.cat((angles, angles), dim=-1).to(dtype=hidden_states.dtype)
    return hidden_states * angles.cos().unsqueeze(0).unsqueeze(0) + rotate_half(hidden_states) * angles.sin().unsqueeze(0).unsqueeze(0)


class CausalSelfAttention(nn.Module):
    def __init__(
        self,
        embedding_dim: int,
        num_heads: int,
        dropout: float = 0.0,
        *,
        use_rope: bool = False,
        rope_theta: float = 10_000.0,
        backend: str = "manual",
    ) -> None:
        super().__init__()
        if embedding_dim % num_heads != 0:
            raise ValueError("embedding_dim precisa ser divisível por num_heads")
        if backend not in {"manual", "sdpa"}:
            raise ValueError("Backend de atenção desconhecido")
        self.embedding_dim = embedding_dim
        self.num_heads = num_heads
        self.head_dim = embedding_dim // num_heads
        if use_rope and self.head_dim % 2:
            raise ValueError("RoPE exige dimensão de cabeça par")
        self.use_rope = use_rope
        self.rope_theta = rope_theta
        # SDPA is bundled with supported PyTorch versions; retain a correct manual route otherwise.
        self.backend = "sdpa" if backend == "sdpa" and hasattr(F, "scaled_dot_product_attention") else "manual"
        self.qkv = nn.Linear(embedding_dim, 3 * embedding_dim)
        self.output = nn.Linear(embedding_dim, embedding_dim)
        self.dropout = nn.Dropout(dropout)

    def _attend_manual(self, query: torch.Tensor, key: torch.Tensor, value: torch.Tensor) -> torch.Tensor:
        scores = (query @ key.transpose(-2, -1)) / math.sqrt(self.head_dim)
        allowed = _cache_mask(query.size(-2), key.size(-2), device=query.device)
        scores = scores.masked_fill(~allowed.unsqueeze(0).unsqueeze(0), float("-inf"))
        weights = self.dropout(torch.softmax(scores, dim=-1))
        return weights @ value

    def _attend_sdpa(self, query: torch.Tensor, key: torch.Tensor, value: torch.Tensor) -> torch.Tensor:
        dropout = self.dropout.p if self.training else 0.0
        if query.size(-2) == key.size(-2):
            return F.scaled_dot_product_attention(query, key, value, dropout_p=dropout, is_causal=True)
        allowed = _cache_mask(query.size(-2), key.size(-2), device=query.device)
        return F.scaled_dot_product_attention(query, key, value, attn_mask=allowed, dropout_p=dropout)

    def forward(
        self,
        hidden_states: torch.Tensor,
        *,
        past_key_value: KVCache | None = None,
        use_cache: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, KVCache]:
        batch_size, sequence_length, _ = hidden_states.shape
        qkv = self.qkv(hidden_states)
        query, key, value = qkv.chunk(3, dim=-1)
        shape = (batch_size, sequence_length, self.num_heads, self.head_dim)
        query = query.view(shape).transpose(1, 2)
        key = key.view(shape).transpose(1, 2)
        value = value.view(shape).transpose(1, 2)
        past_length = 0 if past_key_value is None else past_key_value[0].size(-2)
        if self.use_rope:
            query = apply_rope(query, position_offset=past_length, theta=self.rope_theta)
            key = apply_rope(key, position_offset=past_length, theta=self.rope_theta)
        if past_key_value is not None:
            past_key, past_value = past_key_value
            key = torch.cat((past_key, key), dim=-2)
            value = torch.cat((past_value, value), dim=-2)
        attended = self._attend_sdpa(query, key, value) if self.backend == "sdpa" else self._attend_manual(query, key, value)
        output = self.output(attended.transpose(1, 2).contiguous().view(batch_size, sequence_length, self.embedding_dim))
        if use_cache:
            return output, (key, value)
        return output
