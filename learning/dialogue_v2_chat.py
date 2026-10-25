"""Local experimental chat using only the project's dialogue-v2 checkpoint."""
from __future__ import annotations

import argparse
from pathlib import Path

import torch

from learning.generate_text import load_inference_checkpoint
from learning.language_pilot import reply
from learning.portuguese_corpus import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, default=ROOT / "artifacts/neural-dialogue-v2/run-001/sft-model.pt")
    parser.add_argument("--ask")
    parser.add_argument("--temperature", type=float, default=0)
    args = parser.parse_args()
    if not 0 <= args.temperature <= 1.5:
        parser.error("Temperatura deve ficar entre 0 e 1,5")
    torch.set_num_threads(2)
    metadata = torch.load(args.checkpoint, weights_only=True, map_location="cpu")
    if metadata.get("stage") != "sft":
        raise ValueError("Este comando requer checkpoint de diálogo, não um marco de pré-treino")
    model, tokenizer = load_inference_checkpoint(args.checkpoint, device=torch.device("cpu"),
                                                tokenizer_path=ROOT / "data/corpus-pt-v1/tokenizer/elysia-bpe.json")
    if args.ask is not None:
        print(reply(model, tokenizer, [{"role": "user", "content": args.ask}], tokens=128, temperature=args.temperature))
        return
    messages = []
    print("Elysia experimental; respostas podem ser incorretas. /limpar reinicia; /sair encerra.")
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
                response = reply(model, tokenizer, candidate, tokens=128, temperature=args.temperature)
            except ValueError as exc:
                print(exc)
                continue
            print("Elysia:", response)
            if response.strip():
                messages = candidate + [{"role": "assistant", "content": response}]
            else:
                print("Resposta vazia; esta troca não foi adicionada ao histórico.")
    except (KeyboardInterrupt, EOFError):
        print("\nEncerrado. Nenhum histórico foi gravado.")


if __name__ == "__main__":
    main()
