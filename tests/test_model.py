import torch

from brain.model import ElysiaTransformer, ModelConfig


def tiny_config() -> ModelConfig:
    return ModelConfig(
        vocab_size=259,
        block_size=16,
        num_layers=1,
        embedding_dim=32,
        num_heads=4,
        feedforward_dim=64,
    )


def test_required_default_architecture() -> None:
    config = ModelConfig()
    assert config.num_layers == 4
    assert config.embedding_dim == 256
    assert config.num_heads == 4
    assert config.feedforward_dim == 1024
    assert config.block_size == 256


def test_tensor_shapes_and_gradients() -> None:
    model = ElysiaTransformer(tiny_config())
    inputs = torch.randint(0, 259, (2, 16))
    targets = torch.randint(0, 259, (2, 16))
    logits, loss = model(inputs, targets)
    assert logits.shape == (2, 16, 259)
    assert loss.ndim == 0
    loss.backward()
    assert all(parameter.grad is not None for parameter in model.parameters())


def test_context_limit_is_enforced() -> None:
    model = ElysiaTransformer(tiny_config())
    inputs = torch.zeros((1, 17), dtype=torch.long)
    try:
        model(inputs)
    except ValueError as error:
        assert "contexto" in str(error)
    else:
        raise AssertionError("A sequência acima do contexto deveria falhar")
