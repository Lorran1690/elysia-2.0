"""Run the bounded v0.4 Machado pilot and record reproducible observations."""

from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path
from typing import Any

import torch
import yaml

from brain.generate import generate
from brain.bpe_tokenizer import ByteBPETokenizer
from brain.model import ElysiaTransformer
from learning.generate_text import load_inference_checkpoint
from learning.train import _model_config, resolve_device, set_seed, train_model


PROMPTS = [
    "Capítulo primeiro. ",
    "A vida é ",
    "Quando o dia ",
    "O leitor verá ",
]


def _generate_samples(
    model: ElysiaTransformer,
    tokenizer: ByteBPETokenizer,
    *,
    device: torch.device,
    seed: int,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for index, prompt in enumerate(PROMPTS):
        set_seed(seed + index)
        prompt_ids = torch.tensor([tokenizer.encode(prompt, add_eos=False)], dtype=torch.long, device=device)
        output_ids = generate(
            model,
            prompt_ids,
            max_new_tokens=80,
            temperature=0.8,
            top_k=20,
            eos_id=tokenizer.eos_id,
            use_cache=True,
        )
        samples.append(
            {
                "prompt": prompt,
                "generated_text": tokenizer.decode(output_ids[0].tolist(), errors="replace"),
                "prompt_tokens": int(prompt_ids.numel()),
                "generated_tokens": int(output_ids.numel() - prompt_ids.numel()),
            }
        )
    return samples


def run_pilot(
    config_path: str | Path,
    *,
    data_dir: str | Path,
    checkpoint_path: str | Path,
    output_path: str | Path,
    device_name: str | None = None,
) -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    device = resolve_device(device_name or config["training"].get("device", "auto"))
    tokenizer = ByteBPETokenizer.load(config["tokenizer"]["path"])
    model_values = dict(config["model"])
    model_values["vocab_size"] = tokenizer.vocab_size
    model_config = _model_config(model_values)

    set_seed(int(config["seed"]))
    before_model = ElysiaTransformer(model_config).to(device)
    before_samples = _generate_samples(
        before_model,
        tokenizer,
        device=device,
        seed=int(config["seed"]) + 10_000,
    )
    del before_model
    gc.collect()
    if device.type == "cuda":
        torch.cuda.empty_cache()

    training = train_model(
        config_path,
        data_dir=data_dir,
        checkpoint_path=checkpoint_path,
        device_name=device_name,
    )
    after_model, after_tokenizer = load_inference_checkpoint(
        checkpoint_path,
        device=device,
        tokenizer_path=config["tokenizer"]["path"],
    )
    after_samples = _generate_samples(
        after_model,
        after_tokenizer,
        device=device,
        seed=int(config["seed"]) + 10_000,
    )
    result = {
        "schema_version": 1,
        "phase": "v0.4-phase-4-bounded-pilot",
        "corpus_policy": "Somente as três obras Machado de Assis já aprovadas e auditadas; nenhum download adicional.",
        "training_policy": {
            "main_pretraining_started": False,
            "architecture_increased": False,
            "test_split_used_for_selection": False,
            "checkpoint_is_local_only": True,
        },
        "fixed_generation_protocol": {
            "prompts": PROMPTS,
            "max_new_tokens": 80,
            "temperature": 0.8,
            "top_k": 20,
            "seed": int(config["seed"]) + 10_000,
            "interpretation_note": "Amostras são observações qualitativas de um piloto curto e não demonstram compreensão, factualidade ou capacidade conversacional geral.",
        },
        "before_training": before_samples,
        "after_training": after_samples,
        "training": training,
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/seed-v0.4-machado-pilot.yaml")
    parser.add_argument("--data-dir", default="data/corpus-v0.4/clean")
    parser.add_argument("--checkpoint", default="learning/checkpoints/elysia-seed-v0.4-machado-pilot.pt")
    parser.add_argument("--output", default="reports/seed-v0.4-pilot-results.json")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default=None)
    args = parser.parse_args()
    result = run_pilot(
        args.config,
        data_dir=args.data_dir,
        checkpoint_path=args.checkpoint,
        output_path=args.output,
        device_name=args.device,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
