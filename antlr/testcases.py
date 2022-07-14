from manual_parser import Parser
import parsetree as pt
from lexer import tok


def flatten(nested_list):
    return [elem for normal_list in nested_list for elem in normal_list]


simpleid = tok.name
simpleid1 = tok.arg1
one = tok(1)
two = tok(2)
three = tok(3)
real = tok(3.5)
lparen = tok.LPAREN
rparen = tok.RPAREN
minus = tok.MINUS
plus = tok.PLUS
times = tok.TIMES
raised = tok.RAISED
logicalnegation = tok.LOGICALNEGATION
comma = tok.COMMA
ternary = tok.TERNARY
colon = tok.COLON


testcases_grouped = [
    (
        Parser.expression,
        [
            ("name", [simpleid], pt.Identifier(simpleid)),
            ("3", [three], pt.Literal(three)),
            ("3.5", [real], pt.Literal(real)),
            (
                "name()",
                [simpleid, lparen, rparen],
                pt.FunctionCall(pt.Identifier(simpleid), []),
            ),
            (
                "name(arg1)",
                [simpleid, lparen, simpleid1, rparen],
                pt.FunctionCall(pt.Identifier(simpleid), [pt.Identifier(simpleid1)]),
            ),
            (
                "name(arg1, 3)",
                [simpleid, lparen, simpleid1, comma, three, rparen],
                pt.FunctionCall(
                    pt.Identifier(simpleid),
                    [pt.Identifier(simpleid1), pt.Literal(three)],
                ),
            ),
            ("-3", [minus, three], pt.Operation(minus, [pt.Literal(value=three)])),
            (
                "!(3.5)",
                [logicalnegation, lparen, real, rparen],
                pt.Operation(logicalnegation, [pt.Literal(value=real)]),
            ),
            (
                "1 +2",
                [one, plus, two],
                pt.Operation(plus, [pt.Literal(one), pt.Literal(two)]),
            ),
            (
                "1+2+3",
                [one, plus, two, plus, three],
                pt.Operation(
                    plus,
                    [
                        pt.Operation(plus, [pt.Literal(one), pt.Literal(two)]),
                        pt.Literal(three),
                    ],
                ),
            ),
            (
                "1*2",
                [one, times, two],
                pt.Operation(times, [pt.Literal(one), pt.Literal(two)]),
            ),
            (
                "1*2*3",
                [one, times, two, times, three],
                pt.Operation(
                    times,
                    [
                        pt.Operation(times, [pt.Literal(one), pt.Literal(two)]),
                        pt.Literal(three),
                    ],
                ),
            ),
            (
                "1**2",
                [one, raised, two],
                pt.Operation(raised, [pt.Literal(one), pt.Literal(two)]),
            ),
            (
                "1**2**3",
                [one, raised, two, raised, three],
                pt.Operation(
                    raised,
                    [
                        pt.Operation(raised, [pt.Literal(one), pt.Literal(two)]),
                        pt.Literal(three),
                    ],
                ),
            ),
            (
                "1+2*3",
                [one, plus, two, times, three],
                pt.Operation(
                    plus,
                    [
                        pt.Literal(one),
                        pt.Operation(times, [pt.Literal(two), pt.Literal(three)]),
                    ],
                ),
            ),
            (
                "1*2+3",
                [one, times, two, plus, three],
                pt.Operation(
                    plus,
                    [
                        pt.Operation(times, [pt.Literal(one), pt.Literal(two)]),
                        pt.Literal(three),
                    ],
                ),
            ),
            (
                "name(1+2,3)",
                [simpleid, lparen, one, plus, two, comma, three, rparen],
                pt.FunctionCall(
                    pt.Identifier(simpleid),
                    [
                        pt.Operation(plus, [pt.Literal(one), pt.Literal(two)]),
                        pt.Literal(three),
                    ],
                ),
            ),
            (
                "1?2:3",
                [one, ternary, two, colon, three],
                pt.Operation(
                    ternary, [pt.Literal(one), pt.Literal(two), pt.Literal(three)]
                ),
            ),
            (
                "1 ? 2 : 3 ? 2 : 1",
                [one, ternary, two, colon, three, ternary, two, colon, one],
                pt.Operation(
                    ternary,
                    [
                        pt.Literal(one),
                        pt.Literal(two),
                        pt.Operation(
                            ternary,
                            [pt.Literal(three), pt.Literal(two), pt.Literal(one)],
                        ),
                    ],
                ),
            ),
        ],
    ),
    (
        Parser.nature,
        [
            (
                """
        nature Current;
        units = "A";
        access = I;
        idt_nature = Charge;
        abstol = 1e-12;
        endnature""",
                [
                    tok.NATURE,
                    tok.Current,
                    tok.SEMICOLON,
                    tok.UNITS,
                    tok.ASSIGNOP,
                    tok("A"),
                    tok.SEMICOLON,
                    tok.ACCESS,
                    tok.ASSIGNOP,
                    tok.I,
                    tok.SEMICOLON,
                    tok.IDT_NATURE,
                    tok.ASSIGNOP,
                    tok.Charge,
                    tok.SEMICOLON,
                    tok.ABSTOL,
                    tok.ASSIGNOP,
                    tok(1e-12),
                    tok.SEMICOLON,
                    tok.ENDNATURE,
                ],
                pt.Nature(
                    name=tok.Current,
                    attributes=[
                        pt.NatureAttribute(
                            tok.UNITS,
                            pt.Literal(tok("A")),
                        ),
                        pt.NatureAttribute(
                            tok.ACCESS,
                            pt.Identifier(tok.I),
                        ),
                        pt.NatureAttribute(
                            tok.IDT_NATURE,
                            pt.Identifier(tok.Charge),
                        ),
                        pt.NatureAttribute(
                            tok.ABSTOL,
                            pt.Literal(tok(1e-12)),
                        ),
                    ],
                ),
            )
        ],
    ),
    (
        Parser.discipline,
        [
            (
                """
        discipline electrical;
        domain discrete;
        potential Voltage;
        flow Current;
        enddiscipline
        """,
                [
                    tok.DISCIPLINE,
                    tok.electrical,
                    tok.SEMICOLON,
                    tok.DOMAIN,
                    tok.DISCRETE,
                    tok.SEMICOLON,
                    tok.POTENTIAL,
                    tok.Voltage,
                    tok.SEMICOLON,
                    tok.FLOW,
                    tok.Current,
                    tok.SEMICOLON,
                    tok.ENDDISCIPLINE,
                ],
                pt.Discipline(
                    name=tok.electrical,
                    attributes=[
                        pt.DisciplineAttribute(
                            tok.DOMAIN,
                            tok.DISCRETE,
                        ),
                        pt.DisciplineAttribute(
                            tok.POTENTIAL,
                            pt.Identifier(tok.Voltage),
                        ),
                        pt.DisciplineAttribute(
                            tok.FLOW,
                            pt.Identifier(tok.Current),
                        ),
                    ],
                ),
            )
        ],
    ),
    (
        Parser.module,
        [
            (
                """
        module modname(inout disc1 p1);
        input p2, p3;
        disc2 p2, p3;
        real real1, real2=4.5;
        integer int1=4, int2;
        endmodule
        """,
                flatten(
                    [
                        [tok.MODULE, tok.modname],
                        [
                            tok.LPAREN,
                            tok.INOUT,
                            tok.disc1,
                            tok.p1,
                            tok.RPAREN,
                            tok.SEMICOLON,
                        ],
                        [tok.INPUT, tok.p2, tok.COMMA, tok.p3, tok.SEMICOLON],
                        [tok.disc2, tok.p2, tok.COMMA, tok.p3, tok.SEMICOLON],
                        [
                            tok.REAL,
                            tok.real1,
                            tok.COMMA,
                            tok.real2,
                            tok.ASSIGNOP,
                            tok(4.5),
                            tok.SEMICOLON,
                        ],
                        [
                            tok.INTEGER,
                            tok.int1,
                            tok.ASSIGNOP,
                            tok(4),
                            tok.COMMA,
                            tok.int2,
                            tok.SEMICOLON,
                        ],
                        [tok.ENDMODULE],
                    ]
                ),
                pt.Module(
                    name=tok.modname,
                    ports=[
                        pt.Port(name=tok.p1, direction=tok.INOUT),
                        pt.Port(name=tok.p2, direction=tok.INPUT),
                        pt.Port(name=tok.p3, direction=tok.INPUT),
                    ],
                    nets=[
                        pt.Net(name=tok.p1, discipline=tok.disc1),
                        pt.Net(name=tok.p2, discipline=tok.disc2),
                        pt.Net(name=tok.p3, discipline=tok.disc2),
                    ],
                    variables=[
                        pt.Variable(name=tok.real1, type=tok.REAL, initializer=None),
                        pt.Variable(
                            name=tok.real2,
                            type=tok.REAL,
                            initializer=pt.Literal(tok(4.5)),
                        ),
                        pt.Variable(
                            name=tok.int1,
                            type=tok.INTEGER,
                            initializer=pt.Literal(tok(4)),
                        ),
                        pt.Variable(name=tok.int2, type=tok.INTEGER, initializer=None),
                    ],
                ),
            )
        ],
    ),
    (
        Parser.statement,
        [
            (
                "var1 = 4",
                [tok.var1, tok.ASSIGNOP, tok(4)],
                pt.Assignment(lvalue=tok.var1, value=pt.Literal(tok(4))),
            ),
            (
                "I(n1,n2) <+ 4",
                [
                    tok.I,
                    tok.LPAREN,
                    tok.n1,
                    tok.COMMA,
                    tok.n2,
                    tok.RPAREN,
                    tok.ANALOGCONTRIBUTION,
                    tok(4),
                ],
                pt.AnalogContribution(
                    accessor=tok.I, arg1=tok.n1, arg2=tok.n2, value=pt.Literal(tok(4))
                ),
            ),
            (
                """
            begin
            var1 = 4;
            var2 = 4.5;
            end
            """,
                [
                    tok.BEGIN,
                    tok.var1,
                    tok.ASSIGNOP,
                    tok(4),
                    tok.SEMICOLON,
                    tok.var2,
                    tok.ASSIGNOP,
                    tok(4.5),
                    tok.SEMICOLON,
                    tok.END,
                ],
                pt.Block(
                    [
                        pt.Assignment(lvalue=tok.var1, value=pt.Literal(tok(4))),
                        pt.Assignment(lvalue=tok.var2, value=pt.Literal(tok(4.5))),
                    ]
                ),
            ),
            (
                " if (cond) lval = val ",
                [
                    tok.IF_,
                    tok.LPAREN,
                    tok.cond,
                    tok.RPAREN,
                    tok.lval,
                    tok.ASSIGNOP,
                    tok.val,
                ],
                pt.If(
                    condition=pt.Identifier(tok.cond),
                    then=pt.Assignment(lvalue=tok.lval, value=pt.Identifier(tok.val)),
                    else_=None,
                ),
            ),
            (
                """
                if (cond)
                lval = val
                else
                lval2 = val2
                """,
                [
                    tok.IF,
                    tok.LPAREN,
                    tok.cond,
                    tok.RPAREN,
                    tok.lval,
                    tok.ASSIGNOP,
                    tok.val,
                    tok.ELSE,
                    tok.lval2,
                    tok.ASSIGNOP,
                    tok.val2,
                ],
                pt.If(
                    condition=pt.Identifier(tok.cond),
                    then=pt.Assignment(lvalue=tok.lval, value=pt.Identifier(tok.val)),
                    else_=pt.Assignment(
                        lvalue=tok.lval2, value=pt.Identifier(tok.val2)
                    ),
                ),
            ),
            (
                """
                if(cond_outer)
                  if(cond_inner)
                    lval = val
                  else
                    lval2 = val2
                """,
                flatten(
                    [
                        [tok.IF, tok.LPAREN, tok.cond_outer, tok.RPAREN],
                        [tok.IF, tok.LPAREN, tok.cond_inner, tok.RPAREN],
                        [tok.lval, tok.ASSIGNOP, tok.val],
                        [tok.ELSE],
                        [tok.lval2, tok.ASSIGNOP, tok.val2],
                    ]
                ),
                pt.If(
                    condition=pt.Identifier(tok.cond_outer),
                    then=pt.If(
                        condition=pt.Identifier(tok.cond_inner),
                        then=pt.Assignment(
                            lvalue=tok.lval, value=pt.Identifier(tok.val)
                        ),
                        else_=pt.Assignment(
                            lvalue=tok.lval2, value=pt.Identifier(tok.val2)
                        ),
                    ),
                    else_=None,
                ),
            ),
        ],
    ),
]
testcases = [
    (source, tokens, parser, expected)
    for parser, cases in testcases_grouped
    for source, tokens, expected in cases
]
