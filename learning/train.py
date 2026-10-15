"""Configurable training loop with checkpoints and CPU/GPU fallback."""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path
from typing import Any

import torch
import yaml

from brain.model import ElysiaTransformer, ModelConfig

from .dataset import (
    load_text_documents,
    make_batch,
    split_documents,
    tokenize_documents,
    write_source_manifest,
)
from .evaluate import evaluate_loss


def resolve_device(requested: str = "auto") -> torch.device:
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA foi solicitado, mas não está disponível neste ambiente")
    return torch.device(requested)


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _model_config(values: dict[str, Any]) -> ModelConfig:
    return ModelConfig(
        vocab_size=int(values.get("vocab_size", 259)),
        block_size=int(values.get("block_size", 256)),
        num_layers=int(values.get("num_layers", 4)),
        embedding_dim=int(values.get("embedding_dim", 256)),
        num_heads=int(values.get("num_heads", 4)),
        feedforward_dim=int(values.get("feedforward_dim", 1024)),
        dropout=float(values.get("dropout", 0.0)),
    )


def save_checkpoint(
    path: str | Path,
    *,
    model: ElysiaTransformer,
    optimizer: torch.optim.Optimizer,
    step: int,
    history: list[dict[str, float]],
    config: dict[str, Any],
) -> None:
    checkpoint = {
        "step": step,
        "model_config": model.config_dict(),
        "model_state": model.state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "history": history,
        "training_config": config,
    }
    checkpoint_path = Path(path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, checkpoint_path)


def train_model(
    config_path: str | Path,
    *,
    data_dir: str | Path,
    checkpoint_path: str | Path,
    device_name: str | None = None,
    max_steps: int | None = None,
) -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    seed = int(config["seed"])
    set_seed(seed)
    device = resolve_device(device_name or config["training"].get("device", "auto"))
    tokenizer = __import__("brain.tokenizer", fromlist=["ByteTokenizer"]).ByteTokenizer()

    documents = load_text_documents(data_dir)
    split = split_documents(
        documents,
        validation_fraction=float(config["data"].get("validation_fraction", 0.25)),
        seed=seed,
    )
    write_source_manifest(
        documents,
        Path(data_dir).parent / "SOURCES.generated.md",
        license_note="Material de demonstração original do projeto; não é uma fonte externa.",
    )
    train_tokens = tokenize_documents(split.train, tokenizer)
    validation_tokens = tokenize_documents(split.validation, tokenizer)

    model_config = _model_config(config["model"])
    if model_config.vocab_size != tokenizer.vocab_size:
        raise ValueError("A configuração do vocabulário não corresponde ao tokenizador")
    model = ElysiaTransformer(model_config).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["training"]["learning_rate"]),
        weight_decay=float(config["training"].get("weight_decay", 0.01)),
    )
    history: list[dict[str, float]] = []
    step = 0
    checkpoint = Path(checkpoint_path)
    if checkpoint.exists():
        saved = torch.load(checkpoint, map_location=device, weights_only=False)
        model.load_state_dict(saved["model_state"])
        optimizer.load_state_dict(saved["optimizer_state"])
        step = int(saved["step"])
        history = list(saved.get("history", []))

    total_steps = max_steps if max_steps is not None else int(config["training"]["steps"])
    batch_size = int(config["training"]["batch_size"])
    block_size = int(config["model"]["block_size"])
    accumulation = int(config["training"].get("gradient_accumulation_steps", 1))
    clip_norm = float(config["training"].get("gradient_clip_norm", 1.0))
    eval_interval = int(config["training"].get("eval_interval", 50))
    eval_batches = int(config["training"].get("eval_batches", 5))
    checkpoint_interval = int(config["training"].get("checkpoint_interval", 100))
    generator = torch.Generator(device="cpu").manual_seed(seed + 1)
    model.train()
    started = time.perf_counter()

    while step < total_steps:
        optimizer.zero_grad(set_to_none=True)
        accumulated_loss = 0.0
        for _ in range(accumulation):
            inputs, targets = make_batch(
                train_tokens,
                batch_size=batch_size,
                block_size=block_size,
                device=device,
                generator=generator,
            )
            _, loss = model(inputs, targets)
            accumulated_loss += float(loss.item())
            (loss / accumulation).backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), clip_norm)
        optimizer.step()
        step += 1

        if step == 1 or step % eval_interval == 0 or step == total_steps:
            validation_loss = evaluate_loss(
                model,
                validation_tokens,
                batch_size=batch_size,
                block_size=block_size,
                batches=eval_batches,
                device=device,
                seed=seed + step,
            )
            history.append(
                {
                    "step": float(step),
                    "train_loss": accumulated_loss / accumulation,
                    "validation_loss": validation_loss,
                }
            )
        if step % checkpoint_interval == 0 or step == total_steps:
            save_checkpoint(
                checkpoint,
                model=model,
                optimizer=optimizer,
                step=step,
                history=history,
                config=config,
            )

    elapsed = time.perf_counter() - started
    return {
        "device": str(device),
        "gpu": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "steps": step,
        "parameters": model.num_parameters(),
        "elapsed_seconds": elapsed,
        "history": history,
        "checkpoint": str(checkpoint),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/seed-v0.1.yaml")
    parser.add_argument("--data-dir", default="data/raw")
    parser.add_argument("--checkpoint", default="learning/checkpoints/elysia-v0.1.pt")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default=None)
    parser.add_argument("--steps", type=int, default=None)
    args = parser.parse_args()
    result = train_model(
        args.config,
        data_dir=args.data_dir,
        checkpoint_path=args.checkpoint,
        device_name=args.device,
        max_steps=args.steps,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
