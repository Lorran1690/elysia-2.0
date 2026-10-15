"""Generate text from a locally trained E.L.Y.S.I.A. checkpoint."""

from __future__ import annotations

import argparse
from pathlib import Path

import torch

from brain.generate import generate
from brain.model import ElysiaTransformer, ModelConfig
from brain.tokenizer import ByteTokenizer
from learning.train import resolve_device


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", default="learning/checkpoints/elysia-v0.1.pt")
    parser.add_argument("--prompt", default="E.L.Y.S.I.A.")
    parser.add_argument("--tokens", type=int, default=80)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    args = parser.parse_args()

    device = resolve_device(args.device)
    checkpoint = torch.load(Path(args.checkpoint), map_location=device, weights_only=False)
    model = ElysiaTransformer(ModelConfig(**checkpoint["model_config"])).to(device)
    model.load_state_dict(checkpoint["model_state"])
    tokenizer = ByteTokenizer()
    prompt_ids = torch.tensor([tokenizer.encode(args.prompt, add_eos=False)], dtype=torch.long, device=device)
    generated_ids = generate(
        model,
        prompt_ids,
        max_new_tokens=args.tokens,
        temperature=args.temperature,
        top_k=args.top_k,
        eos_id=tokenizer.EOS_ID,
    )
    print(tokenizer.decode(generated_ids[0].tolist()))


if __name__ == "__main__":
    main()
