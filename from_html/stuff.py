import sys
import re
from functools import total_ordering
from collections import defaultdict
from abc import ABC, abstractmethod
import dataclasses
from antlr4 import FileStream, CommonTokenStream, InputStream
from BNFLexer import BNFLexer
from BNFParser import BNFParser
from BNFVisitor import BNFVisitor
from itertools import groupby
import logging


logger = logging.getLogger(__name__)


@total_ordering
class Definition(ABC):
    precedence = None

    @staticmethod
    def from_bnf(bnf):
        if not bnf:
            return empty()
        input_stream = InputStream(bnf)
        lexer = BNFLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = BNFParser(stream)
        tree = parser.definition()
        return MyVisitor().visit(tree=tree)

    def __lt__(self, other):
        assert isinstance(other, Definition)
        class_order = [
            Literal,
            Identifier,
            CharacterClass,
            Optional,
            ZeroOrMore,
            Concatenation,
            Alternatives,
        ]
        idx1 = class_order.index(type(self))
        idx2 = class_order.index(type(other))
        if idx1 < idx2:
            return True
        elif idx1 > idx2:
            return False
        assert isinstance(self, type(other))
        return self.lessthan(other)

    def has_children(self):
        return hasattr(self, "children")

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
            newchildren = tuple(
                child.substitute(replacements) for child in self.getchildren()
            )
            changes = any(
                newchild is not oldchild
                for newchild, oldchild in zip(newchildren, self.children)
            )
            if changes:
                return dataclasses.replace(self, children=newchildren)
            else:
                return self

    def remove(self, to_remove):
        ret = self.substitute({to_remove: impossible()})
        return ret.simplify()

    def simplify(self):
        return self


def empty():
    return Concatenation(())


def impossible():
    return Alternatives(())


@dataclasses.dataclass(frozen=True)
class Identifier(Definition):
    name: str

    def to_bnf(self):
        return self.name

    def to_antlr(self):
        return self.name

    def lessthan(self, other):
        return self.name < other.name


@dataclasses.dataclass(frozen=True)
class Literal(Definition):
    value: str

    def __post_init__(self):
        object.__setattr__(
            self, "value", self.value.replace(r"\'", "'").replace(r"\\", "\\")
        )

    def to_bnf(self):
        return repr(self.value)

    def to_antlr(self):
        return repr(self.value)

    def lessthan(self, other):
        return self.value < other.value


@dataclasses.dataclass(frozen=True)
class CharacterClass(Definition):
    pattern: str

    def to_bnf(self):
        return "[" + self.pattern + "]"

    def to_antlr(self):
        pattern = self.pattern
        negated = pattern[0] == '^'
        # TODO: other escapes?
        pattern = pattern.replace('\\', '\\\\').replace(']', '\\]')
        if negated:
            return "~[" + pattern[1:] + "]"
        return "[" + pattern + "]"

    def lessthan(self, other):
        return self.pattern < other.pattern


def parenthesize(string, inner_precedence, outer_precedence):
    if inner_precedence is not None and inner_precedence > outer_precedence:
        return "(" + string + ")"
    return string


@dataclasses.dataclass(frozen=True)
class Concatenation(Definition):
    children: [Definition]
    precedence = 1

    def to_bnf(self):
        if not self.children:
            return "ε"
        return " ".join(parenthesize(child.to_bnf(), child.precedence, self.precedence)
                for child in self.children)

    def to_antlr(self):
        if not self.children:
            return ""
        return " ".join(parenthesize(child.to_antlr(), child.precedence, self.precedence)
                for child in self.children)

    def lessthan(self, other):
        return self.children < other.children

    def simplify(self):
        children1 = [child.simplify() for child in self.children]
        children2 = []
        for child in children1:
            if isinstance(child, Concatenation):
                children2.extend(child.children)
            else:
                children2.append(child)
        if any(child == impossible() for child in children2):
            return impossible()
        if len(children2) == 1:
            return children2[0]
        return Concatenation(tuple(children2))


@dataclasses.dataclass(frozen=True)
class Alternatives(Definition):
    children: [Definition]
    precedence = 2

    def to_bnf(self):
        if not self.children:
            return "Ø"
        return " | ".join(parenthesize(child.to_bnf(), child.precedence, self.precedence)
                for child in self.children)

    def to_antlr(self):
        if not self.children:
            return "impossible"
        return " | ".join(parenthesize(child.to_antlr(), child.precedence, self.precedence)
                for child in self.children)

    def lessthan(self, other):
        return self.children < other.children

    def simplify(self):
        children = []
        for child in self.children:
            child = child.simplify()
            if isinstance(child, Alternatives):
                children.extend(child.children)
            else:
                children.append(child)
        children = tuple(sorted(set(children)))
        if len(children) == 1:
            return children[0]
        return Alternatives(children)


@dataclasses.dataclass(frozen=True)
class SingleChild(Definition):
    children: [Definition]

    @property
    def child(self):
        (child,) = self.children
        return child

    def lessthan(self, other):
        return self.child < other.child

    def __init__(self, child=None, children=None):
        if child is not None:
            assert children is None
        else:
            (child,) = children
        object.__setattr__(self, "children", (child,))


class Optional(SingleChild):
    precedence = 0
    def to_bnf(self):
        return "[ " + self.child.to_bnf() + " ]"

    def to_antlr(self):
        child = parenthesize(self.child.to_antlr(), self.child.precedence, self.precedence)
        return child + '?'

    def simplify(self):
        child = self.child.simplify()
        if child == impossible() or child == empty():
            return empty()
        return Optional(child)


class ZeroOrMore(SingleChild):
    precedence = 0
    def to_bnf(self):
        return "{ " + self.child.to_bnf() + " }"

    def to_antlr(self):
        child = parenthesize(self.child.to_antlr(), self.child.precedence, self.precedence)
        return child + '*'

    def simplify(self):
        child = self.child.simplify()
        if child == impossible() or child == empty():
            return empty()
        return ZeroOrMore(child)


class MyVisitor(BNFVisitor):
    def visitDocument(self, ctx: BNFParser.DocumentContext):
        ret = {}
        for rule in ctx.bnfrule():
            k, v = self.visitBnfrule(rule)
            ret[k] = v
        return ret

    def visitBnfrule(self, ctx: BNFParser.BnfruleContext):
        name = ctx.IDENTIFIER().getText()
        definition = self.visit(ctx.definition())
        return name, definition

    def visitIdentifier(self, ctx: BNFParser.IdentifierContext):
        return Identifier(ctx.IDENTIFIER().getText())

    def visitLiteral(self, ctx: BNFParser.LiteralContext):
        return Literal(ctx.LITERAL().getText()[1:-1])

    def visitCharclass(self, ctx: BNFParser.CharclassContext):
        pattern = ctx.CHARACTERCLASS().getText()[1:-1]
        # TODO: other escapes?
        pattern = pattern.replace('\\]', ']').replace('\\\\', '\\')
        return CharacterClass(pattern)

    def visitImpossible(self, ctx: BNFParser.ImpossibleContext):
        return impossible()

    def visitEmpty(self, ctx: BNFParser.EmptyContext):
        return empty()

    def visitBracketed(self, ctx: BNFParser.BracketedContext):
        return Optional(self.visit(ctx.definition()))

    def visitParenthesized(self, ctx: BNFParser.ParenthesizedContext):
        return self.visit(ctx.definition())

    def visitBraced(self, ctx: BNFParser.BracedContext):
        return ZeroOrMore(self.visit(ctx.definition()))

    def visitConcatenate(self, ctx: BNFParser.ConcatenateContext):
        return Concatenation(
            tuple(self.visit(definition) for definition in ctx.definition())
        )

    def visitAlternative(self, ctx: BNFParser.AlternativeContext):
        return Alternatives(
            tuple(self.visit(definition) for definition in ctx.definition())
        )


class Grammar:
    def __init__(self, rules):
        self.rules = rules
        self.invalidate()

    def __repr__(self):
        return f'Grammar({self.rules!r})'

    def update(self, grammar):
        self.rules.update(grammar.rules)
        self.invalidate()

    def __delitem__(self, name):
        del self.rules[name]
        self.invalidate()

    def to_bnf(self):
        pieces = []
        for name, definition in sorted(self.rules.items()):
            pieces.append(name + ' ::= ' + definition.to_bnf())
        return '\n'.join(pieces)

    @staticmethod
    def tag_definition(rule, definition, tags):
        ret = definition.to_antlr()
        try:
            tag = ' # ' + tags[rule, ret]
        except KeyError:
            tag = ''
        return ret + tag


    def rule_order(self, rule):
        name, definition = rule
        is_literal = isinstance(definition, Literal)
        length = len(definition.value) if is_literal else 0
        return not is_literal, -length, name, definition
        

    def to_antlr(self, tags=None):
        if tags is None:
            tags = {}
        pieces = []
        for name, definition in sorted(self.rules.items(), key=self.rule_order):
            if isinstance(definition, Alternatives):
                if len(definition.children) == 0:
                    definition = 'impossible'
                else:
                    definition = (
                        '\n    | '.join(self.tag_definition(name, child, tags) for child in definition.children)
                    )
            else:
                definition = definition.to_antlr()
            pieces.append(name + ':\n      ' + definition + ';')
        return '\n'.join(pieces)

    def invalidate(self):
        self._literals = None
        self._rule_users = None
        self._literal_users = None
        self._missing_rules = None

    def __eq__(self, other):
        if not isinstance(other, Grammar):
            return False
        return self.canonicalize().rules == other.canonicalize().rules

    def canonicalize(self, inplace=False):
        rules = self.rules
        if not inplace:
            rules = rules.copy()
        for k, v in list(rules.items()):
            rules[k] = v.simplify()
        if not inplace:
            return Grammar(rules)

    def remove(self, node):
        pending = {node}
        while pending:
            to_remove = pending.pop()
            for name, original in list(self.rules.items()):
                changed = original.remove(to_remove)
                if changed == impossible():
                    del self.rules[name]
                    pending.add(Identifier(name))
                else:
                    self.rules[name] = changed

    @classmethod
    def from_bnf(cls, filename=None, bnf=None):
        if filename is not None:
            input_stream = FileStream(filename)
        elif bnf is not None:
            input_stream = InputStream(bnf)
        else:
            raise Exception("Either filename or bnf must be specified")
        lexer = BNFLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = BNFParser(stream)
        tree = parser.document()
        rules = MyVisitor().visit(tree=tree)
        return cls(rules)

    def calculateDirectUsers(self):
        """Calculate dict mapping rule or literal name to the rules which mention it"""
        rule_users = defaultdict(list)
        literal_users = defaultdict(list)
        for rulename, rule in self.rules.items():
            for node in rule.descendants():
                if isinstance(node, Identifier):
                    rule_users[node.name].append(rulename)
                elif isinstance(node, Literal):
                    literal_users[node.value].append(rulename)
        self._rule_users = dict(rule_users)
        self._literal_users = dict(literal_users)

    def ensure_directusers_valid(self):
        if self._rule_users is None:
            self.calculateDirectUsers()

    @property
    def rule_users(self):
        self.ensure_directusers_valid()
        return self._rule_users

    @property
    def literal_users(self):
        self.ensure_directusers_valid()
        return self._literal_users

    @property
    def literals(self):
        if self._literals is None:
            self._literals = {
                node.value
                for rule in self.rules.values()
                for node in rule.descendants(Literal)
            }
        return self._literals

    def recurseRules(self, start, ignore_missing=True):
        visited = set()
        pending = {start}
        while pending:
            name = pending.pop()
            visited.add(name)
            try:
                rule = self.rules[name]
            except KeyError:
                if not ignore_missing:
                    raise
                continue
            mentioned = {
                identifier.name
                for identifier in rule.descendants(Identifier)
            }
            pending.update(mentioned - visited)
        return visited

    def removeOrphans(self, startrule):
        visited = self.recurseRules(startrule)
        orphans = set(self.rules) - visited
        logger.debug("Culling orphans: %s", orphans)
        for name in orphans:
            del self.rules[name]
        self.invalidate()

    def replace_rules(self, **replacements):
        for k, v in replacements.items():
            assert k in self.rules
            self.rules[k] = v
        self.invalidate()

    def substitute(self, replacements):
        for name in self.rules:
            self.rules[name] = self.rules[name].substitute(replacements)
        self.invalidate()

    @property
    def missing_rules(self):
        if self._missing_rules is None:
            self._missing_rules = set(self.rule_users) - set(self.rules)
        return self._missing_rules

    def __getitem__(self, name):
        return self.rules[name]

    def __setitem__(self, name, value):
        self.rules[name] = value
        self.invalidate()

    def replace_single_identifier_rules(self):
        """Replace rules which are only a single identifier, with that identifier"""
        while True:
            single_identifier_rules = {Identifier(name): definition 
                                       for name, definition in self.rules.items() 
                                       if isinstance(definition, Identifier)}
            if not single_identifier_rules:
                break
            self.substitute(single_identifier_rules)
            for identifier in single_identifier_rules:
                del self.rules[identifier.name]
            self.canonicalize(inplace=True)
