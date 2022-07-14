from verilogatypes import VAType
from llvmlite import ir
import hir
from compiler import compile_ir, get_engine, vatype_to_ctype
from codegen import CodegenContext
from ctypes import POINTER, cast


class CompiledModule:
    def __init__(self, run_analog, variable_pointers):
        self.vars = self.Vars(variable_pointers)
        self.run_analog = run_analog

    class Vars:
        def __init__(self, pointers):
            self.pointers = pointers

        def __getitem__(self, name):
            return self.pointers[name][0]

        def __setitem__(self, name, value):
            self.pointers[name][0] = value

    @classmethod
    def from_hir(cls, module):
        codegen = CodegenContext.module_to_llvm_module_ir(module)
        llvm_ir = str(codegen.irmodule)
        print(llvm_ir)
        mod = compile_ir(llvm_ir)

        func_ptr = get_engine().get_function_address("run_analog")
        cfunctype = vatype_to_ctype(
            hir.FunctionSignature(returntype=VAType.void, parameters=[])
        )
        run_analog = cfunctype(func_ptr)

        variable_pointers = {}
        # TODO: choose only exported variables
        for symbol in codegen.compiled.values():
            if isinstance(symbol, ir.GlobalVariable):
                address = get_engine().get_global_value_address(symbol.name)
                type_ = POINTER(
                    vatype_to_ctype(VAType.int if "int" in symbol.name else VAType.real)
                )
                variable_pointers[symbol.name] = cast(address, type_)
        return cls(run_analog=run_analog, variable_pointers=variable_pointers)
