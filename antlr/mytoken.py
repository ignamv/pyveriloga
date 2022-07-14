from typing import Tuple, List, Optional
from dataclasses import dataclass, replace
import os

FileLocation = Tuple[Optional[str], int, int]


@dataclass
class MyToken:
    type: str
    value: str | int | float
    origin: List[FileLocation]

    def included_from(self, origin: List[FileLocation]):
        """Return copy of token with added path of include or macro call"""
        return replace(self, origin=origin + self.origin)

    def __repr__(self):
        origin = [
            (os.path.basename(f) if f is not None else None, line, column)
            for f, line, column in self.origin
        ]
        return f"MyToken({self.type}, {self.value!r}, {origin!r})"
