from antlr4 import FileStream, CommonTokenStream, ParseTreeVisitor, ParserRuleContext
from antlr4.error.ErrorStrategy import ErrorStrategy
from generated.VerilogALexer import VerilogALexer
from generated.VerilogAParser import VerilogAParser
from generated.VerilogAParserVisitor import VerilogAParserVisitor
from preprocessor import VerilogAPreprocessor, lex
from typing import Mapping, Union, List
from verilogatypes import VAType
from symboltable import Scope, SymbolTable
from contextlib import contextmanager
import hir

from dataclasses import dataclass, field


class ParseError(Exception):
    pass


class ExceptionErrorStrategy(ErrorStrategy):
    def __init__(self):
        super(ExceptionErrorStrategy, self).__init__()

    def reportError(self, recognizer, e):
        raise e

    def reportMatch(self, recognizer):
        pass


def parse_without_visiting(source, rule):
    preprocessor = VerilogAPreprocessor(lex(content=source))
    stream = CommonTokenStream(preprocessor)
    parser = VerilogAParser(stream)
    parser._errHandler = ExceptionErrorStrategy()
    tree = getattr(parser, rule)()
    assert tree is not None, "Parse error"
    return tree


def parse(source, rule, visitor=None):
    if visitor is None:
        visitor = MyVisitor()
    return visitor.visit(tree=parse_without_visiting(source, rule))


Context = Union[Scope, hir.Nature, hir.Discipline]


class MyVisitor(ParseTreeVisitor):
    def __init__(self, context: List[Context] = None, symboltable: SymbolTable = None):
        # The identifier when defining a module, variable, etc must be undefined, do not resolve it
        self.defining_identifier = False
        if context is None:
            context = []
        # Stack of e.g. SourceFile, Module, Block, Sequence, ...
        self.context = context
        if symboltable is None:
            symboltable = SymbolTable()
        self.symboltables = [symboltable]
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

    @contextmanager
    def push_context(self, context, newscope=True):
        self.context.append(context)
        if newscope:
            self.symboltables.append(SymbolTable())
        yield
        del self.context[-1]
        if newscope:
            del self.symboltables[-1]

    def define(self, symbol):
        self.symboltable.define(symbol)

    # def visitChildren(self, node):
    # raise NotImplementedError()

    def visitTerminal(self, node):
        type_ = node.getSymbol().type
        name = VerilogALexer.ruleNames[type_ - 1]
        try:
            method = getattr(self, "visit" + name)
        except AttributeError:
            # Assume reserved
            return node.getText()
        return method(node)

    def visitUNSIGNED_NUMBER(self, node):
        return hir.Literal(int(node.getText()))

    def visitREAL_NUMBER(self, node):
        # TODO: SI prefixes
        return hir.Literal(float(node.getText()))

    def visitSTRING_LITERAL(self, node):
        # TODO: unescape
        return hir.Literal(node.getText()[1:-1])

    def is_defined_in_this_scope(self, name):
        return name in self.symboltable

    @property
    def active_context(self):
        return self.context[-1]

    @property
    def symboltable(self):
        """Return active (innermost) symbol table"""
        return self.symboltables[-1]

    def assert_context_type(self, type_):
        assert isinstance(self.active_context, type_)

    def visitSYSTEM_IDENTIFIER(self, node):
        return self.resolve(node)

    def visitSIMPLE_IDENTIFIER(self, node):
        name = node.getText()
        if self.defining_identifier:
            if self.is_defined_in_this_scope(name):
                raise Exception("Identifier already defined", node)
            return name
        return self.resolve(node)

    def resolve(self, node):
        name = node.getText()
        for symboltable in reversed(self.symboltables):
            try:
                return symboltable[name]
            except KeyError:
                continue
        raise KeyError(node, "unknown identifier")

    def visitExpr1_withoperator(self, ctx):
        "expr1 : unary_operator expr_primary"
        return self.operatorcall(
            operator_ctx=ctx.unary_operator(), args_ctx=(ctx.expr_primary(),)
        )

    def visitExpr1_withoutoperator(self, ctx):
        "expr1 : expr_primary"
        return self.visit(ctx.getChild(0))

    def visitExpr13_withoperator(self, ctx):
        "expr13 : expr12 TERNARY expr13 COLON expr13"
        return self.operatorcall(
            operator_ctx=ctx.TERNARY(), args_ctx=(ctx.expr12(),) + tuple(ctx.expr13())
        )

    def visitExpr13_withoutoperator(self, ctx):
        "expr13 : expr12"
        return self.visit(ctx.getChild(0))

    def visitbinary(self, ctx):
        childcount = ctx.getChildCount()
        if childcount == 3:
            return self.operatorcall(
                operator_ctx=ctx.getChild(1),
                args_ctx=(ctx.getChild(0), ctx.getChild(2)),
            )
        elif childcount == 1:
            return self.visit(ctx.getChild(0))
        else:
            raise Exception("Unexpected number of children", childcount)

    def operatorcall(self, operator_ctx, args_ctx):
        args = [self.visit(arg) for arg in args_ctx]
        binary_operators = {
            "*": (hir.integer_product, hir.real_product),
            "+": (hir.integer_addition, hir.real_addition),
            "/": (hir.integer_division, hir.real_division),
            "-": (hir.integer_subtraction, hir.real_subtraction),
            "==": (hir.integer_equality, hir.real_equality),
            "!=": (hir.integer_inequality, hir.real_inequality),
        }
        operator = self.visit(operator_ctx)
        if operator in binary_operators:
            intfunc, realfunc = binary_operators[operator]
            if any(arg.type == VAType.real for arg in args):
                function = realfunc
                args = [hir.ensure_type(arg, VAType.real) for arg in args]
            else:
                assert all(arg.type == VAType.integer for arg in args)
                function = intfunc
        else:
            raise NotImplementedError(operator_ctx)
        return hir.FunctionCall(function=function, arguments=tuple(args))

    def visitParenthesized_expr(self, ctx):
        return self.visit(ctx.expression())

    def visitNature_attribute_expression(self, ctx):
        x = self.visit(ctx.getChild(0))
        if isinstance(x, hir.Literal):
            return x.value
        assert isinstance(x, str)
        return x

    def visitNature_attribute(self, ctx):
        name = self.visit(ctx.nature_attribute_identifier())
        if name in ("idt_nature", "ddt_nature"):
            # This can't be resolved the usual way because natures make circular references
            # TODO: make a forward reference and resolve them at some point
            return name, hir.Literal(0)
        # The value of `access` is an undefined identifier,
        # do not try to resolve it (rather, define it)
        value_ctx = ctx.nature_attribute_expression()
        if name == "access":
            accessorname = self.visit_undefined_identifier(value_ctx)
            # value = hir.Accessor(name=accessorname, nature=self.active_context)
            # self.define(value)
            value = accessorname
        else:
            value = self.visit(value_ctx)
        setattr(self.active_context, name, value)

    def visitNature_declaration(self, ctx):
        name = self.visit_undefined_identifier(ctx.nature_identifier())
        ret = hir.Nature(name, abstol=None, access=None, units=None)
        with self.push_context(ret, newscope=False):
            for c in ctx.nature_item():
                self.visit(c)
        self.define(ret)
        return ret

    def visit_undefined_identifier(self, ctx):
        with self.define_identifiers_context():
            ret = self.visit(ctx)
            if not isinstance(ret, str):
                raise Exception("Expecting identifier", ctx)
            if self.is_defined_in_this_scope(ret):
                raise Exception("Identifier already defined in this scope", ctx)
        return ret

    def visitNature_binding(self, ctx):
        potential_or_flow = self.visit(ctx.potential_or_flow())
        nature = self.visit(ctx.nature_identifier())
        context = self.active_context
        assert isinstance(context, hir.Discipline)
        if potential_or_flow == "potential":
            self.active_context.potential = nature
        elif potential_or_flow == "flow":
            self.active_context.flow = nature
        else:
            raise Exception(potential_or_flow)

    def visitDiscipline_domain_binding(self, ctx):
        self.assert_context_type(hir.Discipline)
        self.active_context.domain = self.visit(ctx.discrete_or_continuous())

    def visitDiscipline_declaration(self, ctx):
        name = self.visit_undefined_identifier(ctx.discipline_identifier())
        discipline = hir.Discipline(
            name=name,
            domain=None,
            flow=None,
            potential=None,
        )
        self.define(discipline)
        with self.push_context(discipline, newscope=False):
            self.visitChildren(ctx)
        return discipline

    def visitModule_declaration(self, ctx):
        name = self.visit_undefined_identifier(ctx.module_identifier())
        module = hir.Module(name=name)
        self.define(module)
        with self.push_context(module):
            self.visitChildren(ctx)
        assert isinstance(self.active_context, hir.SourceFile)
        self.active_context.modules.append(module)
        return module

    def visitList_of_ports(self, ctx):
        assert isinstance(self.active_context, hir.Module)
        for name_ctx in ctx.port():
            name = self.visit_undefined_identifier(name_ctx)
            port = hir.Port(name=name, discipline=None, direction=None)
            self.define(port)
            self.active_context.ports.append(port)
            self.active_context.nets.append(port)

    def visitList_of_port_identifiers(self, ctx):
        ret = []
        assert isinstance(self.active_context, hir.Module)
        for name_ctx in ctx.port_identifier():
            name = self.visit_undefined_identifier(name_ctx)
            port = hir.Port(name=name, discipline=None, direction=None)
            self.define(port)
            ret.append(port)
            self.active_context.ports.append(port)
            self.active_context.nets.append(port)
        return ret

    def visitInout_declaration(self, ctx):
        # TODO: set discipline if specified
        discipline = self.visit(ctx.discipline_identifier())
        for port in self.visit(ctx.list_of_port_identifiers()):
            port.direction = "inout"
            port.discipline = discipline

    def visitReal_type(self, ctx):
        name = self.visit_undefined_identifier(ctx.real_identifier())
        initializer = ctx.constant_expression()
        if initializer is not None:
            initializer = self.visit(initializer)
        # TODO: check initializer is constant
        self.define(hir.Variable(name=name, type=VAType.real, initializer=initializer))

    def visitVariable_type(self, ctx):
        name = self.visit_undefined_identifier(ctx.variable_identifier())
        initializer = ctx.constant_expression()
        if initializer is not None:
            initializer = self.visit(initializer)
        # TODO: check initializer is constant
        self.define(
            hir.Variable(name=name, type=VAType.integer, initializer=initializer)
        )

    def visitAnalog_construct(self, ctx):
        statement = self.visit(ctx.getChild(1))
        assert isinstance(self.active_context, hir.Module)
        self.active_context.statements.append(statement)

    def visitContribution_statement(self, ctx):
        raise NotImplementedError()
        funcall = self.visit(ctx.branch_lvalue())
        assert 1 <= len(funcall.arguments) <= 2
        assert all(isinstance(arg, hir.Net) for arg in funcall.arguments)
        nets = funcall.arguments
        if len(nets) == 1:
            nets = nets + (hir.ground,)
        rvalue = self.visit(ctx.analog_expression())
        return hir.AnalogContribution(
            accessor=funcall.function, lvalue1=nets[0], lvalue2=nets[1], rvalue=rvalue
        )

    def visitFunction_call(self, ctx):
        function = self.visit(ctx.hierarchical_function_identifier())
        arguments = tuple(map(self.visit, ctx.expression()))
        raise NotImplementedError()
        return function.call(arguments)

    def visitAnalog_seq_block(self, ctx):
        seq = hir.Block()
        with self.push_context(seq):
            # TODO: use label
            for declaration in ctx.analog_block_item_declaration():
                self.visit(declaration)
            seq.statements.extend(map(self.visit, ctx.analog_statement()))
        return seq

    def visitAnalog_procedural_assignment(self, ctx):
        return self.visit(ctx.analog_variable_assignment())

    def visitScalar_analog_variable_assignment(self, ctx):
        lvalue_ctx = ctx.scalar_analog_variable_lvalue()
        lvalue = self.visit(lvalue_ctx)
        if not isinstance(lvalue, hir.Variable):
            raise Exception("Expected variable as lvalue", lvalue_ctx)
        return hir.Assignment(
            lvalue=lvalue,
            value=hir.ensure_type(self.visit(ctx.analog_expression()), lvalue.type),
        )

    def visitSource_text(self, ctx):
        ret = hir.SourceFile()
        with self.push_context(ret):
            self.visitChildren(ctx)
        return ret

    def visitAnalog_conditional_statement_noelse(self, ctx):
        "analog_conditional_statement : IF LPAREN expression RPAREN analog_statement_or_null"
        return hir.If(
            condition=self.visit(ctx.expression()),
            then=self.visit(ctx.analog_statement_or_null()),
        )

    def visitAnalog_conditional_statement_else(self, ctx):
        "analog_conditional_statement : IF LPAREN expression RPAREN analog_statement_or_null ELSE analog_statement_or_null"
        return hir.If(
            condition=self.visit(ctx.expression()),
            then=self.visit(ctx.analog_statement_or_null()[0]),
            else_=self.visit(ctx.analog_statement_or_null()[1]),
        )

    def visitAnalog_statement_or_null_semicolon(self, ctx):
        "analog_statement_or_null : attribute_instance* SEMICOLON"
        return None

    def visitAnalog_statement_or_null_statement(self, ctx):
        "analog_statement_or_null : analog_statement"
        return self.visit(ctx.analog_statement())

    @contextmanager
    def define_identifiers_context(self):
        self.defining_identifier = True
        yield
        self.defining_identifier = False

    def visitNet_declaration(self, ctx):
        # discipline_identifier list_of_net_identifiers SEMICOLON;
        discipline = self.visit(ctx.discipline_identifier())
        assert isinstance(self.active_context, hir.Module)
        with self.define_identifiers_context():
            for netname in self.visit(ctx.list_of_net_identifiers()):
                net = hir.Net(name=netname, discipline=discipline)
                self.define(net)
                self.active_context.nets.append(net)

    def visitList_of_net_identifiers(self, ctx):
        return [self.visit(net) for net in ctx.ams_net_identifier()]

    def visitBranch_declaration(self, ctx):
        # BRANCH LPAREN branch_terminal (COMMA branch_terminal)? RPAREN list_of_branch_identifiers SEMICOLON;
        nets = [self.visit(net) for net in ctx.branch_terminal()]
        if len(nets) == 1:
            nets.append(hir.ground)
        assert isinstance(self.active_context, hir.Module)
        with self.define_identifiers_context():
            for name in self.visit(ctx.list_of_branch_identifiers()):
                branch = hir.Branch(name=name, net1=nets[0], net2=nets[1])
                self.define(branch)
                self.active_context.branches.append(branch)

    def visitList_of_branch_identifiers(self, ctx):
        return [self.visit(branch) for branch in ctx.branch_identifier()]

    def visitAttr_spec(self, ctx):
        name = self.visit_undefined_identifier(ctx.attr_name())
        ctx_value = ctx.constant_expression()
        if ctx_value is None:
            value = hir.Literal(1)
        else:
            value = self.visit(ctx_value)
        return name, value

    def visitAttribute_instance(self, ctx):
        ret = {}
        for ctx_spec in ctx.attr_spec():
            name, value = self.visit(ctx_spec)
            ret[name] = value
        return ret

    def visitParameter_declaration_withtype(self, ctx):
        "parameter_declaration : PARAMETER parameter_type list_of_param_assignments"
        type_ = {
            "string": VAType.string,
            "real": VAType.real,
            "integer": VAType.integer,
        }[self.visit(ctx.parameter_type())]
        assert isinstance(self.active_context, hir.Module)
        for name, value in self.visit(ctx.list_of_param_assignments()):
            var = hir.Variable(name=name, type=type_, initializer=value)
            self.define(var)
            self.active_context.parameters.append(var)

    def visitParameter_declaration_withouttype(self, ctx):
        "parameter_declaration : PARAMETER list_of_param_assignments"
        raise NotImplementedError()

    def visitList_of_param_assignments(self, ctx):
        return [self.visit(assignment) for assignment in ctx.param_assignment()]

    def visitParam_assignment(self, ctx):
        name = self.visit_undefined_identifier(ctx.parameter_identifier())
        value = self.visit(ctx.constant_mintypmax_expression())
        return name, value
