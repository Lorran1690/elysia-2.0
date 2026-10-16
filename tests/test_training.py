import random
from pathlib import Path

import pytest
import torch

from brain.generate import generate
from brain.bpe_tokenizer import ByteBPETokenizer
from brain.model import ElysiaTransformer, ModelConfig
from learning.dataset import make_batch
from learning.train import _build_scheduler, load_checkpoint, save_checkpoint, set_seed
from learning.generate_text import load_inference_checkpoint


def tiny_config() -> ModelConfig:
    return ModelConfig(
        vocab_size=259,
        block_size=16,
        num_layers=1,
        embedding_dim=32,
        num_heads=4,
        feedforward_dim=64,
    )


def test_one_batch_updates_parameters_on_cpu() -> None:
    set_seed(11)
    model = ElysiaTransformer(tiny_config())
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.003)
    tokens = torch.tensor(list(range(32)) * 20, dtype=torch.long)
    before = [parameter.detach().clone() for parameter in model.parameters()]
    generator = torch.Generator(device="cpu").manual_seed(11)
    inputs, targets = make_batch(
        tokens,
        batch_size=2,
        block_size=16,
        device=torch.device("cpu"),
        generator=generator,
    )
    _, loss = model(inputs, targets)
    loss.backward()
    optimizer.step()
    assert torch.isfinite(loss)
    assert any(not torch.equal(old, new) for old, new in zip(before, model.parameters()))


def test_controlled_overfit_reduces_loss() -> None:
    set_seed(12)
    model = ElysiaTransformer(tiny_config())
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01)
    tokens = torch.tensor(([97, 98, 99, 100] * 80), dtype=torch.long)
    generator = torch.Generator(device="cpu").manual_seed(12)
    inputs, targets = make_batch(
        tokens,
        batch_size=8,
        block_size=16,
        device=torch.device("cpu"),
        generator=generator,
    )
    _, initial_loss = model(inputs, targets)
    for _ in range(30):
        optimizer.zero_grad(set_to_none=True)
        _, loss = model(inputs, targets)
        loss.backward()
        optimizer.step()
    assert float(loss.item()) < float(initial_loss.item())


def test_checkpoint_round_trip(tmp_path: Path) -> None:
    model = ElysiaTransformer(tiny_config())
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
    path = tmp_path / "checkpoint.pt"
    save_checkpoint(
        path,
        model=model,
        optimizer=optimizer,
        step=7,
        history=[{"step": 7.0, "train_loss": 1.0, "validation_loss": 1.2}],
        config={"seed": 1},
    )
    loaded = torch.load(path, map_location="cpu", weights_only=True)
    restored = ElysiaTransformer(ModelConfig(**loaded["model_config"]))
    restored.load_state_dict(loaded["model_state"])
    assert loaded["step"] == 7
    assert all(torch.equal(a, b) for a, b in zip(model.parameters(), restored.parameters()))


def test_checkpoint_restores_random_states_and_rejects_wrong_config(tmp_path: Path) -> None:
    set_seed(21)
    model = ElysiaTransformer(tiny_config())
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
    generator = torch.Generator(device="cpu").manual_seed(88)
    path = tmp_path / "safe-checkpoint.pt"
    save_checkpoint(
        path,
        model=model,
        optimizer=optimizer,
        step=3,
        history=[],
        config={"seed": 21},
        batch_generator=generator,
        tokenizer_metadata={"type": "byte_utf8", "vocab_size": 259, "fingerprint": "test"},
    )
    expected_python = random.random()
    expected_torch = torch.rand(3)
    expected_batch = torch.randint(100, (3,), generator=generator)

    set_seed(999)
    restored_model = ElysiaTransformer(tiny_config())
    restored_optimizer = torch.optim.AdamW(restored_model.parameters(), lr=0.001)
    restored_generator = torch.Generator(device="cpu").manual_seed(1)
    load_checkpoint(
        path,
        model=restored_model,
        optimizer=restored_optimizer,
        device=torch.device("cpu"),
        expected_tokenizer={"type": "byte_utf8", "vocab_size": 259, "fingerprint": "test"},
        batch_generator=restored_generator,
    )
    assert random.random() == expected_python
    assert torch.equal(torch.rand(3), expected_torch)
    assert torch.equal(torch.randint(100, (3,), generator=restored_generator), expected_batch)

    wrong_model = ElysiaTransformer(ModelConfig(**{**tiny_config().__dict__, "embedding_dim": 16, "num_heads": 4}))
    with pytest.raises(ValueError, match="incompatível"):
        load_checkpoint(path, model=wrong_model, device=torch.device("cpu"))


def test_checkpoint_refuses_resume_with_other_corpus(tmp_path: Path) -> None:
    model = ElysiaTransformer(tiny_config())
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
    path = tmp_path / "audited.pt"
    data = {"fingerprint": "corpus-a"}
    save_checkpoint(path, model=model, optimizer=optimizer, step=1, history=[], config={}, data_metadata=data)
    with pytest.raises(ValueError, match="Dados ou divisão incompatíveis"):
        load_checkpoint(path, model=model, device=torch.device("cpu"), expected_data={"fingerprint": "corpus-b"})


def test_safe_inference_validates_bpe_fingerprint(tmp_path: Path) -> None:
    tokenizer = ByteBPETokenizer(280).train(["modelo local repetido " * 20])
    tokenizer_path = tmp_path / "tokenizer.json"
    tokenizer.save(tokenizer_path)
    model = ElysiaTransformer(ModelConfig(**{**tiny_config().__dict__, "vocab_size": tokenizer.vocab_size}))
    path = tmp_path / "inference.pt"
    save_checkpoint(
        path,
        model=model,
        optimizer=torch.optim.AdamW(model.parameters()),
        step=1,
        history=[],
        config={},
        tokenizer_metadata=tokenizer.metadata(),
    )
    loaded_model, loaded_tokenizer = load_inference_checkpoint(path, device=torch.device("cpu"), tokenizer_path=tokenizer_path)
    assert loaded_model.config.vocab_size == loaded_tokenizer.vocab_size
    other_path = tmp_path / "other.json"
    ByteBPETokenizer(280).train(["outro vocabulário " * 20]).save(other_path)
    with pytest.raises(ValueError, match="vocabulário local"):
        load_inference_checkpoint(path, device=torch.device("cpu"), tokenizer_path=other_path)


def test_seed_makes_initialization_reproducible() -> None:
    set_seed(99)
    first = ElysiaTransformer(tiny_config())
    set_seed(99)
    second = ElysiaTransformer(tiny_config())
    assert all(torch.equal(a, b) for a, b in zip(first.parameters(), second.parameters()))


def test_generation_produces_tokens() -> None:
    model = ElysiaTransformer(tiny_config())
    prompt = torch.tensor([[257, 97, 98]], dtype=torch.long)
    output = generate(model, prompt, max_new_tokens=5, temperature=0.0)
    assert output.shape == (1, 8)
    assert output.dtype == torch.long


def test_cosine_scheduler_warms_up_and_decays() -> None:
    model = torch.nn.Linear(2, 2)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1.0)
    scheduler = _build_scheduler(optimizer, name="cosine", warmup_steps=2, total_steps=6)
    assert scheduler is not None
    rates = [optimizer.param_groups[0]["lr"]]
    for _ in range(6):
        optimizer.step()
        scheduler.step()
        rates.append(optimizer.param_groups[0]["lr"])
    assert rates[0] == 0.5
    assert rates[1] == 1.0
    assert rates[-1] == 0.0
    assert rates[2] > rates[-1]


def test_checkpoint_restores_scheduler_and_progress_metadata(tmp_path: Path) -> None:
    model = ElysiaTransformer(tiny_config())
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01)
    scheduler = _build_scheduler(optimizer, name="cosine", warmup_steps=1, total_steps=4)
    assert scheduler is not None
    optimizer.step()
    scheduler.step()
    path = tmp_path / "resumable.pt"
    save_checkpoint(
        path,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        step=1,
        history=[],
        config={},
        processed_tokens=32,
        progress_metadata={"best_step": 1, "best_validation_loss": 2.0},
    )
    restored_model = ElysiaTransformer(tiny_config())
    restored_optimizer = torch.optim.AdamW(restored_model.parameters(), lr=0.01)
    restored_scheduler = _build_scheduler(restored_optimizer, name="cosine", warmup_steps=1, total_steps=4)
    assert restored_scheduler is not None
    checkpoint = load_checkpoint(
        path,
        model=restored_model,
        optimizer=restored_optimizer,
        scheduler=restored_scheduler,
        device=torch.device("cpu"),
    )
    assert checkpoint["progress"] == {"processed_tokens": 32, "best_step": 1, "best_validation_loss": 2.0}
    assert restored_optimizer.param_groups[0]["lr"] == optimizer.param_groups[0]["lr"]


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA não disponível")
def test_gpu_forward_when_cuda_is_available() -> None:
    model = ElysiaTransformer(tiny_config()).cuda()
    inputs = torch.randint(0, 259, (1, 16), device="cuda")
    logits = model(inputs)
    assert logits.is_cuda
