from lexer import tok, lex
import pytest
import hir
import parsetree as pt
from manual_parser import Parser
from lower_parsetree import LowerParseTree
from verilogatypes import VAType
from preprocessor import VerilogAPreprocessor
from dataclasses import replace
from vabuiltins import builtins
from symboltable import SymbolTable
from functools import singledispatch

@singledispatch
def strip_parsed(node: hir.HIR) -> hir.HIR:
    """Set `parsed` field to None recursively to make test cases more concise"""
    return replace(node, parsed=None)

@strip_parsed.register
def _(node: hir.Discipline):
    return replace(node, parsed=None, flow=strip_parsed(node.flow), potential=strip_parsed(node.potential))

@strip_parsed.register
def _(node: hir.Net):
    return replace(node, parsed=None, discipline=strip_parsed(node.discipline))

@strip_parsed.register
def _(node: hir.FunctionCall):
    return replace(node, parsed=None, arguments=tuple(map(strip_parsed,node.arguments)))

@strip_parsed.register
def _(node: hir.Variable):
    return replace(node, parsed=None, initializer=strip_parsed(node.initializer))

@strip_parsed.register
def _(node: hir.Assignment):
    return replace(node, parsed=None, lvalue=strip_parsed(node.lvalue), value=strip_parsed(node.value))

@strip_parsed.register
def _(node: hir.Block):
    return replace(node, parsed=None, statements=list(map(strip_parsed,node.statements)))

@strip_parsed.register
def _(node: hir.If):
    return replace(node, parsed=None, condition=strip_parsed(node.condition), then=strip_parsed(node.then), else_=strip_parsed(node.else_))


@strip_parsed.register
def _(node: hir.If):
    return replace(node, parsed=None, 
            ports=list(map(strip_parsed, node.ports)),
            nets=list(map(strip_parsed, node.nets)),
            branches=list(map(strip_parsed, node.branches)),
            parameters=list(map(strip_parsed, node.parameters)),
            statements=list(map(strip_parsed, node.statements)),
            )


@strip_parsed.register
def _(node: hir.SourceFile):
    return replace(node, parsed=None, 
            modules=list(map(strip_parsed, node.modules)))

syms = {
    var.name: var
    for var in (
        hir.Variable(name="real1", type_=VAType.real, initializer=hir.Literal(1.5)),
        hir.Variable(name="real2", type_=VAType.real, initializer=hir.Literal(2.5)),
        hir.Variable(name="int1", type_=VAType.integer, initializer=hir.Literal(1)),
        hir.Variable(name="int2", type_=VAType.integer, initializer=hir.Literal(2)),
    )
}

@pytest.mark.parametrize('source,expected', [
    ('3', hir.Literal(3)),
    ('real1', syms['real1']),
    ('3.5', hir.Literal(3.5)),
    ('3.5 + 4.5', hir.FunctionCall(builtins.real_addition, (hir.Literal(3.5), hir.Literal(4.5)))),
    ('int1 + int2',  hir.FunctionCall(builtins.integer_addition, (syms['int1'], syms['int2']))),
    ("1+2*3", hir.FunctionCall( builtins.integer_addition, ( hir.Literal(1), hir.FunctionCall( builtins.integer_product, (hir.Literal(2), hir.Literal(3)))))),
    ( "1*(2+3)", hir.FunctionCall( builtins.integer_product, ( hir.Literal(1), hir.FunctionCall( builtins.integer_addition, (hir.Literal(2), hir.Literal(3)))))),
    ( "1*2+3", hir.FunctionCall( builtins.integer_addition, ( hir.FunctionCall( builtins.integer_product, (hir.Literal(1), hir.Literal(2)),), hir.Literal(3)))),
    ("int1+3", hir.FunctionCall( builtins.integer_addition, arguments=(syms["int1"], hir.Literal(3)))),
    ("int1+3.5", hir.FunctionCall( builtins.real_addition, arguments=( hir.FunctionCall( builtins.cast_int_to_real, (syms["int1"],)), hir.Literal(3.5)))),
    ("2 == 3", hir.FunctionCall( builtins.integer_equality, (hir.Literal(2), hir.Literal(3)))),
    ("2 != 3.0", hir.FunctionCall( builtins.real_inequality, ( hir.FunctionCall( builtins.cast_int_to_real, (hir.Literal(2),)), hir.Literal(3.0)))),
    ("$temperature", builtins["$temperature"]),
])
def test_lower_parsetree(source: str, expected: hir.HIR):
    symbols = list(syms.values()) + list(builtins.symbols.values())
    context = [(hir.SourceFile(), SymbolTable(symbols))]
    tokens = list(VerilogAPreprocessor(lex(content=source)))
    parser = Parser(tokens)
    parsetree = parser.expression()
    assert not list(parser.peekiterator), 'Not all input was consumed'
    actual = strip_parsed(LowerParseTree(context).lower(parsetree))
    assert actual == expected
