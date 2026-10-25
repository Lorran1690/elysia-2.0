from learning.wiki_foundation import eligible


def article(text,title='Ciência',url='https://pt.wikipedia.org/wiki/Ciência'):
    return {'text':text,'title':title,'url':url}


def test_article_source_and_contact_filters():
    text='Um texto enciclopédico sobre processos naturais e suas consequências. '*10
    cleaned,reason=eligible(article(text))
    assert reason is None and cleaned==text.strip()
    assert eligible(article(text,url='https://other.invalid/wiki/x'))[1]=='non_portuguese_url'
    assert eligible(article(text,title='Ciência (desambiguação)'))[1]=='disambiguation'
    assert eligible(article(text+' pessoa@example.com'))[1]=='identifier_pattern'
    assert eligible(article('Muito curto.'))[1]=='length'
