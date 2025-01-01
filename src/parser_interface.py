from argparse import ArgumentParser
from pathlib import Path
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
    include_path: Optional[list[Path|str]] = None,
) -> HIR:
    """Lex, preprocess, parse and lower"""
    if include_path is None:
        include_path = []
    tokens = list(VerilogAPreprocessor(lex(content=content, filename=filename), include_path=include_path))
    if method is None:
        method = Parser.sourcefile
    parser = Parser(tokens)
    parsetree = method(parser)
    hir = LowerParseTree().lower(parsetree)
    return hir


def main():
    parser = ArgumentParser()
    parser.add_argument("veriloga")
    parser.add_argument("-I", action="append")
    args = parser.parse_args()
    parse_source(filename=args.veriloga, include_path=args.I)
    print("OK")


if __name__ == "__main__":
    main()
