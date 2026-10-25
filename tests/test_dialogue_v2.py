import copy
import json

import pytest
import torch

from learning.dialogue_v2_data import DEST, FastProjectTokenizer, strip_book
from learning.portuguese_corpus import ROOT
from learning.train_dialogue_v2 import train


def test_fast_adapter_has_identical_project_ids_and_round_trips():
    tokenizer = FastProjectTokenizer()
    for text in ["Olá, Elysia!", "Meu nome é Inês.\nComo você está?", "A árvore e o café."]:
        assert tokenizer.encode(text) == tokenizer.own.encode(text)
        assert tokenizer.decode(tokenizer.encode(text)) == text


def test_book_extraction_requires_real_boundaries():
    with pytest.raises(ValueError, match="boundaries"):
        strip_book("Texto qualquer sem declaração editorial.")


def test_new_dialogue_groups_and_literary_authors_are_disjoint():
    groups, tree_ids, authors = [], [], []
    legacy = set()
    for split in ["train", "validation", "test"]:
        legacy.update(r["tree_id"] for r in json.loads((ROOT / f"data/language-pilot/{split}.json").read_text()))
        records = json.loads((DEST / f"dialogues/{split}.json").read_text())
        groups.append({r["group_id"] for r in records})
        tree_ids.append({r["tree_id"] for r in records})
        books = [json.loads(s) for s in (DEST / f"literature/{split}.jsonl").read_text().splitlines()]
        authors.append({r["group_id"] for r in books})
        assert not tree_ids[-1] & legacy
        assert all(not r["synthetic"] and "user_id" not in r for r in records)
    for values in [groups, tree_ids, authors]:
        assert all(not a & b for i, a in enumerate(values) for b in values[i + 1:])


def test_resume_at_optimizer_step_boundary_is_exact(tmp_path):
    protocol = copy.deepcopy(json.loads((DEST / "protocol.json").read_text()))
    protocol.update(pretrain_steps=3, sft_steps=2, pretrain_context=32, sft_context=32)
    protocol["model"].update(num_layers=1, embedding_dim=16, num_heads=2, feedforward_dim=32)
    uninterrupted, resumed = tmp_path / "continuous", tmp_path / "resumed"
    train(uninterrupted, protocol_override=protocol, finalize=False)
    train(resumed, protocol_override=protocol, pause_after=2, finalize=False)
    assert not (resumed / "results.json").exists()
    train(resumed, protocol_override=protocol, resume=True, finalize=False)
    a = torch.load(uninterrupted / "last.pt", weights_only=True)
    b = torch.load(resumed / "last.pt", weights_only=True)
    assert a["progress"]["global_step"] == b["progress"]["global_step"] == 5
    assert a["progress"]["stage"] == b["progress"]["stage"] == "complete"
    assert all(torch.equal(a["model_state"][k], b["model_state"][k]) for k in a["model_state"])
    assert torch.equal(a["batch_rng"], b["batch_rng"])
    assert torch.equal(a["torch_rng"], b["torch_rng"])
    # Configuration/source changes cannot be silently used to resume a run.
    changed = copy.deepcopy(protocol)
    changed["seed"] += 1
    with pytest.raises(ValueError, match="mismatch"):
        train(resumed, protocol_override=changed, resume=True, finalize=False)
