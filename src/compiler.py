from verilogatypes import VAType
import hir
from dataclasses import dataclass
from ctypes import c_double, c_int32, c_char_p, CFUNCTYPE


def vatype_to_ctype(vatype):
    if vatype == VAType.real:
        return c_double
    elif vatype == VAType.integer:
        return c_int32
    elif vatype == VAType.void:
        return None
    elif isinstance(vatype, hir.FunctionSignature):
        return CFUNCTYPE(
            vatype_to_ctype(vatype.returntype), *map(vatype_to_ctype, vatype.parameters)
        )
    else:
        raise Exception(vatype)


import llvmlite.binding as llvm


engine = None


def initialize_llvm():
    """Initializations required for code generation"""
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()


def create_execution_engine():
    """
    Create an ExecutionEngine suitable for JIT code generation on
    the host CPU.  The engine is reusable for an arbitrary number of
    modules.
    """
    initialize_llvm()
    # Create a target machine representing the host
    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    # And an execution engine with an empty backing module
    backing_mod = llvm.parse_assembly("")
    engine = llvm.create_mcjit_compiler(backing_mod, target_machine)
    return engine


def compile_ir(llvm_ir):
    """
    Compile the LLVM IR string with the given engine.
    The compiled module object is returned.
    """
    global engine
    if engine is None:
        engine = create_execution_engine()
    # Create a LLVM module object from the IR
    mod = llvm.parse_assembly(llvm_ir)
    mod.verify()
    # Now add the module and make sure it is ready for execution
    engine.add_module(mod)
    engine.finalize_object()
    engine.run_static_constructors()
    return mod


def get_engine():
    return engine
