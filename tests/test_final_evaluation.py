from __future__ import annotations

import hashlib
from array import array
from pathlib import Path

import pytest
import torch

from brain.model import ElysiaTransformer, ModelConfig
from learning.dataset import TokenStore
from learning.final_evaluation_v04 import build_final_test_windows, evaluate_final_test


def _token_store(tmp_path: Path, values: list[int]) -> TokenStore:
    path = tmp_path / "test.bin"
    raw = array("I", values).tobytes()
    path.write_bytes(raw)
    return TokenStore(
        path=path,
        token_count=len(values),
        sha256=hashlib.sha256(raw).hexdigest(),
        metadata_path=path.with_suffix(".json"),
    )


def _model() -> ElysiaTransformer:
    return ElysiaTransformer(
        ModelConfig(
            vocab_size=32,
            block_size=5,
            num_layers=1,
            embedding_dim=8,
            num_heads=2,
            feedforward_dim=16,
        )
    )


def test_final_windows_score_each_next_token_once_with_a_short_tail(tmp_path: Path) -> None:
    tokens = _token_store(tmp_path, list(range(17)))
    windows = build_final_test_windows(tokens, block_size=5)

    assert [(window.offset, window.target_tokens) for window in windows.windows] == [(0, 5), (5, 5), (10, 5), (15, 1)]
    targets = [
        target
        for window in windows.windows
        for target in range(window.offset + 1, window.offset + window.target_tokens + 1)
    ]
    assert targets == list(range(1, tokens.token_count))
    assert windows.metadata()["trailing_window_target_tokens"] == 1


def test_final_windows_reject_non_test_partition(tmp_path: Path) -> None:
    tokens = _token_store(tmp_path, list(range(8)))
    with pytest.raises(ValueError, match="partição test"):
        build_final_test_windows(tokens, block_size=4, partition="validation")


def test_final_evaluation_reports_weighted_metrics_and_special_tokens(tmp_path: Path) -> None:
    torch.manual_seed(7)
    tokens = _token_store(tmp_path, [30, 1, 2, 3, 4, 5, 6, 7, 31])
    windows = build_final_test_windows(tokens, block_size=5)
    result = evaluate_final_test(
        _model(),
        tokens,
        windows,
        batch_size=2,
        device=torch.device("cpu"),
        text_bytes=7,
        special_token_ids={30, 31},
    )

    assert result["evaluated_target_tokens"] == 8
    assert result["content_target_tokens"] == 7
    assert result["excluded_special_target_tokens"] == 1
    assert result["window_count"] == 2
    assert result["batch_count"] == 2
    assert result["loss"] > 0
    assert result["perplexity"] > 1
    assert result["bits_per_byte"] > 0
