import copy

import pytest
import torch

from brain.attention import CausalSelfAttention, apply_rope
from brain.generate import generate
from brain.model import ElysiaTransformer, ModelConfig, RMSNorm
from learning.benchmark import benchmark_model


def config(**changes: object) -> ModelConfig:
    values: dict[str, object] = {
        "vocab_size": 97,
        "block_size": 16,
        "num_layers": 2,
        "embedding_dim": 32,
        "num_heads": 4,
        "feedforward_dim": 64,
        "dropout": 0.0,
    }
    values.update(changes)
    return ModelConfig(**values)  # type: ignore[arg-type]


def test_rope_preserves_shape_and_vector_norm() -> None:
    hidden = torch.randn(2, 4, 5, 8)
    rotated = apply_rope(hidden, position_offset=3)
    assert rotated.shape == hidden.shape
    assert torch.allclose(rotated.norm(dim=-1), hidden.norm(dim=-1), atol=1e-5)
    with pytest.raises(ValueError, match="par"):
        apply_rope(torch.randn(1, 1, 2, 7))


def test_rope_model_supports_cpu_gradients() -> None:
    model = ElysiaTransformer(config(positional_embedding="rope"))
    logits, loss = model(torch.randint(0, 97, (2, 8)), torch.randint(0, 97, (2, 8)))
    loss.backward()
    assert logits.shape == (2, 8, 97)
    assert all(parameter.grad is not None for parameter in model.parameters())


def test_rmsnorm_is_finite_and_has_gradients() -> None:
    norm = RMSNorm(13)
    hidden = torch.randn(3, 5, 13, requires_grad=True)
    output = norm(hidden)
    output.square().mean().backward()
    assert torch.isfinite(output).all()
    assert hidden.grad is not None and torch.isfinite(hidden.grad).all()
    assert norm.weight.grad is not None


def test_swiglu_keeps_parameter_count_close_to_gelu() -> None:
    gelu = ElysiaTransformer(config(feedforward_type="gelu"))
    swiglu = ElysiaTransformer(config(feedforward_type="swiglu"))
    difference = abs(gelu.num_parameters() - swiglu.num_parameters())
    assert difference / gelu.num_parameters() < 0.01
    assert swiglu(torch.randint(0, 97, (1, 4))).shape == (1, 4, 97)


def test_sdpa_matches_manual_attention_without_dropout() -> None:
    torch.manual_seed(4)
    manual = CausalSelfAttention(32, 4, backend="manual")
    sdpa = CausalSelfAttention(32, 4, backend="sdpa")
    sdpa.load_state_dict(copy.deepcopy(manual.state_dict()))
    hidden = torch.randn(2, 7, 32)
    assert torch.allclose(manual(hidden), sdpa(hidden), atol=1e-5, rtol=1e-5)


def test_kv_cache_matches_uncached_deterministic_generation() -> None:
    torch.manual_seed(8)
    model = ElysiaTransformer(config(positional_embedding="rope", attention_backend="sdpa"))
    prompt = torch.tensor([[1, 2, 3, 4]], dtype=torch.long)
    without_cache = generate(model, prompt, max_new_tokens=10, temperature=0.0, use_cache=False)
    with_cache = generate(model, prompt, max_new_tokens=10, temperature=0.0, use_cache=True)
    assert torch.equal(with_cache, without_cache)


def test_kv_cache_matches_full_forward_for_multiple_new_tokens() -> None:
    torch.manual_seed(11)
    model = ElysiaTransformer(config(positional_embedding="rope", attention_backend="sdpa"))
    tokens = torch.randint(0, 97, (1, 7))
    full = model(tokens)
    _, cache = model(tokens[:, :3], use_cache=True)
    cached, cache = model(tokens[:, 3:], past_key_values=cache, use_cache=True)
    assert len(cache) == model.config.num_layers
    assert torch.allclose(cached, full[:, 3:], atol=1e-5, rtol=1e-5)


def test_kv_cache_respects_context_window() -> None:
    model = ElysiaTransformer(config(block_size=8, positional_embedding="rope"))
    prompt = torch.tensor([[1, 2, 3, 4, 5, 6]], dtype=torch.long)
    output = generate(model, prompt, max_new_tokens=12, temperature=0.0, use_cache=True)
    assert output.shape == (1, 18)


def test_cpu_benchmark_returns_resource_metrics() -> None:
    metrics = benchmark_model(ElysiaTransformer(config()), device=torch.device("cpu"), steps=1)
    assert metrics["parameters"] > 0
    assert metrics["tokens_per_second"] > 0
    assert metrics["kv_cache_bytes_for_prompt"] > 0


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA não disponível")
def test_rope_and_cache_on_cuda() -> None:
    model = ElysiaTransformer(config(positional_embedding="rope", norm_type="rmsnorm", feedforward_type="swiglu")).cuda()
    prompt = torch.tensor([[1, 2, 3]], device="cuda")
    assert generate(model, prompt, max_new_tokens=3, temperature=0.0, use_cache=True).is_cuda
