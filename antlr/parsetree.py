from __future__ import annotations
from typing import List, Union, Optional
from mytoken import MyToken
from dataclasses import dataclass


@dataclass
class Identifier:
    name: MyToken


@dataclass
class FunctionCall:
    function: Identifier
    args: List[Expression]


@dataclass
class Literal:
    value: MyToken


@dataclass
class Operation:
    operator: MyToken
    operands: List[Expression]


@dataclass
class Nature:
    name: Identifier
    attributes: List[NatureAttribute]


@dataclass
class NatureAttribute:
    name: MyToken
    value: Expression


@dataclass
class Discipline:
    name: Identifier
    attributes: List[DisciplineAttribute]


@dataclass
class DiscreteOrContinuous:
    value: MyToken


@dataclass
class DisciplineAttribute:
    name: MyToken
    value: Identifier | DiscreteOrContinuous


@dataclass
class Port:
    name: MyToken
    direction: MyToken


@dataclass
class Net:
    name: MyToken
    discipline: Identifier


@dataclass
class Module:
    name: MyToken
    ports: List[Port]
    nets: List[Net]
    variables: List[Variable]


@dataclass
class Assignment:
    lvalue: MyToken
    value: Expression


@dataclass
class AnalogContribution:
    accessor: MyToken
    arg1: MyToken
    arg2: Optional[MyToken]
    value: Expression


@dataclass
class Block:
    statements: List[Statement]


@dataclass
class If:
    condition: Expression
    then: Statement
    else_: Optional[Statement]


@dataclass
class Variable:
    name: MyToken
    type: MyToken
    initializer: Optional[Expression]


@dataclass
class SourceFile:
    natures: List[Nature]
    disciplines: List[Discipline]
    modules: List[Module]


Expression = Union[Identifier, Literal, FunctionCall, Operation]
Statement = Union[Assignment, AnalogContribution, Block]

ParseTree = Union[
    Identifier,
    FunctionCall,
    Literal,
    Operation,
    Nature,
    NatureAttribute,
    Discipline,
    DiscreteOrContinuous,
    DisciplineAttribute,
    Port,
    Net,
    Module,
    Assignment,
    AnalogContribution,
    Block,
    If,
    Variable,
    SourceFile,
]
