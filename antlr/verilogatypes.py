from enum import Enum, auto


class VAType(Enum):
    real = auto()
    integer = auto()
    string = auto()
    net = auto()
    void = auto()  # For internal use, not present in VerilogA

    def __repr__(self):
        return "VAType." + self.name


# from typing import Any
# from dataclasses import dataclass
# from llvmlite import ir
# from ctypes import c_double, c_int32, c_char_p
# integertype = VerilogAType(int, c_int32, ir.IntType(32))
# realtype = VerilogAType(float, c_double, ir.DoubleType())
# stringtype = VerilogAType(str, c_char_p, ir.PointerType(ir.IntType(8)))
# nettype = VerilogAType(str, c_char_p, ir.PointerType(ir.IntType(8)))
