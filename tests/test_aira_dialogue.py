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


def test_cached_pair_construction_matches_reference_full_transcripts():
    tokenizer = FastProjectTokenizer()
    messages = []
    for i in range(5):
        messages.extend([
            {'role': 'user', 'content': f'Questão {i}: como isso funciona?\nPode explicar?'},
            {'role': 'assistant', 'content': ('Explicação detalhada com acentuação. ' * (i+1))},
        ])
    for context in [32, 64, 128, 256, 512]:
        reference = []
        for end in [2, len(messages)]:
            start = 0
            while start < end-2:
                ids, labels = encode_messages(tokenizer, messages[start:end])
                if len(ids) <= context+1:
                    break
                start += 2
            ids, labels = encode_messages(tokenizer, messages[start:end])
            if len(ids) > context+1:
                continue
            prefix, _ = encode_messages(tokenizer, messages[start:end-1], for_reply=True)
            labels[:len(prefix)] = [-100] * len(prefix)
            reference.append((ids, labels))
        assert answer_windows(tokenizer, messages, context) == reference
