import ply.lex as lex
from dataclasses import dataclass


@dataclass
class Token:
    type_: str
    value: str | float
    # Hierarchy of inclusion: (filename, line, byte)
    origin: [(str, int, int)]


class VerilogALexer:
    reserved = (
        "module endmodule in out inout analog begin end real parameter from".split()
    )
    literals = "+-!~&|^*/%=;()[],:><?@"
    tokens = (
        "DIRECTIVE",
        "STRING",
        "ID",
        "ATTR",
        "ENDATTR",
        "DECIMALNUMBER",
        "REALNUMBER",
        "SYSFUNCID",
        "ANALOGCONTRIBUTION",
        "NEWLINE",
        "COMMENT",
        "CONTINUATION",
    ) + tuple(s.upper() for s in reserved)
    t_ignore = " \t"
    t_ATTR = r"\(\*"
    t_ENDATTR = r"\*\)"
    t_DECIMALNUMBER = r"\d+"
    t_SYSFUNCID = r"\$[a-zA-Z0-9_$]+"
    t_ANALOGCONTRIBUTION = r"<\+"
    t_CONTINUATION = r"\\\n"
    t_NEWLINE = r"\n"

    # Make ply track line numbers
    def t_newline(self, t):
        r"\n+"
        t.lexer.lineno += len(t.value)

    def t_DIRECTIVE(self, t):
        r"`\w+"
        t.value = t.value[1:]
        return t

    def t_STRING(self, t):
        r'"(?:[^"\n]|\"|\\\n)+"'
        t.value = t.value[1:-1]
        return t

    def t_REALNUMBER(self, t):
        r"\d+\.\d+([eE][+-]?\d+|[TGMKkmunpfa])?|\d+([eE][+-]?\d+|[TGMKkmunpfa])"
        prefixes = {
            "T": 12,
            "G": 9,
            "M": 6,
            "K": 3,
            "k": 3,
            "m": -3,
            "u": -6,
            "n": -9,
            "p": -12,
            "f": -15,
            "a": -18,
        }
        if t.value[-1] in prefixes:
            exponent = prefixes[t.value[-1]]
            t.value = t.value[:-1] + "e" + str(exponent)
        t.value = float(t.value)
        return t

    def t_ID(self, t):
        r"\\?[a-zA-Z_]\w*"
        if t.value in self.reserved:
            t.type = t.value.upper()
        else:
            t.type = "ID"
        if t.value[0] == '\\':
            t.value = t.value[1:]
        return t

    def t_COMMENT(self, t):
        r"/\*(.|\n)*?\*/|//[^\n]*"
        pass

    def __init__(self):
        self.lexer = None

    def build(self, **kwargs):
        self.lexer = lex.lex(module=self, **kwargs)

    def lex(self, input_, filename, included_from=None):
        if included_from is None:
            included_from = []
        if self.lexer is None:
            self.build()
        self.lexer.input(input_)
        for original_token in iter(self.lexer.token, None):
            token = Token(
                type_=original_token.type,
                value=original_token.value,
                origin=included_from
                + [(filename, original_token.lineno, original_token.lexpos)],
            )
            yield token


def lex_all():
    from pathlib import Path

    for filename in (Path(".") / "inputfiles" / "dump").glob("*.va"):
        print(filename)
        with filename.open() as fd:
            content = fd.read()
        lexer = VerilogALexer()
        list(lexer.lex(content))


def lexme():
    lexer = VerilogALexer()
    content = '`hola "PEPE\\"SASA" begin pepe ; (* 2 2.3 2.3e-3 2.3T $strobe <+ /* !@\n#$\n%^& */ //pepe\nhola'
    print(list(lexer.lex(content)))


if __name__ == "__main__":
    # lexme()
    lex_all()
