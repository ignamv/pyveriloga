from lex import VerilogALexer, Token
from dataclasses import dataclass
import itertools
from pathlib import Path


def split(func, iterable):
    ret = []
    empty = True
    for x in iterable:
        empty = False
        if func(x):
            yield ret
            ret = []
        else:
            ret.append(x)
    if not empty:
        yield ret


@dataclass
class Macro:
    parameters: [str]
    body: [Token]
    
    def substitute(self, arguments):
        for token in self.body:
            if token.type_ != 'ID' or token.value not in self.parameters:
                yield token
                continue
            idx = self.parameters.index(token.value)
            yield from arguments[idx]


def preprocess(tokens, include_dirs=None, definitions=None):
    if definitions is None:
        definitions = {}
    if include_dirs is None:
        include_dirs = []
    tokens = iter(tokens)
    yield from PreprocessBlockRecursive(tokens, definitions, outerblock=True, include_dirs=include_dirs)



class PreprocessBlockRecursive:
    """Preprocess until `else or `endif or EOF"""

    def __init__(self, tokens, definitions, outerblock, include_dirs):
        self.tokens = iter(tokens)
        self.definitions = definitions
        self.outerblock = outerblock
        self.last_token = None
        self.include_dirs = include_dirs

    def skip_ifblock(self):
        while True:
            token = self.get_token()
            if token.type_ == 'DIRECTIVE' and token.value in ('endif', 'else'):
                return token
        self.fail('Unexpected EOF')


    def get_token(self, fail_on_eof=True):
        """If fail_on_eof=False, pass on StopIteration so caller can handle it"""
        try:
            self.last_token = next(self.tokens)
        except StopIteration:
            if fail_on_eof:
                self.fail('Unexpected EOF')
            else:
                raise
        return self.last_token


    def fail(self, why):
        raise Exception(why, self.last_token)


    def expect(self, type_=None, value=None):
        try:
            ret = self.get_token()
        except StopIteration:
            self.fail('Unexpected EOF')
        if type_ is not None and ret.type_ != type_:
            self.fail(f'Expected {type_}, got {ret.type_}')
        if value is not None and ret.value != value:
            self.fail(f'Expected {value}, got {ret.value}')
        return ret


    def __iter__(self):
        return self.preprocess_block_recursive(blocktype='outer')


    def consume_definition(self):
        name = self.expect('ID').value
        value = []
        while True:
            token = self.get_token()
            if token.type_ == '\\':
                self.expect('NEWLINE')
                continue
            elif token.type_ == 'NEWLINE':
                break
            value.append(token)
        if value[0].type_ == '(':
            # Substitution macro
            value.pop(0)
            parameters = []
            while True:
                assert value[0].type_ == 'ID'
                parameters.append(value.pop(0).value)
                tok = value.pop(0)
                if tok.type_ == ')':
                    break
                elif tok.type_ == ',':
                    continue
                raise Exception(tok)
            value = Macro(parameters=parameters, body=value)
        self.definitions[name] = value

    def evaluate_macro(self, name):
        value = self.definitions[name]
        if isinstance(value, Macro):
            # Consume arguments
            self.expect('(')
            all_arguments = list(self.preprocess_block_recursive(blocktype='parentheses'))
            split_arguments = list(split(lambda tok: tok.type_ == ',', all_arguments))
            yield from value.substitute(split_arguments)
        else:
            yield from value


    def process_ifdef(self):
        query = self.expect('ID').value
        found = query in self.definitions
        if found:
            # Emit until `else or `endif
            yield from self.preprocess_block_recursive(blocktype='if')
            assert self.last_token.type_ == 'DIRECTIVE'
            if self.last_token.value == 'endif':
                return
            elif self.last_token.value == 'else':
                # Skip until `endif
                assert self.skip_ifblock().value == 'endif'
            else:
                raise Exception('Unexpected token', self.last_token)
        else:
            # Skip until `else or `endif
            lasttoken = self.skip_ifblock()
            if lasttoken.value == 'endif':
                return
            # Else block, emit until endif
            yield from self.preprocess_block_recursive(blocktype='if')

    def process_include(self):
        filename = self.expect('STRING').value
        candidate = filename
        if candidate[0] != '/':
            # Relative import, check directory of current file
            current_file = Path(self.last_token.origin[-1][0])
            candidate = (current_file.parent) / filename
            if not candidate.exists():
                for dirname in self.include_dirs:
                    candidate = Path(dirname) / filename
                    if candidate.exists():
                        break
                else:
                    self.fail(f'File not found: {filename}')
        with open(candidate) as fd:
            included_tokens = list(VerilogALexer().lex(fd.read(), fd.name, included_from=self.last_token.origin))
        self.tokens = itertools.chain(included_tokens, self.tokens)

    def preprocess_block_recursive(self, blocktype):
        parentheses_level = 0
        # Can't use for loop because I'm reassigning self.tokens on `include
        while True:
            try:
                token = self.get_token(fail_on_eof=False)
            except StopIteration:
                break
            if token.type_ != "DIRECTIVE":
                if token.type_ == '(':
                    parentheses_level += 1
                elif token.type_ == ')':
                    parentheses_level -= 1
                    if parentheses_level == -1:
                        assert blocktype == 'parentheses'
                        return
                yield token
                continue
            if token.value == 'define':
                self.consume_definition()
            elif token.value in self.definitions:
                yield from self.evaluate_macro(token.value)
            elif token.value in ('else', 'endif'):
                assert blocktype == 'if'
                break
            elif token.value == 'ifdef':
                yield from self.process_ifdef()
            elif token.value == 'include':
                self.process_include()
            else:
                self.fail('Macro not found')
        else:
            # Reached EOF
            assert blocktype == 'outer'


def preprocess_all():
    from pathlib import Path

    filenames = (Path(".") / "inputfiles" / "dump").glob("resistor.va")
    filenames = [(Path(".") / "include" / "disciplines.vams")]
    for filename in filenames:
        print(filename)
        with filename.open() as fd:
            content = fd.read()
        lexer = VerilogALexer()
        tokens = lexer.lex(content, str(filename))
        output = list(preprocess(tokens, include_dirs=['include']))


if __name__ == "__main__":
    preprocess_all()
