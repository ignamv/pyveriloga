import pytest
from stuff import Grammar, Definition

bnf = Definition.from_bnf


@pytest.mark.parametrize(
    "definition, to_remove, expected",
    [
        ("'abc'", "'abc'", "Ø"),
        ("'abc'", "'def'", "'abc'"),
        ("'abc'", "abc", "'abc'"),
        ("abc", "'abc'", "abc"),
        ("[ 'abc' ]", "'abc'", ""),
        ("{ 'abc' }", "'abc'", ""),
        ("before { 'abc' } after", "'abc'", "before after"),
        ("before [ 'abc' ] after", "'abc'", "before after"),
        ("before 'abc' after", "'abc'", "Ø"),
    ],
)
def test_remove_definition(definition, to_remove, expected):
    definition, to_remove, expected = map(bnf, (definition, to_remove, expected))
    assert definition.remove(to_remove) == expected


@pytest.mark.parametrize(
    "original,to_remove,expected",
    [
        (
            " start ::= 'some' [ 'optional' ] 'stuff' ",
            "'optional'",
            " start ::= 'some' 'stuff' ",
        ),
        (
            " start ::= 'some' { 'optional' } 'stuff' ",
            "'optional'",
            " start ::= 'some' 'stuff' ",
        ),
        (
            " start ::= possible | impossible | another ",
            "impossible",
            " start ::= another | possible",
        ),
        (" start ::= 'some' 'nonoptional' 'stuff' ", "'nonoptional'", " ",),
        (""" 
        direct_victim ::= 'some' 'nonoptional' 'stuff' 
        downstream_dependency ::= abc direct_victim def
        """, "'nonoptional'", " ",),
        (""" 
        direct_victim ::= 'some' 'nonoptional' 'stuff' 
        downstream_dependency ::= abc direct_victim def | should_remain
        """, "'nonoptional'", " downstream_dependency ::= should_remain",),
        (""" 
        direct_victim ::= 'some' 'nonoptional' 'stuff' 
        downstream_dependency ::= abc [ direct_victim | should_remain ] def
        """, "'nonoptional'", " downstream_dependency ::= abc [ should_remain ] def",),
    ],
)
def test_remove(original, to_remove, expected):
    original, expected = [Grammar.from_bnf(bnf=bnf) for bnf in (original, expected)]
    original.remove(bnf(to_remove))
    print('EXPECTED')
    print(expected)
    print('ACTUAL')
    print(original)
    assert original == expected


@pytest.mark.parametrize(
    "original,expected",
    [
        ("c | Ø | b", "b | c"),
        ("a [ ε c | Ø | b ]", "a [ b | c ]"),
        ("b  Ø  c", "Ø"),
        ("c  ε  b", "c b"),
        ("b  [ Ø ]  c", "b c"),
        ("b  { Ø }  c", "b c"),
        ("b  [ ε ]  c", "b c"),
        ("b  { ε }  c", "b c"),
        ("b  { ε }  c", "b c"),
    ],
)
def test_simplify(original, expected):
    assert bnf(original).simplify() == bnf(expected)


def test_grammar_equality():
    g1 = Grammar.from_bnf(bnf=' name1 ::= c | b \n name2 ::= f | e')
    g1_reorder = Grammar.from_bnf(bnf=' name2 ::= e | f \n name1 ::= b | c')
    g2 = Grammar.from_bnf(bnf=' name1 ::= d \n name2 ::= z')
    assert g1 == g1_reorder
    assert g1_reorder == g1
    assert g1 != g2
    assert g2 != g1
    assert g1_reorder != g2
    assert g2 != g1_reorder


def test_parse_grammar():
    assert Grammar.from_bnf(bnf=' ') == Grammar({})
