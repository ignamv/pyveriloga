from typing import List
import pytest
from testcases import testcases
from lexer import lex, MyToken
from dataclasses import replace


def token(type_, value=None):
    return MyToken(type=type_, value=value, origin=[])


old = [
    ("3", [MyToken("UNSIGNED_NUMBER", 3, [(None, 1, 1)])]),
    (
        "(3.5 )",
        [
            MyToken("LPAREN", "(", [(None, 1, 1)]),
            MyToken("REAL_NUMBER", 3.5, [(None, 1, 2)]),
            MyToken("RPAREN", ")", [(None, 1, 6)]),
        ],
    ),
]


@pytest.mark.parametrize(
    "source,expected_tokens",
    [(source, expected_tokens) for source, expected_tokens, _, _ in testcases],
)
def test_lexer(source: str, expected_tokens: List[MyToken]):
    source = source.replace("\n", " ")
    result = [replace(tok, origin=[]) for tok in lex(content=source)]
    assert result == expected_tokens
