"""Bounded language pretraining and answer-only tuning on audited OASST1 data."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time

import psutil
import torch
from torch.nn import functional as F

from brain.bpe_tokenizer import ByteBPETokenizer
from brain.generate import generate
from brain.model import ElysiaTransformer, ModelConfig
from learning.generate_text import load_inference_checkpoint
from learning.prepare_oasst_pilot import DEST, sha

ROOT = Path(__file__).resolve().parents[1]


def encode_messages(tokenizer, messages: list[dict], *, for_reply=False):
    """Use identical role/content token boundaries during training and inference."""
    ids, labels = [tokenizer.bos_id], [-100]
    for i, message in enumerate(messages):
        role = "user" if i % 2 == 0 else "assistant"
        if message["role"] != role or not message["content"].strip():
            raise ValueError("Expected alternating nonempty user/assistant messages")
        prefix = "Usuário: " if role == "user" else "Elysia: "
        prefix_ids = tokenizer.encode(prefix, add_bos=False, add_eos=False)
        # Normalize internal line breaks so they cannot create transcript role lines.
        text = " ".join(message["content"].split())
        content = tokenizer.encode(text, add_bos=False, add_eos=False)
        ending = [tokenizer.eos_id] if role == "assistant" else tokenizer.encode("\n", add_bos=False, add_eos=False)
        ids.extend(prefix_ids + content + ending)
        labels.extend([-100] * len(prefix_ids) + (content + ending if role == "assistant" else [-100] * (len(content) + len(ending))))
    if for_reply:
        if not messages or messages[-1]["role"] != "user":
            raise ValueError("Reply requires a final user message")
        prefix_ids = tokenizer.encode("Elysia: ", add_bos=False, add_eos=False)
        ids.extend(prefix_ids)
        labels.extend([-100] * len(prefix_ids))
    return ids, labels


def make_training_batch(documents, generator, *, batch_size, context, assistant_only):
    x = torch.full((batch_size, context), 0, dtype=torch.long)
    y = torch.full_like(x, -100)
    for i in range(batch_size):
        # Reject windows without supervised targets in answer-only mode.
        for _ in range(1000):
            ids, labels = documents[int(torch.randint(len(documents), (1,), generator=generator))]
            start = int(torch.randint(max(1, len(ids) - context), (1,), generator=generator))
            stop = min(start + context + 1, len(ids))
            targets = labels[start + 1:stop] if assistant_only else ids[start + 1:stop]
            if any(t != -100 for t in targets):
                break
        else:
            raise ValueError("No supervised targets available")
        inputs = ids[start:stop - 1]
        x[i, :len(inputs)] = torch.tensor(inputs)
        y[i, :len(targets)] = torch.tensor(targets)
    return x, y


@torch.no_grad()
def evaluate(model, documents):
    """Token-weighted full pass, scoring every next-token target exactly once."""
    model.eval()
    totals = {"all": [0.0, 0], "assistant": [0.0, 0]}
    for ids, labels in documents:
        for start in range(0, len(ids) - 1, model.config.block_size):
            stop = min(start + model.config.block_size + 1, len(ids))
            x = torch.tensor([ids[start:stop - 1]])
            logits = model(x).flatten(0, 1)
            for name, targets in (("all", ids[start + 1:stop]), ("assistant", labels[start + 1:stop])):
                y = torch.tensor(targets)
                totals[name][0] += F.cross_entropy(logits, y, ignore_index=-100, reduction="sum").item()
                totals[name][1] += int((y != -100).sum())
    return {name: {"loss": total / count, "perplexity": math.exp(min(50, total / count)), "targets": count}
            for name, (total, count) in totals.items()}


def reply(model, tokenizer, messages, *, tokens=96, temperature=0.0):
    ids, _ = encode_messages(tokenizer, messages, for_reply=True)
    if len(ids) > model.config.block_size - tokens:
        raise ValueError("Contexto cheio neste piloto; use /limpar ou uma pergunta menor.")
    output = generate(model, torch.tensor([ids]), max_new_tokens=tokens, temperature=temperature,
                      top_k=20, eos_id=tokenizer.eos_id, use_cache=True)
    return tokenizer.decode(output[0, len(ids):].tolist(), errors="replace")


def run(output: Path, *, steps=1800, sft_steps=400, seconds=600, resume=False):
    if not 1 <= steps <= 4000 or not 0 <= sft_steps < steps or not 1 <= seconds <= 1800:
        raise ValueError("Run budget outside supported bounds")
    if output.exists() and not resume:
        raise ValueError("Choose a new output directory or explicitly resume")
    if (output / "results.json").exists():
        raise ValueError("Final evaluation already exists; this run is frozen")
    torch.set_num_threads(2)
    torch.manual_seed(25102027)
    torch.use_deterministic_algorithms(True)
    output.mkdir(parents=True, exist_ok=resume)
    hashes = {s: sha(DEST / f"{s}.json") for s in ("train", "validation", "test")}
    manifest = json.loads((DEST / "manifest.json").read_text(encoding="utf-8"))
    if any(hashes[s] != manifest["splits"][s]["sha256"] for s in hashes):
        raise ValueError("Corpus differs from audited split manifest")
    specification = ROOT / "data/language-pilot/open-evaluation.json"
    specification_hash = sha(specification)
    training = json.loads((DEST / "train.json").read_text(encoding="utf-8"))
    validation = json.loads((DEST / "validation.json").read_text(encoding="utf-8"))
    tokenizer_path = output / "tokenizer.json"
    if resume:
        tokenizer = ByteBPETokenizer.load(tokenizer_path)
    else:
        unique = sorted({" ".join(m["content"].split()) for r in training for m in r["messages"]})
        print(json.dumps({"phase": "tokenizer_train_only", "unique_messages": len(unique)}), flush=True)
        tokenizer = ByteBPETokenizer(1024).train(unique, min_pair_frequency=3)
        tokenizer.save(tokenizer_path)
    documents = [encode_messages(tokenizer, r["messages"]) for r in training]
    val_documents = [encode_messages(tokenizer, r["messages"]) for r in validation]
    config = ModelConfig(vocab_size=tokenizer.vocab_size, block_size=256, num_layers=4,
                         embedding_dim=192, num_heads=4, feedforward_dim=768,
                         positional_embedding="rope", norm_type="rmsnorm",
                         feedforward_type="swiglu", attention_backend="sdpa")
    model = ElysiaTransformer(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.0005, weight_decay=0.01)
    generator = torch.Generator().manual_seed(25102028)
    settings = {"steps": steps, "sft_steps": sft_steps, "batch_size": 4, "training_context": 128,
                "data_sha256": hashes, "open_evaluation_sha256": specification_hash,
                "tokenizer": tokenizer.metadata(), "model_config": model.config_dict(),
                "seed": 25102027, "learning_rate": 0.0005, "weight_decay": 0.01}
    step, best_step, best, history = 0, 0, float("inf"), []
    total_tokens = 0
    if resume:
        saved = torch.load(output / "last.pt", map_location="cpu", weights_only=True)
        if saved["settings"] != settings:
            raise ValueError("Resume config/corpus/tokenizer/evaluation mismatch")
        model.load_state_dict(saved["model_state"])
        optimizer.load_state_dict(saved["optimizer"])
        generator.set_state(saved["batch_rng"])
        torch.set_rng_state(saved["torch_rng"])
        step, best_step, best = saved["step"], saved["best_step"], saved["best_loss"]
        history, total_tokens = saved["history"], saved["total_tokens"]
    baseline = evaluate(model, val_documents) if not resume else saved["baseline_validation"]
    initial_weight = model.token_embeddings.weight.detach().clone()
    start = time.perf_counter()
    stop_reason = "steps_limit"
    process = psutil.Process()
    peak_ram = process.memory_info().rss

    def save_last():
        payload = {"settings": settings, "model_config": model.config_dict(), "model_state": model.state_dict(),
                   "tokenizer": tokenizer.metadata(), "optimizer": optimizer.state_dict(), "step": step,
                   "best_step": best_step, "best_loss": best, "history": history, "total_tokens": total_tokens,
                   "batch_rng": generator.get_state(), "torch_rng": torch.get_rng_state(),
                   "baseline_validation": baseline}
        temporary = output / "last.tmp"
        torch.save(payload, temporary)
        temporary.replace(output / "last.pt")

    try:
        while step < steps:
            if time.perf_counter() - start >= seconds:
                stop_reason = "duration_limit"
                break
            assistant_only = step >= steps - sft_steps
            model.train()
            x, y = make_training_batch(documents, generator, batch_size=4, context=128, assistant_only=assistant_only)
            lr = 0.0005 * min(1, (step + 1) / 100) * (0.1 + 0.9 * (1 + math.cos(math.pi * step / steps)) / 2)
            for group in optimizer.param_groups:
                group["lr"] = lr
            logits = model(x)
            loss = F.cross_entropy(logits.flatten(0, 1), y.flatten(), ignore_index=-100)
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite loss; previous checkpoint remains available")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1)
            optimizer.step()
            step += 1
            total_tokens += int((y != -100).sum())
            peak_ram = max(peak_ram, process.memory_info().rss)
            if step == 1 or step % 200 == 0 or step == steps:
                metrics = evaluate(model, val_documents)
                row = {"step": step, "phase": "answer_only" if assistant_only else "language",
                       "batch_loss": loss.item(), "validation": metrics}
                history.append(row)
                if metrics["assistant"]["loss"] < best:
                    best_step, best = step, metrics["assistant"]["loss"]
                    torch.save({"model_config": model.config_dict(), "model_state": model.state_dict(),
                                "tokenizer": tokenizer.metadata(), "step": step, "settings": settings}, output / "model.tmp")
                    (output / "model.tmp").replace(output / "model.pt")
                save_last()
                print(json.dumps(row), flush=True)
    except KeyboardInterrupt:
        save_last()
        print("Interrupted; last.pt saved; no test evaluation performed.", flush=True)
        return
    save_last()
    if stop_reason != "steps_limit":
        print("Budget reached; resumable last.pt saved; no test evaluation performed.", flush=True)
        return
    if hashes != {s: sha(DEST / f"{s}.json") for s in hashes} or sha(specification) != specification_hash:
        raise ValueError("Data or evaluation changed during training")
    if (output / "results.json").exists():
        raise ValueError("Final test already evaluated; do not repeat it")
    selected, _ = load_inference_checkpoint(output / "model.pt", device=torch.device("cpu"), tokenizer_path=tokenizer_path)
    test = json.loads((DEST / "test.json").read_text(encoding="utf-8"))
    test_metrics = evaluate(selected, [encode_messages(tokenizer, r["messages"]) for r in test])
    probes = json.loads(specification.read_text(encoding="utf-8"))
    samples = []
    for item in probes["cases"]:
        samples.append({**item, "generated": reply(selected, tokenizer, item["messages"]),
                        "automatic_pass": None, "review_status": "requires semantic review; no keyword scoring"})
    report = {"status": "small licensed-language pilot, not a conversational assistant", "settings": settings,
              "parameters": model.num_parameters(), "torch": str(torch.__version__), "device": "cpu",
              "threads": 2, "steps_completed": step, "best_step": best_step,
              "supervised_tokens_processed": total_tokens, "baseline_validation": baseline,
              "history": history, "test": test_metrics, "test_evaluation_count": 1,
              "generation_cases": samples, "weights_updated_in_current_session": not torch.equal(initial_weight, model.token_embeddings.weight),
              "checkpoint_sha256": sha(output / "model.pt"), "resume_sha256": sha(output / "last.pt"),
              "tokenizer_sha256": sha(tokenizer_path), "elapsed_seconds_excluding_tokenizer": time.perf_counter() - start,
              "peak_sampled_process_ram_bytes": peak_ram,
              "tokens_per_partition": {"train": sum(len(x) for x, _ in documents), "validation": sum(len(x) for x, _ in val_documents)}}
    (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"best_step": best_step, "test": test_metrics, "elapsed": report["elapsed_seconds_excluding_tokenizer"]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/language-pilot/run-001")
    parser.add_argument("--steps", type=int, default=1800)
    parser.add_argument("--sft-steps", type=int, default=400)
    parser.add_argument("--seconds", type=int, default=600)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--chat", action="store_true")
    args = parser.parse_args()
    if args.chat:
        torch.set_num_threads(2)
        tokenizer_path = args.output / "tokenizer.json"
        model, tokenizer = load_inference_checkpoint(args.output / "model.pt", device=torch.device("cpu"), tokenizer_path=tokenizer_path)
        messages = []
        print("Piloto sem competência conversacional comprovada. /limpar reinicia; /sair encerra.")
        try:
            while True:
                text = input("Você: ").strip()
                if text == "/sair":
                    break
                if text == "/limpar":
                    messages = []
                    continue
                if not text:
                    continue
                candidate = messages + [{"role": "user", "content": text}]
                try:
                    result = reply(model, tokenizer, candidate)
                except ValueError as error:
                    print(error)
                    continue
                print("Elysia:", result)
                if result.strip():
                    messages = candidate + [{"role": "assistant", "content": result}]
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrado, sem gravar o histórico.")
    else:
        run(args.output, steps=args.steps, sft_steps=args.sft_steps, seconds=args.seconds, resume=args.resume)


if __name__ == "__main__":
    main()
