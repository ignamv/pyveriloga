from typing import TypeVar, Generic, List
from collections import OrderedDict
from collections.abc import Iterable
from abc import ABC, abstractmethod
from dataclasses import dataclass

class SymbolABC(ABC):
    @property
    @abstractmethod
    def name(self):
        raise NotImplementedError()

Symbol = TypeVar('Symbol', bound=SymbolABC)
@dataclass
class SymbolTable(Generic[Symbol]):
    symbols: OrderedDict[str, Symbol]

    def __init__(self, symbols: List[Symbol]):
        self.symbols = OrderedDict()
        for sym in symbols:
            self.symbols[sym.name] = sym

    def declare(self, symbol: Symbol):
        assert symbol.name not in self.symbols
        self.symbols[symbol.name] = symbol

    def __getitem__(self, name: str) -> Symbol:
        return self.symbols[name]

    def __iter__(self) -> Iterable[Symbol]:
        return iter(self.symbols.values())
