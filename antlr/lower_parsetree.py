from typing import Mapping, Optional, Tuple, Union, List
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
    def __init__(self, context: Optional[List[Context]] = None):
        if context is None:
            context = []
        self.context = context

    @contextmanager
    def push_context(self, context: Context):
        self.context.append(context)
        yield
        del self.context[-1]

    @property
    def symboltable(self):
        """Return active (innermost) symbol table"""
        return self.context[-1][1]

    def resolve(self, identifier_token):
        name = identifier_token.value
        for _, symboltable in reversed(self.context):
            try:
                return symboltable[name]
            except KeyError:
                continue
        raise KeyError(identifier_token, "Undefined identifier")

    @singledispatchmethod
    def lower(self, parsetree: pt.ParseTree) -> hir.HIR:
        raise NotImplementedError()

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
