"""Validate the metadata-only Phase 2G corpus-expansion plan.

This module never retrieves a source, extracts text, trains a tokenizer, creates
splits, or changes model state. It validates the documented gates required before
any later, explicitly approved acquisition batch can begin.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


PHASE = "phase-2g-expansion-readiness"
APPROVED_BASE_COMMIT = "cabdb1010280df2f4ef24112841d790f9bee8311"
STATUS_VALUES = frozenset({"candidate", "pending_verification", "rejected"})
RISK_LEVELS = frozenset({"low", "medium", "high"})
REQUIRED_POLICY_FLAGS = frozenset(
    {
        "full_text_downloaded",
        "new_dataset_downloaded",
        "tokenization_started",
        "bpe_trained",
        "splits_created",
        "neural_training_started",
        "weights_or_checkpoints_modified",
        "ollama_or_external_models_used",
    }
)
REQUIRED_CANDIDATE_FIELDS = frozenset(
    {
        "id",
        "name",
        "official_url",
        "evidence_url",
        "authors_or_institution",
        "genre",
        "language",
        "license",
        "format_available",
        "volume",
        "risks",
        "language_quality",
        "elysia_utility",
        "status",
        "status_reason",
        "collection_scope",
        "group_id_rule",
        "text_collected",
        "content_hash",
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
REQUIRED_SCENARIOS = frozenset(
    {
        "everyday_conversations",
        "questions_and_answers",
        "explanations_at_multiple_difficulty_levels",
        "step_by_step_instructions",
        "multi_turn_dialogues",
        "ambiguous_requests",
        "error_corrections",
        "admission_of_uncertainty",
        "local_tool_interactions",
        "technical_support",
    }
)
REQUIRED_INGESTION_CONTROLS = frozenset(
    {
        "versioned manifests",
        "original preservation",
        "UTF-8/NFC derivatives",
        "document provenance",
        "license and attribution record",
        "personal-data scan",
        "exact duplicate detection",
        "near-duplicate detection",
        "third-party quotation review",
        "cleaning-artifact detection",
        "audit reports",
        "individual approval control",
    }
)


class ExpansionReadinessError(ValueError):
    """Raised when a Phase 2G research artifact violates its safety contract."""


def load_manifest(path: str | Path) -> dict[str, Any]:
    """Load a UTF-8 JSON manifest without resolving any external source URL."""

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ExpansionReadinessError("O manifesto raiz precisa ser um objeto JSON")
    return value


def _require_string(mapping: dict[str, Any], key: str, location: str) -> None:
    if not isinstance(mapping.get(key), str) or not mapping[key].strip():
        raise ExpansionReadinessError(f"{location}.{key} precisa ser uma string nao vazia")


def _require_https(mapping: dict[str, Any], key: str, location: str) -> None:
    _require_string(mapping, key, location)
    if not mapping[key].startswith("https://"):
        raise ExpansionReadinessError(f"{location}.{key} precisa usar HTTPS")


def _require_string_list(value: Any, location: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        raise ExpansionReadinessError(f"{location} precisa ser uma lista nao vazia de strings")
    return value


def _validate_range(value: Any, location: str) -> None:
    if not isinstance(value, dict):
        raise ExpansionReadinessError(f"{location} precisa ser um objeto")
    for key in ("minimum", "maximum"):
        if type(value.get(key)) is not int or value[key] <= 0:
            raise ExpansionReadinessError(f"{location}.{key} precisa ser um inteiro positivo")
    if value["minimum"] > value["maximum"]:
        raise ExpansionReadinessError(f"{location} tem faixa invertida")


def _validate_risk(value: Any, location: str) -> None:
    if not isinstance(value, dict):
        raise ExpansionReadinessError(f"{location} precisa ser um objeto")
    if value.get("level") not in RISK_LEVELS:
        raise ExpansionReadinessError(f"{location}.level precisa ser low, medium ou high")
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


def _validate_license(value: Any, location: str) -> None:
    if not isinstance(value, dict):
        raise ExpansionReadinessError(f"{location} precisa ser um objeto")
    for key in ("name", "evidence", "verification"):
        _require_string(value, key, location)
    _require_https(value, "evidence_url", location)


def _validate_candidate(candidate: Any, index: int, seen_ids: set[str]) -> None:
    location = f"candidates[{index}]"
    if not isinstance(candidate, dict):
        raise ExpansionReadinessError(f"{location} precisa ser um objeto")
    missing = sorted(REQUIRED_CANDIDATE_FIELDS - set(candidate))
    if missing:
        raise ExpansionReadinessError(f"{location} nao possui campos obrigatorios: {', '.join(missing)}")
    for key in (
        "id",
        "name",
        "authors_or_institution",
        "genre",
        "language",
        "language_quality",
        "elysia_utility",
        "status_reason",
        "collection_scope",
        "group_id_rule",
    ):
        _require_string(candidate, key, location)
    if candidate["id"] in seen_ids:
        raise ExpansionReadinessError(f"{location}.id esta duplicado: {candidate['id']}")
    seen_ids.add(candidate["id"])
    _require_https(candidate, "official_url", location)
    _require_https(candidate, "evidence_url", location)
    _validate_license(candidate["license"], f"{location}.license")
    _require_string_list(candidate["format_available"], f"{location}.format_available")
    volume = candidate["volume"]
    if not isinstance(volume, dict):
        raise ExpansionReadinessError(f"{location}.volume precisa ser um objeto")
    _validate_range(volume.get("documents"), f"{location}.volume.documents")
    _validate_range(volume.get("tokens"), f"{location}.volume.tokens")
    _require_string(volume, "basis", f"{location}.volume")
    risks = candidate["risks"]
    if not isinstance(risks, dict):
        raise ExpansionReadinessError(f"{location}.risks precisa ser um objeto")
    for risk_name in ("third_party", "personal_data", "duplication"):
        _validate_risk(risks.get(risk_name), f"{location}.risks.{risk_name}")
    if candidate["status"] not in STATUS_VALUES:
        raise ExpansionReadinessError(f"{location}.status nao e reconhecido")
    if candidate["status"] == "candidate" and candidate["license"]["name"].startswith("not_"):
        raise ExpansionReadinessError(f"{location} candidata nao pode ter licenca nao verificada")
    if candidate["text_collected"] is not False:
        raise ExpansionReadinessError(f"{location}.text_collected precisa ser false nesta fase")
    if candidate["content_hash"] is not None:
        raise ExpansionReadinessError(f"{location}.content_hash precisa ser null sem coleta autorizada")


def _validate_conversational_protocol(value: Any) -> None:
    if not isinstance(value, dict):
        raise ExpansionReadinessError("conversational_data_protocol precisa ser um objeto")
    if value.get("no_model_generated_content") is not True:
        raise ExpansionReadinessError("O protocolo conversacional precisa proibir conteudo gerado por modelos")
    if value.get("no_automatic_mass_generation") is not True:
        raise ExpansionReadinessError("O protocolo conversacional precisa proibir geracao automatica em massa")
    if value.get("protocol_status") != "proposal_only":
        raise ExpansionReadinessError("O protocolo conversacional precisa permanecer somente proposta")
    for key in ("pretraining_linguistic_data", "future_conversational_tuning"):
        track = value.get(key)
        if not isinstance(track, dict):
            raise ExpansionReadinessError(f"conversational_data_protocol.{key} precisa ser um objeto")
        for field in ("purpose", "unit"):
            _require_string(track, field, f"conversational_data_protocol.{key}")
        for field in ("exclude", "quality_controls"):
            _require_string_list(track.get(field), f"conversational_data_protocol.{key}.{field}")
    scenarios = value.get("required_scenario_families")
    if not isinstance(scenarios, list) or set(scenarios) != REQUIRED_SCENARIOS or len(scenarios) != len(REQUIRED_SCENARIOS):
        raise ExpansionReadinessError("O protocolo conversacional precisa registrar exatamente as dez familias requeridas")
    _require_string_list(value.get("recording_requirements"), "conversational_data_protocol.recording_requirements")


def _validate_scale_planning(value: Any) -> None:
    if not isinstance(value, dict):
        raise ExpansionReadinessError("scale_planning precisa ser um objeto")
    _require_string(value, "estimate_note", "scale_planning")
    scenarios = value.get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != 2:
        raise ExpansionReadinessError("scale_planning.scenarios precisa ter os dois cenarios autorizados")
    expected_tokens = {"initial_5m": 5_000_000, "expanded_20m": 20_000_000}
    seen_ids: set[str] = set()
    for index, scenario in enumerate(scenarios):
        location = f"scale_planning.scenarios[{index}]"
        if not isinstance(scenario, dict):
            raise ExpansionReadinessError(f"{location} precisa ser um objeto")
        scenario_id = scenario.get("id")
        if scenario_id not in expected_tokens or scenario_id in seen_ids:
            raise ExpansionReadinessError(f"{location}.id nao corresponde a um cenario planejado")
        seen_ids.add(scenario_id)
        if scenario.get("target_tokens") != expected_tokens[scenario_id]:
            raise ExpansionReadinessError(f"{location}.target_tokens diverge da meta aprovada")
        for field in ("clean_utf8_bytes", "expected_documents", "source_family_count", "human_cleaning_hours"):
            _validate_range(scenario.get(field), f"{location}.{field}")
        for field in ("recommended_mix", "limitation"):
            _require_string(scenario, field, location)
        _require_string_list(scenario.get("duplication_risks"), f"{location}.duplication_risks")
    if seen_ids != set(expected_tokens):
        raise ExpansionReadinessError("Os cenarios de 5M e 20M precisam estar presentes")
    _require_string_list(value.get("architecture_limitations"), "scale_planning.architecture_limitations")


def _validate_ingestion_architecture(value: Any) -> None:
    if not isinstance(value, dict):
        raise ExpansionReadinessError("batch_ingestion_architecture precisa ser um objeto")
    for field in ("approval_gate", "group_id_strategy", "split_policy"):
        _require_string(value, field, "batch_ingestion_architecture")
    for field in ("manifest_fields", "states", "processing_order", "required_controls"):
        _require_string_list(value.get(field), f"batch_ingestion_architecture.{field}")
    if not REQUIRED_INGESTION_CONTROLS.issubset(set(value["required_controls"])):
        missing = sorted(REQUIRED_INGESTION_CONTROLS - set(value["required_controls"]))
        raise ExpansionReadinessError(f"A arquitetura de ingestao nao possui controles: {', '.join(missing)}")
    if "group_id" not in value["manifest_fields"]:
        raise ExpansionReadinessError("A arquitetura de ingestao precisa registrar group_id")
    if "No split" not in value["split_policy"]:
        raise ExpansionReadinessError("A arquitetura de ingestao nao pode criar splits nesta fase")


def _validate_first_lot(value: Any, candidates: list[dict[str, Any]]) -> None:
    if not isinstance(value, dict):
        raise ExpansionReadinessError("first_recommended_authorization_lot precisa ser um objeto")
    if value.get("requires_fresh_user_approval") is not True:
        raise ExpansionReadinessError("O primeiro lote precisa exigir nova aprovacao do usuario")
    if value.get("collection_started") is not False:
        raise ExpansionReadinessError("O primeiro lote nao pode iniciar coleta nesta fase")
    if value.get("no_source_substitution") is not True:
        raise ExpansionReadinessError("O primeiro lote precisa proibir substituicao de fonte")
    items = value.get("items")
    if not isinstance(items, list) or not items or len(items) > 5:
        raise ExpansionReadinessError("O primeiro lote precisa conter de uma a cinco fontes pequenas")
    candidates_by_id = {candidate["id"]: candidate for candidate in candidates}
    seen_ids: set[str] = set()
    required_fields = frozenset(
        {
            "source_id",
            "justification",
            "license_evidence_url",
            "expected_tokens",
            "risks",
            "acceptance_criteria",
            "rejection_criteria",
        }
    )
    for index, item in enumerate(items):
        location = f"first_recommended_authorization_lot.items[{index}]"
        if not isinstance(item, dict):
            raise ExpansionReadinessError(f"{location} precisa ser um objeto")
        missing = sorted(required_fields - set(item))
        if missing:
            raise ExpansionReadinessError(f"{location} nao possui campos obrigatorios: {', '.join(missing)}")
        source_id = item["source_id"]
        if source_id in seen_ids or source_id not in candidates_by_id:
            raise ExpansionReadinessError(f"{location}.source_id precisa apontar para uma candidata unica")
        seen_ids.add(source_id)
        if candidates_by_id[source_id]["status"] != "candidate":
            raise ExpansionReadinessError(f"{location}.source_id precisa apontar para uma fonte candidata")
        for field in ("justification", "risks"):
            _require_string(item, field, location)
        _require_https(item, "license_evidence_url", location)
        _validate_range(item["expected_tokens"], f"{location}.expected_tokens")
        _require_string_list(item["acceptance_criteria"], f"{location}.acceptance_criteria")
        _require_string_list(item["rejection_criteria"], f"{location}.rejection_criteria")


def summarize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a compact, deterministic summary for audit logs and tests."""

    candidates = manifest["candidates"]
    return {
        "candidate_count": len(candidates),
        "status_counts": dict(sorted(Counter(candidate["status"] for candidate in candidates).items())),
        "full_text_collected_count": sum(candidate["text_collected"] is True for candidate in candidates),
        "first_recommended_lot_count": len(manifest["first_recommended_authorization_lot"]["items"]),
        "collection_started": manifest["first_recommended_authorization_lot"]["collection_started"],
        "future_split_created": manifest["collection_policy"]["splits_created"],
        "model_or_tokenizer_activity": any(
            manifest["collection_policy"][key]
            for key in ("tokenization_started", "bpe_trained", "neural_training_started", "weights_or_checkpoints_modified")
        ),
        "conversation_protocol_is_proposal_only": manifest["conversational_data_protocol"]["protocol_status"] == "proposal_only",
    }


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate the Phase 2G plan without touching corpus or model artifacts."""

    if manifest.get("schema_version") != 1:
        raise ExpansionReadinessError("schema_version precisa ser 1")
    if manifest.get("phase") != PHASE:
        raise ExpansionReadinessError("A fase do manifesto nao corresponde a Phase 2G")
    if manifest.get("approved_base_commit") != APPROVED_BASE_COMMIT:
        raise ExpansionReadinessError("O commit-base aprovado foi alterado")
    _require_string(manifest, "project", "manifest")
    _require_string(manifest, "created_at", "manifest")
    _require_string(manifest, "purpose", "manifest")
    preservation = manifest.get("preservation")
    if not isinstance(preservation, dict):
        raise ExpansionReadinessError("preservation precisa ser um objeto")
    for key in ("historical_manifests_preserved",):
        if preservation.get(key) is not True:
            raise ExpansionReadinessError(f"preservation.{key} precisa ser true")
    for key in ("desktop_branch_modified", "voice_command_life_modified", "v04_modified"):
        if preservation.get(key) is not False:
            raise ExpansionReadinessError(f"preservation.{key} precisa ser false")
    _require_string(preservation, "phase_2f_audit_path", "preservation")
    policy = manifest.get("collection_policy")
    if not isinstance(policy, dict):
        raise ExpansionReadinessError("collection_policy precisa ser um objeto")
    for key in REQUIRED_POLICY_FLAGS:
        if policy.get(key) is not False:
            raise ExpansionReadinessError(f"collection_policy.{key} precisa ser false")
    for key in ("explicit_user_approval_required_before_collection", "per_document_approval_required", "no_source_substitution_without_new_approval"):
        if policy.get(key) is not True:
            raise ExpansionReadinessError(f"collection_policy.{key} precisa ser true")
    forbidden = _find_forbidden_content_fields(manifest)
    if forbidden:
        raise ExpansionReadinessError(f"O catalogo metadata-only nao pode conter texto ou arquivos: {', '.join(forbidden)}")
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list) or not 15 <= len(candidates) <= 25:
        raise ExpansionReadinessError("O catalogo precisa conter entre 15 e 25 fontes")
    seen_ids: set[str] = set()
    for index, candidate in enumerate(candidates):
        _validate_candidate(candidate, index, seen_ids)
    _validate_conversational_protocol(manifest.get("conversational_data_protocol"))
    _validate_scale_planning(manifest.get("scale_planning"))
    _validate_ingestion_architecture(manifest.get("batch_ingestion_architecture"))
    _validate_first_lot(manifest.get("first_recommended_authorization_lot"), candidates)
    return summarize_manifest(manifest)


def validate_repository_references(manifest: dict[str, Any], root: str | Path) -> None:
    """Confirm that Phase 2G points at the preserved local Phase 2F audit."""

    audit_path = Path(root) / manifest["preservation"]["phase_2f_audit_path"]
    if not audit_path.is_file():
        raise ExpansionReadinessError(f"O manifesto historico da Fase 2F nao existe: {audit_path}")
    audit = load_manifest(audit_path)
    if "documents" not in audit:
        raise ExpansionReadinessError("O manifesto historico da Fase 2F nao contem documentos")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the ELYSIA v0.5 Phase 2G expansion-readiness manifest")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/corpus-v0.5/expansion-readiness-candidates.json"),
        help="Path to the metadata-only Phase 2G manifest",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root for historical-reference checks")
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    summary = validate_manifest(manifest)
    validate_repository_references(manifest, args.root)
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
