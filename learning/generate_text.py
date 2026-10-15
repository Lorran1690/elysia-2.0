"""Generate text from a locally trained E.L.Y.S.I.A. checkpoint."""

from __future__ import annotations

import argparse
from pathlib import Path

import torch

from brain.generate import generate
from brain.bpe_tokenizer import ByteBPETokenizer
from brain.model import ElysiaTransformer, ModelConfig
from brain.tokenizer import ByteTokenizer
from learning.train import resolve_device


def load_inference_checkpoint(
    checkpoint_path: str | Path,
    *,
    device: torch.device,
    tokenizer_path: str | Path | None = None,
) -> tuple[ElysiaTransformer, ByteTokenizer | ByteBPETokenizer]:
    """Load only project checkpoints made of tensors and primitive metadata."""
    checkpoint = torch.load(Path(checkpoint_path), map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict) or not {"model_config", "model_state"}.issubset(checkpoint):
        raise ValueError("Checkpoint de inferência incompleto ou inválido")
    model_config = checkpoint["model_config"]
    if not isinstance(model_config, dict):
        raise ValueError("Configuração do modelo inválida no checkpoint")
    model = ElysiaTransformer(ModelConfig(**model_config)).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    tokenizer_info = checkpoint.get("tokenizer") or {"type": "byte_utf8"}
    if tokenizer_info.get("type") == "byte_bpe":
        path = Path(tokenizer_path or "data/processed/tokenizer-v0.2-audited.json")
        tokenizer = ByteBPETokenizer.load(path)
        for key in ("type", "vocab_size", "fingerprint"):
            if tokenizer.metadata().get(key) != tokenizer_info.get(key):
                raise ValueError(f"O vocabulário local não corresponde ao checkpoint: {key}")
    elif tokenizer_info.get("type") == "byte_utf8":
        tokenizer = ByteTokenizer()
        if tokenizer_info.get("fingerprint") not in (None, tokenizer.metadata()["fingerprint"]):
            raise ValueError("O tokenizador UTF-8 não corresponde ao checkpoint")
    else:
        raise ValueError("Tipo de tokenizador desconhecido no checkpoint")
    return model, tokenizer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", default="learning/checkpoints/elysia-v0.1.pt")
    parser.add_argument("--prompt", default="E.L.Y.S.I.A.")
    parser.add_argument("--tokens", type=int, default=80)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--tokenizer-path", default=None)
    args = parser.parse_args()

    device = resolve_device(args.device)
    model, tokenizer = load_inference_checkpoint(args.checkpoint, device=device, tokenizer_path=args.tokenizer_path)
    prompt_ids = torch.tensor([tokenizer.encode(args.prompt, add_eos=False)], dtype=torch.long, device=device)
    eos_id = tokenizer.eos_id
    generated_ids = generate(
        model,
        prompt_ids,
        max_new_tokens=args.tokens,
        temperature=args.temperature,
        top_k=args.top_k,
        eos_id=eos_id,
    )
    print(tokenizer.decode(generated_ids[0].tolist(), errors="replace"))


if __name__ == "__main__":
    main()
