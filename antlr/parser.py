from antlr4 import FileStream, CommonTokenStream, ParseTreeVisitor
from generated.VerilogALexer import VerilogALexer
from generated.VerilogAParser import VerilogAParser
from generated.VerilogAParserVisitor import VerilogAParserVisitor
from preprocessor import VerilogAPreprocessor, lex
from typing import Mapping
from verilogatypes import integertype, realtype, VerilogAType

from dataclasses import dataclass, field


def parse(source, rule):
    preprocessor = VerilogAPreprocessor(lex(content=source))
    stream = CommonTokenStream(preprocessor)
    parser = VerilogAParser(stream)
    tree = getattr(parser, rule)()
    assert tree is not None, "Parse error"
    return MyVisitor().visit(tree=tree)


@dataclass
class VariableAssignment:
    lvalue: str
    value: object
    type: VerilogAType = None


@dataclass
class InitializedVariable:
    name: str
    type: VerilogAType
    initializer: object
    compiled: object = None


@dataclass
class Analog:
    content: object = None
    compiled: object = None


@dataclass
class Variables:
    variables: Mapping[str, InitializedVariable] = field(default_factory=dict)

    def declare(self, variable):
        assert variable.name not in self.variables
        self.variables[variable.name] = variable

    def __getitem__(self, name):
        return self.variables[name]

    def __iter__(self):
        return iter(self.variables.values())


@dataclass
class AnalogSequence:
    variables: Variables = field(default_factory=Variables)
    statements: list = field(default_factory=list)


@dataclass
class FunctionSignature:
    returntype: VerilogAType
    parameters: [VerilogAType]


@dataclass
class Function:
    name: str
    signature: FunctionSignature
    compiled: object = None


@dataclass
class FunctionCall:
    name: str
    arguments: list


@dataclass
class AnalogContribution:
    accessor: str
    lvalue1: str
    lvalue2: str = None
    rvalue: object = None


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
class Module:
    name: str
    variables: Variables = field(default_factory=Variables)
    ports: [Port] = field(default_factory=list)
    nets: [Net] = field(default_factory=list)
    analogs: [Analog] = field(default_factory=list)

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
    type: VerilogAType = None


@dataclass
class Float:
    value: float
    type: VerilogAType = realtype

    def __post_init__(self):
        self.value = float(self.value)


@dataclass
class String:
    value: str


@dataclass
class Int:
    value: int
    type: VerilogAType = integertype

    def __post_init__(self):
        assert isinstance(self.value, int)


@dataclass
class BinaryOp:
    operator: str
    left: object
    right: object
    type: VerilogAType = None


@dataclass
class UnaryOp:
    operator: str
    child: object
    type: VerilogAType = None


@dataclass
class TernaryOp:
    condition: object
    iftrue: object
    iffalse: object
    type: VerilogAType = None


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


class MyVisitor(ParseTreeVisitor):
    def __init__(self):
        self.disciplines = []
        self.modules = []
        self.active_module = None
        self.active_context = None
        self.active_discipline = None
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

    def visitParenthesized_expr(self, ctx):
        return self.visit(ctx.expression())

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
        module = Module(name=self.visit(ctx.module_identifier()).name)
        self.modules.append(module)
        self.active_module = module
        self.active_context = module
        self.visitChildren(ctx)
        # for child in ctx.getChildren():
        # self.visit(child)
        self.active_context = None
        self.active_module = None
        return module

    def visitList_of_ports(self, ctx):
        for port in ctx.port():
            self.active_module.newPort(self.visit(port).name)

    def visitList_of_port_identifiers(self, ctx):
        identifiers = list(map(self.visit, ctx.port_identifier()))
        names = [identifier.name for identifier in identifiers]
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
        for var in self.visit(ctx.list_of_variable_identifiers()):
            self.active_context.variables.declare(var)

    def visitReal_declaration(self, ctx):
        for var in self.visit(ctx.list_of_real_identifiers()):
            self.active_context.variables.declare(var)

    def visitNet_declaration(self, ctx):
        self.active_module.nets.extend(
            identifier.name for identifier in self.visit(ctx.list_of_net_identifiers())
        )

    def visitList_of_variable_identifiers(self, ctx):
        return list(map(self.visit, ctx.variable_type()))

    def visitList_of_real_identifiers(self, ctx):
        return list(map(self.visit, ctx.real_type()))

    def visitList_of_net_identifiers(self, ctx):
        return list(map(self.visit, ctx.ams_net_identifier()))

    def visitReal_type(self, ctx):
        initializer = ctx.constant_expression()
        if initializer is not None:
            initializer = self.visit(initializer)
        return InitializedVariable(
            self.visit(ctx.real_identifier()).name, realtype, initializer
        )

    def visitVariable_type(self, ctx):
        initializer = ctx.constant_expression()
        if initializer is not None:
            initializer = self.visit(initializer)
        return InitializedVariable(
            self.visit(ctx.variable_identifier()).name, integertype, initializer
        )

    def visitAnalog_construct(self, ctx):
        analog = Analog(self.visit(ctx.getChild(1)))
        self.active_module.analogs.append(analog)

    def visitContribution_statement(self, ctx):
        funcall = self.visit(ctx.branch_lvalue())
        assert 1 <= len(funcall.arguments) <= 2
        assert all(isinstance(arg, Identifier) for arg in funcall.arguments)
        names = [arg.name for arg in funcall.arguments]
        if len(names) == 1:
            names.append(None)
        rvalue = self.visit(ctx.analog_expression())
        return AnalogContribution(
            accessor=funcall.name, lvalue1=names[0], lvalue2=names[1], rvalue=rvalue
        )

    def visitFunction_call(self, ctx):
        name = self.visit(ctx.hierarchical_function_identifier()).name
        arguments = list(map(self.visit, ctx.expression()))
        return FunctionCall(name, arguments)

    def visitAnalog_seq_block(self, ctx):
        seq = AnalogSequence()
        self.active_context = seq
        # TODO: use label
        for declaration in ctx.analog_block_item_declaration():
            self.visit(declaration)
        seq.statements.extend(map(self.visit, ctx.analog_statement()))
        self.active_context = None
        return seq

    def visitAnalog_procedural_assignment(self, ctx):
        return self.visit(ctx.analog_variable_assignment())

    def visitScalar_analog_variable_assignment(self, ctx):
        return VariableAssignment(
            self.visit(ctx.scalar_analog_variable_lvalue()).name,
            self.visit(ctx.analog_expression()),
        )
