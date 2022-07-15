from lexer import tok
import pytest
import hir
import parsetree as pt
from lower_parsetree import lower_parsetree
from dataclasses import replace
from vabuiltins import builtins

def strip_parsed(hirnode: hir.HIR) -> hir.HIR:
    fields = [field for field in dir(hirnode) if not field.startswith('_')]
    replacements = {}
    for field in fields:
        value = getattr(hirnode, field)
        if value.__class__.__module__ != 'hir':
            continue
        replacements[field] = strip_parsed(value)
    if 'parsed' in fields:
        replacements['parsed'] = None
    return replace(hirnode, **replacements)

@pytest.mark.parametrize('parsetree,expected', [
    (pt.Literal(tok(3)), hir.Literal(3)),
    (pt.Literal(tok(3.5)), hir.Literal(3.5)),
    (pt.Operation(tok.PLUS, [pt.Literal(tok(3.5)), pt.Literal(tok(4.5))]), hir.FunctionCall(builtins['builtin.real_addition'], [hir.Literal(3.5), hir.Literal(4.5)])),
])
def test_lower_parsetree(parsetree: pt.ParseTree, expected: hir.HIR):
    assert strip_parsed(lower_parsetree(parsetree)) == expected
