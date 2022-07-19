from __future__ import annotations
from dataclasses import dataclass, field
from verilogatypes import VAType
from typing import Union, Optional, List
from abc import ABC, abstractmethod
from collections import OrderedDict
import parsetree as pt


@dataclass(frozen=True)
class Symbol:
    name: str


@dataclass(frozen=True)
class Nature(Symbol):
    abstol: float
    access: str
    # idt_nature: Nature
    units: str
    # ddt_nature: Nature = None
    parsed: Optional[pt.Nature] = None


@dataclass(frozen=True)
class Discipline(Symbol):
    domain: str
    potential: Nature
    flow: Nature
    parsed: Optional[pt.Discipline] = None


@dataclass(frozen=True)
class Net(Symbol):
    discipline: Optional[Discipline] = None
    parsed: Optional[List[pt.Net|pt.Port]] = None


ground = Net(name="gnd", discipline=None)


@dataclass(frozen=True)
class Port(Net):
    direction: Optional[str] = None


# class Expression(ABC):
# @property
# @abstractmethod
# def type(self):
# raise NotImplementedError()


@dataclass(init=False)
class Literal:
    value: int | float | str
    type_: VAType
    parsed: Optional[pt.Literal] = None

    def __init__(self, value: int | float | str, type_: Optional[VAType]=None, parsed: Optional[pt.Literal]=None):
        self.value = value
        if type_ is None:
            type_ = {int: VAType.integer, float: VAType.real, str: VAType.string}[
                type(value)
            ]
        self.type_ = type_
        self.parsed = parsed

    def __repr__(self):
        return f"hir.Literal({self.value!r})"


@dataclass(frozen=True)
class FunctionSignature:
    returntype: VAType
    parameters: Tuple[VAType,...]


@dataclass(frozen=True)
class Function(Symbol):
    type_: FunctionSignature


@dataclass(frozen=True)
class FunctionCall:
    function: Function
    arguments: tuple[Expression]
    parsed: Optional[pt.FunctionCall] = None

    @property
    def type_(self):
        # Get result type from function signature
        return self.function.type_.returntype


@dataclass(frozen=True)
class Variable(Symbol):
    type_: VAType
    initializer: Expression
    parsed: Optional[pt.Variable] = None


Expression = Union[Literal, FunctionCall, Variable]


@dataclass(frozen=True)
class Assignment:
    lvalue: Variable
    value: Expression
    parsed: Optional[pt.Assignment] = None


@dataclass(frozen=True)
class Block:
    statements: List[Statement] = field(default_factory=list)
    parsed: Optional[pt.Block] = None


@dataclass(frozen=True)
class If:
    condition: Expression
    then: Statement
    else_: Optional[Statement] = None
    parsed: Optional[pt.If] = None


Statement = Union[Assignment, Block, If]


@dataclass(frozen=True)
class Module(Symbol):
    ports: List[Port] = field(default_factory=list)
    nets: List[Net] = field(default_factory=list)
    branches: List[Branch] = field(default_factory=list)
    parameters: List[Variable] = field(default_factory=list)
    statements: List[Statement] = field(default_factory=list)
    parsed: Optional[pt.Module] = None


@dataclass(frozen=True)
class SourceFile:
    modules: List[Module] = field(default_factory=list)
    parsed: Optional[pt.SourceFile] = None


@dataclass(frozen=True)
class Accessor(Symbol):
    nature: Nature

    def __init__(self, name: str, nature: Nature):
        self.name = name
        self.nature = nature


@dataclass(frozen=True)
class Branch(Symbol):
    net1: Net
    net2: Net

    @property
    def discipline(self):
        return self.net1.discipline

HIR = Union[ Nature, Discipline, Net, Port, Literal, FunctionCall, Variable, Assignment, Block, If, Module, SourceFile, Branch]
