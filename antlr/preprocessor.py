import os
import re
from dataclasses import dataclass, replace
from itertools import takewhile, count
from antlr4 import Token, InputStream
from generated.VerilogALexer import VerilogALexer


def token_code_to_name(code):
    if code == -1:
        return "EOF"
    return VerilogALexer.symbolicNames[code]


@dataclass
class MyToken:
    type: int
    text: str
    channel: int
    origin: [(str, int, int)]

    @property
    def line(self):
        return self.origin[-1][1]

    @property
    def column(self):
        return self.origin[-1][2]

    @classmethod
    def from_antlr_token(cls, token, filename=None):
        origin = [(filename, token.line, token.column)]
        return cls(
            type=token.type, text=token.text, channel=token.channel, origin=origin
        )

    def included_from(self, origin):
        """Return copy of token with added path of include or macro call"""
        return replace(self, origin=origin + self.origin)

    def typename(self):
        return token_code_to_name(self.type)

    def __repr__(self):
        origin = [
            (os.path.basename(f) if f is not None else None, line, column)
            for f, line, column in self.origin
        ]
        return f"MyToken({self.typename()}, {self.text!r}, {origin!r})"

    # source
    # channel
    # start
    # stop
    # tokenIndex
    # line
    # column
    # _text


@dataclass
class Macro:
    parameters: [str]
    body: [MyToken]

    def expand(self, arguments, origin):
        for tok in self.body:
            tok = tok.included_from(origin)
            if tok.type == VerilogALexer.SIMPLE_IDENTIFIER:
                try:
                    idx = self.parameters.index(tok.text)
                except ValueError:
                    pass
                else:
                    for argument_token in arguments[idx]:
                        yield argument_token.included_from(tok.origin)
                    continue
            yield tok


def iter_tokens(tokensource):
    while True:
        ret = tokensource.nextToken()
        yield ret
        if ret.type == Token.EOF:
            return


def lex(filename=None, content=None):
    if content is None:
        assert (
            filename is not None
        ), "If filename is not provided then content is mandatory"
        with open(filename) as fd:
            content = fd.read()
    input_stream = InputStream(content)
    for raw_token in iter_tokens(VerilogALexer(input_stream)):
        yield MyToken.from_antlr_token(raw_token, filename=filename)


class VerilogAPreprocessor:
    def __init__(self, source, definitions=None):
        self.input_iterator = self.input_generator(source)
        self.output_iterator = self.output_generator()
        if definitions is None:
            self.definitions = {}
        else:
            self.definitions = definitions

    def __iter__(self):
        return self.output_iterator

    def input_generator(self, source):
        for token in source:
            self.last_token = token
            yield token

    def nextToken(self):
        return next(self.output_iterator)

    def getSourceName(self):
        return self.lexer.getSourceName()

    def fail(self, why):
        raise Exception(why, self.last_token)

    def output_generator(self, source=None, end=Token.EOF):
        if source is None:
            source = self.input_iterator
        if not isinstance(end, tuple):
            end = (end,)
        for token in source:
            if token.type in end:
                if token.type == Token.EOF:
                    yield token
                return
            if token.type == Token.EOF:
                self.fail("Unexpected EOF")
            elif token.type == VerilogALexer.DEFINE:
                self.define()
            elif token.type == VerilogALexer.IFDEF:
                yield from self.ifdef()
            elif token.type == VerilogALexer.ELSEDEF:
                self.fail("Unexpected `else")
            elif token.type == VerilogALexer.ENDIFDEF:
                self.fail("Unexpected `endif")
            elif token.type == VerilogALexer.INCLUDE:
                yield from self.include()
            elif token.type == VerilogALexer.MACROCALL:
                yield from self.macrocall()
            elif token.type == VerilogALexer.NEWLINE:
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
        match = re.match(r"`define\s+([a-zA-Z_]\w*)(\(?)", self.last_token.text)
        name, parenthesis = match.groups()
        if parenthesis:
            # Macro definition
            parameters = list(self.consume_macro_definition_parameters())
        else:
            # Basic definition
            parameters = []
        body = list(self.takeuntil(lambda tok: tok.type == VerilogALexer.NEWLINE))[:-1]
        definition = Macro(parameters, body)
        self.definitions[name] = definition

    def consume_macro_definition_parameters(self):
        for ii in count():
            tok = next(self.input_iterator)
            if tok.type == VerilogALexer.RPAREN:
                return
            if ii != 0:
                self.expect(
                    VerilogALexer.COMMA, "macro parameter separator", last_token=True
                )
                next(self.input_iterator)
            tok = self.expect(
                VerilogALexer.SIMPLE_IDENTIFIER, "macro parameter", last_token=True
            )
            yield tok.text

    def macrocall(self):
        name = self.last_token.text[1:]
        origin = self.last_token.origin
        macro = self.definitions[name]
        arguments = list(self.consume_macrocall_arguments(len(macro.parameters)))
        yield from VerilogAPreprocessor(
            source=macro.expand(arguments, origin), definitions=self.definitions
        )

    def expect(self, type_, why, last_token=False):
        if not last_token:
            tok = next(self.input_iterator)
        else:
            tok = self.last_token
        if tok.type != type_:
            self.fail("Expected " + token_code_to_name(type_) + " (" + why + ")")
        return tok

    def consume_macrocall_arguments(self, number):
        if number == 0:
            return
        self.expect(VerilogALexer.LPAREN, "beginning of macro call argument list")
        for ii in range(number):
            delimiter = (
                VerilogALexer.COMMA if ii != number - 1 else VerilogALexer.RPAREN
            )
            argument = list(self.output_generator(end=delimiter))
            yield argument

    def ifdef(self):
        name = self.expect(VerilogALexer.SIMPLE_IDENTIFIER, "ifdef").text
        found = name in self.definitions
        # TODO: handle `elseif
        if found:
            yield from self.output_generator(
                end=(VerilogALexer.ENDIFDEF, VerilogALexer.ELSEDEF)
            )
            if self.last_token.type == VerilogALexer.ELSEDEF:
                # Drop `else block
                list(self.output_generator(end=VerilogALexer.ENDIFDEF))
        else:
            # Drop this block
            list(
                self.output_generator(
                    end=(VerilogALexer.ENDIFDEF, VerilogALexer.ELSEDEF)
                )
            )
            if self.last_token.type == VerilogALexer.ELSEDEF:
                # Preprocess `else block
                yield from self.output_generator(end=VerilogALexer.ENDIFDEF)
