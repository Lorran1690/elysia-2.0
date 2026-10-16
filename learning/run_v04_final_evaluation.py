"""Freeze-audit and evaluate the ELYSIA-Seed v0.4 best checkpoint exactly once."""

from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import torch

from .dataset import TokenStore, load_corpus, split_documents
from .final_evaluation_v04 import build_final_test_windows, evaluate_final_test
from .generate_text import load_inference_checkpoint
from .train import _file_sha256, _stable_fingerprint, _verify_audit_manifest, resolve_device


ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / "learning" / "checkpoints" / "elysia-seed-v0.4-machado-extended-best.pt"
LAST_CHECKPOINT = ROOT / "learning" / "checkpoints" / "elysia-seed-v0.4-machado-extended-last.pt"
TOKENIZER = ROOT / "data" / "corpus-v0.4" / "processed" / "tokenizer-v0.4-machado.json"
CLEAN_CORPUS = ROOT / "data" / "corpus-v0.4" / "clean"
AUDIT_MANIFEST = ROOT / "data" / "corpus-v0.4" / "audit-manifest.json"
LOCAL_TEST_STORE = ROOT / "data" / "corpus-v0.4" / "processed" / "tokens-test-7fca4ee72e78.bin"
DEFAULT_OUTPUT = ROOT / "reports" / "seed-v0.4-final-evaluation.json"


def _load_checkpoint(path: Path) -> dict[str, Any]:
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    required = {"step", "model_config", "model_state", "tokenizer", "data", "architecture", "progress"}
    missing = required.difference(checkpoint)
    if missing:
        raise ValueError(f"Checkpoint incompleto; campos ausentes: {sorted(missing)}")
    return checkpoint


def _same_model_weights(first: dict[str, Any], second: dict[str, Any]) -> bool:
    first_state = first["model_state"]
    second_state = second["model_state"]
    if first_state.keys() != second_state.keys():
        return False
    return all(torch.equal(first_state[name], second_state[name]) for name in first_state)


def _canonical_split_metadata(split: Any) -> dict[str, Any]:
    """Match the repository-relative path representation frozen in the audit manifest."""
    members = {
        name: [
            {
                "sha256": document.sha256,
                "group": document.split_group,
                "path": str(document.path.relative_to(ROOT)) if document.path.is_absolute() else str(document.path),
            }
            for document in documents
        ]
        for name, documents in (("train", split.train), ("validation", split.validation), ("test", split.test))
    }
    base = {
        "seed": split.seed,
        "validation_fraction": split.validation_fraction,
        "test_fraction": split.test_fraction,
        "members": members,
    }
    return {**base, "fingerprint": _stable_fingerprint(base)}


def _open_existing_token_store(
    path: Path,
    *,
    test_document_sha256: str,
    tokenizer_metadata: dict[str, Any],
    split_metadata: dict[str, Any],
) -> TokenStore:
    metadata_path = path.with_suffix(".json")
    if not path.exists() or not metadata_path.exists():
        raise FileNotFoundError("Token store final incompleto")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    actual_sha = _file_sha256(path)
    expected_sha = metadata.get("sha256")
    if actual_sha != expected_sha:
        raise ValueError("Hash do token store final não corresponde ao manifesto local")
    if path.stat().st_size % 4:
        raise ValueError("Token store final tem tamanho inválido")
    token_count = path.stat().st_size // 4
    if token_count != metadata.get("token_count"):
        raise ValueError("Contagem do token store final diverge do manifesto local")
    if metadata.get("documents") != [test_document_sha256]:
        raise ValueError("Token store final não contém exclusivamente Quincas Borba")
    if metadata.get("tokenizer") != tokenizer_metadata:
        raise ValueError("Token store final não corresponde ao tokenizador congelado")
    if metadata.get("split", {}).get("fingerprint") != split_metadata.get("fingerprint"):
        raise ValueError("Token store final não corresponde ao split auditado")
    return TokenStore(path=path, token_count=token_count, sha256=actual_sha, metadata_path=metadata_path)


@contextmanager
def _deterministic_algorithms() -> Iterator[dict[str, bool]]:
    previous = torch.are_deterministic_algorithms_enabled()
    previous_warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    torch.use_deterministic_algorithms(True)
    try:
        yield {
            "deterministic_algorithms_enforced": True,
            "previously_enabled": previous,
            "previous_warn_only": previous_warn_only,
        }
    finally:
        torch.use_deterministic_algorithms(previous, warn_only=previous_warn_only)


def _checkpoint_audit(best: dict[str, Any], last: dict[str, Any]) -> dict[str, Any]:
    if best["step"] != 1000 or last["step"] != 1000:
        raise ValueError("A Fase 6 exige os checkpoints da etapa 1.000")
    if best["model_config"] != last["model_config"]:
        raise ValueError("Melhor e último checkpoint têm arquiteturas diferentes")
    if best["tokenizer"] != last["tokenizer"]:
        raise ValueError("Melhor e último checkpoint têm tokenizadores diferentes")
    if best["data"] != last["data"]:
        raise ValueError("Melhor e último checkpoint têm dados auditados diferentes")
    if not _same_model_weights(best, last):
        raise ValueError("Os pesos do melhor e do último checkpoint não são idênticos")
    config = best["model_config"]
    parameter_count = sum(tensor.numel() for tensor in best["model_state"].values())
    architecture_fingerprint = _stable_fingerprint(config)
    if best["architecture"].get("fingerprint") != architecture_fingerprint:
        raise ValueError("Fingerprint da arquitetura não corresponde à configuração salva")
    return {
        "checkpoint": {
            "path": str(CHECKPOINT.relative_to(ROOT)),
            "sha256": _file_sha256(CHECKPOINT),
            "bytes": CHECKPOINT.stat().st_size,
            "step": best["step"],
            "progress": best["progress"],
        },
        "last_checkpoint": {
            "path": str(LAST_CHECKPOINT.relative_to(ROOT)),
            "sha256": _file_sha256(LAST_CHECKPOINT),
            "bytes": LAST_CHECKPOINT.stat().st_size,
            "step": last["step"],
        },
        "model": {
            "config": config,
            "architecture_fingerprint": architecture_fingerprint,
            "parameter_count": parameter_count,
        },
        "tokenizer": best["tokenizer"],
        "corpus": {
            "checkpoint_data_fingerprint": best["data"].get("fingerprint"),
            "split_fingerprint": best["data"].get("split", {}).get("fingerprint"),
            "audit_manifest_sha256": best["data"].get("audit_manifest", {}).get("sha256"),
        },
        "best_and_last_weights_identical": True,
        "weight_tensor_count": len(best["model_state"]),
        "file_hashes_differ_despite_identical_model_weights": _file_sha256(CHECKPOINT) != _file_sha256(LAST_CHECKPOINT),
    }


def run_final_evaluation(*, device_name: str = "auto") -> dict[str, Any]:
    """Execute the single permitted test pass, refusing to overwrite its manifest."""
    output = DEFAULT_OUTPUT.resolve()
    if output.exists():
        raise FileExistsError(f"A avaliação final já foi registrada em {output}; uma segunda execução é bloqueada")
    if not CHECKPOINT.exists() or not LAST_CHECKPOINT.exists() or not TOKENIZER.exists():
        raise FileNotFoundError("Checkpoint ou tokenizador local obrigatório não foi encontrado")

    best = _load_checkpoint(CHECKPOINT)
    last = _load_checkpoint(LAST_CHECKPOINT)
    checkpoint_audit = _checkpoint_audit(best, last)
    audit_manifest = _verify_audit_manifest(AUDIT_MANIFEST)
    documents, corpus_stats = load_corpus(CLEAN_CORPUS)
    split = split_documents(documents, validation_fraction=0.15, test_fraction=0.15, seed=2026)
    split_metadata = _canonical_split_metadata(split)
    if split_metadata["fingerprint"] != audit_manifest.get("split_fingerprint"):
        raise ValueError("O split reconstruído diverge do manifesto auditado")
    if split_metadata["fingerprint"] != checkpoint_audit["corpus"]["split_fingerprint"]:
        raise ValueError("O split reconstruído diverge do checkpoint congelado")
    if len(split.test) != 1 or split.test[0].path.name != "quincas-borba.txt":
        raise ValueError("A partição final precisa conter exclusivamente Quincas Borba")

    device = resolve_device(device_name)
    model, tokenizer = load_inference_checkpoint(CHECKPOINT, device=device, tokenizer_path=TOKENIZER)
    if tokenizer.metadata() != checkpoint_audit["tokenizer"]:
        raise ValueError("O tokenizador local diverge do tokenizador congelado")
    test_tokens = _open_existing_token_store(
        LOCAL_TEST_STORE,
        test_document_sha256=split.test[0].sha256,
        tokenizer_metadata=tokenizer.metadata(),
        split_metadata=split_metadata,
    )
    windows = build_final_test_windows(test_tokens, block_size=model.config.block_size)

    with _deterministic_algorithms() as determinism:
        metrics = evaluate_final_test(
            model,
            test_tokens,
            windows,
            batch_size=8,
            device=device,
            text_bytes=sum(document.byte_count for document in split.test),
            special_token_ids={tokenizer.bos_id, tokenizer.eos_id},
        )

    result = {
        "schema_version": 1,
        "phase": "v0.4-phase-6-final-test-evaluation",
        "evaluation_count": 1,
        "policy": {
            "checkpoint_frozen": True,
            "weights_updated": False,
            "optimizer_loaded": False,
            "architecture_changed": False,
            "new_datasets_downloaded": False,
            "existing_test_token_store_reused_without_writing": True,
            "test_work": "Quincas Borba",
            "test_was_previously_evaluated_in_phase_4": True,
            "novel_global_test_claim_permitted": False,
            "repeat_execution_blocked_when_manifest_exists": True,
        },
        "checkpoint_audit": checkpoint_audit,
        "audit_manifest": {
            "path": str(AUDIT_MANIFEST.relative_to(ROOT)),
            "sha256": _file_sha256(AUDIT_MANIFEST),
            "fingerprint": audit_manifest.get("fingerprint"),
        },
        "test_partition": {
            "document": {
                "path": str(split.test[0].path.relative_to(ROOT)),
                "sha256": split.test[0].sha256,
                "characters": split.test[0].character_count,
                "utf8_bytes": split.test[0].byte_count,
            },
            "token_store": {
                "path": str(test_tokens.path.relative_to(ROOT)),
                "sha256": test_tokens.sha256,
                "token_count": test_tokens.token_count,
            },
            "corpus_files_seen": corpus_stats.files_seen,
        },
        "execution": {
            "device": str(device),
            "gpu_name": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
            "inference_only": True,
            "determinism": determinism,
        },
        "metrics": metrics,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_bytes(json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    temporary.replace(output)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    args = parser.parse_args()
    result = run_final_evaluation(device_name=args.device)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
