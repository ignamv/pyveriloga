from __future__ import annotations
from dataclasses import dataclass, field
from verilogatypes import VAType
from typing import Union, Optional
from abc import ABC, abstractmethod
from collections import OrderedDict
import parsetree as pt


@dataclass
class Symbol:
    name: str


@dataclass
class Nature(Symbol):
    abstol: float
    access: str
    # idt_nature: Nature
    units: str
    # ddt_nature: Nature = None
    parsed: pt.Nature


@dataclass
class Discipline(Symbol):
    domain: str
    potential: Nature
    flow: Nature
    parsed: pt.Discipline


@dataclass
class Net(Symbol):
    discipline: Optional[Discipline]
    parsed_net: List[pt.Net]


ground = Net(name="gnd", discipline=None)


@dataclass
class Port(Net):
    direction: str = None
    parsed_port: List[pt.Port]


# class Expression(ABC):
# @property
# @abstractmethod
# def type(self):
# raise NotImplementedError()


@dataclass
class Literal:
    value: int | float
    type: VAType
    parsed: pt.Literal

    def __init__(self, value: int | float | str):
        self.value = value
        self.type = {int: VAType.integer, float: VAType.real, str: VAType.string}[
            type(value)
        ]

    def __repr__(self):
        return f"hir.Literal({self.value!r})"


@dataclass
class FunctionSignature:
    returntype: VAType
    parameters: List[VAType]


@dataclass(eq=False)
class Function(Symbol):
    type: FunctionSignature


@dataclass
class FunctionCall:
    function: Function
    arguments: tuple[Expression]
    parsed: pt.FunctionCall

    @property
    def type(self):
        # Get result type from function signature
        return self.function.type.returntype


@dataclass
class Variable(Symbol):
    type: VAType
    initializer: Expression
    parsed: pt.Variable


Expression = Union[Literal, FunctionCall, Variable]


@dataclass
class Assignment:
    lvalue: Variable
    value: Expression
    parsed: pt.Assignment


@dataclass
class Block:
    statements: List[Statement] = field(default_factory=list)
    parsed: pt.Block


@dataclass
class If:
    condition: Expression
    then: Statement
    else_: Optional[Statement] = None
    parsed: pt.If


Statement = Union[Assignment, Block, If]


@dataclass
class Module(Symbol):
    ports: [Port] = field(default_factory=list)
    nets: [Net] = field(default_factory=list)
    branches: [Branch] = field(default_factory=list)
    parameters: [Variable] = field(default_factory=list)
    statements: [Statement] = field(default_factory=list)
    parsed: pt.Module


@dataclass
class SourceFile:
    modules: [Module] = field(default_factory=list)


def ensure_type(expression, type):
    if expression.type == type:
        return expression
    if type == VAType.integer:
        assert expression.type == VAType.real
        function = cast_real_to_int
    elif type == VAType.real:
        assert expression.type == VAType.integer
        function = cast_int_to_real
    else:
        raise Exception(type)
    return FunctionCall(function=function, arguments=(expression,))


@dataclass
class Accessor(Symbol):
    nature: Nature

    def __init__(self, name: str, nature: Nature):
        self.name = name
        self.nature = nature


@dataclass
class Branch(Symbol):
    net1: Net
    net2: Net

    @property
    def discipline(self):
        return self.net1.discipline
