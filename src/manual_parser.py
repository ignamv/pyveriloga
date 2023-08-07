import parsetree as pt
from typing import Callable
from lexer import tokens as token_types

DIRECTIONS = ("INPUT", "OUTPUT", "INOUT")
VARTYPES = ("REAL", "INTEGER", "STRING")
NATUREATTRS = ("UNITS", "ACCESS", "IDT_NATURE", "DDT_NATURE", "ABSTOL")
BUILTIN_FUNCTIONS = (
    "LN",
    "LOG",
    "EXP",
    "SQRT",
    "MIN",
    "MAX",
    "ABS",
    "POW",
    "FLOOR",
    "CEIL",
    "SIN",
    "COS",
    "TAN",
    "ASIN",
    "ACOS",
    "ATAN",
    "ATAN2",
    "HYPOT",
    "SINH",
    "COSH",
    "TANH",
    "ASINH",
    "ACOSH",
    "ATANH",
)


class PeekIterator:
    def __init__(self, source):
        self.source = iter(source)
        self.buffer = []

    def __iter__(self):
        return self

    def peek(self):
        if not self.buffer:
            self.buffer.append(next(self.source))
        return self.buffer[0]

    def __next__(self):
        if self.buffer:
            self.last_token = self.buffer.pop()
        else:
            self.last_token = next(self.source)
        return self.last_token

    def eof(self):
        try:
            self.peek()
        except StopIteration:
            return True
        return False


unary_operators = ["MINUS", "PLUS", "LOGICALNEGATION", "BITWISENEGATION"]
operators = {
    "RAISED": (
        13,
        "L",
    ),  # ** is left-associative, confirmed with Spectre.
    "TIMES": (12, "L"),
    "DIVIDED": (12, "L"),
    "MODULUS": (12, "L"),
    "PLUS": (11, "L"),
    "MINUS": (11, "L"),
    "LOGICRIGHTSHIFT": (10, "L"),
    "LOGICLEFTSHIFT": (10, "L"),
    "GREATEROREQUAL": (9, "L"),
    "GREATER": (9, "L"),
    "SMALLER": (9, "L"),
    "SMALLEROREQUAL": (9, "L"),
    "NOTEQUAL": (8, "L"),
    "EQUALS": (8, "L"),
    "BITWISEAND": (7, "L"),
    "XOROP": (6, "L"),
    "XNOROP": (6, "L"),
    "BITWISEOR": (5, "L"),
    "LOGICALAND": (4, "L"),
    "LOGICALOR": (3, "L"),
    "TERNARY": (2, "R"),
}


class Parser:
    def __init__(self, tokens):
        self.peekiterator = PeekIterator(tokens)

    def fail(self, message):
        raise Exception(self.peekiterator.last_token, message)

    def expect_types(self, types, why=""):
        assert all(type_ in token_types for type_ in types)
        tok = next(self.peekiterator)
        if tok.type not in types:
            self.fail(f"Expected {types} {why}")
        return tok

    def expect_type(self, type_, why=""):
        return self.expect_types([type_], why)

    def peek_type(self):
        return self.peekiterator.peek().type

    def eof(self):
        return self.peekiterator.eof()

    def peek(self):
        return self.peekiterator.peek()

    def next(self):
        return next(self.peekiterator)

    def expression(self, min_precedence=-1):
        if self.peek_type() in unary_operators:
            operator = self.next()
            result = pt.Operation(operator, [self.expression_primary()])
        else:
            result = self.expression_primary()
        while True:
            if self.eof():
                return result
            operator = self.peek()
            type_ = operator.type
            if type_ not in operators or operators[type_][0] < min_precedence:
                return result
            self.next()
            precedence, associativity = operators[operator.type]
            child_min_precedence = (
                precedence + 1 if associativity == "L" else precedence
            )
            operands = [
                result,
                self.expression(min_precedence=child_min_precedence),
            ]
            if type_ == "TERNARY":
                self.expect_type("COLON", "separating ternary expression arguments")
                operands.append(self.expression(min_precedence=child_min_precedence))
            result = pt.Operation(operator, operands)

    def expression_primary(self):
        tok = self.next()
        if tok.type == "LPAREN":
            ret = self.expression()
            self.expect_type("RPAREN", "to close parenthesized expression")
            return ret
        if tok.type in ("REAL_NUMBER", "UNSIGNED_NUMBER", "STRING_LITERAL"):
            return pt.Literal(tok)
        if tok.type in ("SIMPLE_IDENTIFIER", "SYSTEM_IDENTIFIER") + BUILTIN_FUNCTIONS:
            id_ = pt.Identifier(tok)
            if self.eof() or self.peek_type() != "LPAREN":
                return id_
            # Function call, eat LPAREN
            self.next()
            arguments = []
            while self.peek_type() != "RPAREN":
                arguments.append(self.expression())
                if self.peek_type() == "RPAREN":
                    break
                self.expect_type("COMMA", "separating function arguments")
            self.next()

            return pt.FunctionCall(function=id_, args=arguments)
        self.fail("Expected expression primary")

    def nature(self):
        self.expect_type("NATURE")
        name = self.expect_type("SIMPLE_IDENTIFIER", " for nature name")
        self.expect_type("SEMICOLON")
        attributes = []
        while self.peek_type() != "ENDNATURE":
            attributes.append(self.natureattribute())
        self.next()
        return pt.Nature(name, attributes)

    def natureattribute(self):
        key = self.expect_types(NATUREATTRS, "for nature attribute name")
        self.expect_type("ASSIGNOP")
        value = self.expression()
        self.expect_type("SEMICOLON")
        return pt.NatureAttribute(key, value)

    def discipline(self):
        self.expect_type("DISCIPLINE")
        name = self.expect_type("SIMPLE_IDENTIFIER", " for discipline name")
        self.expect_type("SEMICOLON")
        attributes = []
        while self.peek_type() != "ENDDISCIPLINE":
            attributes.append(self.disciplineattribute())
        self.next()
        return pt.Discipline(name, attributes)

    def disciplineattribute(self):
        key = self.expect_types(
            ("FLOW", "POTENTIAL", "DOMAIN"), "for discipline attribute"
        )
        if key.type == "DOMAIN":
            value = self.expect_type("DISCRETE")
        else:
            value = self.expect_type("SIMPLE_IDENTIFIER")
        self.expect_type("SEMICOLON")
        return pt.DisciplineAttribute(key, value)

    def module(self):
        self.expect_type("MODULE")
        name = self.expect_type("SIMPLE_IDENTIFIER")
        if self.peek_type() == "LPAREN":
            ports, nets = self.list_of_ports()
        else:
            ports = []
            nets = []
        variables = []
        statements = []
        self.expect_type("SEMICOLON")
        while True:
            type_ = self.peek_type()
            if type_ == "ENDMODULE":
                break
            elif type_ == "SIMPLE_IDENTIFIER":
                nets.extend(self.net_declaration())
            elif type_ in DIRECTIONS:
                new_nets, new_ports = self.port_declaration()
                nets.extend(new_nets)
                ports.extend(new_ports)
            elif type_ in VARTYPES:
                variables.extend(self.variable_declaration())
            elif type_ == "ANALOG":
                self.next()
                statements.append(self.statement())
            else:
                self.next()
                self.fail("Invalid module item")
        self.next()
        return pt.Module(
            name=name,
            nets=nets,
            ports=ports,
            variables=variables,
            statements=statements,
        )

    def list_of_ports(self):
        self.expect_type("LPAREN")
        nets = []
        ports = []
        while True:
            tok1 = self.expect_types(("RPAREN", "SIMPLE_IDENTIFIER") + DIRECTIONS)
            type_ = tok1.type
            if type_ == "RPAREN":
                break
            elif type_ == "SIMPLE_IDENTIFIER":
                ports.append(pt.Port(name=tok1, direction=None))
            elif type_ in DIRECTIONS:
                direction = tok1
                name_or_discipline = self.expect_type("SIMPLE_IDENTIFIER")
                if self.peek_type() == "SIMPLE_IDENTIFIER":
                    discipline = name_or_discipline
                    name = self.next()
                    nets.append(pt.Net(name=name, discipline=discipline))
                else:
                    name = name_or_discipline
                ports.append(pt.Port(name=name, direction=direction))
            tok = self.expect_types(("RPAREN", "COMMA"))
            if tok.type == "RPAREN":
                break
        return ports, nets

    def port_declaration(self):
        nets = []
        ports = []
        names = []
        direction = self.expect_types(DIRECTIONS)
        name_or_discipline = self.expect_type("SIMPLE_IDENTIFIER")
        if self.peek_type() == "SIMPLE_IDENTIFIER":
            discipline = name_or_discipline
        else:
            discipline = None
            names.append(name_or_discipline)
        while True:
            if names:
                tok = self.expect_types(
                    (
                        "SEMICOLON",
                        "COMMA",
                    )
                )
                if tok.type == "SEMICOLON":
                    break
            names.append(self.expect_type("SIMPLE_IDENTIFIER"))
        for name in names:
            ports.append(pt.Port(name=name, direction=direction))
            if discipline is not None:
                nets.append(pt.Net(name=name, discipline=discipline))
        return nets, ports

    def net_declaration(self):
        nets = []
        discipline = self.expect_type("SIMPLE_IDENTIFIER")
        while True:
            nets.append(
                pt.Net(
                    name=self.expect_type("SIMPLE_IDENTIFIER", why='Net discipline'), discipline=discipline
                )
            )
            tok = self.expect_types(("SEMICOLON", "COMMA"))
            if tok.type == "SEMICOLON":
                break
        return nets

    def analog(self):
        self.expect_type("ANALOG")
        return self.statement()

    def statement(self):
        type_ = self.peek_type()
        if type_ == "SIMPLE_IDENTIFIER":
            return self.assignment_or_analogcontribution()
        elif type_ == "BEGIN":
            return self.block()
        elif type_ == "IF":
            return self.if_()
        else:
            self.next()
            self.fail("Expected analog statement")

    def assignment_or_analogcontribution(self):
        lvalue_or_accessor = self.expect_type("SIMPLE_IDENTIFIER")
        tok = self.expect_types(("ASSIGNOP", "LPAREN"))
        if tok.type == "ASSIGNOP":
            value = self.expression()
            return pt.Assignment(lvalue=lvalue_or_accessor, value=value)
        elif tok.type == "LPAREN":
            arg1 = self.expect_type("SIMPLE_IDENTIFIER")
            tok = self.expect_types(("COMMA", "RPAREN"))
            if tok.type == "COMMA":
                arg2 = self.expect_type("SIMPLE_IDENTIFIER")
                self.expect_type("RPAREN")
            else:
                arg2 = None
            self.expect_type("ANALOGCONTRIBUTION")
            value = self.expression()
            return pt.AnalogContribution(
                accessor=lvalue_or_accessor, arg1=arg1, arg2=arg2, value=value
            )

    def block(self):
        statements = []
        self.expect_type("BEGIN")
        while self.peek_type() != "END":
            statements.append(self.statement())
            self.expect_type("SEMICOLON")
        self.next()
        return pt.Block(statements=statements)

    def if_(self):
        self.expect_type("IF")
        self.expect_type("LPAREN")
        condition = self.expression()
        self.expect_type("RPAREN")
        then = self.statement()
        if self.peek_type() == "ELSE":
            self.next()
            else_ = self.statement()
        else:
            else_ = None
        return pt.If(condition=condition, then=then, else_=else_)

    def variable_declaration(self):
        variables = []
        type_ = self.expect_types(VARTYPES)
        while True:
            name = self.expect_type("SIMPLE_IDENTIFIER")
            tok = self.expect_types(("COMMA", "SEMICOLON", "ASSIGNOP"))
            print(tok.type)
            if tok.type == "ASSIGNOP":
                initializer = self.expression()
                tok = self.expect_types(("COMMA", "SEMICOLON"))
            else:
                initializer = None
            variables.append(
                pt.Variable(name=name, type=type_, initializer=initializer)
            )
            if tok.type == "SEMICOLON":
                break
        return variables

    def sourcefile(self):
        sourcefile = pt.SourceFile()
        while True:
            try:
                tok = self.peek()
            except StopIteration:
                break
            if tok.type == "MODULE":
                sourcefile.modules.append(self.module())
            elif tok.type == "NATURE":
                sourcefile.natures.append(self.nature())
            elif tok.type == "DISCIPLINE":
                sourcefile.disciplines.append(self.discipline())
            else:
                break
        return sourcefile


ParseMethod = Callable[[Parser], pt.ParseTree]
