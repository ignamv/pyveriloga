from typing import List, Callable, Optional
import pytest
from manual_parser import PeekIterator, Parser
from mytoken import MyToken
import parsetree as pt
from lexer import reserved, operators, tok, lex
from preprocessor import VerilogAPreprocessor
from testcases import testcases, flatten
from dataclasses import replace


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


@pytest.mark.parametrize("source,tokens,method,expected", testcases)
def test_parser(
    source: str,
    tokens: Optional[List[MyToken]],
    method: Callable[[Parser, List[MyToken]], pt.ParseTree],
    expected: pt.ParseTree,
):
    if tokens is None:
        tokens = [
            replace(tok, origin=[]) for tok in VerilogAPreprocessor(lex(content=source))
        ]
    guard = [tok.guard]
    parser = Parser(tokens + guard)
    result = method(parser)
    unconsumed_tokens = list(parser.peekiterator)
    assert len(unconsumed_tokens) >= len(guard), "Too much input consumed"
    assert len(unconsumed_tokens) <= len(guard), "Not all input consumed"
    assert result == expected
