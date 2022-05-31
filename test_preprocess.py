import pytest
from lex import Token, VerilogALexer
from preprocess import preprocess, split


@pytest.mark.parametrize(
    "input_,expected",
    [
        # No changes
        ([("MODULE", ""), ("ID", "diode")], [("MODULE", ""), ("ID", "diode")]),
        # Remove content of false ifdef
        (
            [
                ("ID", "before"),
                ("DIRECTIVE", "ifdef"),
                ("ID", "MISSING"),
                ("ID", "should_be_excluded"),
                ("DIRECTIVE", "endif"),
                ("ID", "after"),
            ],
            [("ID", "before"), ("ID", "after")],
        ),
        # Include content of else in false ifdef
        (
            [
                ("ID", "before"),
                ("DIRECTIVE", "ifdef"),
                ("ID", "MISSING"),
                ("ID", "should_be_excluded"),
                ("DIRECTIVE", "else"),
                ("ID", "should_be_included"),
                ("DIRECTIVE", "endif"),
                ("ID", "after"),
            ],
            [("ID", "before"), 
                ("ID", "should_be_included"),
                ("ID", "after")],
        ),
        # Define constant macro
        (
            [
                ("DIRECTIVE", "define"), ('ID', 'myvar'), ('REALNUMBER', 2.3), ('NEWLINE', ''),
                ("DIRECTIVE", "myvar")
            ],
            [
                ('REALNUMBER', 2.3),
                ],
            ),

        # Include content of true ifdef
        (
            [
                ("DIRECTIVE", "define"), ('ID', 'myvar'), ('REALNUMBER', 2.3), ('NEWLINE', ''),
                ("DIRECTIVE", "ifdef"),
                ("ID", "myvar"),
                ("ID", "should_be_included"),
                ("DIRECTIVE", "endif"),
                ("ID", "after"),
            ],
            [("ID", "should_be_included"), ("ID", "after")],
        ),
        # Exclude content of else in true ifdef
        (
            [
                ("DIRECTIVE", "define"), ('ID', 'myvar'), ('REALNUMBER', 2.3), ('NEWLINE', ''),
                ("DIRECTIVE", "ifdef"),
                ("ID", "myvar"),
                ("ID", "should_be_included"),
                ("DIRECTIVE", "else"),
                ("ID", "should_be_excluded"),
                ("DIRECTIVE", "endif"),
                ("ID", "after"),
            ],
            [
                ("ID", "should_be_included"),
                ("ID", "after")],
        ),
        # Define substitution macro
        (
            [
                ("DIRECTIVE", "define"), 
                ('ID', 'mymacro'), ('(',''),('ID', 'a'),(',',''),('ID','b'),(')','') ,
                ('ID','a'),('+',''),('\\',''),('NEWLINE',''),('ID','b'),('NEWLINE', ''),
                ("DIRECTIVE", "mymacro"),('(',''),('ID', 'value_a'),(',',''),('ID','value_b'),(')','') 

            ],
            [
                ('ID','value_a'),('+',''),('ID','value_b')
                ],
            ),
    ],
)
def test_preprocess_simple(input_, expected):
    realinput = [Token(type_=type_, value=value, origin=[]) for type_, value in input_]
    realoutput = list(preprocess(realinput))
    output = [(t.type_, t.value) for t in realoutput]
    assert output == expected


def test_include(tmp_path):
    in1 = tmp_path / 'in1'
    in2 = tmp_path / 'in2'
    incdir = tmp_path / 'incdir'
    incdir.mkdir()
    in3 = incdir / 'in3'
    in1_content = f'in1\n`include "in2"'
    with in2.open('w') as fd:
        fd.write(f'in2\n`include "in3"')
    with in3.open('w') as fd:
        fd.write('in3')
    tokens = VerilogALexer().lex(in1_content, str(in1))
    output = list(preprocess(tokens, include_dirs=[incdir]))
    assert all(tok.type_ == 'ID' for tok in output)
    assert [tok.value for tok in output] == ['in1','in2','in3']


def test_split():
    is_comma = lambda s: s == ','
    assert list(split(is_comma, '')) == []
    assert list(split(is_comma, 'a')) == [['a']]
    assert list(split(is_comma, 'ab')) == [['a','b']]
    assert list(split(is_comma, 'ab,')) == [['a','b'],[]]
    assert list(split(is_comma, 'ab,cd,ef')) == [['a','b'],['c','d'],['e','f']]
