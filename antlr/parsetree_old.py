from __future__ import annotations
from dataclasses import dataclass, field
from verilogatypes import VerilogAType as VAType, realtype, integertype
from typing import Mapping, List, Optional, Union
from collections import OrderedDict
import hir


@dataclass
class Nature:
    name: str
    abstol: float
    access: str
    idt_nature: str
    units: str
    ddt_nature: Optional[str] = None


@dataclass
class Discipline:
    name: str
    domain: str
    potentialnature: str
    flownature: str


@dataclass
class Net:
    name: str
    discipline: Optional[str] = None

    def resolve(self, disciplines: Mapping[str, hir.Discipline]):
        return hir.Net(name=self.name, discipline=disciplines[self.discipline])


@dataclass
class Port(Net):
    name: str
    discipline: Optional[str] = None
    direction: Optional[str] = None

    def resolve(self, disciplines: Mapping[str, hir.Discipline]):
        return hir.Port(
            name=self.name,
            discipline=disciplines[self.discipline],
            direction=self.direction,
        )


@dataclass
class Literal:
    value: int | float
    type: VAType

    def resolve(self, symboltable):
        return hir.Literal(value=self.value, type=self.type)


@dataclass
class FunctionCall:
    name: str
    arguments: List[Expression]

    def resolve(self, symboltable):
        arguments = [arg.resolve(symboltable) for arg in self.arguments]
        binary_operators = {
            "*": (hir.integer_product, hir.real_product),
            "+": (hir.integer_addition, hir.real_addition),
        }
        if self.name in binary_operators:
            intfunc, realfunc = binary_operators[self.name]
            if any(arg.type == realtype for arg in arguments):
                function = realfunc
                arguments = [hir.ensure_real(arg) for arg in arguments]
            else:
                function = intfunc
        elif self.name in symboltable:
            function = symboltable[self.name]
            assert len(arguments) == len(function.type.parameters)
            arguments = [
                hir.ensure_type(arg, type)
                for arg, type in zip(arguments, function.type.parameters)
            ]
        else:
            raise Exception(self.name)
        return hir.FunctionCall(function=function, arguments=arguments)


@dataclass
class Identifier:
    name: str

    def resolve(self, symboltable):
        return symboltable[self.name]


Expression = Union[Literal, Identifier, FunctionCall]


def resolve_symbols(self, symboltable, parent_symboltable):
    symboltable = symboltable.copy()
    resolved = []
    for var in self:
        if var.initializer is None:
            initializer = None
        else:
            initializer = var.initializer.resolve(symboltable)
        var_resolved = hir.Variable(
            name=var.name, type=var.type, initializer=initializer
        )
        symboltable[var.name] = var_resolved
        resolved.append(var_resolved)
    return hir.Variables(resolved), symboltable


@dataclass
class Assignment:
    lvalue: str
    value: Expression

    def resolve(self, symboltable):
        lvalue = symboltable[self.lvalue]
        return hir.Assignment(
            lvalue=lvalue,
            value=hir.ensure_type(self.value.resolve(symboltable), lvalue.type),
        )


@dataclass
class Block:
    variables: Variables
    statements: List[Statement]

    def resolve(self, symboltable):
        variables, symboltable = self.variables.resolve(symboltable)
        statements = [statement.resolve(symboltable) for statement in self.statements]
        return hir.Block(variables=variables, statements=statements)


Statement = Union[Assignment, Block]


@dataclass
class Analog:
    statement: Statement


@dataclass
class Module:
    name: str
    variables: Variables = field(default_factory=Variables)
    ports: List[Port] = field(default_factory=list)
    nets: List[Net] = field(default_factory=list)
    analogs: List[Analog] = field(default_factory=list)

    def resolve(natures: Mapping[str, hir.Nature]):
        variables, symboltable = self.variables.resolve()
        return hir.Module(
            name=self.name,
            variables=variables,
            ports=[port.resolve(natures) for port in self.ports],
            nets=[net.resolve(natures) for port in self.nets],
            analogs=[analog.resolve(symboltable, natures) for analog in self.analogs],
        )


Symbol = Union[Nature, Discipline, Module, Variable, Net]


@dataclass
class SourceFile:
    symbols: SymbolTable[Symbol]
