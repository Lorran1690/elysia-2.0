import math
from learning.curriculum_v2 import (lexical_features, probabilities, prefix_candidates,
                                    select_per_group, encode_target)
from learning.dialogue_v2_data import FastProjectTokenizer


def target(bucket,family,group,index=0):
    return {'bucket':bucket,'prefix_family':family,'source_group_id':group,
            'source_record_id':group,'preceding_pairs':index,'assistant_pair_index':index}


def test_generic_uncertainty_is_preserved_with_bounded_mass():
    rows=[target('generic_deferral_candidate','same',str(i)) for i in range(30)]
    rows += [target('contextual','context', 'c',1),target('standalone','other','s')]
    mass=probabilities(rows)
    assert math.isclose(mass['generic_deferral_candidate'],0.1)
    assert math.isclose(mass['contextual'],0.6)
    assert all(r['sampling_probability']>0 for r in rows)
    assert math.isclose(sum(r['sampling_probability'] for r in rows),1)


def test_missing_bucket_mass_stays_with_substantive_targets():
    mass=probabilities([target('standalone','a','a'),target('generic_deferral_candidate','b','b')])
    assert math.isclose(mass['standalone'],0.9)
    assert math.isclose(mass['generic_deferral_candidate'],0.1)


def test_context_is_complete_and_earlier_answers_are_not_supervised():
    tokenizer=FastProjectTokenizer()
    row={'id':'a','group_id':'g','messages':[
        {'role':'user','content':'Meu nome é Tereza.'},
        {'role':'assistant','content':'Olá, Tereza. Como posso ajudar?'},
        {'role':'user','content':'Como me chamo?'},
        {'role':'assistant','content':'Seu nome é Tereza.'}]}
    rows,_,_=prefix_candidates(tokenizer,row,2048)
    final=rows[-1];assert final['preceding_pairs']==1
    ids,labels=encode_target(tokenizer,row['messages'],final)
    assert tokenizer.decode(ids).startswith('Usuário: Meu nome é Tereza.')
    supervised=[t for t in labels if t!=-100]
    assert tokenizer.decode(supervised)=='Seu nome é Tereza.'
    short,why,_=prefix_candidates(tokenizer,row,rows[0]['tokens_with_bos']-1)
    assert len(short)==1
    assert why['complete_history_exceeds_context']==1


def test_group_limit_and_lexical_repetition_flags():
    rows=[target('contextual','a','shared',1),target('contextual','b','shared',3),
          target('standalone','c','shared'),target('generic_deferral_candidate','d','shared',2)]
    selected=select_per_group(rows)
    assert len(selected)==2
    assert selected[0]['preceding_pairs']==3
    assert lexical_features('Não tenho acesso a informações particulares.')['generic_deferral_candidate']
    assert lexical_features('uma resposta sem relação alguma ' * 20)['strong_repetition']
    assert not lexical_features('Não sei sua senha. Você pode verificar o roteador.')['strong_repetition']
