from __future__ import annotations
from dataclasses import dataclass, field, replace
from verilogatypes import VAType
from typing import Union, Optional, List, Literal
from abc import ABC, abstractmethod, abstractproperty
from collections import OrderedDict
import parsetree as pt


class HIR:
    def strip_parsed(self):
        return replace(self, parsed=None)


@dataclass(frozen=False)
class Symbol(HIR):
    name: str


@dataclass(frozen=True)
class FrozenSymbol(HIR):
    name: str


@dataclass(frozen=False)
class Nature(Symbol):
    abstol: Optional[float] = None
    access: Optional[str] = None
    units: Optional[str] = None
    idt_nature: Optional[Nature] = None
    ddt_nature: Optional[Nature] = None
    parsed: Optional[pt.Nature] = None

    def __eq__(self, other):
        if not (
            (self.name == other.name)
            and (self.access.name == other.access.name)
            and (self.abstol == other.abstol)
            and (self.units == other.units)
            and (self.units == other.units)
            and (self.parsed == other.parsed)
        ):
            return False
        if (
            self.idt_nature is not None
            and self.idt_nature.name != other.idt_nature.name
        ):
            return False
        if (
            self.ddt_nature is not None
            and self.ddt_nature.name != other.ddt_nature.name
        ):
            return False
        return True


@dataclass(frozen=False)
class Discipline(Symbol):
    domain: Optional[str] = None
    potential: Optional[Nature] = None
    flow: Optional[Nature] = None
    parsed: Optional[pt.Discipline] = None

    def strip_parsed(node: hir.Discipline):
        return replace(
            node,
            parsed=None,
            flow=node.flow.strip_parsed(),
            potential=node.potential.strip_parsed(),
        )


@dataclass(frozen=False)
class Net(Symbol):
    discipline: Optional[Discipline] = None
    parsed: Optional[pt.Net] = None

    def strip_parsed(node: hir.Net):
        return replace(node, parsed=None, discipline=node.discipline.strip_parsed())


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

    def __init__(
        self,
        value: int | float | str,
        type_: Optional[VAType] = None,
        parsed: Optional[pt.Literal] = None,
    ):
        self.value = value
        if type_ is None:
            type_ = {int: VAType.integer, float: VAType.real, str: VAType.string}[
                type(value)
            ]
        self.type_ = type_
        self.parsed = parsed

    def __repr__(self):
        return f"hir.Literal({self.value!r})"

    def strip_parsed(self):
        return replace(self, parsed=None)


@dataclass(frozen=True)
class FunctionSignature:
    returntype: VAType
    parameters: Tuple[VAType, ...]


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

    def strip_parsed(node: hir.FunctionCall):
        return replace(
            node,
            parsed=None,
            arguments=tuple(arg.strip_parsed() for arg in node.arguments),
        )


@dataclass(frozen=False)
class Variable(Symbol):
    type_: VAType
    initializer: Expression
    parsed: Optional[pt.Variable] = None

    def strip_parsed(node: hir.Variable):
        return replace(
            node,
            parsed=None,
            initializer=node.initializer.strip_parsed()
            if node.initializer is not None
            else None,
        )


Expression = Union[Literal, FunctionCall, Variable]


@dataclass(frozen=False)
class Assignment:
    lvalue: Variable
    value: Expression
    parsed: Optional[pt.Assignment] = None

    def strip_parsed(node: hir.Assignment):
        return replace(
            node,
            parsed=None,
            lvalue=node.lvalue.strip_parsed(),
            value=node.value.strip_parsed(),
        )


@dataclass(frozen=False)
class Block:
    statements: List[Statement] = field(default_factory=list)
    parsed: Optional[pt.Block] = None

    def strip_parsed(node: hir.Block):
        return replace(
            node,
            parsed=None,
            statements=[statement.strip_parsed() for statement in node.statements],
        )


@dataclass(frozen=False)
class If:
    condition: Expression
    then: Statement
    else_: Optional[Statement] = None
    parsed: Optional[pt.If] = None

    def strip_parsed(node: hir.If):
        return replace(
            node,
            parsed=None,
            condition=node.condition.strip_parsed(),
            then=node.then.strip_parsed(),
            else_=node.else_.strip_parsed() if node.else_ is not None else None,
        )


@dataclass(frozen=True)
class AnalogContribution(HIR):
    branch: Branch
    value: Expression
    type_: Literal["flow", "potential"]
    parsed: Optional[pt.AnalogContribution] = None

    def strip_parsed(self):
        return replace(
            self,
            parsed=None,
            branch=self.branch.strip_parsed(),
            value=self.value.strip_parsed(),
        )


Statement = Union[Assignment, Block, If]


@dataclass(frozen=False)
class Module(Symbol):
    ports: List[Port] = field(default_factory=list)
    nets: List[Net] = field(default_factory=list)
    branches: Mapping[Tuple[str,Optional[str]],Branch] = field(default_factory=dict)
    parameters: List[Variable] = field(default_factory=list)
    variables: List[Variable] = field(default_factory=list)
    statements: List[Statement] = field(default_factory=list)
    parsed: Optional[pt.Module] = None

    def strip_parsed(module: hir.Module):
        return replace(
            module,
            parsed=None,
            ports=[port.strip_parsed() for port in module.ports],
            nets=[net.strip_parsed() for net in module.nets],
            branches={k: branch.strip_parsed() for k,branch in module.branches.items()},
            parameters=[parameter.strip_parsed() for parameter in module.parameters],
            variables=[variable.strip_parsed() for variable in module.variables],
            statements=[statement.strip_parsed() for statement in module.statements],
        )


@dataclass(frozen=False)
class SourceFile:
    modules: List[Module] = field(default_factory=list)
    parsed: Optional[pt.SourceFile] = None

    def strip_parsed(node: hir.SourceFile):
        return replace(
            node,
            parsed=None,
            modules=[module.strip_parsed() for module in node.modules],
        )


@dataclass(frozen=False)
class Accessor(Symbol):
    nature: Nature

    def __init__(self, name: str, nature: Nature):
        self.name = name
        self.nature = nature


@dataclass(frozen=False)
class Branch(Symbol):
    net1: Net
    net2: Optional[Net]

    @property
    def discipline(self):
        return self.net1.discipline

    def strip_parsed(self):
        return replace(self, net1=self.net1.strip_parsed(), net2=self.net2.strip_parsed() if self.net2 is not None else None)


HIR = Union[
    Nature,
    Discipline,
    Net,
    Port,
    Literal,
    FunctionCall,
    Variable,
    Assignment,
    Block,
    If,
    Module,
    SourceFile,
    Branch,
]
