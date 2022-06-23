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
int myint;
endmodule
"""
    assert parse(src, "start_module") == Module(
        name=Identifier(name="mymodule"),
        ports=[
            Port(name=Identifier(name="pin1"), nature=None, direction="inout"),
            Port(name=Identifier(name="pin2"), nature=None, direction="inout"),
        ],
        reals=[
            InitializedVariable(
                name=Identifier(name="myreal"), type="real", initializer=None
            )
        ],
        integers=[],
        nets=[Identifier(name="mynet"), Identifier(name="myint")],
    )
