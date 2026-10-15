"""Short v0.4 architecture pilot; it does not download data or start pretraining."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
import yaml

from brain.generate import generate
from brain.model import ElysiaTransformer

from .benchmark import benchmark_model
from .train import _model_config, resolve_device, set_seed, train_model


def _configuration(name: str) -> dict[str, object]:
    base = {"vocab_size": 504, "block_size": 256, "num_layers": 4, "embedding_dim": 256, "num_heads": 4, "feedforward_dim": 1024, "dropout": 0.0, "positional_embedding": "absolute", "norm_type": "layernorm", "feedforward_type": "gelu", "attention_backend": "manual"}
    changes = {
        "swiglu-sdpa": {"feedforward_type": "swiglu", "attention_backend": "sdpa"},
        "swiglu": {"feedforward_type": "swiglu"},
        "sdpa": {"attention_backend": "sdpa"},
        "combined": {"positional_embedding": "rope", "norm_type": "rmsnorm", "feedforward_type": "swiglu", "attention_backend": "sdpa"},
    }
    base.update(changes[name])
    return base


def cache_window_equivalence(model: ElysiaTransformer, device: torch.device) -> dict[str, object]:
    prompts = [
        torch.arange(7, device=device).unsqueeze(0) % model.config.vocab_size,
        torch.arange(251, device=device).unsqueeze(0) % model.config.vocab_size,
        torch.arange(256, device=device).unsqueeze(0) % model.config.vocab_size,
    ]
    rows: list[dict[str, object]] = []
    for prompt in prompts:
        uncached = generate(model, prompt, max_new_tokens=12, temperature=0.0, use_cache=False)
        cached = generate(model, prompt, max_new_tokens=12, temperature=0.0, use_cache=True)
        rows.append({"prompt_tokens": prompt.size(1), "new_tokens": 12, "equal": bool(torch.equal(uncached, cached))})
    return {"cases": rows, "all_equal": all(bool(row["equal"]) for row in rows)}


def run(*, device_name: str, pilot_steps: int, repetitions: int) -> dict[str, object]:
    device = resolve_device(device_name)
    results: dict[str, object] = {"device": str(device), "benchmark_kind": "synthetic tensors", "experiments": {}}
    for name in ("swiglu-sdpa", "swiglu", "sdpa", "combined"):
        set_seed(2026)
        model = ElysiaTransformer(_model_config(_configuration(name))).to(device)
        results["experiments"][name] = benchmark_model(model, device=device, steps=5, warmup=2, repetitions=repetitions)
        model.eval()
        results["experiments"][name]["cache_window_equivalence"] = cache_window_equivalence(model, device)
    set_seed(2026)
    pilot = train_model(
        "configs/seed-v0.4-swiglu-sdpa.yaml",
        data_dir="data/raw",
        checkpoint_path="learning/checkpoints/elysia-seed-v0.4-pilot.pt",
        device_name=device_name,
        max_steps=pilot_steps,
    )
    results["corpus_pilot"] = pilot
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--pilot-steps", type=int, default=10)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output", default="reports/seed-v0.4-architecture.json")
    args = parser.parse_args()
    result = run(device_name=args.device, pilot_steps=args.pilot_steps, repetitions=args.repetitions)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
