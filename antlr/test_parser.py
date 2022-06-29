import pytest
from parser import (
    parse,
    Float,
    Identifier,
    Int,
    BinaryOp,
    UnaryOp,
    Nature,
    Discipline,
    Port,
    InitializedVariable,
    Module,
    Analog,
    AnalogContribution,
    AnalogSequence,
    VariableAssignment,
    FunctionCall,
    Variables,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("33", Int(33)),
        ("33.0", Float(33)),
        ("hola", Identifier("hola")),
        ("-hola", UnaryOp("-", Identifier("hola"))),
        ("-33.0", UnaryOp("-", Float(33))),
        ("hola ** 3", BinaryOp("**", Identifier("hola"), Int(3))),
        (
            "2 * (hola + 3)",
            BinaryOp("*", Int(2), BinaryOp("+", Identifier("hola"), Int(3))),
        ),
        (
            "(hola + 3) * 2",
            BinaryOp("*", BinaryOp("+", Identifier("hola"), Int(3)), Int(2)),
        ),
        ("-hola ** 3", BinaryOp("**", UnaryOp("-", Identifier("hola")), Int(3))),
        (
            "2 * hola ** 3",
            BinaryOp("*", Int(2), BinaryOp("**", Identifier("hola"), Int(3))),
        ),
        ("2 + hola", BinaryOp("+", Int(2), Identifier("hola"))),
        (
            "4 + 2 * hola ** 3",
            BinaryOp(
                "+",
                Int(4),
                BinaryOp("*", Int(2), BinaryOp("**", Identifier("hola"), Int(3))),
            ),
        ),
        (
            "2 * hola ** 3 + 4",
            BinaryOp(
                "+",
                BinaryOp("*", Int(2), BinaryOp("**", Identifier("hola"), Int(3))),
                Int(4),
            ),
        ),
        (
            "-1 || 2 && 3 == 4 < 5 + 6 * 7 ** 8",
            BinaryOp(
                "||",
                UnaryOp("-", Int(1)),
                BinaryOp(
                    "&&",
                    Int(2),
                    BinaryOp(
                        "==",
                        Int(3),
                        BinaryOp(
                            "<",
                            Int(4),
                            BinaryOp(
                                "+",
                                Int(5),
                                BinaryOp("*", Int(6), BinaryOp("**", Int(7), Int(8))),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        (
            "-1 ** 2 * 3 + 4 < 5 == 6 && 7 || 8",
            BinaryOp(
                "||",
                BinaryOp(
                    "&&",
                    BinaryOp(
                        "==",
                        BinaryOp(
                            "<",
                            BinaryOp(
                                "+",
                                BinaryOp(
                                    "*",
                                    BinaryOp("**", UnaryOp("-", Int(1)), Int(2)),
                                    Int(3),
                                ),
                                Int(4),
                            ),
                            Int(5),
                        ),
                        Int(6),
                    ),
                    Int(7),
                ),
                Int(8),
            ),
        ),
        # ('-hola + 3', BinaryOp('+', UnaryOp('-', Identifier('hola')), Int(3))),
        # ('2 + 3 * 4', BinaryOp('+', Int(2), BinaryOp('*', Int(3), Int(4)))),
    ],
)
def test_parse_expression(text, expected):
    assert parse(text, "start_expression") == expected


def test_parse_nature():
    src = """
nature Current; 
  units        = "A";
  access       = I;
  idt_nature   = Charge;
  abstol       = 1e-12;
endnature 
"""
    assert parse(src, "start_nature") == Nature(
        name="Current",
        abstol=1e-12,
        access="I",
        idt_nature="Charge",
        units="A",
        ddt_nature=None,
    )


def test_parse_discipline():
    src = r"""
discipline \logic ; 
  domain discrete;
  potential    Voltage;
  flow         Current;
enddiscipline 
"""
    assert parse(src, "start_discipline") == Discipline(
        name=Identifier(name="\\logic"),
        domain="discrete",
        potentialnature="Voltage",
        flownature="Current",
    )


def test_parse_module_ports():
    src = """
module mymodule (pin1, pin2);
inout pin1, pin2;
real myreal;
electrical mynet;
integer myint;

analog I(pin1, pin2) <+ 3;

analog V(pin1) <+ 7;

analog begin: mylabel
    real analogreal;
    myreal = 2 * (1 + V(pin1, pin2));
    analogreal = V(pin1);
    V(pin2) <+ 7;
end

endmodule
"""
    assert parse(src, "start_module") == Module(
        name="mymodule",
        ports=[
            Port(name="pin1", nature=None, direction="inout"),
            Port(name="pin2", nature=None, direction="inout"),
        ],
        variables=Variables(
            {
                "myreal": InitializedVariable(
                    name="myreal", type="real", initializer=None
                ),
                "myint": InitializedVariable(
                    name="myint", type="integer", initializer=None
                ),
            }
        ),
        nets=["mynet"],
        analogs=[
            Analog(
                content=AnalogContribution(
                    accessor="I", lvalue1="pin1", lvalue2="pin2", rvalue=Int(value=3)
                )
            ),
            Analog(
                content=AnalogContribution(
                    accessor="V", lvalue1="pin1", lvalue2=None, rvalue=Int(value=7)
                )
            ),
            Analog(
                content=AnalogSequence(
                    variables=Variables(
                        {
                            "analogreal": InitializedVariable(
                                name="analogreal", type="real", initializer=None
                            )
                        }
                    ),
                    statements=[
                        VariableAssignment(
                            name="myreal",
                            value=BinaryOp(
                                operator="*",
                                left=Int(value=2),
                                right=BinaryOp(
                                    operator="+",
                                    left=Int(value=1),
                                    right=FunctionCall(
                                        name="V",
                                        arguments=[
                                            Identifier(name="pin1"),
                                            Identifier(name="pin2"),
                                        ],
                                    ),
                                ),
                            ),
                        ),
                        VariableAssignment(
                            name="analogreal",
                            value=FunctionCall(
                                name="V", arguments=[Identifier(name="pin1")]
                            ),
                        ),
                        AnalogContribution(
                            accessor="V",
                            lvalue1="pin2",
                            lvalue2=None,
                            rvalue=Int(value=7),
                        ),
                    ],
                )
            ),
        ],
    )
