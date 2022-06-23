from antlr4 import FileStream, CommonTokenStream, ParseTreeVisitor
from generated.VerilogALexer import VerilogALexer
from generated.VerilogAParser import VerilogAParser
from generated.VerilogAParserVisitor import VerilogAParserVisitor
from preprocessor import VerilogAPreprocessor, lex

from dataclasses import dataclass, field


def parse(source, rule):
    preprocessor = VerilogAPreprocessor(lex(content=source))
    stream = CommonTokenStream(preprocessor)
    parser = VerilogAParser(stream)
    tree = getattr(parser, rule)()
    assert tree is not None, "Parse error"
    return MyVisitor().visit(tree=tree)


@dataclass
class Net:
    name: str
    nature: str = None


@dataclass
class Port(Net):
    # name: str
    # nature: str = None
    direction: str = None


@dataclass
class InitializedVariable:
    name: str
    type: type
    initializer: object


@dataclass
class Module:
    name: str
    ports: [Port] = field(default_factory=list)
    reals: [InitializedVariable] = field(default_factory=list)
    integers: [InitializedVariable] = field(default_factory=list)
    nets: [Net] = field(default_factory=list)

    def newPort(self, name):
        for port in self.ports:
            if port.name == name:
                return port
        port = Port(name=name)
        self.ports.append(port)
        return port


@dataclass
class Identifier:
    name: str


@dataclass
class Float:
    value: float


@dataclass
class String:
    value: str


@dataclass
class Int:
    value: int


@dataclass
class BinaryOp:
    operator: str
    left: object
    right: object


@dataclass
class UnaryOp:
    operator: str
    child: object


@dataclass
class TernaryOp:
    condition: object
    iftrue: object
    iffalse: object


@dataclass
class Nature:
    name: str
    abstol: float
    access: str
    idt_nature: str
    units: str
    ddt_nature: str = None


@dataclass
class Discipline:
    name: str
    domain: str
    potentialnature: str
    flownature: str


@dataclass
class NatureBinding:
    potential_or_flow: str
    nature: str


@dataclass
class DomainBinding:
    discrete_or_continuous: str


class MyVisitor(ParseTreeVisitor):
    def __init__(self):
        self.disciplines = []
        self.modules = []
        with open("single_identifier_rules.txt") as fd:
            single_identifier_rules = set(fd.read().split())
        single_identifier_rules |= set(
            """
start
expression
expr_primary
expr_primary
number
unary_operator
binary_operator2
binary_operator3
binary_operator4
binary_operator6
binary_operator7
binary_operator11
binary_operator12""".split()
        )
        for method in single_identifier_rules:
            name = "visit" + method.capitalize()
            if not hasattr(MyVisitor, name):
                setattr(self, name, self.visitsinglechild)
        for binaryrule in """
expr2
expr3
expr4
expr6
expr7
expr11
expr12
            """.split():
            setattr(self, "visit" + binaryrule.capitalize(), self.visitbinary)

    def visitsinglechild(self, ctx):
        return self.visit(ctx.getChild(0))

    # def visitChildren(self, node):
    # raise NotImplementedError()

    def visitTerminal(self, node):
        type_ = node.getSymbol().type
        name = VerilogALexer.ruleNames[type_ - 1]
        try:
            method = getattr(self, "visit" + name)
        except AttributeError:
            return node.getText()
        return method(node.getText())

    def visitUNSIGNED_NUMBER(self, text):
        return Int(int(text))

    def visitREAL_NUMBER(self, text):
        # TODO: SI prefixes
        return Float(float(text))

    def visitSTRING(self, text):
        # TODO: unescape
        return String(text[1:-1])

    def visitSIMPLE_IDENTIFIER(self, text):
        return Identifier(text)

    def visitExpr1_withoperator(self, ctx):
        "expr1 : unary_operator expr_primary"
        return UnaryOp(self.visit(ctx.getChild(0)), self.visit(ctx.getChild(1)))

    def visitExpr1_withoutoperator(self, ctx):
        "expr1 : expr_primary"
        return self.visit(ctx.getChild(0))

    def visitExpr13_withoperator(self, ctx):
        "expr13 : expr12 TERNARY expr13 COLON expr13"
        return TernaryOp(
            self.visit(ctx.getChild(0)),
            self.visit(ctx.getChild(1)),
            self.visit(ctx.getChild(2)),
        )

    def visitExpr13_withoutoperator(self, ctx):
        "expr13 : expr12"
        return self.visit(ctx.getChild(0))

    def visitbinary(self, ctx):
        childcount = ctx.getChildCount()
        if childcount == 3:
            return BinaryOp(
                self.visit(ctx.getChild(1)),
                self.visit(ctx.getChild(0)),
                self.visit(ctx.getChild(2)),
            )
        elif childcount == 1:
            return self.visit(ctx.getChild(0))
        else:
            raise Exception("Unexpected number of children", childcount)

    def visitNature_attribute_expression(self, ctx):
        x = self.visit(ctx.getChild(0))
        if isinstance(x, Identifier):
            return x.name
        elif isinstance(x, (Float, Int, String)):
            return x.value
        raise Exception(x)

    def visitNature_attribute(self, ctx):
        return (
            self.visit(ctx.nature_attribute_identifier()),
            self.visit(ctx.nature_attribute_expression()),
        )

    def visitNature_declaration(self, ctx):
        print(dict(self.visit(c) for c in ctx.nature_item()))
        return Nature(
            self.visit(ctx.nature_identifier()).name,
            **dict(self.visit(c) for c in ctx.nature_item())
        )

    def visitNature_binding(self, ctx):
        name = self.visit(ctx.nature_identifier()).name
        potential_or_flow = self.visit(ctx.potential_or_flow())
        if potential_or_flow == "potential":
            self.active_discipline.potentialnature = name
        elif potential_or_flow == "flow":
            self.active_discipline.flownature = name
        else:
            raise Exception(potential_or_flow)

    def visitDiscipline_domain_binding(self, ctx):
        self.active_discipline.domain = self.visit(ctx.discrete_or_continuous())

    def visitDiscipline_declaration(self, ctx):
        discipline = Discipline(
            name=self.visit(ctx.discipline_identifier()),
            domain=None,
            flownature=None,
            potentialnature=None,
        )
        self.active_discipline = discipline
        self.disciplines.append(discipline)
        for item in ctx.discipline_item():
            self.visit(item)
        self.active_discipline = None
        return discipline

    def visitModule_declaration(self, ctx):
        module = Module(name=self.visit(ctx.module_identifier()))
        self.modules.append(module)
        self.active_module = module
        self.visitChildren(ctx)
        # for child in ctx.getChildren():
        # self.visit(child)
        self.active_module = None
        return module

    def visitList_of_ports(self, ctx):
        for port in ctx.port():
            self.active_module.newPort(self.visit(port))

    def visitList_of_port_identifiers(self, ctx):
        names = list(map(self.visit, ctx.port_identifier()))
        for name in names:
            self.active_module.newPort(name)
        return names

    def visitInout_declaration(self, ctx):
        # TODO: set discipline if specified
        print("visited inout")
        # import pdb; pdb.set_trace()
        for port in self.visit(ctx.list_of_port_identifiers()):
            self.active_module.newPort(port).direction = "inout"

    def visitInteger_declaration(self, ctx):
        self.active_module.integers.extend(
            self.visit(ctx.list_of_variable_identifiers())
        )

    def visitReal_declaration(self, ctx):
        self.active_module.reals.extend(self.visit(ctx.list_of_real_identifiers()))

    def visitNet_declaration(self, ctx):
        self.active_module.nets.extend(self.visit(ctx.list_of_net_identifiers()))

    def visitList_of_variable_identifiers(self, ctx):
        return list(map(self.visit, ctx.variable_type()))

    def visitList_of_real_identifiers(self, ctx):
        return list(map(self.visit, ctx.real_type()))

    def visitList_of_net_identifiers(self, ctx):
        return list(map(self.visit, ctx.ams_net_identifier()))

    def visitVariable_type(self, ctx):
        return InitializedVariable(
            self.visit(ctx.variable_identifier()), self.visit(ctx.constant_expression())
        )

    def visitReal_type(self, ctx):
        initializer = ctx.constant_expression()
        if initializer is not None:
            initializer = self.visit(initializer)
        return InitializedVariable(
            self.visit(ctx.real_identifier()), "real", initializer
        )
