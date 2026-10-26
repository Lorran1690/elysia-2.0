import ast
import pytest
from actions.code_tools import scaffold, validate_python
from actions.local_tools import run_tool


def test_python_scaffold_is_valid_and_quotes_project_name_as_data():
    for title in ['Meu projeto','x\nprint("unsafe")','"""\\\x00']:
        value=scaffold('python',title)
        ast.parse(value['code'])
        assert value['extension']=='py'


def test_code_validation_never_executes_program(tmp_path):
    target=tmp_path/'must-not-exist'
    assert 'Nenhum código foi executado' in validate_python(f'open({str(target)!r}, "w").write("x")')['result']
    assert not target.exists()
    with pytest.raises(ValueError,match='linha'):
        validate_python('def broken(:')


def test_scaffold_escapes_html_title_and_routes_explicit_tool():
    value=run_tool({'tool':'code_scaffold','language':'html','text':'<script>test</script>'})
    assert '&lt;script&gt;test&lt;/script&gt;' in value['code']
    assert run_tool({'tool':'python_validate','text':'value = 18'})['result'].startswith('Sintaxe Python válida')
    with pytest.raises(ValueError):scaffold('shell','x')


@pytest.mark.parametrize('text',['return 1','break'])
def test_code_validation_rejects_invalid_statement_context(text):
    with pytest.raises(ValueError,match='Sintaxe Python inválida'):
        validate_python(text)
