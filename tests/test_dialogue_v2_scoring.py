import copy
import json

import pytest

from learning.portuguese_corpus import ROOT
from learning.score_dialogue_v2 import response_hash, score


def fixture():
    spec = json.loads((ROOT / "evaluation/portuguese-v1.json").read_text())
    protocol = json.loads((ROOT / "data/neural-dialogue-v2/protocol.json").read_text())
    # Artificial review fixtures exercise accounting only, not model competence.
    cases = [{**c, "generated": "Resposta fictícia para testar o contador.", "error": None} for c in spec["cases"]]
    live = [{"id": c["id"], "messages": c["messages"] + [{"role": "assistant", "content": "Resposta fictícia."}], "error": None}
            for c in spec["cases"] if len(c["messages"]) > 1]
    results = {"generation_cases": cases, "live_rollouts": live}
    review = {"reviewer": "test fixture", "review_type": "synthetic test, not a semantic evaluation"}
    for label, rows in (("static", cases), ("live", live)):
        review[label] = {r["id"]: {"score": 2, "reason": "Fixture only", "generation_sha256": response_hash(r), "critical_errors": []} for r in rows}
    return spec, protocol, results, review


def test_critical_error_prevents_claiming_the_milestone():
    spec, protocol, results, review = fixture()
    assert score(results, review, spec, protocol)["small_milestone_met"]
    next(iter(review["static"].values()))["critical_errors"] = ["fabricated_private_information"]
    assert not score(results, review, spec, protocol)["small_milestone_met"]


def test_keywords_cannot_override_a_failed_semantic_review():
    spec, protocol, results, review = fixture()
    for decision in review["static"].values():
        decision["score"] = 0
    report = score(results, review, spec, protocol)
    assert report["scores"]["static"]["fully_correct"] == 0
    assert not report["small_milestone_met"]


def test_review_cannot_be_reused_for_changed_output_or_changed_prompt():
    spec, protocol, results, review = fixture()
    modified = copy.deepcopy(results)
    modified["generation_cases"][0]["generated"] += " Outro texto."
    with pytest.raises(ValueError, match="another generated response"):
        score(modified, review, spec, protocol)
    modified = copy.deepcopy(results)
    modified["generation_cases"][0]["messages"][0]["content"] = "Pergunta mais fácil."
    with pytest.raises(ValueError, match="prompt or criterion changed"):
        score(modified, review, spec, protocol)


def test_all_cases_must_have_a_review():
    spec, protocol, results, review = fixture()
    review["live"].pop(next(iter(review["live"])))
    with pytest.raises(ValueError, match="Every generated case"):
        score(results, review, spec, protocol)
