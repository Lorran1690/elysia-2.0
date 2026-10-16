"""Validate the research-only source manifest for ELYSIA-Seed v0.5.

This module deliberately validates metadata only. It never downloads a source,
creates a token store, trains a tokenizer, or touches model weights.
"""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any


STATUS_VALUES = frozenset({"approved", "pending", "rejected"})
RISK_LEVELS = frozenset({"low", "medium", "high"})
REQUIRED_CANDIDATE_FIELDS = frozenset(
    {
        "id",
        "source_family",
        "title",
        "authors",
        "responsible_institution",
        "source_url",
        "metadata_evidence_url",
        "publication_or_edition",
        "language_variant",
        "content_type",
        "license",
        "attribution_obligations",
        "reuse_distribution_conditions",
        "estimated_words",
        "estimated_tokens",
        "privacy_risk",
        "duplication_risk",
        "synthetic_content_risk",
        "text_collected",
        "content_hash",
        "content_hash_status",
        "status",
        "status_rationale",
        "future_collection_requirements",
    }
)
FORBIDDEN_CONTENT_FIELDS = frozenset(
    {
        "full_text",
        "raw_text",
        "clean_text",
        "text_content",
        "token_ids",
        "token_store",
        "downloaded_file",
        "original_path",
        "clean_path",
        "processed_path",
    }
)
V04_EXPECTED = {
    "best_checkpoint_sha256": "f8e2ec643cd963ebfd47c9c7b6d87a8a5b79af9c0fb7f8e1e75744106e1943d3",
    "last_checkpoint_sha256": "0585ed247ccc7d8259390e250393b27b43a429368424f9d6de71c6b02fbc15c1",
    "architecture_fingerprint": "1ec4192799a32ee7a0320ccf71a9bfe1f3f708f2e5c9193faa294a3b1e776ae7",
    "tokenizer_fingerprint": "d7b27519afcc8a19deb57691617e7a1478893bbf3d71768508a998ca48d887a8",
    "data_fingerprint": "eb4d6655b08d35a51e91779ff72c15d8f904c6b1fd64a4321d3ed87ea484ca06",
    "split_fingerprint": "7fca4ee72e780084b1a364cf80424e9d0d3a1cb2ad9cacc3c257c8002282e757",
}


class ManifestValidationError(ValueError):
    """Raised when a research-only manifest violates its safety contract."""


def load_manifest(path: str | Path) -> dict[str, Any]:
    """Load a UTF-8 JSON candidate manifest without resolving any source URL."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ManifestValidationError("O manifesto raiz precisa ser um objeto JSON")
    return value


def _require_string(mapping: dict[str, Any], key: str, location: str) -> None:
    if not isinstance(mapping.get(key), str) or not mapping[key].strip():
        raise ManifestValidationError(f"{location}.{key} precisa ser uma string nao vazia")


def _require_https(mapping: dict[str, Any], key: str, location: str) -> None:
    _require_string(mapping, key, location)
    if not mapping[key].startswith("https://"):
        raise ManifestValidationError(f"{location}.{key} precisa usar HTTPS")


def _validate_estimate(value: Any, location: str) -> None:
    if not isinstance(value, dict):
        raise ManifestValidationError(f"{location} precisa ser um objeto")
    for key in ("minimum", "maximum"):
        if not isinstance(value.get(key), int) or value[key] < 0:
            raise ManifestValidationError(f"{location}.{key} precisa ser inteiro nao negativo")
    if value["minimum"] > value["maximum"]:
        raise ManifestValidationError(f"{location} tem faixa invertida")
    _require_string(value, "basis", location)


def _validate_risk(value: Any, location: str) -> None:
    if not isinstance(value, dict):
        raise ManifestValidationError(f"{location} precisa ser um objeto")
    if value.get("level") not in RISK_LEVELS:
        raise ManifestValidationError(f"{location}.level precisa ser low, medium ou high")
    _require_string(value, "notes", location)


def _find_forbidden_content_fields(value: Any, location: str = "manifest") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}"
            if key in FORBIDDEN_CONTENT_FIELDS:
                findings.append(child_location)
            findings.extend(_find_forbidden_content_fields(child, child_location))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_find_forbidden_content_fields(child, f"{location}[{index}]"))
    return findings


def _approved_license(name: str) -> bool:
    normalized = name.strip().lower()
    return normalized == "cc by 4.0" or normalized == "cc0 1.0"


def _validate_candidate(candidate: Any, index: int, seen_ids: set[str]) -> None:
    location = f"candidates[{index}]"
    if not isinstance(candidate, dict):
        raise ManifestValidationError(f"{location} precisa ser um objeto")
    missing = sorted(REQUIRED_CANDIDATE_FIELDS - set(candidate))
    if missing:
        raise ManifestValidationError(f"{location} nao possui campos obrigatorios: {', '.join(missing)}")
    for key in (
        "id",
        "source_family",
        "title",
        "responsible_institution",
        "publication_or_edition",
        "language_variant",
        "content_type",
        "attribution_obligations",
        "reuse_distribution_conditions",
        "content_hash_status",
        "status_rationale",
    ):
        _require_string(candidate, key, location)
    if candidate["id"] in seen_ids:
        raise ManifestValidationError(f"{location}.id esta duplicado: {candidate['id']}")
    seen_ids.add(candidate["id"])
    if not isinstance(candidate["authors"], list) or not candidate["authors"] or not all(
        isinstance(author, str) and author.strip() for author in candidate["authors"]
    ):
        raise ManifestValidationError(f"{location}.authors precisa ser uma lista nao vazia de strings")
    _require_https(candidate, "source_url", location)
    _require_https(candidate, "metadata_evidence_url", location)
    license_info = candidate["license"]
    if not isinstance(license_info, dict):
        raise ManifestValidationError(f"{location}.license precisa ser um objeto")
    for key in ("name", "evidence", "verification_level"):
        _require_string(license_info, key, f"{location}.license")
    _require_https(license_info, "evidence_url", f"{location}.license")
    _validate_estimate(candidate["estimated_words"], f"{location}.estimated_words")
    _validate_estimate(candidate["estimated_tokens"], f"{location}.estimated_tokens")
    for risk_name in ("privacy_risk", "duplication_risk", "synthetic_content_risk"):
        _validate_risk(candidate[risk_name], f"{location}.{risk_name}")
    if candidate["text_collected"] is not False:
        raise ManifestValidationError(f"{location}.text_collected precisa ser false nesta fase")
    if candidate["content_hash"] is not None:
        raise ManifestValidationError(f"{location}.content_hash precisa ser null sem download autorizado")
    if candidate["status"] not in STATUS_VALUES:
        raise ManifestValidationError(f"{location}.status nao e reconhecido")
    if candidate["status"] == "approved" and not _approved_license(license_info["name"]):
        raise ManifestValidationError(f"{location} aprovado precisa ter CC BY 4.0 ou CC0 1.0 explicito")
    requirements = candidate["future_collection_requirements"]
    if not isinstance(requirements, list) or not requirements or not all(
        isinstance(item, str) and item.strip() for item in requirements
    ):
        raise ManifestValidationError(f"{location}.future_collection_requirements precisa ser uma lista nao vazia")


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate the no-collection contract and return a compact audit summary."""
    if manifest.get("schema_version") != 1:
        raise ManifestValidationError("schema_version precisa ser 1")
    if manifest.get("phase") != "research-and-corpus-plan-only":
        raise ManifestValidationError("A fase precisa permanecer research-and-corpus-plan-only")
    policy = manifest.get("collection_policy")
    if not isinstance(policy, dict):
        raise ManifestValidationError("collection_policy precisa ser um objeto")
    for key in (
        "full_text_downloaded",
        "new_dataset_downloaded",
        "tokenizer_trained",
        "model_weights_modified",
        "training_started",
    ):
        if policy.get(key) is not False:
            raise ManifestValidationError(f"collection_policy.{key} precisa ser false")
    if policy.get("explicit_approval_required_before_collection") is not True:
        raise ManifestValidationError("Aprovação explicita precisa permanecer obrigatoria antes da coleta")
    if policy.get("never_collect_without_per_document_audit") is not True:
        raise ManifestValidationError("A auditoria por documento precisa permanecer obrigatoria")
    forbidden = _find_forbidden_content_fields(manifest)
    if forbidden:
        raise ManifestValidationError(f"O manifesto de pesquisa nao pode conter texto ou arquivos: {', '.join(forbidden)}")
    v04 = manifest.get("v04_preservation")
    if not isinstance(v04, dict):
        raise ManifestValidationError("v04_preservation precisa ser um objeto")
    if v04.get("approved_base_commit") != "80140df0242c309911efaace921eafdf05b6a0f3":
        raise ManifestValidationError("O baseline aprovado da v0.4 foi alterado")
    if v04.get("tokenizer", {}).get("reuse_in_v05") is not False:
        raise ManifestValidationError("O BPE de Machado nao pode ser marcado para reuso na v0.5")
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ManifestValidationError("candidates precisa ser uma lista nao vazia")
    seen_ids: set[str] = set()
    for index, candidate in enumerate(candidates):
        _validate_candidate(candidate, index, seen_ids)
    scielo_count = sum(candidate["source_family"] == "SciELO Brasil" for candidate in candidates)
    if not 20 <= scielo_count <= 50:
        raise ManifestValidationError("A triagem preliminar da SciELO precisa conter de 20 a 50 artigos")
    return summarize_manifest(manifest)


def validate_v04_reference(manifest: dict[str, Any], evaluation_path: str | Path) -> None:
    """Compare the frozen v0.4 references against its tracked final audit."""
    report = load_manifest(evaluation_path)
    audit = report.get("checkpoint_audit")
    if not isinstance(audit, dict):
        raise ManifestValidationError("O relatorio final da v0.4 nao contem checkpoint_audit")
    v04 = manifest["v04_preservation"]
    actual = {
        "best_checkpoint_sha256": audit["checkpoint"]["sha256"],
        "last_checkpoint_sha256": audit["last_checkpoint"]["sha256"],
        "architecture_fingerprint": audit["model"]["architecture_fingerprint"],
        "tokenizer_fingerprint": audit["tokenizer"]["fingerprint"],
        "data_fingerprint": audit["corpus"]["checkpoint_data_fingerprint"],
        "split_fingerprint": audit["corpus"]["split_fingerprint"],
    }
    if actual != V04_EXPECTED:
        raise ManifestValidationError("O relatorio final da v0.4 nao corresponde aos anchors congelados")
    expected_from_manifest = {
        "best_checkpoint_sha256": v04["best_checkpoint"]["sha256"],
        "last_checkpoint_sha256": v04["last_checkpoint"]["sha256"],
        "architecture_fingerprint": v04["architecture"]["fingerprint"],
        "tokenizer_fingerprint": v04["tokenizer"]["fingerprint"],
        "data_fingerprint": v04["corpus"]["data_fingerprint"],
        "split_fingerprint": v04["corpus"]["split_fingerprint"],
    }
    if expected_from_manifest != actual:
        raise ManifestValidationError("O manifesto v0.5 nao preserva as referencias congeladas da v0.4")
    if audit.get("best_and_last_weights_identical") is not True:
        raise ManifestValidationError("A igualdade de pesos best/last da v0.4 deixou de estar registrada")


def summarize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic summary suitable for tests and CI logs."""
    candidates = manifest["candidates"]
    return {
        "candidate_count": len(candidates),
        "source_counts": dict(sorted(Counter(candidate["source_family"] for candidate in candidates).items())),
        "status_counts": dict(sorted(Counter(candidate["status"] for candidate in candidates).items())),
        "scielo_preliminary_article_count": sum(candidate["source_family"] == "SciELO Brasil" for candidate in candidates),
        "full_text_collected_count": sum(candidate["text_collected"] for candidate in candidates),
        "collection_requires_explicit_approval": manifest["collection_policy"]["explicit_approval_required_before_collection"],
        "v04_tokenizer_reused": manifest["v04_preservation"]["tokenizer"]["reuse_in_v05"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="data/corpus-v0.5/source-candidates.json")
    parser.add_argument("--v04-evaluation", default="reports/seed-v0.4-final-evaluation.json")
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    summary = validate_manifest(manifest)
    validate_v04_reference(manifest, args.v04_evaluation)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
