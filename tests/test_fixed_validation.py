from array import array
from pathlib import Path

import pytest
import torch

from brain.model import ElysiaTransformer, ModelConfig
from learning.dataset import TokenStore
from learning.fixed_validation import build_fixed_validation_windows, build_full_validation_windows, evaluate_fixed_validation
from learning.run_v04_extended import _scheduled_steps


def token_store(tmp_path: Path, count: int = 4097) -> TokenStore:
    path = tmp_path / "validation.bin"
    values = array("I", (index % 259 for index in range(count)))
    path.write_bytes(values.tobytes())
    return TokenStore(path=path, token_count=count, sha256="validation-hash", metadata_path=tmp_path / "validation.json")


def tiny_model() -> ElysiaTransformer:
    return ElysiaTransformer(
        ModelConfig(vocab_size=259, block_size=16, num_layers=1, embedding_dim=32, num_heads=4, feedforward_dim=64)
    )


def test_fixed_windows_are_deterministic_and_distributed(tmp_path: Path) -> None:
    store = token_store(tmp_path, 10_001)
    first = build_fixed_validation_windows(store, block_size=16, window_count=17)
    second = build_fixed_validation_windows(store, block_size=16, window_count=17)
    assert first == second
    assert first.offsets[0] == 0
    assert first.offsets[-1] == store.token_count - 17
    assert len(set(first.offsets)) == 17
    assert first.metadata()["evaluated_tokens"] == 17 * 16


def test_fixed_validation_is_repeatable_and_counts_tokens(tmp_path: Path) -> None:
    store = token_store(tmp_path)
    windows = build_fixed_validation_windows(store, block_size=16, window_count=32)
    model = tiny_model()
    first = evaluate_fixed_validation(model, store, windows, batch_size=8, device=torch.device("cpu"))
    second = evaluate_fixed_validation(model, store, windows, batch_size=8, device=torch.device("cpu"))
    assert first["loss"] == second["loss"]
    assert first["evaluated_tokens"] == 512
    assert first["protocol"] == second["protocol"]


def test_validation_selection_rejects_test_partition(tmp_path: Path) -> None:
    store = token_store(tmp_path)
    with pytest.raises(ValueError, match="validation"):
        build_fixed_validation_windows(store, block_size=16, window_count=4, partition="test")
    with pytest.raises(ValueError, match="validation"):
        build_full_validation_windows(store, block_size=16, partition="test")


def test_full_validation_mode_is_explicit_and_does_not_select_test(tmp_path: Path) -> None:
    store = token_store(tmp_path, 101)
    windows = build_full_validation_windows(store, block_size=16)
    metadata = windows.metadata()
    assert metadata["partition"] == "validation"
    assert metadata["mode"] == "full_non_overlapping"
    assert metadata["evaluated_tokens"] == metadata["window_count"] * 16


def test_phase_five_requires_all_hundred_step_evaluations() -> None:
    expected = list(range(0, 1_001, 100))
    assert _scheduled_steps(1_000, expected) == tuple(expected)
    with pytest.raises(ValueError, match="evaluation_steps"):
        _scheduled_steps(1_000, [0, 100, 1_000])
