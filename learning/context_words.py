"""Small synthetic context-retrieval experiment; not general conversation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import torch
from torch.nn import functional as F

from brain.generate import generate
from brain.model import ElysiaTransformer, ModelConfig
from brain.tokenizer import ByteTokenizer
from learning.first_words import batch, digest
from learning.generate_text import load_inference_checkpoint

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/context-words"
TOK = ByteTokenizer()


def format_history(messages: list[dict[str, str]]) -> str:
    if not messages or messages[-1]["role"] != "user":
        raise ValueError("Histórico deve terminar com mensagem do usuário.")
    lines = []
    for i, message in enumerate(messages):
        expected = "user" if i % 2 == 0 else "assistant"
        if message["role"] != expected or not message["content"].strip():
            raise ValueError("Papéis alternados e mensagens não vazias são necessários.")
        content = message["content"]
        if "\n" in content or "\r" in content:
            raise ValueError("Este protocolo de ensaio aceita uma linha por mensagem.")
        lines.append(("Usuário: " if expected == "user" else "Elysia: ") + content)
    return "\n".join(lines) + "\nElysia: "


def as_training(records: list[dict]) -> list[dict]:
    # Reuse the audited answer-only batch function without changing its mask.
    return [{"question": format_history(r["messages"])[len("Usuário: "):-len("\nElysia: ")],
             "answer": r["answer"]} for r in records]


def respond(model: ElysiaTransformer, messages: list[dict]) -> str:
    ids = TOK.encode(format_history(messages), add_eos=False)
    if len(ids) + 64 > model.config.block_size:
        raise ValueError("Contexto cheio neste modelo experimental; inicie outra conversa.")
    x = torch.tensor([ids], dtype=torch.long)
    out = generate(model, x, max_new_tokens=64, temperature=0, eos_id=TOK.EOS_ID, use_cache=True)
    return TOK.decode(out[0, len(ids):].tolist(), errors="replace")


@torch.no_grad()
def loss_on(model: ElysiaTransformer, records: list[dict]) -> float:
    model.eval()
    total, count = 0.0, 0
    for start in range(0, len(records), 8):
        x, y = batch(as_training(records[start:start + 8]), model.config.block_size)
        logits = model(x)
        total += F.cross_entropy(logits.flatten(0, 1), y.flatten(), ignore_index=-100, reduction="sum").item()
        count += int((y != -100).sum())
    return total / count


def train(output: Path, steps: int) -> None:
    if output.exists() or not 1 <= steps <= 2000:
        raise ValueError("Escolha diretório novo e 1–2000 etapas.")
    torch.set_num_threads(2)
    torch.manual_seed(25102026)
    torch.use_deterministic_algorithms(True)
    hashes = {s: digest(DATA / f"{s}.json") for s in ("train", "validation", "test")}
    records = json.loads((DATA / "train.json").read_text(encoding="utf-8"))["records"]
    validation = json.loads((DATA / "validation.json").read_text(encoding="utf-8"))["records"]
    config = ModelConfig(block_size=384, num_layers=3, embedding_dim=128,
                         num_heads=4, feedforward_dim=512, attention_backend="sdpa")
    model = ElysiaTransformer(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
    initial = model.token_embeddings.weight.detach().clone()
    output.mkdir(parents=True)
    history = []
    best = float("inf")
    start = time.perf_counter()
    for step in range(steps + 1):
        if step % 100 == 0 or step == steps:
            value = loss_on(model, validation)
            row = {"step": step, "train_loss": loss_on(model, records), "validation_loss": value}
            history.append(row)
            print(json.dumps(row), flush=True)
            if value < best:
                best, best_step = value, step
                torch.save({"model_config": model.config_dict(), "model_state": model.state_dict(),
                            "tokenizer": TOK.metadata(), "step": step, "seed": 25102026,
                            "data_sha256": hashes, "synthetic_diagnostic_only": True}, output / "model.pt")
        if step == steps:
            break
        model.train()
        indices = torch.randint(len(records), (8,)).tolist()
        x, y = batch(as_training([records[i] for i in indices]), config.block_size)
        logits = model(x)
        loss = F.cross_entropy(logits.flatten(0, 1), y.flatten(), ignore_index=-100)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
    restored, _ = load_inference_checkpoint(output / "model.pt", device=torch.device("cpu"))
    if hashes != {s: digest(DATA / f"{s}.json") for s in hashes}:
        raise ValueError("Dados alterados durante o treino.")
    # The test is read only after checkpoint selection on validation loss.
    test = json.loads((DATA / "test.json").read_text(encoding="utf-8"))["records"]
    results = {}
    for label, items in (("train_memorization", records), ("test_unseen_combinations", test)):
        rows = []
        for item in items:
            generated = respond(restored, item["messages"])
            rows.append({**item, "generated": generated, "exact_match": generated == item["answer"]})
        results[label] = {"exact_matches": sum(r["exact_match"] for r in rows), "total": len(rows), "samples": rows}
    # Also test real conversations: intermediate replies come from the model,
    # not the gold assistant messages provided by the dataset.
    rollouts = []
    for item in test:
        messages = []
        for message in item["messages"]:
            if message["role"] == "user":
                messages.append(message)
                generated = respond(restored, messages)
                messages.append({"role": "assistant", "content": generated})
                if not generated.strip() or "\n" in generated or "\r" in generated:
                    break
        complete = len(messages) == len(item["messages"]) + 1
        rollouts.append({"id": item["id"], "expected": item["answer"], "messages": messages,
                         "complete": complete, "exact_match": complete and generated == item["answer"]})
    results["test_live_rollout"] = {"exact_matches": sum(r["exact_match"] for r in rollouts),
                                    "total": len(rollouts), "samples": rollouts}
    report = {"status": "synthetic context retrieval, not conversational competence",
              "parameters": model.num_parameters(), "steps": steps, "best_step": best_step,
              "seed": 25102026, "device": "cpu", "threads": 2, "torch": str(torch.__version__),
              "elapsed_seconds_including_evaluation": time.perf_counter() - start,
              "weights_updated": not torch.equal(initial, restored.token_embeddings.weight),
              "checkpoint_sha256": digest(output / "model.pt"), "data_sha256": hashes,
              "history": history, "results": results}
    (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: {"exact_matches": v["exact_matches"], "total": v["total"]}
                      for k, v in results.items()}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/context-words/run-001")
    parser.add_argument("--steps", type=int, default=1200)
    parser.add_argument("--chat", type=Path, help="Checkpoint para chat experimental local")
    args = parser.parse_args()
    if args.chat:
        torch.set_num_threads(2)
        model, _ = load_inference_checkpoint(args.chat, device=torch.device("cpu"))
        messages = []
        print("Ensaio sintético; pode produzir texto incorreto. /limpar reinicia, /sair encerra.")
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
                    result = respond(model, candidate)
                except ValueError as error:
                    print(error)
                    continue
                print("Elysia:", result)
                if result.strip() and "\n" not in result and "\r" not in result:
                    messages = candidate + [{"role": "assistant", "content": result}]
                else:
                    print("Resposta fora do protocolo; histórico preservado sem adicionar esta troca.")
        except (EOFError, KeyboardInterrupt):
            print("\nConversa encerrada; nenhum histórico foi salvo.")
    else:
        train(args.output, args.steps)


if __name__ == "__main__":
    main()
