from lower_parsetree import lower_parsetree
from lexer import lex
from manual_parser import Parser
from typing import Optional, List
from parsetree import ParseTree
from mytoken import MyToken
from hir import HIR

def parse_source(content:Optional[str]=None, filename:Optional[str]=None, method:Optional[ParseMethod]=None) -> HIR:
    tokens = list(VerilogAPreprocessor(lex(content=content, filename=filename)))
    if method is None:
        method = Parser.sourcefile
    parser = Parser(tokens)
    parsetree = method(parser)
    hir = lower_parsetree(parsetree)
    return hir
