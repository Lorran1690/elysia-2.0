"""Configurable training loop with safe checkpoints and RNG restoration."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path
from typing import Any

import torch
import yaml

from brain.bpe_tokenizer import ByteBPETokenizer
from brain.model import ElysiaTransformer, ModelConfig
from brain.tokenizer import ByteTokenizer

from .dataset import (
    CorpusStats,
    TokenStore,
    iter_document_chunks,
    load_corpus,
    make_batch,
    prepare_token_store,
    split_documents,
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


def capture_rng_state(batch_generator: torch.Generator | None = None) -> dict[str, Any]:
    state: dict[str, Any] = {
        "python": random.getstate(),
        "torch": torch.get_rng_state(),
    }
    if torch.cuda.is_available():
        state["cuda"] = torch.cuda.get_rng_state_all()
    if batch_generator is not None:
        state["batch_generator"] = batch_generator.get_state()
    return state


def restore_rng_state(state: dict[str, Any], batch_generator: torch.Generator | None = None) -> None:
    if "python" in state:
        random.setstate(state["python"])
    if "torch" in state:
        torch.set_rng_state(state["torch"])
    if "cuda" in state and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["cuda"])
    if batch_generator is not None and "batch_generator" in state:
        batch_generator.set_state(state["batch_generator"])


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


def _stable_fingerprint(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def save_checkpoint(
    path: str | Path,
    *,
    model: ElysiaTransformer,
    optimizer: torch.optim.Optimizer,
    step: int,
    history: list[dict[str, float]],
    config: dict[str, Any],
    batch_generator: torch.Generator | None = None,
    tokenizer_metadata: dict[str, str | int] | None = None,
    data_metadata: dict[str, Any] | None = None,
) -> None:
    checkpoint = {
        "checkpoint_version": 3,
        "step": step,
        "model_config": model.config_dict(),
        "model_state": model.state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "history": history,
        "training_config": config,
        "tokenizer": tokenizer_metadata,
        "data": data_metadata,
        "architecture": {"config": model.config_dict(), "fingerprint": _stable_fingerprint(model.config_dict())},
        "rng_state": capture_rng_state(batch_generator),
    }
    checkpoint_path = Path(path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, checkpoint_path)


def load_checkpoint(
    path: str | Path,
    *,
    model: ElysiaTransformer,
    optimizer: torch.optim.Optimizer | None = None,
    device: torch.device,
    expected_tokenizer: dict[str, str | int] | None = None,
    expected_data: dict[str, Any] | None = None,
    batch_generator: torch.Generator | None = None,
) -> dict[str, Any]:
    """Load only the tensor/primitive checkpoint format created by this project."""
    # Load serialized state on CPU first; RNG byte tensors are CPU-only inputs.
    checkpoint = torch.load(Path(path), map_location="cpu", weights_only=True)
    required = {"model_config", "model_state", "step", "history"}
    missing = required.difference(checkpoint)
    if missing:
        raise ValueError(f"Checkpoint incompleto; campos ausentes: {sorted(missing)}")
    if checkpoint["model_config"] != model.config_dict():
        raise ValueError("Configuração do checkpoint incompatível com o modelo solicitado")
    if expected_tokenizer is not None:
        saved_tokenizer = checkpoint.get("tokenizer")
        if not isinstance(saved_tokenizer, dict):
            if checkpoint.get("checkpoint_version", 1) == 1 and expected_tokenizer.get("type") == "byte_utf8" and expected_data is None:
                saved_tokenizer = expected_tokenizer
            else:
                raise ValueError("Checkpoint sem metadados do tokenizador")
        for key in ("type", "vocab_size", "fingerprint"):
            if saved_tokenizer.get(key) != expected_tokenizer.get(key):
                raise ValueError(f"Tokenizador incompatível no checkpoint: {key}")
    if expected_data is not None:
        saved_data = checkpoint.get("data")
        if not isinstance(saved_data, dict):
            raise ValueError("Checkpoint legado não pode retomar treinamento auditado")
        if saved_data.get("fingerprint") != expected_data.get("fingerprint"):
            raise ValueError("Dados ou divisão incompatíveis no checkpoint")
        architecture = checkpoint.get("architecture")
        if not isinstance(architecture, dict) or architecture.get("fingerprint") != _stable_fingerprint(model.config_dict()):
            raise ValueError("Arquitetura incompatível no checkpoint")
    model.load_state_dict(checkpoint["model_state"])
    if optimizer is not None:
        if "optimizer_state" not in checkpoint:
            raise ValueError("Checkpoint sem estado do otimizador")
        optimizer.load_state_dict(checkpoint["optimizer_state"])
    if isinstance(checkpoint.get("rng_state"), dict):
        restore_rng_state(checkpoint["rng_state"], batch_generator)
    return checkpoint


def _prepare_tokenizer(
    config: dict[str, Any], documents: list[Any], *, training_fingerprint: str, work_dir: Path
) -> ByteTokenizer | ByteBPETokenizer:
    tokenizer_config = config.get("tokenizer", {"type": "byte_utf8"})
    tokenizer_type = tokenizer_config.get("type", "byte_utf8")
    if tokenizer_type == "byte_utf8":
        return ByteTokenizer()
    if tokenizer_type != "byte_bpe":
        raise ValueError(f"Tipo de tokenizador desconhecido: {tokenizer_type}")
    path = Path(tokenizer_config["path"])
    manifest_path = path.with_suffix(".manifest.json")
    if path.exists():
        if not manifest_path.exists():
            raise ValueError("Tokenizador existente sem manifesto auditado; use um novo caminho")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("training_split_fingerprint") != training_fingerprint:
            raise ValueError("Tokenizador existente foi treinado com outro conjunto de treino")
        return ByteBPETokenizer.load(path)
    tokenizer = ByteBPETokenizer(int(tokenizer_config.get("vocab_size", 512)))
    tokenizer.train_documents(
        (iter_document_chunks(document) for document in documents),
        min_pair_frequency=int(tokenizer_config.get("min_pair_frequency", 2)),
        work_dir=work_dir,
    )
    tokenizer.save(path)
    manifest_path.write_text(
        json.dumps(
            {"schema_version": 1, "training_split_fingerprint": training_fingerprint, "tokenizer": tokenizer.metadata()},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return tokenizer


def _write_stats(stats: CorpusStats, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(stats.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    documents, corpus_stats = load_corpus(data_dir)
    split = split_documents(
        documents,
        validation_fraction=float(config["data"].get("validation_fraction", 0.15)),
        test_fraction=float(config["data"].get("test_fraction", 0.15)),
        seed=seed,
    )
    split_metadata = split.metadata()
    tokenizer = _prepare_tokenizer(
        config,
        split.train,
        training_fingerprint=_stable_fingerprint({"split": split_metadata, "partition": "train"}),
        work_dir=Path(data_dir).parent / "processed" / "bpe-work",
    )
    write_source_manifest(
        documents,
        Path(data_dir).parent / "SOURCES.generated.md",
        license_note="Material local autorizado para demonstração; nenhuma fonte externa foi baixada.",
        stats=corpus_stats,
    )
    _write_stats(corpus_stats, Path(data_dir).parent / "processed" / "dataset-stats.json")
    processed = Path(data_dir).parent / "processed"
    token_suffix = split_metadata["fingerprint"][:12]
    train_tokens = prepare_token_store(split.train, tokenizer, processed / f"tokens-train-{token_suffix}.bin", split_metadata=split_metadata)
    validation_tokens = prepare_token_store(split.validation, tokenizer, processed / f"tokens-validation-{token_suffix}.bin", split_metadata=split_metadata)
    test_tokens = prepare_token_store(split.test, tokenizer, processed / f"tokens-test-{token_suffix}.bin", split_metadata=split_metadata)

    model_values = dict(config["model"])
    if model_values.get("vocab_size") is None:
        model_values["vocab_size"] = tokenizer.vocab_size
    model_config = _model_config(model_values)
    if model_config.vocab_size != tokenizer.vocab_size:
        raise ValueError("A configuração do vocabulário não corresponde ao tokenizador")
    tokenizer_metadata = tokenizer.metadata()
    data_metadata = {
        "raw_files": corpus_stats.raw_files,
        "split": split_metadata,
        "tokenizer": tokenizer_metadata,
        "token_stores": {
            name: {"path": str(store.path), "token_count": store.token_count, "sha256": store.sha256}
            for name, store in (("train", train_tokens), ("validation", validation_tokens), ("test", test_tokens))
        },
    }
    data_metadata["fingerprint"] = _stable_fingerprint(data_metadata)
    model = ElysiaTransformer(model_config).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["training"]["learning_rate"]),
        weight_decay=float(config["training"].get("weight_decay", 0.01)),
    )
    history: list[dict[str, float]] = []
    step = 0
    checkpoint = Path(checkpoint_path)
    batch_generator = torch.Generator(device="cpu").manual_seed(seed + 1)
    if checkpoint.exists():
        saved = load_checkpoint(
            checkpoint,
            model=model,
            optimizer=optimizer,
            device=device,
            expected_tokenizer=tokenizer_metadata,
            expected_data=data_metadata,
            batch_generator=batch_generator,
        )
        step = int(saved["step"])
        history = list(saved.get("history", []))

    total_steps = max_steps if max_steps is not None else int(config["training"]["steps"])
    batch_size = int(config["training"]["batch_size"])
    block_size = model_config.block_size
    validation_block_size = min(block_size, validation_tokens.numel() - 1)
    test_block_size = min(block_size, test_tokens.numel() - 1)
    if validation_block_size < 1 or test_block_size < 1:
        raise ValueError("Os splits de validação e teste precisam conter pelo menos dois tokens")
    accumulation = int(config["training"].get("gradient_accumulation_steps", 1))
    clip_norm = float(config["training"].get("gradient_clip_norm", 1.0))
    eval_interval = int(config["training"].get("eval_interval", 50))
    eval_batches = int(config["training"].get("eval_batches", 5))
    checkpoint_interval = int(config["training"].get("checkpoint_interval", 100))
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
                generator=batch_generator,
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
                block_size=validation_block_size,
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
                batch_generator=batch_generator,
                tokenizer_metadata=tokenizer_metadata,
                data_metadata=data_metadata,
            )

    test_loss = evaluate_loss(
        model,
        test_tokens,
        batch_size=batch_size,
        block_size=test_block_size,
        batches=eval_batches,
        device=device,
        seed=seed + 999,
    )
    elapsed = time.perf_counter() - started
    return {
        "device": str(device),
        "gpu": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "steps": step,
        "parameters": model.num_parameters(),
        "elapsed_seconds": elapsed,
        "history": history,
        "test_loss": test_loss,
        "tokenizer": tokenizer_metadata,
        "corpus": corpus_stats.to_dict(),
        "checkpoint": str(checkpoint),
        "data": data_metadata,
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
