"""Run the small, reproducible v0.3 architecture ablations locally."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
import yaml

from brain.model import ElysiaTransformer

from .benchmark import benchmark_model
from .train import _model_config, resolve_device, set_seed, train_model


EXPERIMENTS = ("baseline", "rope", "rmsnorm", "swiglu", "sdpa", "combined")


def run_ablations(*, device_name: str = "auto", steps: int | None = None) -> dict[str, object]:
    device = resolve_device(device_name)
    results: dict[str, object] = {}
    for name in EXPERIMENTS:
        config_path = Path(f"configs/seed-v0.3-{name}.yaml")
        checkpoint = Path(f"learning/checkpoints/elysia-seed-v0.3-{name}.pt")
        trained = train_model(
            config_path,
            data_dir="data/raw",
            checkpoint_path=checkpoint,
            device_name=device_name,
            max_steps=steps,
        )
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        model_values = dict(config["model"])
        model_values["vocab_size"] = trained["tokenizer"]["vocab_size"]
        set_seed(int(config["seed"]))
        benchmark = benchmark_model(ElysiaTransformer(_model_config(model_values)), device=device)
        results[name] = {"training": trained, "benchmark": benchmark}
    return {"device": str(device), "experiments": results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--output", default="reports/seed-v0.3-results.json")
    args = parser.parse_args()
    result = run_ablations(device_name=args.device, steps=args.steps)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
