"""Two-stage, resumable CPU experiment with frozen evaluation and own weights."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import signal
import time

import torch
from torch.nn import functional as F

from brain.model import ElysiaTransformer, ModelConfig
from learning.dataset import TokenStore, make_batch
from learning.dialogue_v2_data import DEST, FastProjectTokenizer
from learning.language_pilot import encode_messages, evaluate, make_training_batch, reply
from learning.prepared_corpus import load_partition
from learning.corpus_tokenizer import sha_file
from learning.portuguese_corpus import ROOT


def atomic_save(payload, path):
    temporary = path.with_suffix(".tmp")
    torch.save(payload, temporary)
    temporary.replace(path)


def literature_store(split):
    manifest = json.loads((DEST / "manifest.json").read_text())
    info = manifest["literature_stores"][split]
    path = DEST / f"literature/tokens-{split}.bin"
    if sha_file(path) != info["sha256"] or path.stat().st_size != info["tokens"] * 4:
        raise ValueError("Literature store changed")
    return TokenStore(path, info["tokens"], info["sha256"], DEST / "manifest.json")


@torch.no_grad()
def prose_validation(model, store, windows=16):
    model.eval()
    length = 256
    maximum = store.numel() - length - 1
    offsets = [round(i * maximum / max(1, windows - 1)) for i in range(windows)]
    loss = 0.0
    for offset in offsets:
        block = store.read_slice(offset, length + 1)
        _, value = model(block[:-1].unsqueeze(0), block[1:].unsqueeze(0))
        loss += value.item()
    return {"loss": loss / windows, "targets": length * windows, "offsets": offsets}


def load_dialogues(tokenizer):
    manifest = json.loads((DEST / "manifest.json").read_text())
    result = {}
    for split in ("train", "validation", "test"):
        path = DEST / f"dialogues/{split}.json"
        if sha_file(path) != manifest["dialogue_splits"][split]["sha256"]:
            raise ValueError("Dialogue partition changed")
        result[split] = [encode_messages(tokenizer, r["messages"]) for r in json.loads(path.read_text())]
    supplement = json.loads((DEST / "dialogues/legacy-synthetic-train.json").read_text())
    result["synthetic_train"] = [encode_messages(tokenizer, r["messages"]) for r in supplement]
    old_val = json.loads((ROOT / "data/context-words/validation.json").read_text())["records"]
    result["synthetic_validation"] = [encode_messages(tokenizer, r["messages"] + [{"role": "assistant", "content": r["answer"]}]) for r in old_val]
    return result


def train(output, *, resume=False, max_seconds=2700, pause_after=None, finalize=True, protocol_override=None):
    if output.exists() and not resume:
        raise ValueError("Run already exists; explicitly resume or choose a new directory")
    if (output / "results.json").exists():
        raise ValueError("Run frozen after final evaluation")
    if not 1 <= max_seconds <= 3600:
        raise ValueError("Invalid CPU duration budget")
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    protocol = protocol_override or json.loads((DEST / "protocol.json").read_text())
    torch.manual_seed(protocol["seed"])
    tokenizer = FastProjectTokenizer()
    model = ElysiaTransformer(ModelConfig(**protocol["model"]))
    if model.config.vocab_size != tokenizer.vocab_size:
        raise ValueError("Vocabulary mismatch")
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.0005, weight_decay=0.01)
    generator = torch.Generator().manual_seed(protocol["seed"] + 1)
    source_paths = [DEST / "manifest.json", DEST / "protocol.json", DEST / "dialogues/legacy-synthetic-train.json",
                    ROOT / "data/corpus-pt-v1/manifest.json", ROOT / "data/corpus-pt-v1/tokenizer/manifest.json",
                    ROOT / "data/context-words/validation.json", ROOT / "evaluation/portuguese-v1.json"]
    settings = {"protocol": protocol, "torch": str(torch.__version__),
                "sources": {str(p.relative_to(ROOT)): sha_file(p) for p in source_paths}}
    state = {"stage": "pretrain", "step": 0, "global_step": 0, "best_loss": float("inf"),
             "best_step": 0, "history": [], "supervised_tokens": 0, "compute_seconds": 0.0}
    if resume:
        saved = torch.load(output / "last.pt", weights_only=True, map_location="cpu")
        if saved["settings"] != settings:
            raise ValueError("Resume configuration, version or source mismatch")
        model.load_state_dict(saved["model_state"])
        optimizer.load_state_dict(saved["optimizer"])
        generator.set_state(saved["batch_rng"])
        torch.set_rng_state(saved["torch_rng"])
        state = saved["progress"]
    output.mkdir(parents=True, exist_ok=resume)
    tech_train, tech_val = load_partition("train", for_training=True), load_partition("validation")
    lit_train, lit_val = literature_store("train"), literature_store("validation")
    dialogues = load_dialogues(tokenizer)
    started = time.perf_counter()
    prior_seconds = state["compute_seconds"]
    stopping = [False]
    original_handlers = {}

    def stop_after_step(signum, frame):
        stopping[0] = True

    for signum in (signal.SIGINT, signal.SIGTERM):
        original_handlers[signum] = signal.signal(signum, stop_after_step)

    def save_last():
        state["compute_seconds"] = prior_seconds + time.perf_counter() - started
        atomic_save({"model_config": model.config_dict(), "model_state": model.state_dict(), "tokenizer": tokenizer.metadata(),
                     "optimizer": optimizer.state_dict(), "progress": state, "settings": settings,
                     "torch_rng": torch.get_rng_state(), "batch_rng": generator.get_state()}, output / "last.pt")

    try:
        while state["stage"] != "complete":
            stage = state["stage"]
            limit = protocol["pretrain_steps"] if stage == "pretrain" else protocol["sft_steps"]
            if state["step"] == limit:
                if stage == "pretrain":
                    selected = torch.load(output / "pretrain-model.pt", weights_only=True, map_location="cpu")
                    model.load_state_dict(selected["model_state"])
                    optimizer = torch.optim.AdamW(model.parameters(), lr=0.0002, weight_decay=0.01)
                    state.update(stage="sft", step=0, best_loss=float("inf"), best_step=0)
                    save_last()
                    continue
                state["stage"] = "complete"
                save_last()
                break
            if stopping[0] or time.perf_counter() - started >= max_seconds or (pause_after is not None and state["global_step"] >= pause_after):
                save_last()
                print(json.dumps({"paused": True, "stage": stage, "step": state["step"], "global_step": state["global_step"]}), flush=True)
                return
            model.train()
            choose = float(torch.rand((), generator=generator))
            if stage == "pretrain":
                source = tech_train if choose < 0.7 else lit_train
                x, y = make_batch(source, batch_size=4, block_size=protocol["pretrain_context"],
                                  device=torch.device("cpu"), generator=generator)
                base_lr = 0.0005
            else:
                source = dialogues["train"] if choose < 0.8 else dialogues["synthetic_train"]
                x, y = make_training_batch(source, generator, batch_size=4,
                                          context=protocol["sft_context"], assistant_only=True)
                base_lr = 0.0002
            factor = min(1, (state["step"] + 1) / min(100, limit)) * (0.1 + 0.9 * (1 + math.cos(math.pi * state["step"] / limit)) / 2)
            for group in optimizer.param_groups:
                group["lr"] = base_lr * factor
            optimizer.zero_grad(set_to_none=True)
            logits = model(x)
            loss = F.cross_entropy(logits.flatten(0, 1), y.flatten(), ignore_index=-100)
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite loss; last complete checkpoint preserved")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1)
            optimizer.step()
            state["step"] += 1
            state["global_step"] += 1
            state["supervised_tokens"] += int((y != -100).sum())
            if state["step"] == 1 or state["step"] % 500 == 0 or state["step"] == limit:
                if stage == "pretrain":
                    a, b = prose_validation(model, tech_val), prose_validation(model, lit_val)
                    score = 0.7 * a["loss"] + 0.3 * b["loss"]
                    detail = {"technical": a, "literature": b}
                else:
                    a = evaluate(model, dialogues["validation"])["assistant"]
                    b = evaluate(model, dialogues["synthetic_validation"])["assistant"]
                    score = 0.8 * a["loss"] + 0.2 * b["loss"]
                    detail = {"fresh_dialogues": a, "synthetic_diagnostic": b}
                row = {"stage": stage, "step": state["step"], "global_step": state["global_step"],
                       "batch_loss": loss.item(), "validation_loss": score, "detail": detail}
                state["history"].append(row)
                if score < state["best_loss"]:
                    state["best_loss"], state["best_step"] = score, state["step"]
                    atomic_save({"model_config": model.config_dict(), "model_state": model.state_dict(),
                                 "tokenizer": tokenizer.metadata(), "settings": settings, "stage": stage,
                                 "step": state["step"], "validation_loss": score}, output / f"{stage}-model.pt")
                save_last()
                print(json.dumps({"stage": stage, "step": state["step"], "validation_loss": score,
                                  "best_step": state["best_step"], "seconds": state["compute_seconds"]}), flush=True)
        if not finalize:
            return
        if any(sha_file(ROOT / relative) != expected for relative, expected in settings["sources"].items()):
            raise ValueError("Source changed during run")
        selected = torch.load(output / "sft-model.pt", weights_only=True, map_location="cpu")
        model.load_state_dict(selected["model_state"])
        cases = json.loads((ROOT / "evaluation/portuguese-v1.json").read_text())["cases"]
        generated, live = [], []
        for case in cases:
            try:
                text = reply(model, tokenizer, case["messages"], tokens=128)
                error = None
            except ValueError as exc:
                text, error = "", str(exc)
            generated.append({**case, "generated": text, "error": error, "semantic_score": None})
            if len(case["messages"]) > 1:
                history = []
                error = None
                for message in case["messages"]:
                    if message["role"] != "user":
                        continue
                    history.append(message)
                    try:
                        text = reply(model, tokenizer, history, tokens=128)
                        if not text.strip():
                            raise ValueError("Empty model response")
                        history.append({"role": "assistant", "content": text})
                    except ValueError as exc:
                        error = str(exc)
                        break
                live.append({"id": case["id"], "messages": history, "error": error, "semantic_score": None})
        report = {"settings": settings, "progress": state, "parameters": model.num_parameters(),
                  "selected_sft_step": selected["step"], "selected_sft_validation_loss": selected["validation_loss"],
                  "final_test_evaluation_count": 1, "fresh_dialogue_test": evaluate(model, dialogues["test"]),
                  "generation_cases": generated, "live_rollouts": live,
                  "checkpoint_sha256": sha_file(output / "sft-model.pt"), "resume_sha256": sha_file(output / "last.pt"),
                  "milestone_result": "requires semantic review; no automatic success inference"}
        (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"completed": True, "static_cases": len(generated), "live_cases": len(live)}), flush=True)
    finally:
        for signum, handler in original_handlers.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/neural-dialogue-v2/run-001")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-seconds", type=int, default=2700)
    parser.add_argument("--pause-after", type=int)
    args = parser.parse_args()
    train(args.output, resume=args.resume, max_seconds=args.max_seconds, pause_after=args.pause_after)
