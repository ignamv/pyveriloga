from __future__ import annotations
from typing import List, Union, Optional
from mytoken import MyToken
from dataclasses import dataclass, field


@dataclass
class Identifier:
    name: MyToken


@dataclass
class FunctionCall:
    function: MyToken
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
    name: MyToken
    attributes: List[NatureAttribute]


@dataclass
class NatureAttribute:
    name: MyToken
    value: Expression


@dataclass
class Discipline:
    name: MyToken
    attributes: List[DisciplineAttribute]


@dataclass
class DisciplineAttribute:
    name: MyToken
    value: MyToken


@dataclass
class Port:
    name: MyToken
    direction: MyToken


@dataclass
class Net:
    name: MyToken
    discipline: MyToken


@dataclass
class Branch:
    name: MyToken
    nets: List[MyToken]


@dataclass
class Module:
    name: MyToken
    ports: List[Port] = field(default_factory=list)
    nets: List[Net] = field(default_factory=list)
    variables: List[Variable] = field(default_factory=list)
    statements: List[Statement] = field(default_factory=list)
    branches: List[Branch] = field(default_factory=list)
    parameters: List[Parameter] = field(default_factory=list)


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
    name: Optional[MyToken] = None
    declarations: Optional[List[Variable]] = None


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
class Parameter:
    name: MyToken
    type: MyToken
    initializer: Expression
    # TODO: include/exclude ranges


@dataclass
class CaseItem:
    expr: Optional[List[Expression]]
    statement: Statement


@dataclass
class Case:
    expr: Expression
    items: CaseItem


@dataclass
class ForLoop:
    initial: Assignment
    condition: Expression
    change: Assignment
    statement: Statement


@dataclass
class SourceFile:
    natures: List[Nature] = field(default_factory=list)
    disciplines: List[Discipline] = field(default_factory=list)
    modules: List[Module] = field(default_factory=list)


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
