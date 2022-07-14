from typing import List, Callable
import pytest
from manual_parser import PeekIterator, Parser
from mytoken import MyToken
import parsetree as pt
from lexer import reserved, operators, tok
from testcases import testcases, flatten


def test_peek():
    iterator = PeekIterator(range(6))
    assert not iterator.eof()
    assert next(iterator) == 0
    assert not iterator.eof()
    assert next(iterator) == 1
    assert not iterator.eof()
    assert iterator.peek() == 2
    assert not iterator.eof()
    assert iterator.peek() == 2
    assert not iterator.eof()
    assert next(iterator) == 2
    assert not iterator.eof()
    assert next(iterator) == 3
    assert not iterator.eof()
    assert iterator.peek() == 4
    assert not iterator.eof()
    assert iterator.peek() == 4
    assert not iterator.eof()
    assert iterator.peek() == 4
    assert not iterator.eof()
    assert next(iterator) == 4
    assert not iterator.eof()
    assert next(iterator) == 5
    assert iterator.eof()


@pytest.mark.parametrize(
    "tokens,method,expected",
    [(tokens, method, expected) for _, tokens, method, expected in testcases],
)
def test_parser(
    tokens: List[MyToken],
    method: Callable[[Parser, List[MyToken]], pt.ParseTree],
    expected: pt.ParseTree,
):
    guard = [tok.guard]
    parser = Parser(tokens + guard)
    result = method(parser)
    unconsumed_tokens = list(parser.peekiterator)
    assert len(unconsumed_tokens) >= len(guard), "Too much input consumed"
    assert len(unconsumed_tokens) <= len(guard), "Not all input consumed"
    assert result == expected
