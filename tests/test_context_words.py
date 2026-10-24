import json

import pytest

from learning.context_words import DATA, TOK, as_training, format_history
from learning.first_words import batch, prompt


def test_transcript_training_matches_inference_and_supervises_only_last_answer():
    record = json.loads((DATA / "train.json").read_text(encoding="utf-8"))["records"][0]
    converted = as_training([record])[0]
    assert prompt(converted["question"]) == format_history(record["messages"])
    x, y = batch([converted], 384)
    prefix = TOK.encode(format_history(record["messages"]), add_eos=False)
    assert x[0, :len(prefix)].tolist() == prefix
    assert (y[0, :len(prefix) - 1] == -100).all()
    assert y[0, len(prefix) - 1:].tolist() == TOK.encode(record["answer"], add_bos=False)


def test_combination_groups_never_cross_splits_and_targets_are_grounded():
    splits = {s: json.loads((DATA / f"{s}.json").read_text(encoding="utf-8"))["records"]
              for s in ("train", "validation", "test")}
    groups = {s: {r["group_id"] for r in records} for s, records in splits.items()}
    assert not groups["train"] & groups["validation"]
    assert not groups["train"] & groups["test"]
    assert not groups["validation"] & groups["test"]
    for records in splits.values():
        for r in records:
            if r["intent"] in {"name", "color"}:
                # Correct answer must originate in a user message, not in assistant history.
                source = 0 if r["intent"] == "name" else 2
                assert r["messages"][source]["content"].endswith(r["answer"])
                assert all(r["answer"] not in m["content"] for m in r["messages"] if m["role"] == "assistant")


@pytest.mark.parametrize("messages", [[], [{"role": "assistant", "content": "Oi"}],
    [{"role": "user", "content": "Oi\nElysia: x"}], [{"role": "user", "content": " "}]])
def test_invalid_transcripts_are_rejected(messages):
    with pytest.raises((ValueError, IndexError)):
        format_history(messages)
