import os
import re
from typing import List, Iterator, Dict, Optional, Union, Tuple, cast
from dataclasses import dataclass, replace
from itertools import takewhile, count
from lexer import lex, TokenSource
from mytoken import MyToken, FileLocation

@dataclass
class Macro:
    parameters: List[str]
    body: List[MyToken]

    def expand(self, arguments: List[List[MyToken]], origin: List[FileLocation]) -> TokenSource:
        for tok in self.body:
            tok = tok.included_from(origin)
            if tok.type == "SIMPLE_IDENTIFIER":
                try:
                    assert isinstance(tok.value, str)
                    idx = self.parameters.index(tok.value)
                except ValueError:
                    pass
                else:
                    for argument_token in arguments[idx]:
                        yield argument_token.included_from(tok.origin)
                    continue
            yield tok

Definitions = Dict[str, Macro]

class VerilogAPreprocessor:
    def __init__(self, source: TokenSource, definitions: Optional[Definitions]=None):
        self.input_iterator = self.input_generator(source)
        self.output_iterator = self.output_generator()
        if definitions is None:
            self.definitions: Definitions = {}
        else:
            self.definitions = definitions

    def __iter__(self):
        return self.output_iterator

    def input_generator(self, source: TokenSource):
        for token in source:
            self.last_token = token
            yield token

    def nextToken(self) -> MyToken:
        return next(self.output_iterator)

    def fail(self, why):
        raise Exception(why, self.last_token)

    def output_generator(self, source:Optional[TokenSource]=None, end:Union[Tuple[Optional[str],...],Optional[str]]=None):
        if source is None:
            source = self.input_iterator
        if not isinstance(end, tuple):
            end = (end,)
        while True:
            try:
                token = next(source)
            except StopIteration:
                if None in end:
                    return
                else:
                    self.fail("Unexpected EOF")
            if token.type in end:
                return
            elif token.type == "DEFINE":
                self.define()
            elif token.type == "IFDEF":
                yield from self.ifdef()
            elif token.type == "ELSEDEF":
                self.fail("Unexpected `else")
            elif token.type == "ENDIFDEF":
                self.fail("Unexpected `endif")
            elif token.type == "INCLUDE":
                yield from self.include()
            elif token.type == "MACROCALL":
                yield from self.macrocall()
            elif token.type == "NEWLINE":
                continue
            else:
                yield token

    def takeuntil(self, condition):
        for token in self.input_iterator:
            yield token
            if condition(token):
                return
        self.fail("Unexpected EOF")

    def define(self):
        name, parenthesis = self.last_token.value
        if parenthesis:
            # Macro definition
            parameters = list(self.consume_macro_definition_parameters())
        else:
            # Basic definition
            parameters = []
        body = list(self.takeuntil(lambda tok: tok.type == "NEWLINE"))[:-1]
        definition = Macro(parameters, body)
        self.definitions[name] = definition

    def consume_macro_definition_parameters(self):
        for ii in count():
            tok = next(self.input_iterator)
            if tok.type == "RPAREN":
                return
            if ii != 0:
                self.expect("COMMA", "macro parameter separator", last_token=True)
                next(self.input_iterator)
            tok = self.expect("SIMPLE_IDENTIFIER", "macro parameter", last_token=True)
            yield tok.value

    def macrocall(self) -> TokenSource:
        name = cast(str, self.last_token.value)[1:]
        origin = self.last_token.origin
        macro = self.definitions[name]
        arguments = list(self.consume_macrocall_arguments(len(macro.parameters)))
        yield from VerilogAPreprocessor(
            source=macro.expand(arguments, origin), definitions=self.definitions
        )

    def expect(self, type_: str, why, last_token=False):
        if not last_token:
            tok = next(self.input_iterator)
        else:
            tok = self.last_token
        if tok.type != type_:
            self.fail("Expected " + type_ + " (" + why + ")")
        return tok

    def consume_macrocall_arguments(self, number: int) -> Iterator[List[MyToken]]:
        if number == 0:
            return
        self.expect("LPAREN", "beginning of macro call argument list")
        for ii in range(number):
            delimiter = "COMMA" if ii != number - 1 else "RPAREN"
            argument = list(self.output_generator(end=delimiter))
            yield argument

    def ifdef(self) -> TokenSource:
        name = self.expect("SIMPLE_IDENTIFIER", "ifdef").value
        found = name in self.definitions
        # TODO: handle `elseif
        if found:
            yield from self.output_generator(end=("ENDIFDEF", "ELSEDEF"))
            if self.last_token.type == "ELSEDEF":
                # Drop `else block
                list(self.output_generator(end="ENDIFDEF"))
        else:
            # Drop this block
            list(self.output_generator(end=("ENDIFDEF", "ELSEDEF")))
            if self.last_token.type == "ELSEDEF":
                # Preprocess `else block
                yield from self.output_generator(end="ENDIFDEF")

    def include(self):
        raise NotImplementedError()
