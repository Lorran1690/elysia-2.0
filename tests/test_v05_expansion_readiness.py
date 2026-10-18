from __future__ import annotations

import copy
from pathlib import Path

import pytest

from learning.v05_expansion_readiness import (
    ExpansionReadinessError,
    load_manifest,
    validate_manifest,
    validate_repository_references,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "corpus-v0.5" / "expansion-readiness-candidates.json"


def manifest() -> dict[str, object]:
    return load_manifest(MANIFEST_PATH)


def test_phase_2g_manifest_is_metadata_only_and_keeps_all_work_gated() -> None:
    summary = validate_manifest(manifest())

    assert summary == {
        "candidate_count": 22,
        "status_counts": {"candidate": 6, "pending_verification": 13, "rejected": 3},
        "full_text_collected_count": 0,
        "first_recommended_lot_count": 4,
        "collection_started": False,
        "future_split_created": False,
        "model_or_tokenizer_activity": False,
        "conversation_protocol_is_proposal_only": True,
    }


def test_phase_2g_keeps_a_reference_to_the_preserved_phase_2f_audit() -> None:
    validate_repository_references(manifest(), ROOT)


def test_phase_2g_rejects_embedded_source_content() -> None:
    invalid = copy.deepcopy(manifest())
    invalid["candidates"][0]["full_text"] = "texto que nao deveria estar no catalogo"  # type: ignore[index]

    with pytest.raises(ExpansionReadinessError, match="nao pode conter texto ou arquivos"):
        validate_manifest(invalid)


def test_phase_2g_rejects_collection_or_tokenization_activity() -> None:
    invalid = copy.deepcopy(manifest())
    invalid["collection_policy"]["tokenization_started"] = True  # type: ignore[index]

    with pytest.raises(ExpansionReadinessError, match="tokenization_started"):
        validate_manifest(invalid)


def test_phase_2g_rejects_a_candidate_without_license_evidence() -> None:
    invalid = copy.deepcopy(manifest())
    candidate = next(item for item in invalid["candidates"] if item["status"] == "candidate")  # type: ignore[index]
    candidate["license"]["name"] = "not_verified"  # type: ignore[index]

    with pytest.raises(ExpansionReadinessError, match="candidata nao pode ter licenca nao verificada"):
        validate_manifest(invalid)


def test_phase_2g_requires_group_isolation_and_all_conversation_families() -> None:
    invalid = copy.deepcopy(manifest())
    invalid["candidates"][0]["group_id_rule"] = ""  # type: ignore[index]

    with pytest.raises(ExpansionReadinessError, match="group_id_rule"):
        validate_manifest(invalid)

    invalid = copy.deepcopy(manifest())
    invalid["conversational_data_protocol"]["required_scenario_families"].pop()  # type: ignore[index]

    with pytest.raises(ExpansionReadinessError, match="dez familias requeridas"):
        validate_manifest(invalid)


def test_phase_2g_first_lot_cannot_substitute_a_pending_source() -> None:
    invalid = copy.deepcopy(manifest())
    invalid["first_recommended_authorization_lot"]["items"][0]["source_id"] = "android-developers-pt-br"  # type: ignore[index]

    with pytest.raises(ExpansionReadinessError, match="fonte candidata"):
        validate_manifest(invalid)
