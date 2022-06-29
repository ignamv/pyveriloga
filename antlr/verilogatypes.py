from dataclasses import dataclass
from ctypes import c_double, c_int32
from llvmlite import ir


@dataclass
class VerilogAType:
    pythontype: type
    ctype: object
    llvmtype: object


integertype = VerilogAType(int, c_int32, ir.IntType(32))
realtype = VerilogAType(float, c_double, ir.DoubleType())
