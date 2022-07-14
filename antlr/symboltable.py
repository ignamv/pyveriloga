from typing import TypeVar, Generic, List, Optional
from collections import OrderedDict
from collections.abc import Iterable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class Symbol(ABC):
    @property
    @abstractmethod
    def name(self):
        raise NotImplementedError()


@dataclass
class SymbolTable:
    symbols: OrderedDict[str, Symbol]

    def __init__(self, symbols: Optional[List[Symbol]] = None):
        self.symbols = OrderedDict()
        if symbols is not None:
            for symbol in symbols:
                self.define(symbol)

    def __repr__(self):
        return "SymbolTable(" + repr(list(self.symbols.values())) + ")"

    def define(self, symbol: Symbol):
        assert symbol.name not in self.symbols
        self.symbols[symbol.name] = symbol

    def __getitem__(self, name: str) -> Symbol:
        return self.symbols[name]

    def __iter__(self) -> Iterable[Symbol]:
        return iter(self.symbols.values())


class Scope(ABC):
    @property
    @abstractmethod
    def symboltable(self) -> SymbolTable:
        raise NotImplementedError()
