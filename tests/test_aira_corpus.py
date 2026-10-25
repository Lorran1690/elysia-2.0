from learning.aira_corpus import assign_groups, filter_messages, leakage_keys


def conversation(root, answer='Uma explicação completa e suficientemente longa.'):
    return [{'role': 'user', 'content': root}, {'role': 'assistant', 'content': answer}]


def test_shared_roots_and_transitive_messages_never_cross_partitions():
    shared = 'Um trecho de resposta suficientemente longo para conectar conversas diferentes sem dividir seus conteúdos. '
    records = [
        {'id': 'a', 'messages': conversation('primeira pergunta', shared)},
        {'id': 'b', 'messages': conversation('segunda pergunta', shared)},
        {'id': 'c', 'messages': conversation('segunda pergunta', 'Outra resposta adequada para o mesmo tema.')},
    ]
    assign_groups(records)
    assert len({r['group_id'] for r in records}) == 1
    assert len({r['split'] for r in records}) == 1
    reversed_records = list(reversed([dict(r) for r in records]))
    assign_groups(reversed_records)
    assert {r['id']: r['group_id'] for r in records} == {r['id']: r['group_id'] for r in reversed_records}


def test_rejects_identifiers_external_personas_and_incomplete_turns():
    assert filter_messages(conversation('meu email: pessoa@example.com')) == 'possible_identifier'
    assert filter_messages(conversation('telefone 11999999999')) == 'possible_identifier'
    assert filter_messages(conversation('Olá', 'Sou ChatGPT, em que posso ajudar você?')) == 'external_identity_or_impersonation'
    assert filter_messages(conversation('Olá')[:1]) == 'turn_count'
    assert filter_messages(conversation('Explique a formação das nuvens.')) is None


def test_normalization_detects_same_prompt_with_accents_and_spacing():
    assert leakage_keys(conversation(' CAFÉ  quente ')) == leakage_keys(conversation('cafe\u0301 quente'))


def test_historical_keys_tolerates_manifest_counters():
    from learning.aira_corpus import historical_keys
    assert historical_keys()
