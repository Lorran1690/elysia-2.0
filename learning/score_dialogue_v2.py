"""Validate an identified semantic review; never infer correctness from keywords."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from learning.portuguese_corpus import ROOT


def response_hash(record):
    return hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def score(results, review, specification, protocol):
    if not review.get("reviewer") or not review.get("review_type"):
        raise ValueError("Identified reviewer and review type are required")
    expected = {c["id"]: c for c in specification["cases"]}
    actual = {c["id"]: c for c in results["generation_cases"]}
    if len(actual) != len(results["generation_cases"]) or set(expected) != set(actual):
        raise ValueError("Missing, duplicated or unknown frozen evaluation case")
    for key, case in actual.items():
        if case["messages"] != expected[key]["messages"] or case["criterion"] != expected[key]["criterion"]:
            raise ValueError("Evaluation prompt or criterion changed")
    live = {r["id"]: r for r in results["live_rollouts"]}
    expected_live = {key for key, c in expected.items() if len(c["messages"]) > 1}
    if set(live) != expected_live or len(live) != len(results["live_rollouts"]):
        raise ValueError("Missing or duplicated live conversation")
    counts = {}
    critical = []
    categories = {}
    for label, records in (("static", actual), ("live", live)):
        decisions = review[label]
        if set(decisions) != set(records):
            raise ValueError("Every generated case requires a review")
        full, points = 0, 0
        for key, record in records.items():
            item = decisions[key]
            value = item.get("score")
            if type(value) is not int or value not in {0, 1, 2} or not item.get("reason"):
                raise ValueError("Review requires score 0/1/2 and a rationale")
            if item.get("generation_sha256") != response_hash(record):
                raise ValueError("Review refers to another generated response")
            empty = not record.get("generated", "").strip() if label == "static" else not record["messages"] or record["messages"][-1]["role"] != "assistant"
            if (record.get("error") or empty) and value:
                raise ValueError("Failed or empty generation cannot receive positive score")
            flags = item.get("critical_errors")
            if not isinstance(flags, list):
                raise ValueError("Explicit critical-error list is required")
            for flag in flags:
                if flag not in {"fabricated_private_information", "false_tool_access"}:
                    raise ValueError("Unknown critical error")
                critical.append({"set": label, "id": key, "error": flag})
            full += value == 2
            points += value
            category = expected[key]["category"]
            if label == "static":
                categories.setdefault(category, {"full": 0, "cases": 0, "points": 0})
                categories[category]["cases"] += 1
                categories[category]["full"] += value == 2
                categories[category]["points"] += value
        counts[label] = {"fully_correct": full, "cases": len(records), "points": points, "maximum_points": 2 * len(records)}
    gate = protocol["milestone_criterion"]
    met = (counts["static"]["fully_correct"] >= gate["fully_correct_static_cases_minimum"]
           and counts["live"]["fully_correct"] >= gate["fully_correct_live_multiturn_cases_minimum"]
           and len(critical) <= gate["critical_personal_information_or_tool_access_fabrications_maximum"])
    return {"reviewer": review["reviewer"], "review_type": review["review_type"],
            "scores": counts, "by_category": categories, "critical_errors": critical,
            "small_milestone_met": met, "chatgpt_equivalence": "not established by this benchmark",
            "limits": "A semantic review is not independent human validation unless the reviewer is actually an independent human."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = score(json.loads(args.results.read_text()), json.loads(args.review.read_text()),
                   json.loads((ROOT / "evaluation/portuguese-v1.json").read_text()),
                   json.loads((ROOT / "data/neural-dialogue-v2/protocol.json").read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
