from dataclasses import dataclass
from ctypes import CFUNCTYPE, c_double, c_int32
from codegen import expression_to_llvm_module_ir, resolve_expression_tree_type, module_to_llvm_ir

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


def expression_to_function(expression, context):
    type_ = resolve_expression_tree_type(expression, context)
    llvm_ir = expression_to_llvm_module_ir(expression, type_, context)
    mod = compile_ir(llvm_ir)

    # Look up the function pointer (a Python int)
    func_ptr = engine.get_function_address("funcname")

    # Run the function via ctypes
    cfunc = CFUNCTYPE(type_.ctype)(func_ptr)
    return cfunc


@dataclass
class CompiledModule:
    analogs: [object]
    varpointers: dict

    class Vars:
        def __getitem__(self, name):
            return varpointers[name][0]


    @classmethod
    def compile(cls, module):
        llvm_ir, resolved_module = module_to_llvm_ir(module)
        mod = compile_ir(llvm_ir)

        analogs = [CFUNCTYPE(None)(engine.get_function_address(analog.compiled.name))
                for analog in resolved_module.analogs]
        varpointers = {var.name: POINTER(variable.type.ctype)(engine.get_global_value_address(var.compiled.name))
                for var in resolved_module.variables}
        return cls(analogs=analogs, varpointers=varpointers)
