"""Bounded Phase 5 training on the audited Machado corpus, without test evaluation."""

from __future__ import annotations

import argparse
import gc
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import psutil
import torch
import yaml

from brain.bpe_tokenizer import ByteBPETokenizer
from brain.model import ElysiaTransformer
from learning.dataset import iter_document_chunks, load_corpus, make_batch, prepare_token_store, split_documents, write_source_manifest
from learning.fixed_validation import build_fixed_validation_windows, build_full_validation_windows, evaluate_fixed_validation
from learning.generate_text import load_inference_checkpoint
from learning.run_v04_pilot import PROMPTS, _generate_samples
from learning.train import (
    _build_scheduler,
    _file_sha256,
    _model_config,
    _prepare_tokenizer,
    _runtime_snapshot,
    _stable_fingerprint,
    _verify_audit_manifest,
    _write_stats,
    load_checkpoint,
    resolve_device,
    save_checkpoint,
    set_seed,
)


def _checkpoint_summary(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": _file_sha256(path),
    }


def _scheduled_steps(total_steps: int, configured: list[int]) -> tuple[int, ...]:
    expected = tuple(range(0, total_steps + 1, 100))
    actual = tuple(int(step) for step in configured)
    if actual != expected:
        raise ValueError(f"evaluation_steps precisa ser {list(expected)} para este experimento")
    return actual


def _progress_metadata(
    *,
    best_validation_loss: float,
    best_step: int,
    early_stop_reference_loss: float,
    evaluations_without_improvement: int,
    validation_fingerprint: str,
) -> dict[str, Any]:
    return {
        "best_validation_loss": best_validation_loss,
        "best_step": best_step,
        "early_stop_reference_loss": early_stop_reference_loss,
        "evaluations_without_improvement": evaluations_without_improvement,
        "validation_protocol_fingerprint": validation_fingerprint,
    }


def train_extended_experiment(
    config_path: str | Path,
    *,
    data_dir: str | Path,
    last_checkpoint_path: str | Path,
    best_checkpoint_path: str | Path,
    device_name: str | None = None,
) -> dict[str, Any]:
    """Train from random weights or resume only this experiment's last checkpoint."""
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    seed = int(config["seed"])
    training_config = config["training"]
    total_steps = int(training_config["steps"])
    if total_steps > 1_000:
        raise ValueError("A Fase 5 permite no máximo 1.000 etapas")
    max_duration_seconds = float(training_config["max_duration_seconds"])
    if max_duration_seconds > 600:
        raise ValueError("A Fase 5 permite no máximo 600 segundos")
    evaluation_steps = _scheduled_steps(total_steps, list(training_config["evaluation_steps"]))

    set_seed(seed)
    device = resolve_device(device_name or training_config.get("device", "auto"))
    audit_metadata = _verify_audit_manifest(config["data"]["audit_manifest"])
    documents, corpus_stats = load_corpus(data_dir)
    split = split_documents(
        documents,
        validation_fraction=float(config["data"].get("validation_fraction", 0.15)),
        test_fraction=float(config["data"].get("test_fraction", 0.15)),
        seed=seed,
    )
    split_metadata = split.metadata()
    if audit_metadata.get("split_fingerprint") != split_metadata["fingerprint"]:
        raise ValueError("A divisão calculada diverge do fingerprint do manifesto auditado")
    training_fingerprint = _stable_fingerprint({"split": split_metadata, "partition": "train"})
    tokenizer = _prepare_tokenizer(
        config,
        split.train,
        training_fingerprint=training_fingerprint,
        split_fingerprint=split_metadata["fingerprint"],
        work_dir=Path(data_dir).parent / "processed" / "bpe-work",
    )
    write_source_manifest(
        documents,
        Path(data_dir).parent / "SOURCES.generated.md",
        license_note="Material local autorizado para demonstração; nenhuma fonte externa foi baixada.",
        stats=corpus_stats,
    )
    processed = Path(data_dir).parent / "processed"
    _write_stats(corpus_stats, processed / "dataset-stats.json")
    token_suffix = split_metadata["fingerprint"][:12]
    train_tokens = prepare_token_store(split.train, tokenizer, processed / f"tokens-train-{token_suffix}.bin", split_metadata=split_metadata)
    validation_tokens = prepare_token_store(
        split.validation,
        tokenizer,
        processed / f"tokens-validation-{token_suffix}.bin",
        split_metadata=split_metadata,
    )

    model_values = dict(config["model"])
    model_values["vocab_size"] = tokenizer.vocab_size
    model_config = _model_config(model_values)
    if model_config.vocab_size != tokenizer.vocab_size:
        raise ValueError("A configuração do vocabulário não corresponde ao tokenizador")

    validation_config = training_config["validation"]
    fixed_windows = build_fixed_validation_windows(
        validation_tokens,
        block_size=model_config.block_size,
        window_count=int(validation_config["window_count"]),
    )
    validation_protocol = fixed_windows.metadata()
    tokenizer_metadata = tokenizer.metadata()
    data_metadata = {
        "raw_files": corpus_stats.raw_files,
        "split": split_metadata,
        "tokenizer": tokenizer_metadata,
        "token_stores": {
            "train": {"path": str(train_tokens.path), "token_count": train_tokens.token_count, "sha256": train_tokens.sha256},
            "validation": {
                "path": str(validation_tokens.path),
                "token_count": validation_tokens.token_count,
                "sha256": validation_tokens.sha256,
            },
        },
        "validation_protocol": validation_protocol,
        "test_policy": {
            "token_store_prepared": False,
            "evaluated": False,
            "purpose": "reserved for a final evaluation after freezing the configuration",
        },
        "audit_manifest": audit_metadata,
    }
    data_metadata["fingerprint"] = _stable_fingerprint(data_metadata)

    model = ElysiaTransformer(model_config).to(device)
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training_config["learning_rate"]),
        weight_decay=float(training_config.get("weight_decay", 0.01)),
    )
    scheduler = _build_scheduler(
        optimizer,
        name=str(training_config.get("lr_scheduler", "cosine")).lower(),
        warmup_steps=int(training_config.get("warmup_steps", 0)),
        total_steps=total_steps,
    )
    if scheduler is None:
        raise ValueError("A Fase 5 requer scheduler cosseno com warmup")

    last_checkpoint = Path(last_checkpoint_path)
    best_checkpoint = Path(best_checkpoint_path)
    batch_generator = torch.Generator(device="cpu").manual_seed(seed + 1)
    history: list[dict[str, Any]] = []
    step = 0
    processed_tokens = 0
    best_validation_loss = float("inf")
    best_step = -1
    early_stop_reference_loss = float("inf")
    evaluations_without_improvement = 0
    if last_checkpoint.exists():
        saved = load_checkpoint(
            last_checkpoint,
            model=model,
            optimizer=optimizer,
            device=device,
            expected_tokenizer=tokenizer_metadata,
            expected_data=data_metadata,
            batch_generator=batch_generator,
            scheduler=scheduler,
        )
        step = int(saved["step"])
        history = list(saved.get("history", []))
        progress = saved.get("progress", {})
        processed_tokens = int(progress.get("processed_tokens", 0))
        best_validation_loss = float(progress.get("best_validation_loss", best_validation_loss))
        best_step = int(progress.get("best_step", best_step))
        early_stop_reference_loss = float(progress.get("early_stop_reference_loss", early_stop_reference_loss))
        evaluations_without_improvement = int(progress.get("evaluations_without_improvement", 0))
        if progress.get("validation_protocol_fingerprint") not in (None, validation_protocol["fingerprint"]):
            raise ValueError("O checkpoint foi criado com outro protocolo de validação")

    batch_size = int(training_config["batch_size"])
    accumulation = int(training_config.get("gradient_accumulation_steps", 1))
    clip_norm = float(training_config.get("gradient_clip_norm", 1.0))
    checkpoint_interval = int(training_config.get("checkpoint_interval", 100))
    validation_batch_size = int(validation_config["batch_size"])
    early_config = training_config.get("early_stopping", {})
    early_enabled = bool(early_config.get("enabled", False))
    early_patience = int(early_config.get("patience_evaluations", 0))
    early_min_delta = float(early_config.get("min_delta", 0.0))
    if early_enabled and early_patience < 1:
        raise ValueError("early_stopping.patience_evaluations precisa ser positivo")

    resource_samples = [_runtime_snapshot(device)]
    checkpoint_saves: list[dict[str, Any]] = []
    last_saved_step = -1
    started = time.perf_counter()

    def state_metadata() -> dict[str, Any]:
        return _progress_metadata(
            best_validation_loss=best_validation_loss,
            best_step=best_step,
            early_stop_reference_loss=early_stop_reference_loss,
            evaluations_without_improvement=evaluations_without_improvement,
            validation_fingerprint=validation_protocol["fingerprint"],
        )

    def save(path: Path, role: str) -> None:
        checkpoint_started = time.perf_counter()
        save_checkpoint(
            path,
            model=model,
            optimizer=optimizer,
            step=step,
            history=history,
            config=config,
            batch_generator=batch_generator,
            tokenizer_metadata=tokenizer_metadata,
            data_metadata=data_metadata,
            scheduler=scheduler,
            processed_tokens=processed_tokens,
            progress_metadata={**state_metadata(), "checkpoint_role": role},
        )
        checkpoint_saves.append({"role": role, "step": step, "seconds": time.perf_counter() - checkpoint_started})

    def evaluate(step_train_loss: float | None) -> bool:
        nonlocal best_validation_loss, best_step, early_stop_reference_loss, evaluations_without_improvement
        measurement = evaluate_fixed_validation(
            model,
            validation_tokens,
            fixed_windows,
            batch_size=validation_batch_size,
            device=device,
        )
        entry: dict[str, Any] = {
            "step": step,
            "validation_loss": measurement["loss"],
            "validation_evaluated_tokens": measurement["evaluated_tokens"],
            "validation_window_count": measurement["window_count"],
            "validation_seconds": measurement["seconds"],
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
        }
        if step_train_loss is not None:
            entry["train_loss"] = step_train_loss
        history.append(entry)
        if measurement["loss"] < best_validation_loss:
            best_validation_loss = measurement["loss"]
            best_step = step
            save(best_checkpoint, "best_validation")
        if measurement["loss"] < early_stop_reference_loss - early_min_delta:
            early_stop_reference_loss = measurement["loss"]
            evaluations_without_improvement = 0
        else:
            evaluations_without_improvement += 1
        return early_enabled and step > 0 and evaluations_without_improvement >= early_patience

    stop_reason = "steps_limit"
    if step == 0:
        should_stop = evaluate(None)
        save(last_checkpoint, "last")
        last_saved_step = 0
        if should_stop:
            stop_reason = "early_stopping"

    while step < total_steps and stop_reason == "steps_limit":
        if max_duration_seconds > 0 and time.perf_counter() - started >= max_duration_seconds:
            stop_reason = "duration_limit"
            break
        optimizer.zero_grad(set_to_none=True)
        accumulated_loss = 0.0
        for _ in range(accumulation):
            inputs, targets = make_batch(
                train_tokens,
                batch_size=batch_size,
                block_size=model_config.block_size,
                device=device,
                generator=batch_generator,
            )
            _, loss = model(inputs, targets)
            accumulated_loss += float(loss.item())
            processed_tokens += int(inputs.numel())
            (loss / accumulation).backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), clip_norm)
        optimizer.step()
        scheduler.step()
        step += 1
        resource_samples.append(_runtime_snapshot(device))

        if step in evaluation_steps:
            if evaluate(accumulated_loss / accumulation):
                stop_reason = "early_stopping"
            save(last_checkpoint, "last")
            last_saved_step = step
        elif step % checkpoint_interval == 0:
            save(last_checkpoint, "last")
            last_saved_step = step
        if max_duration_seconds > 0 and time.perf_counter() - started >= max_duration_seconds and stop_reason == "steps_limit":
            stop_reason = "duration_limit"

    if step >= total_steps and stop_reason == "steps_limit":
        stop_reason = "steps_limit"
    if last_saved_step != step:
        save(last_checkpoint, "last")

    full_validation = None
    if bool(validation_config.get("full_evaluation", False)):
        full_windows = build_full_validation_windows(validation_tokens, block_size=model_config.block_size)
        full_validation = evaluate_fixed_validation(
            model,
            validation_tokens,
            full_windows,
            batch_size=validation_batch_size,
            device=device,
        )
        full_validation["selection_used"] = False

    elapsed = time.perf_counter() - started
    resource_samples.append(_runtime_snapshot(device))
    tokens_per_second = processed_tokens / elapsed if elapsed else 0.0
    peak_vram = max((sample.get("vram_allocated_bytes", 0) for sample in resource_samples), default=0)
    return {
        "device": str(device),
        "gpu": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "parameters": model.num_parameters(),
        "steps": step,
        "stop_reason": stop_reason,
        "elapsed_seconds": elapsed,
        "processed_tokens": processed_tokens,
        "tokens_per_second": tokens_per_second,
        "equivalent_epochs": processed_tokens / train_tokens.token_count,
        "history": history,
        "best_step": best_step,
        "best_validation_loss": best_validation_loss,
        "validation_protocol": validation_protocol,
        "full_validation": full_validation,
        "test_policy": data_metadata["test_policy"],
        "data": data_metadata,
        "resource_usage": {
            "ram_before_bytes": resource_samples[0]["ram_bytes"],
            "ram_peak_sampled_bytes": max(sample["ram_bytes"] for sample in resource_samples),
            "vram_peak_sampled_bytes": peak_vram or None,
            "gpu_peak_allocated_bytes": int(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else None,
            "cpu_count": psutil.cpu_count(logical=True),
        },
        "checkpoint_saves": checkpoint_saves,
        "best_checkpoint": _checkpoint_summary(best_checkpoint),
        "last_checkpoint": _checkpoint_summary(last_checkpoint),
    }


def _generated_portion(sample: dict[str, Any]) -> str:
    text = str(sample["generated_text"])
    prompt = str(sample["prompt"])
    return text[len(prompt) :] if text.startswith(prompt) else text


def _longest_training_match(text: str, training_text: str) -> int:
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", text.casefold())
    source = " ".join(re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", training_text.casefold()))
    for size in range(min(16, len(words)), 4, -1):
        for first in range(len(words) - size + 1):
            if " ".join(words[first : first + size]) in source:
                return size
    return 0


def analyze_generations(samples: list[dict[str, Any]], training_text: str) -> dict[str, Any]:
    per_prompt = []
    for sample in samples:
        generated = _generated_portion(sample)
        words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", generated)
        adjacent_repetitions = sum(left.casefold() == right.casefold() for left, right in zip(words, words[1:]))
        invalid = sum(character == "\ufffd" or (ord(character) < 32 and character not in "\n\r\t") for character in generated)
        per_prompt.append(
            {
                "prompt": sample["prompt"],
                "word_like_units": len(words),
                "invalid_or_control_characters": invalid,
                "adjacent_word_repetitions": adjacent_repetitions,
                "longest_exact_training_word_sequence": _longest_training_match(generated, training_text),
            }
        )
    return {
        "per_prompt": per_prompt,
        "invalid_or_control_characters": sum(item["invalid_or_control_characters"] for item in per_prompt),
        "adjacent_word_repetitions": sum(item["adjacent_word_repetitions"] for item in per_prompt),
        "maximum_exact_training_word_sequence": max(item["longest_exact_training_word_sequence"] for item in per_prompt),
        "coherence_note": "Métricas automáticas não comprovam coerência local; a leitura das quatro saídas completas continua necessária.",
    }


def run_experiment(
    config_path: str | Path,
    *,
    data_dir: str | Path,
    last_checkpoint_path: str | Path,
    best_checkpoint_path: str | Path,
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
    untrained_model = ElysiaTransformer(model_config).to(device)
    untrained_samples = _generate_samples(untrained_model, tokenizer, device=device, seed=int(config["seed"]) + 10_000)
    del untrained_model
    gc.collect()
    if device.type == "cuda":
        torch.cuda.empty_cache()

    training = train_extended_experiment(
        config_path,
        data_dir=data_dir,
        last_checkpoint_path=last_checkpoint_path,
        best_checkpoint_path=best_checkpoint_path,
        device_name=device_name,
    )
    best_model, best_tokenizer = load_inference_checkpoint(best_checkpoint_path, device=device, tokenizer_path=config["tokenizer"]["path"])
    best_samples = _generate_samples(best_model, best_tokenizer, device=device, seed=int(config["seed"]) + 10_000)
    last_model, last_tokenizer = load_inference_checkpoint(last_checkpoint_path, device=device, tokenizer_path=config["tokenizer"]["path"])
    last_samples = _generate_samples(last_model, last_tokenizer, device=device, seed=int(config["seed"]) + 10_000)

    documents, _ = load_corpus(data_dir)
    split = split_documents(
        documents,
        validation_fraction=float(config["data"].get("validation_fraction", 0.15)),
        test_fraction=float(config["data"].get("test_fraction", 0.15)),
        seed=int(config["seed"]),
    )
    training_text = "".join(chunk for document in split.train for chunk in iter_document_chunks(document))
    result = {
        "schema_version": 1,
        "phase": "v0.4-phase-5-extended-controlled-training",
        "policy": {
            "test_split_evaluated": False,
            "test_split_used_for_checkpoint_selection": False,
            "new_downloads": False,
            "architecture_increased": False,
            "previous_phase_4_checkpoint_preserved": True,
        },
        "generation_protocol": {
            "prompts": PROMPTS,
            "max_new_tokens": 80,
            "temperature": 0.8,
            "top_k": 20,
            "seed": int(config["seed"]) + 10_000,
        },
        "untrained": {"samples": untrained_samples, "analysis": analyze_generations(untrained_samples, training_text)},
        "best_validation_checkpoint": {"samples": best_samples, "analysis": analyze_generations(best_samples, training_text)},
        "last_checkpoint": {"samples": last_samples, "analysis": analyze_generations(last_samples, training_text)},
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
    parser.add_argument("--config", default="configs/seed-v0.4-machado-extended.yaml")
    parser.add_argument("--data-dir", default="data/corpus-v0.4/clean")
    parser.add_argument("--last-checkpoint", default="learning/checkpoints/elysia-seed-v0.4-machado-extended-last.pt")
    parser.add_argument("--best-checkpoint", default="learning/checkpoints/elysia-seed-v0.4-machado-extended-best.pt")
    parser.add_argument("--output", default="reports/seed-v0.4-extended-training-results.json")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default=None)
    args = parser.parse_args()
    result = run_experiment(
        args.config,
        data_dir=args.data_dir,
        last_checkpoint_path=args.last_checkpoint,
        best_checkpoint_path=args.best_checkpoint,
        output_path=args.output,
        device_name=args.device,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
