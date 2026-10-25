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


def test_optimizer_boundary_resume_matches_continuous_run(tmp_path, monkeypatch):
    """Mechanical tiny-model fixture, not a semantic benchmark or real run."""
    import types
    import learning.aira_dialogue as trainer
    from brain.model import ElysiaTransformer, ModelConfig

    torch.manual_seed(111)
    model = ElysiaTransformer(ModelConfig(vocab_size=2048, block_size=512,
                             num_layers=1, embedding_dim=16, num_heads=2,
                             feedforward_dim=32, dropout=0.1))
    source = tmp_path / 'initial.pt'
    torch.save({'model_config': model.config_dict(), 'model_state': model.state_dict()}, source)
    monkeypatch.setattr(trainer, 'BASE', source)
    documents = [([1, 10, 20, 30, 40, 2], [-100, -100, -100, 30, 40, 2])]
    monkeypatch.setattr(trainer, 'load_windows', lambda tokenizer, context:
                        ({s: documents for s in ['train', 'validation', 'test']}, {'fixture': True}))
    monkeypatch.setattr(trainer, 'reply', lambda *args, **kwargs: 'Mechanical test fixture.')
    monkeypatch.setattr(trainer, 'time', types.SimpleNamespace(perf_counter=lambda: 0.0))
    trainer.train(tmp_path/'continuous', steps=3)
    ticks = iter([0.0, 0.0, 0.0, 2.0, 2.0])
    monkeypatch.setattr(trainer, 'time', types.SimpleNamespace(perf_counter=lambda: next(ticks)))
    trainer.train(tmp_path/'resumed', steps=3, max_seconds=1)
    saved = torch.load(tmp_path/'resumed/last.pt', weights_only=True)
    assert saved['progress']['step'] == 1
    assert not (tmp_path/'resumed/results.json').exists()
    monkeypatch.setattr(trainer, 'time', types.SimpleNamespace(perf_counter=lambda: 0.0))
    trainer.train(tmp_path/'resumed', steps=3, resume=True)
    a = torch.load(tmp_path/'continuous/last.pt', weights_only=True)
    b = torch.load(tmp_path/'resumed/last.pt', weights_only=True)
    assert a['progress']['history'] == b['progress']['history']
    assert torch.equal(a['batch_rng'], b['batch_rng'])
    assert torch.equal(a['torch_rng'], b['torch_rng'])
    for key, value in a['model_state'].items():
        assert torch.equal(value, b['model_state'][key])
    import pytest
    with pytest.raises(ValueError, match='frozen'):
        trainer.train(tmp_path/'resumed', steps=3, resume=True)
