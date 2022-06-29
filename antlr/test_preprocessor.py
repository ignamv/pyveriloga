import pytest
import dataclasses
from antlr4 import FileStream, CommonTokenStream, InputStream, Token
from generated.VerilogALexer import VerilogALexer
from preprocessor import VerilogAPreprocessor, lex, MyToken


def strip_token_origin(token):
    return dataclasses.replace(token, origin=None)


@pytest.mark.parametrize(
    "src_in,src_out",
    [
        (
            """
`define HOLA 2 3
1 `HOLA 4
""",
            "1 2 3 4",
        ),
        (
            """
`define HOLA(x) x+2*x
1 `HOLA(a) 4
""",
            "1 a + 2 * a 4",
        ),
        (
            """
`define HOLA(x) x+2*x
`define TRIPLE(x) 3*x
1 `HOLA(`TRIPLE(a)) 4
""",
            "1 3 * a + 2 * 3 * a 4",
        ),
        (
            """
`define PI 3
`define CIRCUMFERENCE(radius) 2 * `PI * radius
`CIRCUMFERENCE(4)""",
            "2 * 3 * 4",
        ),
        (
            """
`define ADD(y, x) x + y
`ADD(2*3, 4*5)
""",
            "4 * 5 + 2 * 3",
        ),
        (
            """
1
`ifdef MISSING
no
`endif
2""",
            "1 2",
        ),
        (
            """
1
`ifdef MISSING
no
`else
2
`endif
3""",
            "1 2 3",
        ),
        (
            """
`define EXISTS
1
`ifdef EXISTS
2
`endif
3""",
            "1 2 3",
        ),
        (
            """
`define EXISTS
1
`ifdef EXISTS
2
`else
no
`endif
3""",
            "1 2 3",
        ),
    ],
)
def test_preprocessor(src_in, src_out):
    preprocessed = list(
        map(strip_token_origin, VerilogAPreprocessor(lex(content=src_in)))
    )
    expected = list(map(strip_token_origin, lex(content=src_out)))
    assert preprocessed == expected


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """
start
`define f(x) 2 * x
`define g(x) 3 * x
`f(`g(4))
theend
""",
            [
                (VerilogALexer.SIMPLE_IDENTIFIER, "start", [("dummyfile", 2, 0)]),
                (
                    VerilogALexer.UNSIGNED_NUMBER,
                    "2",
                    [("dummyfile", 5, 0), ("dummyfile", 3, 13)],
                ),
                (VerilogALexer.TIMES, "*", [("dummyfile", 5, 0), ("dummyfile", 3, 15)]),
                (
                    VerilogALexer.UNSIGNED_NUMBER,
                    "3",
                    [
                        ("dummyfile", 5, 0),
                        ("dummyfile", 3, 17),
                        ("dummyfile", 5, 3),
                        ("dummyfile", 4, 13),
                    ],
                ),
                (
                    VerilogALexer.TIMES,
                    "*",
                    [
                        ("dummyfile", 5, 0),
                        ("dummyfile", 3, 17),
                        ("dummyfile", 5, 3),
                        ("dummyfile", 4, 15),
                    ],
                ),
                (
                    VerilogALexer.UNSIGNED_NUMBER,
                    "4",
                    [
                        ("dummyfile", 5, 0),
                        ("dummyfile", 3, 17),
                        ("dummyfile", 5, 3),
                        ("dummyfile", 4, 17),
                        ("dummyfile", 5, 6),
                    ],
                ),
                (VerilogALexer.SIMPLE_IDENTIFIER, "theend", [("dummyfile", 6, 0)]),
                (Token.EOF, "<EOF>", [("dummyfile", 7, 0)]),
            ],
        ),
        (
            """
start
`define f(x) 2 * `g(x)
`define g(x) 3 * x
`f(4)
theend
""",
            [
                (VerilogALexer.SIMPLE_IDENTIFIER, "start", [("dummyfile", 2, 0)]),
                (
                    VerilogALexer.UNSIGNED_NUMBER,
                    "2",
                    [("dummyfile", 5, 0), ("dummyfile", 3, 13)],
                ),
                (VerilogALexer.TIMES, "*", [("dummyfile", 5, 0), ("dummyfile", 3, 15)]),
                (
                    VerilogALexer.UNSIGNED_NUMBER,
                    "3",
                    [("dummyfile", 5, 0), ("dummyfile", 3, 17), ("dummyfile", 4, 13)],
                ),
                (
                    VerilogALexer.TIMES,
                    "*",
                    [("dummyfile", 5, 0), ("dummyfile", 3, 17), ("dummyfile", 4, 15)],
                ),
                (
                    VerilogALexer.UNSIGNED_NUMBER,
                    "4",
                    [
                        ("dummyfile", 5, 0),
                        ("dummyfile", 3, 17),
                        ("dummyfile", 4, 17),
                        ("dummyfile", 5, 0),
                        ("dummyfile", 3, 20),
                        ("dummyfile", 5, 3),
                    ],
                ),
                (VerilogALexer.SIMPLE_IDENTIFIER, "theend", [("dummyfile", 6, 0)]),
                (Token.EOF, "<EOF>", [("dummyfile", 7, 0)]),
            ],
        ),
    ],
)
def test_token_origin(src, expected):
    filename = "dummyfile"
    tokens = list(VerilogAPreprocessor(lex(content=src, filename=filename)))
    assert tokens == [
        MyToken(type_, text, channel=0, origin=origin)
        for type_, text, origin in expected
    ]
