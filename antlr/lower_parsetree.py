from typing import Mapping, Optional, Tuple, Union, List, Sequence
import hir
import parsetree as pt
from functools import singledispatchmethod
from contextlib import contextmanager
from verilogatypes import VAType
from vabuiltins import builtins
from symboltable import SymbolTable

Context = Tuple[Union[hir.SourceFile, hir.Module, hir.Block], SymbolTable]


def ensure_type(expression, type_):
    if expression.type_ == type_:
        return expression
    if type_ == VAType.integer:
        assert expression.type_ == VAType.real
        function = builtins.cast_real_to_int
    elif type_ == VAType.real:
        assert expression.type_ == VAType.integer
        function = builtins.cast_int_to_real
    else:
        raise Exception(type_)
    return hir.FunctionCall(function=function, arguments=(expression,))


class LowerParseTree:
    def __init__(self, contexts: Optional[List[Context]] = None):
        if contexts is None:
            contexts = []
        self.contexts = contexts

    @contextmanager
    def push_context(self, context: Context):
        self.contexts.append(context)
        yield
        del self.contexts[-1]

    @property
    def symboltable(self):
        """Return active (innermost) symbol table"""
        return self.contexts[-1][1]

    def resolve(self, identifier_token):
        name = identifier_token.value
        for _, symboltable in reversed(self.contexts):
            try:
                return symboltable[name]
            except KeyError:
                continue
        raise KeyError(identifier_token, "Undefined identifier")

    @singledispatchmethod
    def lower(self, parsetree: pt.ParseTree) -> hir.HIR:
        raise NotImplementedError(parsetree)

    @lower.register
    def _(self, literal: pt.Literal):
        return hir.Literal(value=literal.value.value, parsed=literal)

    @lower.register
    def _(self, identifier: pt.Identifier):
        return self.resolve(identifier.name)

    @lower.register
    def _(self, operation: pt.Operation):
        operands = [self.lower(operand) for operand in operation.operands]
        binary_operators = {
            "*": (builtins.integer_product, builtins.real_product),
            "+": (builtins.integer_addition, builtins.real_addition),
            "/": (builtins.integer_division, builtins.real_division),
            "-": (builtins.integer_subtraction, builtins.real_subtraction),
            "==": (builtins.integer_equality, builtins.real_equality),
            "!=": (builtins.integer_inequality, builtins.real_inequality),
        }
        operator = operation.operator.value
        if len(operands) == 1:
            operand, = operands
            unary_operators = {
                "+": (builtins.integer_addition, builtins.real_addition),
                "-": (builtins.integer_subtraction, builtins.real_subtraction),
            }
            if operator == '+':
                return operand
            elif operator == '-':
                if operand.type_ == VAType.integer:
                    function = builtins.integer_subtraction
                    operands = [hir.Literal(0), operand]
                elif operand.type_ == VAType.real:
                    function = builtins.real_subtraction
                    operands = [hir.Literal(0.0), operand]
                else:
                    raise Exception(operation.operands[0])
            else:
                raise Exception(operation.operator)
        if operator in binary_operators:
            intfunc, realfunc = binary_operators[operator]
            if any(operand.type_ == VAType.real for operand in operands):
                function = realfunc
                operands = [ensure_type(operand, VAType.real) for operand in operands]
            else:
                # TODO: better error messages if mixing with other types
                assert all(operand.type_ == VAType.integer for operand in operands)
                function = intfunc
        else:
            raise NotImplementedError(operation.operator)
        return hir.FunctionCall(function=function, arguments=tuple(operands))

    @lower.register
    def _(self, funcall: pt.FunctionCall):
        function = self.resolve(funcall.function.name)
        arguments = [self.lower(arg) for arg in funcall.args]
        if isinstance(function, hir.Accessor):
            assert 1 <= len(arguments) <= 2
            branch, type_ = self.resolve_analog(function, arguments[0], None if len(arguments) == 1 else arguments[1])
            arguments = [branch]
            function = {'potential': builtins.potential, 'flow': builtins.flow}[type_]
        elif isinstance(function, hir.Function):
            assert len(funcall.args) == len(function.type_.parameters)
            arguments = [
                ensure_type(arg, type_)
                for arg, type_ in zip(arguments, function.type_.parameters)
            ]
        return hir.FunctionCall(
            function=function, arguments=tuple(arguments), parsed=funcall
        )

    def lower_natures(self, nature_pts: Sequence[pt.Nature]) -> List[hir.Nature]:
        lowered = {}
        # Need two passes because of circular references
        for nature_pt in nature_pts:
            name = nature_pt.name.value
            lowered[name] = hir.Nature(name=name, parsed=nature_pt)
        for nature_pt in nature_pts:
            nature_hir = lowered[nature_pt.name.value]
            attributes = {}
            for attr in nature_pt.attributes:
                name = attr.name.value
                if name == "access":
                    value = hir.Accessor(name=attr.value.name.value, nature=nature_hir)
                elif name.endswith("_nature"):
                    value = lowered[attr.value.name.value]
                else:
                    # Evaluate expression
                    value = self.lower(attr.value)
                    # Evaluate strings/numbers
                    if not isinstance(value, hir.Nature):
                        assert isinstance(value, hir.Literal)
                        value = value.value
                setattr(nature_hir, name, value)
        return list(lowered.values())

    @lower.register
    def _(self, discipline: pt.Discipline):
        ret = hir.Discipline(name=discipline.name.value, parsed=discipline)
        for attr in discipline.attributes:
            name = attr.name.value
            if name in ("flow", "potential"):
                value = self.resolve(attr.value)
            elif name == "domain":
                assert attr.value.type in ["DISCRETE", "CONTINUOUS"]
                value = attr.value.value
            else:
                raise Exception(attr.name)
            setattr(ret, name, value)
        return ret

    @lower.register
    def _(self, module: pt.Module):
        ret = hir.Module(name=module.name.value, parsed=module)
        with self.push_context((ret, SymbolTable())):
            ret.ports = [
                self.lower(port) for port in module.ports if port.direction is not None
            ]
            ret.nets = list(map(self.lower, module.nets))
            # ret.branches = list(map(self.lower, module.branches))
            ret.variables = list(map(self.lower, module.variables))
            for variable in ret.variables:
                self.symboltable.define(variable)
            for net in ret.nets:
                self.symboltable.define(net)
            ret.statements = list(map(self.lower, module.statements))
        return ret

    @lower.register
    def _(self, port: pt.Port):
        return hir.Port(
            name=port.name.value, direction=port.direction.value, parsed=port
        )

    @lower.register
    def _(self, block: pt.Block):
        return hir.Block(
            statements=[self.lower(statement) for statement in block.statements],
            parsed=block,
        )

    @lower.register
    def _(self, net: pt.Net):
        return hir.Net(
            name=net.name.value, discipline=self.resolve(net.discipline), parsed=net
        )

    @staticmethod
    def lower_type(typetoken):
        try:
            return {
                "STRING": VAType.string,
                "REAL": VAType.real,
                "INTEGER": VAType.integer,
            }[typetoken.type]
        except KeyError:
            raise Exception(typetoken)

    @lower.register
    def _(self, variable: pt.Variable):
        if variable.initializer is None:
            initializer = None
        else:
            initializer = self.lower(variable.initializer)
        return hir.Variable(
            name=variable.name.value,
            type_=self.lower_type(variable.type),
            initializer=initializer,
            parsed=variable,
        )

    @lower.register
    def _(self, assignment: pt.Assignment):
        lvalue = self.resolve(assignment.lvalue)
        return hir.Assignment(
            lvalue=lvalue,
            value=ensure_type(self.lower(assignment.value), lvalue.type_),
            parsed=assignment,
        )

    @lower.register
    def _(self, if_: pt.If):
        else_ = self.lower(if_.else_) if if_.else_ is not None else None
        return hir.If(
            condition=self.lower(if_.condition),
            then=self.lower(if_.then),
            else_=else_,
        )

    def resolve_analog(self, accessor, net1, net2):
        """
        Determine if accessor is flow or potential, and check net compatibility

        Returns hir.Branch and "flow" or "potential"
        """
        # TODO: handle branch argument
        assert isinstance(net1, hir.Net)
        assert isinstance(accessor, hir.Accessor)
        nature = accessor.nature
        if nature == net1.discipline.potential:
            type_ = "potential"
        elif nature == net1.discipline.flow:
            type_ = "flow"
        else:
            raise Exception(
                "Accessor is neither flow nor potential for given net", contribution
            )
        if net2 is not None:
            assert isinstance(net2, hir.Net)
            assert net1.discipline is net2.discipline
        else:
            net2 = None
        branch = hir.Branch(name='', net1=net1, net2=net2)
        return branch, type_

    @lower.register
    def _(self, contribution: pt.AnalogContribution):
        accessor = self.resolve(contribution.accessor)
        net1 = self.resolve(contribution.arg1)
        net2 = None if contribution.arg2 is None else self.resolve(contribution.arg2)
        value = self.lower(contribution.value)
        branch, type_ = self.resolve_analog(accessor, net1, net2)
        return hir.AnalogContribution(branch=branch, type_=type_, value=value)

    @lower.register
    def _(self, sourcefile: pt.SourceFile):
        ret = hir.SourceFile(parsed=sourcefile)
        with self.push_context((ret, SymbolTable())):
            for nature in self.lower_natures(sourcefile.natures):
                self.symboltable.define(nature)
                self.symboltable.define(nature.access)
            for discipline in sourcefile.disciplines:
                self.symboltable.define(self.lower(discipline))
            for module_pt in sourcefile.modules:
                ret.modules.append(self.lower(module_pt))
        return ret
