from __future__ import annotations

import copy
from pathlib import Path

import pytest

from learning.v05_corpus_plan import ManifestValidationError, load_manifest, validate_manifest, validate_v04_reference


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "corpus-v0.5" / "source-candidates.json"
V04_EVALUATION_PATH = ROOT / "reports" / "seed-v0.4-final-evaluation.json"


def manifest() -> dict[str, object]:
    return load_manifest(MANIFEST_PATH)


def test_v05_manifest_is_metadata_only_and_has_required_scielo_screen() -> None:
    summary = validate_manifest(manifest())
    assert summary == {
        "candidate_count": 28,
        "source_counts": {"Padrao Digital de Governo": 1, "SciELO Brasil": 20, "eMAG": 1, "eduCAPES": 6},
        "status_counts": {"approved": 2, "pending": 21, "rejected": 5},
        "scielo_preliminary_article_count": 20,
        "full_text_collected_count": 0,
        "collection_requires_explicit_approval": True,
        "v04_tokenizer_reused": False,
    }


def test_v05_manifest_matches_the_frozen_v04_audit() -> None:
    validate_v04_reference(manifest(), V04_EVALUATION_PATH)


def test_v05_manifest_rejects_embedded_source_content() -> None:
    invalid = copy.deepcopy(manifest())
    invalid["candidates"][0]["full_text"] = "texto que nao deveria estar no manifesto"  # type: ignore[index]
    with pytest.raises(ManifestValidationError, match="nao pode conter texto"):
        validate_manifest(invalid)


def test_v05_manifest_rejects_an_approved_candidate_without_a_permissive_license() -> None:
    invalid = copy.deepcopy(manifest())
    approved_candidate = next(candidate for candidate in invalid["candidates"] if candidate["status"] == "approved")  # type: ignore[index]
    approved_candidate["license"]["name"] = "desconhecida"
    with pytest.raises(ManifestValidationError, match="CC BY 4.0 ou CC0 1.0"):
        validate_manifest(invalid)


def test_v05_manifest_rejects_collection_before_explicit_approval() -> None:
    invalid = copy.deepcopy(manifest())
    invalid["collection_policy"]["new_dataset_downloaded"] = True  # type: ignore[index]
    with pytest.raises(ManifestValidationError, match="new_dataset_downloaded"):
        validate_manifest(invalid)


def test_v05_manifest_records_the_blocked_emag_attempt_without_collecting_content() -> None:
    emag = next(candidate for candidate in manifest()["candidates"] if candidate["id"] == "emag-v3-1")  # type: ignore[index]

    assert emag["status"] == "pending"
    assert emag["text_collected"] is False
    assert emag["content_hash"] is None
    assert emag["collection_attempt"]["outcome"] == "blocked_file_unavailable"
    assert emag["collection_attempt"]["files_downloaded"] == 0
    assert emag["collection_attempt"]["source_bytes_saved"] == 0
