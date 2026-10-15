"""Randomly initialized decoder-only Transformer for E.L.Y.S.I.A. 2.0."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import torch
from torch import nn
from torch.nn import functional as F

from .attention import CausalSelfAttention


@dataclass(frozen=True)
class ModelConfig:
    vocab_size: int = 259
    block_size: int = 256
    num_layers: int = 4
    embedding_dim: int = 256
    num_heads: int = 4
    feedforward_dim: int = 1024
    dropout: float = 0.0


class FeedForward(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(config.embedding_dim, config.feedforward_dim),
            nn.GELU(),
            nn.Linear(config.feedforward_dim, config.embedding_dim),
            nn.Dropout(config.dropout),
        )

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        return self.network(hidden_states)


class DecoderBlock(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.attention_norm = nn.LayerNorm(config.embedding_dim)
        self.attention = CausalSelfAttention(
            config.embedding_dim,
            config.num_heads,
            config.dropout,
        )
        self.feedforward_norm = nn.LayerNorm(config.embedding_dim)
        self.feedforward = FeedForward(config)

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        hidden_states = hidden_states + self.attention(self.attention_norm(hidden_states))
        hidden_states = hidden_states + self.feedforward(self.feedforward_norm(hidden_states))
        return hidden_states


class ElysiaTransformer(nn.Module):
    """Small GPT-like model whose weights are initialized locally from scratch."""

    def __init__(self, config: ModelConfig | None = None) -> None:
        super().__init__()
        self.config = config or ModelConfig()
        self.token_embeddings = nn.Embedding(self.config.vocab_size, self.config.embedding_dim)
        self.position_embeddings = nn.Embedding(self.config.block_size, self.config.embedding_dim)
        self.blocks = nn.ModuleList(DecoderBlock(self.config) for _ in range(self.config.num_layers))
        self.final_norm = nn.LayerNorm(self.config.embedding_dim)
        self.output_projection = nn.Linear(self.config.embedding_dim, self.config.vocab_size)
        self.apply(self._initialize_weights)

    @staticmethod
    def _initialize_weights(module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(
        self,
        input_ids: torch.Tensor,
        targets: torch.Tensor | None = None,
    ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
        if input_ids.ndim != 2:
            raise ValueError("input_ids precisa ter o formato [batch, sequência]")
        _, sequence_length = input_ids.shape
        if sequence_length > self.config.block_size:
            raise ValueError("A sequência excede o contexto configurado")
        positions = torch.arange(sequence_length, device=input_ids.device)
        hidden_states = self.token_embeddings(input_ids) + self.position_embeddings(positions)
        for block in self.blocks:
            hidden_states = block(hidden_states)
        logits = self.output_projection(self.final_norm(hidden_states))
        if targets is None:
            return logits
        loss = F.cross_entropy(logits.reshape(-1, self.config.vocab_size), targets.reshape(-1))
        return logits, loss

    def num_parameters(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())

    def config_dict(self) -> dict[str, int | float]:
        return asdict(self.config)
