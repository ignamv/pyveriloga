from typing import Dict, List, Tuple, Optional, Iterator
from dataclasses import dataclass, replace
import ply.lex  # type: ignore
import re
import os
from mytoken import MyToken

with open("../grammar_manipulation/operators") as fd:
    operators: Dict[str, str] = {}
    for line in fd:
        operator, name = line.strip().split("\t")
        operators[name] = operator
for name, value in operators.items():
    globals()["t_" + name] = re.escape(value)

with open("../grammar_manipulation/reserved") as fd:
    reserved = tuple(line.strip() for line in fd)

tokens = (
    (
        "REAL_NUMBER",
        "UNSIGNED_NUMBER",
        "STRING_LITERAL",
        "SIMPLE_IDENTIFIER",
        "SYSTEM_IDENTIFIER",
        "DEFINE",
        "IFDEF",
        "ELSEDEF",
        "ENDIFDEF",
        "INCLUDE",
        "MACROCALL",
        "NEWLINE",
    )
    + tuple(map(str.upper, reserved))
    + tuple(operators.keys())
)


def t_DEFINE(t):
    r"`define\s+(?P<define_name>[a-zA-Z_][a-zA-Z0-9_]*)(?P<define_parenthesis>\(?)"
    t.value = t.lexer.lexmatch.group("define_name"), t.lexer.lexmatch.group(
        "define_parenthesis"
    )
    return t


t_ignore = " \t"

# Silly way to give `ifdef and friends priority over macro calls (ply sorts by regex length)
# TODO: convert to functions, ply respects their order
t_IFDEF = r"`ifdef                    "
t_ELSEDEF = r"`else                     "
t_ENDIFDEF = r"`endif                    "
t_INCLUDE = r"`include                  "
t_MACROCALL = r"`[a-zA-Z_][a-zA-Z0-9_]*"


def t_NEWLINE(t):
    r"\n+"
    t.lexer.lineno += len(t.value)
    t.lexer.line_beginning = t.lexpos + len(t.value)
    return t


def t_COMMENT(t):
    r"//.*\n"
    t.lexer.lineno += 1
    t.lexer.line_beginning = t.lexpos + len(t.value)



def t_REAL_NUMBER(t):
    r"\d+\.\d+([TGMKkmunpfa]|[eE][+-]*\d+)?|\d+([TGMKkmunpfa]|[eE][+-]*\d+)"
    t.value = float(t.value)
    return t


def t_UNSIGNED_NUMBER(t):
    r"\d+"
    t.value = int(t.value)
    return t


def t_STRING_LITERAL(t):
    r'"(\\"|[^"])*"'
    # TODO: unescape
    t.value = t.value[1:-1]
    return t


# TODO: unescape escaped identifiers
def t_SIMPLE_IDENTIFIER(t):
    r"[a-zA-Z_\\][a-zA-Z0-9_$]*"
    if t.value in reserved:
        t.type = t.value.upper()
    return t


t_SYSTEM_IDENTIFIER = r"\$[a-zA-Z_\\][a-zA-Z0-9_$]*"


def t_error(t):
    raise Exception(f"Illegal character '{t.value[0]}' at {t.lexer.filename}:{t.lexer.lineno}")



TokenSource = Iterator[MyToken]


def lex(filename: Optional[str] = None, content: Optional[str] = None) -> TokenSource:
    if content is None:
        assert (
            filename is not None
        ), "If filename is not provided then content is mandatory"
        with open(filename) as fd:
            content = fd.read()
    # Can't create this at the module level because then the lexer is not reentrant
    # This breaks lexing of included files
    lexer = ply.lex.lex()
    lexer.filename = filename
    lexer.line_beginning = 0
    lexer.lineno = 1
    lexer.input(content)
    for raw_token in lexer:
        column = raw_token.lexpos - lexer.line_beginning + 1
        yield MyToken(
            type=raw_token.type,
            value=raw_token.value,
            origin=[(filename, raw_token.lineno, column)],
        )


class TokenHelper:
    """Helper class to concisely create tokens for testing"""

    def __getattr__(self, name: str) -> MyToken:
        if name.endswith("_"):
            name = name[:-1]
        namelower = name.lower()
        if namelower in reserved:
            return MyToken(type=name, value=namelower, origin=[])
        if name in operators:
            return MyToken(type=name, value=operators[name], origin=[])
        return MyToken(type="SIMPLE_IDENTIFIER", value=name, origin=[])

    def __call__(self, value: int | float | str) -> MyToken:
        """
        Create literal token
        """
        if isinstance(value, int):
            return MyToken("UNSIGNED_NUMBER", value, origin=[])
        elif isinstance(value, float):
            return MyToken("REAL_NUMBER", value, origin=[])
        elif isinstance(value, str):
            return MyToken("STRING_LITERAL", value, origin=[])
        else:
            raise Exception(value)


tok = TokenHelper()
