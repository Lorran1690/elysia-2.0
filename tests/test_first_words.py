import json

import pytest
import torch

from brain.model import ElysiaTransformer, ModelConfig
from learning.first_words import DATA, TEST, TOKENIZER, answer, batch, prompt


def test_only_answer_and_eos_are_supervised():
    record = {"question": "Oi.", "answer": "Olá!"}
    x, y = batch([record, {"question": "Nome?", "answer": "Elysia."}], 192)
    prefix = TOKENIZER.encode(prompt(record["question"]), add_eos=False)
    expected = TOKENIZER.encode(record["answer"], add_bos=False)
    assert (y[0, :len(prefix) - 1] == -100).all()
    assert y[0, len(prefix) - 1:len(prefix) - 1 + len(expected)].tolist() == expected
    assert (y[0, len(prefix) - 1 + len(expected):] == -100).all()
    assert x[0, :len(prefix)].tolist() == prefix


def test_rejects_truncation_and_keeps_splits_separate():
    with pytest.raises(ValueError, match="contexto"):
        batch([{"question": "a" * 192, "answer": "x"}], 192)
    train = json.loads(DATA.read_text(encoding="utf-8"))["records"]
    test = json.loads(TEST.read_text(encoding="utf-8"))["records"]
    assert not ({r["question"] for r in train} & {r["question"] for r in test})


def test_answer_comes_from_logits_not_a_lookup():
    model = ElysiaTransformer(ModelConfig(block_size=192, num_layers=1,
                                         embedding_dim=16, num_heads=2, feedforward_dim=32))
    # Force EOS through the neural output head, independently of the question.
    with torch.no_grad():
        model.output_projection.weight.zero_()
        model.output_projection.bias.zero_()
        model.output_projection.bias[TOKENIZER.EOS_ID] = 100
    assert answer(model, "Qual é o seu nome?") == ""
