from llvmlite import ir
import hir
from compiler import compile_ir, get_engine, vatype_to_ctype
from codegen import CodegenContext


def expression_to_pythonfunc(expression):
    funcname = "evaluate_expression"
    irmodule = CodegenContext.expression_to_llvm_module_ir(expression, funcname)
    mod = compile_ir(str(irmodule))

    func_ptr = get_engine().get_function_address(funcname)

    # Run the function via ctypes
    cfunctype = vatype_to_ctype(
        hir.FunctionSignature(returntype=expression.type_, parameters=[])
    )
    cfunc = cfunctype(func_ptr)
    return cfunc
