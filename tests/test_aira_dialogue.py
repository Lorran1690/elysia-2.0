import torch
from learning.aira_dialogue import answer_windows, batch
from learning.dialogue_v2_data import FastProjectTokenizer
from learning.language_pilot import encode_messages


def test_window_keeps_question_and_masks_earlier_assistant_targets():
    tokenizer = FastProjectTokenizer()
    messages = [
        {'role': 'user', 'content': 'Meu nome é Tadeu.'},
        {'role': 'assistant', 'content': 'Olá, Tadeu, como você está hoje?'},
        {'role': 'user', 'content': 'Qual é meu nome?'},
        {'role': 'assistant', 'content': 'Seu nome é Tadeu.'},
    ]
    windows = answer_windows(tokenizer, messages, 256)
    ids, labels = windows[-1]
    prefix, _ = encode_messages(tokenizer, messages[:-1], for_reply=True)
    assert ids[:len(prefix)] == prefix
    assert all(t == -100 for t in labels[:len(prefix)])
    assert labels[-1] == tokenizer.eos_id
    assert len(windows) == 2
    x, y = batch(windows, torch.Generator().manual_seed(1), 2, 256)
    assert x.shape == y.shape == (2, 256)
    assert torch.all(y[:, max(len(w[0]) for w in windows)-1:] == -100)


def test_answer_too_long_is_rejected_instead_of_disconnected_tail():
    tokenizer = FastProjectTokenizer()
    messages = [{'role': 'user', 'content': 'Explique isso.'},
                {'role': 'assistant', 'content': 'Uma resposta extensa. ' * 200}]
    assert answer_windows(tokenizer, messages, 64) == []
