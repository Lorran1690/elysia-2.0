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
