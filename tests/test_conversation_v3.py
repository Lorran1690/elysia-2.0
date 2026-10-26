import torch

from learning.conversation_v3 import batch
from learning.curriculum_v2 import encode_target, prefix_candidates, probabilities
from learning.dialogue_v2_data import FastProjectTokenizer
from learning.language_pilot import encode_messages


def test_complete_context_is_never_cropped_and_only_final_answer_is_supervised():
    tokenizer = FastProjectTokenizer()
    messages = [{'role':'user','content':'Minha gata se chama Pipoca.'},
                {'role':'assistant','content':'Pipoca é um nome divertido para sua gata.'},
                {'role':'user','content':'Qual é o nome dela?'},
                {'role':'assistant','content':'Sua gata se chama Pipoca.'}]
    row={'id':'test-record','group_id':'test-group','messages':messages}
    candidates,_,_=prefix_candidates(tokenizer,row,maximum=512)
    target=candidates[-1]
    ids,labels=encode_target(tokenizer,messages,target)
    prompt,_=encode_messages(tokenizer,messages[:-1],for_reply=True)
    assert ids[:len(prompt)]==prompt and all(t==-100 for t in labels[:len(prompt)])
    assert labels[-1]==tokenizer.eos_id
    too_short,_,_=prefix_candidates(tokenizer,row,maximum=len(ids)-2)
    assert all(t['assistant_pair_index']==0 for t in too_short)


def test_weighted_dynamic_batch_masks_padding_and_restores_sampling_rng():
    rows=[{'ids':[1,5,6,2],'labels':[-100,-100,6,2]},
          {'ids':[1,8,2],'labels':[-100,8,2]}]
    weights=torch.tensor([0.,1.],dtype=torch.float64)
    rng=torch.Generator().manual_seed(19)
    state=rng.get_state()
    x,y=batch(rows,weights,rng,size=3)
    assert x.tolist()==[[1,8]]*3 and y.tolist()==[[8,2]]*3
    rng.set_state(state)
    repeat=batch(rows,weights,rng,size=3)
    assert torch.equal(x,repeat[0]) and torch.equal(y,repeat[1])
    both=torch.ones(2,dtype=torch.float64)
    x,y=batch(rows,both,torch.Generator().manual_seed(4),size=20)
    assert x.shape==y.shape==(20,3)
    assert all((last_x,last_y)==(0,-100) for last_x,last_y in zip(x[x[:,1]==8,-1].tolist(),y[x[:,1]==8,-1].tolist()))


def test_deferral_mass_is_limited_without_discarding_legitimate_uncertainty():
    rows=[{'bucket':b,'prefix_family':str(i)} for i,b in enumerate(
        ['contextual','standalone','generic_deferral_candidate','generic_deferral_candidate'])]
    assert probabilities(rows)=={'contextual':.6,'standalone':.3,'generic_deferral_candidate':.1}


def test_interrupted_training_resumes_to_identical_weights_and_rng(tmp_path, monkeypatch):
    import signal
    import pytest
    import learning.conversation_v3 as trainer
    from brain.model import ElysiaTransformer, ModelConfig
    tokenizer = FastProjectTokenizer()
    torch.manual_seed(7)
    model = ElysiaTransformer(ModelConfig(vocab_size=tokenizer.vocab_size, block_size=512,
        num_layers=1, embedding_dim=16, num_heads=2, feedforward_dim=32, dropout=.1))
    base = tmp_path / 'initial.pt'
    torch.save({'model_config':model.config_dict(), 'model_state':model.state_dict(),
                'tokenizer':tokenizer.metadata()}, base)
    monkeypatch.setattr(trainer, 'BASE', base)
    monkeypatch.setattr(trainer, 'DEPLOYED', base)
    rows = [{'ids':[1,10,11,12,2], 'labels':[-100,-100,11,12,2], 'sampling_probability':.5},
            {'ids':[1,14,15,2], 'labels':[-100,-100,15,2], 'sampling_probability':.5}]
    monkeypatch.setattr(trainer, 'load_data', lambda: ({s:rows for s in ['train','validation','test']}, {'partitions':{}}))
    reference = tmp_path / 'reference'
    monkeypatch.setattr(trainer, 'OUT', reference)
    trainer.train(steps=2, max_seconds=60)
    resumed = tmp_path / 'resumed'
    monkeypatch.setattr(trainer, 'OUT', resumed)
    original_batch = trainer.batch
    def interrupted_batch(*args, **kwargs):
        result = original_batch(*args, **kwargs)
        signal.raise_signal(signal.SIGTERM)
        return result
    monkeypatch.setattr(trainer, 'batch', interrupted_batch)
    trainer.train(steps=2, max_seconds=60)
    partial = torch.load(resumed/'last.pt', weights_only=True)
    assert partial['progress']['step'] == 1
    assert not (resumed/'results.json').exists()
    monkeypatch.setattr(trainer, 'batch', original_batch)
    trainer.train(steps=2, max_seconds=60, resume=True)
    expected = torch.load(reference/'last.pt', weights_only=True)
    actual = torch.load(resumed/'last.pt', weights_only=True)
    assert actual['progress']['step'] == expected['progress']['step'] == 2
    for name in expected['model_state']:
        assert torch.equal(actual['model_state'][name], expected['model_state'][name])
    assert torch.equal(actual['batch_rng'], expected['batch_rng'])
    assert torch.equal(actual['torch_rng'], expected['torch_rng'])
    with pytest.raises(ValueError, match='Finalized'):
        trainer.train(steps=2, max_seconds=60, resume=True)
