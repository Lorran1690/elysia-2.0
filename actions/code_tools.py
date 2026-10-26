"""Code scaffolds and syntax checks; never execute submitted programs."""
import ast
import html
import json

EXTENSIONS={'python':'py','javascript':'js','html':'html','css':'css','json':'json'}


def scaffold(language,title):
    if not isinstance(language,str) or language not in EXTENSIONS or not isinstance(title,str) or not 1<=len(title.strip())<=80:
        raise ValueError('Linguagem ou nome de projeto inválido.')
    title=title.strip()
    templates={
        'python':f'''"""Script inicial criado a partir de um modelo local."""\n\ndef main():\n    print({title!r})\n\n\nif __name__ == "__main__":\n    main()\n''',
        'javascript':f'''// Módulo inicial. Edite e teste no seu ambiente de desenvolvimento.\nexport function mensagem() {{\n  return {json.dumps(title,ensure_ascii=False)};\n}}\n''',
        'html':f'''<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n<title>{html.escape(title)}</title>\n<style>body{{font:18px system-ui;background:#100d20;color:#eee;padding:40px}}h1{{color:#a78bfa}}</style>\n</head>\n<body><h1>{html.escape(title)}</h1><p>Seu projeto começa aqui.</p></body>\n</html>\n''',
        'css':'/* Estilo inicial */\n:root { color-scheme: dark; }\nbody { margin: 0; padding: 32px; font: 18px system-ui; background: #100d20; color: #eee; }\n',
        'json':json.dumps({'projeto':title,'versao':1,'itens':[]},ensure_ascii=False,indent=2)+'\n',
    }
    return {'code':templates[language],'extension':EXTENSIONS[language],
            'origin':'Modelo inicial determinístico; não gerado por um modelo de linguagem.'}


def validate_python(text):
    try:
        tree=ast.parse(text,mode='exec')
        compile(tree, '<editor>', 'exec', dont_inherit=True)
    except SyntaxError as exc:
        raise ValueError(f'Sintaxe Python inválida na linha {exc.lineno}, coluna {exc.offset}: {exc.msg}') from None
    except (ValueError,RecursionError):
        raise ValueError('Código inválido ou complexo demais para análise.') from None
    return {'result':f'Sintaxe Python válida: {len(text.splitlines())} linhas, {sum(1 for _ in ast.walk(tree))} elementos. Nenhum código foi executado.'}
