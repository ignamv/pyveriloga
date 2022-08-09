from lexer import tok, lex
import pytest
import hir
import parsetree as pt
from manual_parser import Parser
from lower_parsetree import LowerParseTree
from verilogatypes import VAType
from preprocessor import VerilogAPreprocessor
from vabuiltins import builtins
from symboltable import SymbolTable
from functools import singledispatch
from utils import DISCIPLINES


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
    actual = LowerParseTree(context).lower(parsetree).strip_parsed()
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
    sourcefile = lowerer.lower(parsetree).strip_parsed()
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
charge = hir.Nature(name="Charge", units="coul", abstol=1e-14)
charge.access = hir.Accessor(name="Q", nature=charge)
current = hir.Nature(name="Current", units="A", idt_nature=charge, abstol=1e-12)
current.access = hir.Accessor(name="I", nature=current)
charge.ddt_nature = current
voltage = hir.Nature(name="Voltage", units="V", abstol=1e-6)
voltage.access = hir.Accessor(name="V", nature=voltage)
electrical = hir.Discipline(name="electrical", potential=voltage, flow=current)
net1 = hir.Net(name="net1", discipline=electrical)
net2 = hir.Net(name="net2", discipline=electrical)


@pytest.mark.parametrize(
    "statement_source,statement_lowered",
    [
        (
            "int1 = real2 * int2",
            hir.Assignment(
                lvalue=int1,
                value=hir.FunctionCall(
                    function=builtins.cast_real_to_int,
                    arguments=(
                        hir.FunctionCall(
                            function=builtins.real_product,
                            arguments=(
                                real2,
                                hir.FunctionCall(
                                    function=builtins.cast_int_to_real,
                                    arguments=(int2,),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        (
            "if (real1) int1 = int2",
            hir.If(
                condition=real1,
                then=hir.Assignment(lvalue=int1, value=int2),
            ),
        ),
        (
            "if (real1) int1 = int2 else int2 = int1",
            hir.If(
                condition=real1,
                then=hir.Assignment(lvalue=int1, value=int2),
                else_=hir.Assignment(lvalue=int2, value=int1),
            ),
        ),
        (
            "I(net1) <+ 4.5",
            hir.AnalogContribution(
                plus=net1, minus=None, type_="flow", value=hir.Literal(4.5)
            ),
        ),
        (
            "I(net1,net2) <+ 4.5",
            hir.AnalogContribution(
                plus=net1, minus=net2, type_="flow", value=hir.Literal(4.5)
            ),
        ),
        (
            "V(net1) <+ 4.5",
            hir.AnalogContribution(
                plus=net1, minus=None, type_="potential", value=hir.Literal(4.5)
            ),
        ),
        (
            "V(net1,net2) <+ 4.5",
            hir.AnalogContribution(
                plus=net1, minus=net2, type_="potential", value=hir.Literal(4.5)
            ),
        ),
    ],
)
def test_lower_parsetree_statement(statement_source, statement_lowered):
    source = (
        DISCIPLINES
        + f"""
module mymod(net1, net2);
inout electrical net1, net2;
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
    sourcefile = LowerParseTree(contexts=contexts).lower(parsetree).strip_parsed()
    electrical = sourcefile.modules[0].nets[0].discipline
    expected_module = hir.Module(
        name="mymod",
        nets=[
            hir.Net(name="net1", discipline=electrical),
            hir.Net(name="net2", discipline=electrical),
        ],
        ports=[
            hir.Port(name="net1", direction="inout"),
            hir.Port(name="net2", direction="inout"),
        ],
        variables=[real1, real2, int1, int2],
        statements=[statement_lowered],
    )
    assert len(sourcefile.modules) == 1
    assert sourcefile.modules[0] == expected_module
