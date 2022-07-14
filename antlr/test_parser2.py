import pytest
from parser import parse, MyVisitor
from verilogatypes import VAType
from symboltable import SymbolTable
from vabuiltins import builtins
import hir

disciplines = """
nature Current; 
  units        = "A";
  access       = I;
  idt_nature   = Charge;
  abstol       = 1e-12;
endnature 

nature Voltage; 
  units      = "V";
  access     = V;
  idt_nature = Flux;
  abstol     = 1e-6;
endnature 

discipline electrical; 
  potential    Voltage;
  flow         Current;
enddiscipline
"""
current = hir.Nature(name="Current", abstol=1e-12, access="I", units="A")
voltage = hir.Nature(name="Voltage", abstol=1e-06, access="V", units="V")
electrical = hir.Discipline(
    name="electrical", domain=None, potential=voltage, flow=current
)


def test_parse_discipline():
    pytest.skip()
    visitor = MyVisitor()
    parse(exprsource, rule="start_source_text", visitor=visitor)


expr_vars = {
    var.name: var
    for var in (
        hir.Variable(name="real1", type=VAType.real, initializer=hir.Literal(1.5)),
        hir.Variable(name="real2", type=VAType.real, initializer=hir.Literal(2.5)),
        hir.Variable(name="int1", type=VAType.integer, initializer=hir.Literal(1)),
        hir.Variable(name="int2", type=VAType.integer, initializer=hir.Literal(2)),
    )
}


@pytest.mark.parametrize(
    "exprsource,expected",
    [
        ("3", hir.Literal(3)),
        (
            "1+2*3",
            hir.FunctionCall(
                builtins["builtin.integer_addition"],
                (
                    hir.Literal(1),
                    hir.FunctionCall(
                        builtins["builtin.integer_product"],
                        (hir.Literal(2), hir.Literal(3)),
                    ),
                ),
            ),
        ),
        (
            "1*(2+3)",
            hir.FunctionCall(
                builtins["builtin.integer_product"],
                (
                    hir.Literal(1),
                    hir.FunctionCall(
                        builtins["builtin.integer_addition"],
                        (hir.Literal(2), hir.Literal(3)),
                    ),
                ),
            ),
        ),
        (
            "1*2+3",
            hir.FunctionCall(
                builtins["builtin.integer_addition"],
                (
                    hir.FunctionCall(
                        builtins["builtin.integer_product"],
                        (hir.Literal(1), hir.Literal(2)),
                    ),
                    hir.Literal(3),
                ),
            ),
        ),
        ("3.5", hir.Literal(3.5)),
        ("real1", expr_vars["real1"]),
        (
            "int1+3",
            hir.FunctionCall(
                builtins["builtin.integer_addition"],
                arguments=(expr_vars["int1"], hir.Literal(3)),
            ),
        ),
        (
            "int1+3.5",
            hir.FunctionCall(
                builtins["builtin.real_addition"],
                arguments=(
                    hir.FunctionCall(
                        builtins["builtin.cast_int_to_real"], (expr_vars["int1"],)
                    ),
                    hir.Literal(3.5),
                ),
            ),
        ),
        (
            "2 == 3",
            hir.FunctionCall(
                builtins["builtin.integer_equality"], (hir.Literal(2), hir.Literal(3))
            ),
        ),
        (
            "2 != 3.0",
            hir.FunctionCall(
                builtins["builtin.real_inequality"],
                (
                    hir.FunctionCall(
                        builtins["builtin.cast_int_to_real"], (hir.Literal(2),)
                    ),
                    hir.Literal(3.0),
                ),
            ),
        ),
        ("2 + $temperature", builtins["$temperature"]),
    ],
)
def test_parser_expr(exprsource, expected):
    module = hir.Module(name="dummymod")
    symboltable = SymbolTable()
    for var in expr_vars.values():
        symboltable.define(var)
    visitor = MyVisitor(context=[module], symboltable=symboltable)
    expr = parse(exprsource, rule="start_expression", visitor=visitor)
    assert expr == expected


@pytest.mark.parametrize(
    "statement_source, expected",
    [
        (
            "real1 = 3.5;",
            hir.Assignment(lvalue=expr_vars["real1"], value=hir.Literal(3.5)),
        ),
        (
            "real1 = 3;",
            hir.Assignment(
                lvalue=expr_vars["real1"],
                value=hir.FunctionCall(
                    builtins["builtin.cast_int_to_real"], (hir.Literal(3),)
                ),
            ),
        ),
        (
            "begin real1 = 3.5; real2 = 5.5; end",
            hir.Block(
                [
                    hir.Assignment(lvalue=expr_vars["real1"], value=hir.Literal(3.5)),
                    hir.Assignment(lvalue=expr_vars["real2"], value=hir.Literal(5.5)),
                ]
            ),
        ),
        (
            "if ( 2.3 ) real1 = 1.0;",
            hir.If(
                condition=hir.Literal(2.3),
                then=hir.Assignment(lvalue=expr_vars["real1"], value=hir.Literal(1.0)),
            ),
        ),
        ("if ( 2.3 ) ;", hir.If(condition=hir.Literal(2.3), then=None)),
        (
            "if ( 2.3 ) real1 = 1.0; else real2 = 2.0;",
            hir.If(
                condition=hir.Literal(2.3),
                then=hir.Assignment(lvalue=expr_vars["real1"], value=hir.Literal(1.0)),
                else_=hir.Assignment(lvalue=expr_vars["real2"], value=hir.Literal(2.0)),
            ),
        ),
        (
            "if ( 2.3 ) if(3.4) real1 = 1.0; else real2 = 2.0;",
            hir.If(
                condition=hir.Literal(2.3),
                then=hir.If(
                    condition=hir.Literal(3.4),
                    then=hir.Assignment(
                        lvalue=expr_vars["real1"], value=hir.Literal(1.0)
                    ),
                    else_=hir.Assignment(
                        lvalue=expr_vars["real2"], value=hir.Literal(2.0)
                    ),
                ),
            ),
        ),
    ],
)
def test_parser_analog_inner(statement_source, expected):
    module = hir.Module(name="dummymod")
    symboltable = SymbolTable()
    for var in expr_vars.values():
        symboltable.define(var)
    visitor = MyVisitor(context=[module], symboltable=symboltable)
    statement = parse(statement_source, rule="start_statement", visitor=visitor)
    assert statement == expected


def test_parser_analog():
    source = """
module mymod();
real real1, real2, real3;
analog real3 = real1 + real2;
endmodule
"""
    actual = parse(source, "start_source_text")
    assert actual == hir.SourceFile(
        modules=[
            hir.Module(
                name="mymod",
                statements=[
                    hir.Assignment(
                        lvalue=hir.Variable(
                            name="real3", type=VAType.real, initializer=None
                        ),
                        value=hir.FunctionCall(
                            function=builtins["builtin.real_addition"],
                            arguments=(
                                hir.Variable(
                                    name="real1", type=VAType.real, initializer=None
                                ),
                                hir.Variable(
                                    name="real2", type=VAType.real, initializer=None
                                ),
                            ),
                        ),
                    )
                ],
            )
        ]
    )


def test_parser_module():
    source = (
        disciplines
        + """
module mymod (inout electrical p1);
electrical mynet;
parameter real realparam = 3.5 from [-3.5:7] exclude 2;
(*desc= "Temperature coeff" *) parameter integer intparam = 3 exclude 42;
branch (p1, mynet) branch_twosided;
branch (p1) branch_onesided;
endmodule
"""
    )
    actual = parse(source, "start_source_text")
    p1 = hir.Port(name="p1", discipline=electrical, direction="inout")
    mynet = hir.Net(name="mynet", discipline=electrical)
    assert actual == hir.SourceFile(
        modules=[
            hir.Module(
                name="mymod",
                ports=[p1],
                nets=[p1, mynet],
                branches=[
                    hir.Branch(name="branch_twosided", net1=p1, net2=mynet),
                    hir.Branch(name="branch_onesided", net1=p1, net2=hir.ground),
                ],
                parameters=[
                    hir.Variable(
                        name="realparam", type=VAType.real, initializer=hir.Literal(3.5)
                    ),
                    hir.Variable(
                        name="intparam", type=VAType.integer, initializer=hir.Literal(3)
                    ),
                ],
                statements=[],
            )
        ]
    )
