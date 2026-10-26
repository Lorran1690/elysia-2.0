"""Bounded deterministic tools. No eval, shell, network or filesystem access."""
import ast
import hashlib
import json
import math
import operator
import re

OPS = {ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,
       ast.Div:operator.truediv,ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod,ast.Pow:operator.pow}


def calculate(expression):
    if len(expression) > 200:
        raise ValueError('Expressão longa demais.')
    try:
        tree = ast.parse(expression, mode='eval')
    except (SyntaxError, RecursionError):
        raise ValueError('Expressão aritmética inválida.') from None
    if sum(1 for _ in ast.walk(tree)) > 64:
        raise ValueError('Expressão complexa demais.')
    def bounded(value):
        if type(value) not in (int,float) or not math.isfinite(value) or abs(value)>1e100:
            raise ValueError('Número fora do limite permitido.')
        return value
    def visit(node):
        if isinstance(node,ast.Constant):
            return bounded(node.value)
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            value=visit(node.operand)
            return value if isinstance(node.op,ast.UAdd) else -value
        if isinstance(node,ast.BinOp) and type(node.op) in OPS:
            left,right=visit(node.left),visit(node.right)
            if isinstance(node.op,ast.Pow) and abs(right)>12:
                raise ValueError('Expoente fora do limite de -12 a 12.')
            try:
                return bounded(OPS[type(node.op)](left,right))
            except (ZeroDivisionError,OverflowError,TypeError):
                raise ValueError('Operação inválida ou divisão por zero.') from None
        raise ValueError('Use somente números e operadores aritméticos.')
    return visit(tree.body)


def run_tool(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('text'),str) or len(payload['text'])>20000:
        raise ValueError('Entrada inválida ou longa demais.')
    text=payload['text'];tool=payload.get('tool')
    if tool=='calculator':
        return {'result':str(calculate(text.strip()))}
    if tool=='sha256':
        return {'result':hashlib.sha256(text.encode('utf-8')).hexdigest()}
    if tool=='text_stats':
        return {'result':{'characters':len(text),'words':len(re.findall(r'\w+',text)),
                          'lines':len(text.splitlines()) if text else 0,'utf8_bytes':len(text.encode('utf-8'))}}
    if tool=='json_validate':
        def pairs(items):
            result={}
            for key,value in items:
                if key in result:raise ValueError('JSON contém chave duplicada: '+key)
                result[key]=value
            return result
        def constant(value):
            raise ValueError('Constante não permitida em JSON: '+value)
        try:
            value=json.loads(text,object_pairs_hook=pairs,parse_constant=constant)
            json.dumps(value,allow_nan=False)
        except (ValueError,RecursionError) as exc:
            raise ValueError('JSON inválido: '+str(exc)) from None
        return {'result':'JSON válido. Tipo principal: '+type(value).__name__+'. O texto original foi preservado.'}
    raise ValueError('Ferramenta desconhecida.')
