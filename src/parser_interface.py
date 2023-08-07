from lower_parsetree import LowerParseTree
from lexer import lex
from manual_parser import Parser, ParseMethod
from preprocessor import VerilogAPreprocessor
from typing import Optional, List
from parsetree import ParseTree
from mytoken import MyToken
from hir import HIR


def parse_source(
    content: Optional[str] = None,
    filename: Optional[str] = None,
    method: Optional[ParseMethod] = None,
) -> HIR:
    """Lex, preprocess, parse and lower"""
    tokens = list(VerilogAPreprocessor(lex(content=content, filename=filename)))
    if method is None:
        method = Parser.sourcefile
    parser = Parser(tokens)
    parsetree = method(parser)
    hir = LowerParseTree().lower(parsetree)
    return hir
