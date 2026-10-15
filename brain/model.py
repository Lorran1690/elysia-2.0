"""Configurable, randomly initialized decoder-only Transformer."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import torch
from torch import nn
from torch.nn import functional as F

from .attention import CausalSelfAttention, KVCache


@dataclass(frozen=True)
class ModelConfig:
    vocab_size: int = 259
    block_size: int = 256
    num_layers: int = 4
    embedding_dim: int = 256
    num_heads: int = 4
    feedforward_dim: int = 1024
    dropout: float = 0.0
    positional_embedding: str = "absolute"
    norm_type: str = "layernorm"
    feedforward_type: str = "gelu"
    attention_backend: str = "manual"
    rope_theta: float = 10_000.0


class RMSNorm(nn.Module):
    def __init__(self, dimension: int, epsilon: float = 1e-6) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dimension))
        self.epsilon = epsilon

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        scale = torch.rsqrt(hidden_states.float().pow(2).mean(dim=-1, keepdim=True) + self.epsilon).to(hidden_states.dtype)
        return hidden_states * scale * self.weight


def _norm(config: ModelConfig) -> nn.Module:
    if config.norm_type == "layernorm":
        return nn.LayerNorm(config.embedding_dim)
    if config.norm_type == "rmsnorm":
        return RMSNorm(config.embedding_dim)
    raise ValueError("Tipo de normalização desconhecido")


class FeedForward(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        if config.feedforward_type == "gelu":
            self.network = nn.Sequential(
                nn.Linear(config.embedding_dim, config.feedforward_dim),
                nn.GELU(),
                nn.Linear(config.feedforward_dim, config.embedding_dim),
                nn.Dropout(config.dropout),
            )
            self.gate = None
        elif config.feedforward_type == "swiglu":
            # 3 * d * hidden approximately matches the 2 * d * ffn GELU projection count.
            hidden = max(1, round((2 * config.feedforward_dim) / 3))
            self.gate = nn.Linear(config.embedding_dim, 2 * hidden)
            self.network = nn.Sequential(nn.Linear(hidden, config.embedding_dim), nn.Dropout(config.dropout))
        else:
            raise ValueError("Tipo de feedforward desconhecido")

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        if self.gate is None:
            return self.network(hidden_states)
        values, gates = self.gate(hidden_states).chunk(2, dim=-1)
        return self.network(values * F.silu(gates))


class DecoderBlock(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.attention_norm = _norm(config)
        self.attention = CausalSelfAttention(
            config.embedding_dim,
            config.num_heads,
            config.dropout,
            use_rope=config.positional_embedding == "rope",
            rope_theta=config.rope_theta,
            backend=config.attention_backend,
        )
        self.feedforward_norm = _norm(config)
        self.feedforward = FeedForward(config)

    def forward(
        self, hidden_states: torch.Tensor, *, past_key_value: KVCache | None = None, use_cache: bool = False
    ) -> torch.Tensor | tuple[torch.Tensor, KVCache]:
        attention = self.attention(self.attention_norm(hidden_states), past_key_value=past_key_value, use_cache=use_cache)
        if use_cache:
            attention_output, cache = attention  # type: ignore[misc]
        else:
            attention_output = attention  # type: ignore[assignment]
        hidden_states = hidden_states + attention_output
        hidden_states = hidden_states + self.feedforward(self.feedforward_norm(hidden_states))
        return (hidden_states, cache) if use_cache else hidden_states


class ElysiaTransformer(nn.Module):
    """Small local model. No pretrained weights or external model code are used."""

    def __init__(self, config: ModelConfig | None = None) -> None:
        super().__init__()
        self.config = config or ModelConfig()
        if self.config.positional_embedding not in {"absolute", "rope"}:
            raise ValueError("Tipo de embedding posicional desconhecido")
        self.token_embeddings = nn.Embedding(self.config.vocab_size, self.config.embedding_dim)
        self.position_embeddings = (
            nn.Embedding(self.config.block_size, self.config.embedding_dim)
            if self.config.positional_embedding == "absolute"
            else None
        )
        self.blocks = nn.ModuleList(DecoderBlock(self.config) for _ in range(self.config.num_layers))
        self.final_norm = _norm(self.config)
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
        *,
        past_key_values: list[KVCache] | None = None,
        use_cache: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor] | tuple[torch.Tensor, list[KVCache]]:
        if input_ids.ndim != 2:
            raise ValueError("input_ids precisa ter o formato [batch, sequência]")
        if targets is not None and use_cache:
            raise ValueError("Cache é exclusivo para inferência")
        _, sequence_length = input_ids.shape
        past_length = 0 if past_key_values is None else past_key_values[0][0].size(-2)
        if past_key_values is not None and len(past_key_values) != len(self.blocks):
            raise ValueError("Cache de KV incompatível com a quantidade de blocos")
        if sequence_length + past_length > self.config.block_size:
            raise ValueError("A sequência excede o contexto configurado")
        hidden_states = self.token_embeddings(input_ids)
        if self.position_embeddings is not None:
            positions = torch.arange(past_length, past_length + sequence_length, device=input_ids.device)
            hidden_states = hidden_states + self.position_embeddings(positions)
        next_cache: list[KVCache] = []
        for index, block in enumerate(self.blocks):
            block_cache = None if past_key_values is None else past_key_values[index]
            output = block(hidden_states, past_key_value=block_cache, use_cache=use_cache)
            if use_cache:
                hidden_states, cache = output  # type: ignore[misc]
                next_cache.append(cache)
            else:
                hidden_states = output  # type: ignore[assignment]
        logits = self.output_projection(self.final_norm(hidden_states))
        if targets is not None:
            loss = F.cross_entropy(logits.reshape(-1, self.config.vocab_size), targets.reshape(-1))
            return logits, loss
        return (logits, next_cache) if use_cache else logits

    def num_parameters(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())

    def config_dict(self) -> dict[str, int | float | str]:
        return asdict(self.config)
