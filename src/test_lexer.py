from typing import List
import pytest
from testcases import testcases
from lexer import lex, MyToken
from dataclasses import replace


def token(type_, value=None):
    return MyToken(type=type_, value=value, origin=[])



# TODO: test multiline comments
@pytest.mark.parametrize(
    "source,expected_tokens",
    [
        ("3", [MyToken("UNSIGNED_NUMBER", 3, [(None, 1, 1)])]),
        (
            "(3.5 )",
            [
                MyToken("LPAREN", "(", [(None, 1, 1)]),
                MyToken("REAL_NUMBER", 3.5, [(None, 1, 2)]),
                MyToken("RPAREN", ")", [(None, 1, 6)]),
            ],
        ),
        (
            "3 //pepe\n4",
            [
                MyToken("UNSIGNED_NUMBER", 3, [(None, 1, 1)]),
                MyToken("UNSIGNED_NUMBER", 4, [(None, 2, 1)]),
            ],
        ),
        (
            "3 /*pepe\nlolo*/4",
            [
                MyToken("UNSIGNED_NUMBER", 3, [(None, 1, 1)]),
                MyToken("UNSIGNED_NUMBER", 4, [(None, 2, 7)]),
            ],
        ),
    ],
)
def test_lexer_with_location(source: str, expected_tokens: list[MyToken]):
    result = list(lex(content=source))
    assert result == expected_tokens



@pytest.mark.parametrize(
    "source,expected_tokens",
    [(source, expected_tokens) for source, expected_tokens, _, _ in testcases],
)
def test_lexer(source: str, expected_tokens: List[MyToken]):
    if expected_tokens is None:
        return
    source = source.replace("\n", " ")
    result = [replace(tok, origin=[]) for tok in lex(content=source)]
    assert result == expected_tokens
