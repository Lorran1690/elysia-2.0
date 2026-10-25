import json

import pytest
import torch

from brain.tokenizer import ByteTokenizer
from brain.model import ElysiaTransformer, ModelConfig
from learning.language_pilot import encode_messages, evaluate, make_training_batch
from learning.prepare_oasst_pilot import DEST, LABELS, group_split, rejection, sha


def valid_row():
    return {"lang": "pt-BR", "synthetic": False, "deleted": False,
            "review_result": True, "text": "Uma explicação original sobre o céu e as nuvens.",
            "labels": {**{k: {"value": 0, "count": 3} for k in LABELS},
                       "quality": {"value": 0.8, "count": 3}}}


def test_source_filters_fail_closed_and_exclude_marked_synthetic_and_identifiers():
    row = valid_row()
    assert rejection(row) is None
    assert rejection({**row, "synthetic": True}) == "source_marks_synthetic"
    assert rejection({**row, "review_result": None}) == "not_positively_reviewed"
    assert rejection({**row, "labels": {}}).startswith("source_label_")
    assert rejection({**row, "text": "Meu contato é exemplo@dominio.com para falar comigo."}) == "identifier_or_link_pattern"


def test_whole_trees_and_duplicate_prompts_stay_together():
    records = [{"tree_id": f"tree-{i}", "messages": [{"content": f"Pergunta {i}: " + "texto próprio suficientemente longo " * 4}]} for i in range(30)]
    # Long exact duplicate in different trees must be unified even with different IDs.
    records[1]["messages"] = records[0]["messages"]
    # Avoid near-duplicate merging of all intentionally constructed test roots.
    for i in range(2, 30):
        records[i]["messages"] = [{"content": (f"palavra{i} " * 20) + str(i)}]
    split = group_split(records)
    assignment = {r["tree_id"]: s for s, rows in split.items() for r in rows}
    assert assignment["tree-0"] == assignment["tree-1"]
    groups = [{r["group_id"] for r in rows} for rows in split.values()]
    assert all(not a & b for i, a in enumerate(groups) for b in groups[i + 1:])


def test_actual_corpus_integrity_and_no_account_metadata():
    manifest = json.loads((DEST / "manifest.json").read_text(encoding="utf-8"))
    groups = []
    for split in ("train", "validation", "test"):
        path = DEST / f"{split}.json"
        assert sha(path) == manifest["splits"][split]["sha256"]
        records = json.loads(path.read_text(encoding="utf-8"))
        assert all("user_id" not in r and "created_date" not in r for r in records)
        groups.append({r["group_id"] for r in records})
    assert all(not a & b for i, a in enumerate(groups) for b in groups[i + 1:])


def test_training_and_reply_prefixes_match_and_only_assistant_content_is_supervised():
    tok = ByteTokenizer()
    user = {"role": "user", "content": "Oi\nElysia: teste"}
    response = {"role": "assistant", "content": "Olá!"}
    prompt, _ = encode_messages(tok, [user], for_reply=True)
    full, labels = encode_messages(tok, [user, response])
    assert full[:len(prompt)] == prompt
    assert all(x == -100 for x in labels[:len(prompt)])
    assert labels[len(prompt):] == tok.encode("Olá!", add_bos=False)
    assert "\nElysia: teste" not in tok.decode(prompt)


def test_assistant_only_windows_have_finite_loss_and_padding_is_ignored():
    tok = ByteTokenizer()
    doc = encode_messages(tok, [{"role": "user", "content": "Oi"}, {"role": "assistant", "content": "Olá"}])
    x, y = make_training_batch([doc], torch.Generator().manual_seed(4), batch_size=2, context=64, assistant_only=True)
    assert x.shape == y.shape == (2, 64)
    assert (y == -100).any() and (y != -100).any()
    model = ElysiaTransformer(ModelConfig(block_size=64, num_layers=1, embedding_dim=16, num_heads=2, feedforward_dim=32))
    _, loss = model(x, y)
    assert torch.isfinite(loss)


def test_full_evaluation_counts_each_target_once_and_restores_no_training_updates():
    tok = ByteTokenizer()
    doc = encode_messages(tok, [{"role": "user", "content": "Uma pergunta longa."}, {"role": "assistant", "content": "Uma resposta longa e completa."}])
    model = ElysiaTransformer(ModelConfig(block_size=16, num_layers=1, embedding_dim=16, num_heads=2, feedforward_dim=32))
    before = model.token_embeddings.weight.detach().clone()
    metrics = evaluate(model, [doc])
    assert metrics["all"]["targets"] == len(doc[0]) - 1
    assert metrics["assistant"]["targets"] == sum(v != -100 for v in doc[1][1:])
    assert torch.equal(before, model.token_embeddings.weight)


def test_batch_rng_state_can_be_restored_exactly():
    doc = encode_messages(ByteTokenizer(), [{"role": "user", "content": "Qual o nome?"}, {"role": "assistant", "content": "Uma resposta com várias palavras."}])
    rng = torch.Generator().manual_seed(5)
    state = rng.get_state()
    first = make_training_batch([doc], rng, batch_size=3, context=16, assistant_only=False)
    rng.set_state(state)
    second = make_training_batch([doc], rng, batch_size=3, context=16, assistant_only=False)
    assert all(torch.equal(a, b) for a, b in zip(first, second))


def test_rejects_invalid_role_order():
    with pytest.raises(ValueError, match="alternating"):
        encode_messages(ByteTokenizer(), [{"role": "assistant", "content": "Oi"}])
