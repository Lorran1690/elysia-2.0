"""Bounded synthetic first-words experiment, never a conversational benchmark."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import torch
from torch.nn import functional as F

from brain.generate import generate
from brain.model import ElysiaTransformer, ModelConfig
from brain.tokenizer import ByteTokenizer
from learning.generate_text import load_inference_checkpoint

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/first-words/train.json"
TEST = ROOT / "data/first-words/heldout.json"
TOKENIZER = ByteTokenizer()


def prompt(text: str) -> str:
    return f"Usuário: {text}\nElysia: "


def batch(records: list[dict], context: int) -> tuple[torch.Tensor, torch.Tensor]:
    """Supervise answer bytes and EOS only; exclude prompts and padding."""
    encoded = []
    for record in records:
        prefix = TOKENIZER.encode(prompt(record["question"]), add_eos=False)
        answer = TOKENIZER.encode(record["answer"], add_bos=False)
        ids = prefix + answer
        if len(ids) - 1 > context:
            raise ValueError("Exemplo excede o contexto; não será truncado.")
        labels = [-100] * (len(prefix) - 1) + answer
        encoded.append((ids[:-1], labels))
    length = max(len(ids) for ids, _ in encoded)
    x = torch.full((len(records), length), TOKENIZER.PAD_ID, dtype=torch.long)
    y = torch.full_like(x, -100)
    for i, (ids, labels) in enumerate(encoded):
        x[i, :len(ids)] = torch.tensor(ids)
        y[i, :len(labels)] = torch.tensor(labels)
    return x, y


def answer(model: ElysiaTransformer, question: str) -> str:
    ids = TOKENIZER.encode(prompt(question), add_eos=False)
    if len(ids) + 96 > model.config.block_size:
        raise ValueError("Pergunta longa demais para este ensaio de contexto curto.")
    x = torch.tensor([ids], device=next(model.parameters()).device)
    output = generate(model, x, max_new_tokens=96, temperature=0,
                      eos_id=TOKENIZER.EOS_ID, use_cache=True)
    return TOKENIZER.decode(output[0, len(ids):].tolist(), errors="replace")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output: Path, steps: int, seed: int, threads: int) -> None:
    if output.exists():
        raise ValueError("Diretório já existe; escolha outro para preservar os resultados.")
    if not 1 <= steps <= 2000 or not 1 <= threads <= 8:
        raise ValueError("Limites: 1–2000 etapas e 1–8 threads.")
    records = json.loads(DATA.read_text(encoding="utf-8"))["records"]
    torch.set_num_threads(threads)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    config = ModelConfig(block_size=192, num_layers=2, embedding_dim=96,
                         num_heads=4, feedforward_dim=384, attention_backend="sdpa")
    model = ElysiaTransformer(config)
    initial = model.token_embeddings.weight.detach().clone()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.002, weight_decay=0.01)
    x, y = batch(records, config.block_size)
    output.mkdir(parents=True)
    # Freeze evaluation identities before training; evaluation contents are read only afterwards.
    test_hash = digest(TEST)
    history = []
    start = time.perf_counter()
    for step in range(steps + 1):
        model.train()
        logits = model(x)
        loss = F.cross_entropy(logits.flatten(0, 1), y.flatten(), ignore_index=-100)
        if step % 100 == 0 or step == steps:
            row = {"step": step, "answer_train_loss": loss.item()}
            history.append(row)
            print(json.dumps(row), flush=True)
        if step == steps:
            break
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
    checkpoint = output / "model.pt"
    torch.save({"model_config": model.config_dict(), "model_state": model.state_dict(),
                "tokenizer": TOKENIZER.metadata(), "step": steps, "seed": seed,
                "train_sha256": digest(DATA), "synthetic_diagnostic_only": True}, checkpoint)
    restored, _ = load_inference_checkpoint(checkpoint, device=torch.device("cpu"))
    assert all(torch.equal(a, b) for a, b in zip(model.parameters(), restored.parameters()))
    if digest(TEST) != test_hash:
        raise ValueError("Avaliação alterada durante o treino.")
    heldout = json.loads(TEST.read_text(encoding="utf-8"))["records"]
    if {r["question"] for r in records} & {r["question"] for r in heldout}:
        raise ValueError("Pergunta de avaliação repetida no treino.")
    results = {}
    for label, items in (("seen_memorization", records), ("heldout_paraphrases", heldout)):
        rows = []
        for item in items:
            generated = answer(restored, item["question"])
            rows.append({**item, "generated": generated, "exact_match": generated == item["answer"]})
        results[label] = {"exact_matches": sum(r["exact_match"] for r in rows),
                          "total": len(rows), "samples": rows}
    report = {"status": "synthetic diagnostic; not conversational competence",
              "seed": seed, "steps": steps, "threads": threads, "device": "cpu",
              "torch": str(torch.__version__), "parameters": model.num_parameters(),
              "elapsed_seconds_including_evaluation": time.perf_counter() - start,
              "weights_updated": not torch.equal(initial, model.token_embeddings.weight),
              "checkpoint_sha256": digest(checkpoint), "train_sha256": digest(DATA),
              "heldout_sha256": test_hash, "history": history, "results": results}
    (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: {"exact_matches": v["exact_matches"], "total": v["total"]}
                      for k, v in results.items()}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/first-words/run-001")
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=24102026)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--ask")
    args = parser.parse_args()
    if args.ask is not None:
        if args.checkpoint is None:
            parser.error("--ask exige --checkpoint")
        torch.set_num_threads(args.threads)
        model, _ = load_inference_checkpoint(args.checkpoint, device=torch.device("cpu"))
        print(answer(model, args.ask))
    else:
        run(args.output, args.steps, args.seed, args.threads)


if __name__ == "__main__":
    main()
