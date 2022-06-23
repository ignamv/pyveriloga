import sys
import re
from collections import defaultdict
from abc import ABC, abstractmethod
from dataclasses import dataclass
from antlr4 import FileStream, CommonTokenStream
from BNFLexer import BNFLexer
from BNFParser import BNFParser
from BNFVisitor import BNFVisitor
from itertools import groupby
import logging


logger = logging.getLogger(__name__)


class Definition(ABC):
    def has_children(self):
        return hasattr(self, 'children')

    def getchildren(self):
        if self.has_children():
            yield from self.children

    def descendants(self, type_=None):
        if type_ is None or isinstance(self, type_):
            yield self
        for child in self.getchildren():
            yield from child.descendants(type_)

    def substitute(self, replacements):
        try:
            return replacements[self]
        except KeyError:
            pass
        if not self.has_children():
            return self
        else:
            newchildren = tuple(child.substitute(replacements) for child in self.getchildren())
            changes = any(newchild is not oldchild for newchild, oldchild in zip(newchildren, self.children))
            if changes:
                return self.replace(children=newchildren)
            else:
                return self

@dataclass(frozen=True)
class Identifier(Definition):
    name: str

@dataclass(frozen=True)
class Literal(Definition):
    value: str
    def __init__(self, value):
        object.__setattr__(self, 'value', value.replace(r"\'", "'").replace(r"\\", "\\"))

@dataclass(frozen=True)
class CharacterClass(Definition):
    pattern: str

@dataclass(frozen=True)
class Concatenation(Definition):
    children: [Definition]

@dataclass(frozen=True)
class Alternatives(Definition):
    children: [Definition]

@dataclass(frozen=True)
class SingleChild(Definition):
    child: Definition
    children: [Definition]
    def __init__(self, child):
        object.__setattr__(self, 'child', child)
        object.__setattr__(self, 'children', (child,))

class Optional(SingleChild):
    pass

class ZeroOrMore(SingleChild):
    pass


class MyVisitor(BNFVisitor):
    def visitDocument(self, ctx:BNFParser.DocumentContext):
        ret = {}
        for section in ctx.section():
            k, v = self.visitSection(section)
            if not v:
                # Skip empty section
                continue
            ret[k] = v
        return ret

    def visitSection(self, ctx:BNFParser.SectionContext):
        name = ctx.SECTION().getText()
        ret = {}
        for rule in ctx.bnfrule():
            k, v = self.visitBnfrule(rule)
            ret[k] = v
        return name, ret

    def visitBnfrule(self, ctx:BNFParser.BnfruleContext):
        name = ctx.IDENTIFIER().getText()
        definition = self.visit(ctx.definition())
        return name, definition

    def visitIdentifier(self, ctx:BNFParser.IdentifierContext):
        return Identifier(ctx.IDENTIFIER().getText())

    def visitLiteral(self, ctx:BNFParser.LiteralContext):
        return Literal(ctx.LITERAL().getText()[1:-1])

    def visitCharclass(self, ctx:BNFParser.CharclassContext):
        return CharacterClass(ctx.CHARACTERCLASS().getText()[1:-1])

    def visitBracketed(self, ctx:BNFParser.BracketedContext):
        return Optional(self.visit(ctx.definition()))

    def visitBraced(self, ctx:BNFParser.BracedContext):
        return ZeroOrMore(self.visit(ctx.definition()))

    def visitConcatenate(self, ctx:BNFParser.ConcatenateContext):
        return Concatenation(tuple(self.visit(definition) for definition in ctx.definition()))

    def visitAlternative(self, ctx:BNFParser.AlternativeContext):
        return Alternatives(tuple(self.visit(definition) for definition in ctx.definition()))

def recurseRules(rules, start):
    visited = set()
    pending = {start}
    while pending:
        name = pending.pop()
        visited.add(name)
        mentioned = {identifier.name for identifier in rules[name].descendants(Identifier)}
        pending.update(mentioned - visited)
    return visited


def removeOrphans(rules, startrule):
    visited = recurseRules(rules, startrule)
    orphans = set(rules) - visited
    logger.debug('Culling orphans: %s', orphans)
    for name in orphans:
        del rules[name]


def findDirectUsers(rules):
    """Return dict mapping rule name to the rules which mention it, same for literals"""
    rule_users = defaultdict(list)
    literal_users = defaultdict(list)
    for rulename, rule in rules.items():
        for node in rule.descendants(Identifier):
            rule_users[node.name].append(rulename)
        for node in rule.descendants(Literal):
            literal_users[node.value].append(rulename)
    return dict(rule_users), dict(literal_users)


def parse_bnf():
    input_stream = FileStream(sys.argv[1])
    lexer = BNFLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = BNFParser(stream)
    tree = parser.document()
    categorized_rules = MyVisitor().visit(tree=tree)
    # Map from section name to rule name
    sections = {k: list(v) for k,v in categorized_rules.items()}
    # All rules together
    rules = {k: v for section in categorized_rules.values() for k,v in section.items()}
    return rules, sections


def main():
    rules, sections = parse_bnf()
    with open('reserved') as fd:
        reserved = set(map(str.strip, fd))
    with open('operators') as fd:
        operator_to_name = dict(line.strip().split('\t') for line in fd)
    #with open('literals') as fd:
        #literal_names = dict(line.strip().split('\t') for line in fd)
    start_rule = 'source_text'
    initial_literals = {node.value for rule in rules.values() for node in rule.descendants(Literal)}
    replacements = {
        'hex_digit': CharacterClass('a-fA-F0-9xXzZ?'),
        'octal_digit': CharacterClass('0-7xXzZ?'),
        'binary_digit': CharacterClass('01xXzZ?'),
        'decimal_digit': CharacterClass('0-9'),
        'non_zero_decimal_digit': CharacterClass('1-9'),
        'analog_function_call': Identifier('function_call'),
        'analog_filter_function_call': Identifier('function_call'),
        'branch_probe_function_call': Identifier('function_call'),
        'indirect_expression': Identifier('function_call'),
        'analog_event_functions': Identifier('function_call'),
    }
    for k, v in replacements.items():
        assert k in rules
        rules[k] = v
    rule_users, literal_users = findDirectUsers(rules)
    missing = set(rule_users) - set(rules)
    for k in missing:
        rules[k] = Literal('MISSING')
    removeOrphans(rules, start_rule)
    rule_users, literal_users = findDirectUsers(rules)
    literals = {node.value for rule in rules.values() for node in rule.descendants(Literal)}
    identifiers = {node.name for rule in rules.values() for node in rule.descendants(Identifier)}
    for lit in literals:
        match = re.match('\$(\w+)\s*\($', lit)
        if not match:
            continue
        print(literal_users[lit])
    replacements = {lit: Concatenation([Identifier('system_function_identifier'), Literal('(')])
        for lit in literals if lit.strip()[0] == '$' and lit[-1] == '('}
    for name in rules:
        rules[name] = rules[name].substitute(replacements)
    literals = {node.value for rule in rules.values() for node in rule.descendants(Literal)}
    identifiers = {node.name for rule in rules.values() for node in rule.descendants(Identifier)}
    weird = literals - reserved - set(operator_to_name)
    replacements = {}
    for l in weird:
        if re.match(r'\$(\w+)\s*\(', l):
            replacements[l] = 

 
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
