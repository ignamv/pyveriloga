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
from utils import DISCIPLINES

@singledispatch
def strip_parsed(node: hir.HIR) -> hir.HIR:
    """Set `parsed` field to None recursively to make test cases more concise"""
    return replace(node, parsed=None)


@strip_parsed.register
def _(node: hir.Discipline):
    return replace(
        node,
        parsed=None,
        flow=strip_parsed(node.flow),
        potential=strip_parsed(node.potential),
    )


@strip_parsed.register
def _(node: hir.Net):
    return replace(node, parsed=None, discipline=strip_parsed(node.discipline))


@strip_parsed.register
def _(node: hir.FunctionCall):
    return replace(
        node, parsed=None, arguments=tuple(map(strip_parsed, node.arguments))
    )


@strip_parsed.register
def _(node: hir.Variable):
    return replace(
        node,
        parsed=None,
        initializer=strip_parsed(node.initializer)
        if node.initializer is not None
        else None,
    )


@strip_parsed.register
def _(node: hir.Assignment):
    return replace(
        node,
        parsed=None,
        lvalue=strip_parsed(node.lvalue),
        value=strip_parsed(node.value),
    )


@strip_parsed.register
def _(node: hir.Block):
    return replace(
        node, parsed=None, statements=list(map(strip_parsed, node.statements))
    )


@strip_parsed.register
def _(node: hir.If):
    return replace(
        node,
        parsed=None,
        condition=strip_parsed(node.condition),
        then=strip_parsed(node.then),
        else_=strip_parsed(node.else_) if node.else_ is not None else None,
    )


@strip_parsed.register
def _(node: hir.SourceFile):
    return replace(node, parsed=None, modules=list(map(strip_parsed, node.modules)))


@strip_parsed.register
def _(module: hir.Module):
    return replace(
        module,
        parsed=None,
        ports=list(map(strip_parsed, module.ports)),
        nets=list(map(strip_parsed, module.nets)),
        branches=list(map(strip_parsed, module.branches)),
        parameters=list(map(strip_parsed, module.parameters)),
        variables=list(map(strip_parsed, module.variables)),
        statements=list(map(strip_parsed, module.statements)),
    )


syms = {
    var.name: var
    for var in (
        hir.Variable(name="real1", type_=VAType.real, initializer=hir.Literal(1.5)),
        hir.Variable(name="real2", type_=VAType.real, initializer=hir.Literal(2.5)),
        hir.Variable(name="int1", type_=VAType.integer, initializer=hir.Literal(1)),
        hir.Variable(name="int2", type_=VAType.integer, initializer=hir.Literal(2)),
    )
}


@pytest.mark.parametrize(
    "source,expected",
    [
        ("3", hir.Literal(3)),
        ("real1", syms["real1"]),
        ("3.5", hir.Literal(3.5)),
        (
            "3.5 + 4.5",
            hir.FunctionCall(
                builtins.real_addition, (hir.Literal(3.5), hir.Literal(4.5))
            ),
        ),
        (
            "int1 + int2",
            hir.FunctionCall(builtins.integer_addition, (syms["int1"], syms["int2"])),
        ),
        (
            "1+2*3",
            hir.FunctionCall(
                builtins.integer_addition,
                (
                    hir.Literal(1),
                    hir.FunctionCall(
                        builtins.integer_product, (hir.Literal(2), hir.Literal(3))
                    ),
                ),
            ),
        ),
        (
            "1*(2+3)",
            hir.FunctionCall(
                builtins.integer_product,
                (
                    hir.Literal(1),
                    hir.FunctionCall(
                        builtins.integer_addition, (hir.Literal(2), hir.Literal(3))
                    ),
                ),
            ),
        ),
        (
            "1*2+3",
            hir.FunctionCall(
                builtins.integer_addition,
                (
                    hir.FunctionCall(
                        builtins.integer_product,
                        (hir.Literal(1), hir.Literal(2)),
                    ),
                    hir.Literal(3),
                ),
            ),
        ),
        (
            "int1+3",
            hir.FunctionCall(
                builtins.integer_addition, arguments=(syms["int1"], hir.Literal(3))
            ),
        ),
        (
            "int1+3.5",
            hir.FunctionCall(
                builtins.real_addition,
                arguments=(
                    hir.FunctionCall(builtins.cast_int_to_real, (syms["int1"],)),
                    hir.Literal(3.5),
                ),
            ),
        ),
        (
            "2 == 3",
            hir.FunctionCall(
                builtins.integer_equality, (hir.Literal(2), hir.Literal(3))
            ),
        ),
        (
            "2 != 3.0",
            hir.FunctionCall(
                builtins.real_inequality,
                (
                    hir.FunctionCall(builtins.cast_int_to_real, (hir.Literal(2),)),
                    hir.Literal(3.0),
                ),
            ),
        ),
        ("$temperature", builtins["$temperature"]),
        (
            "pow(2, 3.0)",
            hir.FunctionCall(
                builtins.pow,
                (
                    hir.FunctionCall(builtins.cast_int_to_real, (hir.Literal(2),)),
                    hir.Literal(3.0),
                ),
            ),
        ),
    ],
)
def test_lower_parsetree_expression(source: str, expected: hir.HIR):
    symbols = list(syms.values()) + list(builtins.symbols.values())
    context = [(hir.SourceFile(), SymbolTable(symbols))]
    tokens = list(VerilogAPreprocessor(lex(content=source)))
    parser = Parser(tokens)
    parsetree = parser.expression()
    assert not list(parser.peekiterator), "Not all input was consumed"
    actual = strip_parsed(LowerParseTree(context).lower(parsetree))
    assert actual == expected


def test_lower_parsetree_disciplines():
    source = (
        DISCIPLINES
        + """
module mymod(p1);
inout electrical p1;
endmodule
"""
    )
    expected = 3
    tokens = list(VerilogAPreprocessor(lex(content=source)))
    parser = Parser(tokens)
    parsetree = parser.sourcefile()
    assert not list(parser.peekiterator), "Not all input was consumed"
    contexts = [(hir.SourceFile(), SymbolTable(builtins.symbols.values()))]
    lowerer = LowerParseTree(contexts=contexts)
    sourcefile = strip_parsed(lowerer.lower(parsetree))
    discipline = sourcefile.modules[0].nets[0].discipline
    assert discipline.name == "electrical"
    assert discipline.potential.name == "Voltage"
    assert discipline.potential.abstol == 1e-6
    assert discipline.flow.name == "Current"
    assert discipline.flow.abstol == 1e-12
    assert discipline.flow.idt_nature.name == "Charge"


real1 = hir.Variable(name="real1", type_=VAType.real, initializer=None)
real2 = hir.Variable(name="real2", type_=VAType.real, initializer=hir.Literal(4.5))
int1 = hir.Variable(name="int1", type_=VAType.integer, initializer=hir.Literal(4))
int2 = hir.Variable(name="int2", type_=VAType.integer, initializer=None)


@pytest.mark.parametrize(
    "statement_source,statement_lowered",
    [
        (
            "int1 = real2 * int2",
            hir.Assignment(
                lvalue=int1,
                value=hir.FunctionCall(function=builtins.cast_real_to_int, arguments=(hir.FunctionCall(
                    function=builtins.real_product,
                    arguments=(
                        real2,
                        hir.FunctionCall(
                            function=builtins.cast_int_to_real, arguments=(int2,)
                        ),
                    ),
                ),)),
            ),
        ),
        (
            "if (real1) int1 = int2",
            hir.If(
                condition=real1,
                then=hir.Assignment(lvalue=int1, value=int2),
            )
        ),
        (
            "if (real1) int1 = int2 else int2 = int1",
            hir.If(
                condition=real1,
                then=hir.Assignment(lvalue=int1, value=int2),
                else_=hir.Assignment(lvalue=int2, value=int1),
            )
        ),
    ],
)
def test_lower_parsetree_statement(statement_source, statement_lowered):
    source = (
        DISCIPLINES
        + f"""
module mymod(p1, p2);
inout electrical p1, p2;
real real1, real2=4.5;
integer int1=4, int2;
analog {statement_source}
endmodule
"""
    )
    tokens = list(VerilogAPreprocessor(lex(content=source)))
    parser = Parser(tokens)
    parsetree = parser.sourcefile()
    assert not list(parser.peekiterator), "Not all input was consumed"
    contexts = [(None, SymbolTable(builtins.symbols.values()))]
    sourcefile = strip_parsed(LowerParseTree(contexts=contexts).lower(parsetree))
    electrical = sourcefile.modules[0].nets[0].discipline
    expected_module = hir.Module(
        name="mymod",
        nets=[
            hir.Net(name="p1", discipline=electrical),
            hir.Net(name="p2", discipline=electrical),
        ],
        ports=[
            hir.Port(name="p1", direction="inout"),
            hir.Port(name="p2", direction="inout"),
        ],
        variables=[real1, real2, int1, int2],
        statements=[statement_lowered],
    )
    assert len(sourcefile.modules) == 1
    assert sourcefile.modules[0] == expected_module
