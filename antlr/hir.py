from __future__ import annotations
from dataclasses import dataclass, field
from verilogatypes import VAType
from typing import Union, Optional, List
from abc import ABC, abstractmethod, abstractproperty
from collections import OrderedDict
import parsetree as pt


@dataclass(frozen=False)
class Symbol:
    name: str


@dataclass(frozen=True)
class FrozenSymbol:
    name: str


@dataclass(frozen=False)
class Nature(Symbol):
    abstol: Optional[float] = None
    access: Optional[str] = None
    units: Optional[str] = None
    idt_nature: Optional[Nature] = None
    ddt_nature: Optional[Nature] = None
    parsed: Optional[pt.Nature] = None


@dataclass(frozen=False)
class Discipline(Symbol):
    domain: Optional[str] = None
    potential: Optional[Nature] = None
    flow: Optional[Nature] = None
    parsed: Optional[pt.Discipline] = None


@dataclass(frozen=False)
class Net(Symbol):
    discipline: Optional[Discipline] = None
    parsed: Optional[pt.Net] = None


ground = Net(name="gnd", discipline=None)


@dataclass(frozen=False)
class Port(Symbol):
    direction: Optional[str] = None
    parsed: Optional[pt.Port] = None


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
class Function(FrozenSymbol):
    type_: FunctionSignature


@dataclass(frozen=False)
class FunctionCall:
    function: Function
    arguments: tuple[Expression]
    parsed: Optional[pt.FunctionCall] = None

    @property
    def type_(self):
        # Get result type from function signature
        return self.function.type_.returntype


@dataclass(frozen=False)
class Variable(Symbol):
    type_: VAType
    initializer: Expression
    parsed: Optional[pt.Variable] = None


Expression = Union[Literal, FunctionCall, Variable]


@dataclass(frozen=False)
class Assignment:
    lvalue: Variable
    value: Expression
    parsed: Optional[pt.Assignment] = None


@dataclass(frozen=False)
class Block:
    statements: List[Statement] = field(default_factory=list)
    parsed: Optional[pt.Block] = None


@dataclass(frozen=False)
class If:
    condition: Expression
    then: Statement
    else_: Optional[Statement] = None
    parsed: Optional[pt.If] = None


Statement = Union[Assignment, Block, If]


@dataclass(frozen=False)
class Module(Symbol):
    ports: List[Port] = field(default_factory=list)
    nets: List[Net] = field(default_factory=list)
    branches: List[Branch] = field(default_factory=list)
    parameters: List[Variable] = field(default_factory=list)
    variables: List[Variable] = field(default_factory=list)
    statements: List[Statement] = field(default_factory=list)
    parsed: Optional[pt.Module] = None


@dataclass(frozen=False)
class SourceFile:
    modules: List[Module] = field(default_factory=list)
    parsed: Optional[pt.SourceFile] = None


@dataclass(frozen=False)
class Accessor(Symbol):
    nature: Nature

    def __init__(self, name: str, nature: Nature):
        self.name = name
        self.nature = nature


@dataclass(frozen=False)
class Branch(Symbol):
    net1: Net
    net2: Net

    @property
    def discipline(self):
        return self.net1.discipline

HIR = Union[ Nature, Discipline, Net, Port, Literal, FunctionCall, Variable, Assignment, Block, If, Module, SourceFile, Branch]
