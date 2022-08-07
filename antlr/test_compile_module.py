from compile_module import CompiledModule
from ctypes import c_int, pointer
from unittest.mock import MagicMock
from codegen import CodegenContext, vatype_to_llvmtype
from llvmlite import ir
from vabuiltins import builtins
from verilogatypes import VAType
import hir
from parser_interface import parse_source
from utils import DISCIPLINES


def test_from_hir_mocking_module_to_llvm_module_ir(monkeypatch):
    codegen = CodegenContext()
    functype = ir.FunctionType(ir.VoidType(), ())
    func = ir.Function(codegen.irmodule, functype, name="run_analog")
    vars_ = {}
    for ii in range(1, 4):
        hirvar = hir.Variable(
            name="real" + str(ii), type_=VAType.real, initializer=None
        )
        compiledvar = ir.GlobalVariable(
            codegen.irmodule, vatype_to_llvmtype(hirvar.type_), hirvar.name
        )
        compiledvar.initializer = ir.Constant(vatype_to_llvmtype(VAType.real), 0)
        vars_[ii] = codegen.compiled[hirvar] = compiledvar
    block = func.append_basic_block(name="entry")
    codegen.builder = ir.IRBuilder(block)
    real1 = codegen.builder.load(vars_[1])
    real2 = codegen.builder.load(vars_[2])
    sum_ = codegen.builder.fadd(real1, real2)
    codegen.builder.store(sum_, vars_[3])
    codegen.builder.ret_void()
    module_to_llvm_module_ir = MagicMock(return_value=codegen)
    monkeypatch.setattr(
        CodegenContext, "module_to_llvm_module_ir", module_to_llvm_module_ir
    )
    compiled = CompiledModule.from_hir(123)
    module_to_llvm_module_ir.assert_called_once_with(123)
    compiled.vars["real1"] = 1
    compiled.vars["real2"] = 2
    compiled.run_analog()
    assert compiled.vars["real3"] == 3
    compiled.vars["real1"] = 8
    compiled.vars["real2"] = 9
    compiled.run_analog()
    assert compiled.vars["real3"] == 17


def test_compiled_module():
    run_analog = MagicMock()
    pointer_a = pointer(c_int(2))
    pointer_b = pointer(c_int(5))
    mod = CompiledModule(run_analog, {"a": pointer_a, "b": pointer_b})
    assert mod.vars["a"] == 2
    assert mod.vars["b"] == 5
    mod.vars["b"] = 9
    assert mod.vars["b"] == 9
    assert pointer_b[0] == 9
    assert mod.vars["a"] == 2
    pointer_a[0] = 3
    assert mod.vars["a"] == 3
    mod.run_analog()
    run_analog.assert_called_once_with()


real1 = hir.Variable(name="real1", type_=VAType.real, initializer=None)
real2 = hir.Variable(name="real2", type_=VAType.real, initializer=None)
real3 = hir.Variable(name="real3", type_=VAType.real, initializer=None)


def test_from_hir_addition():
    module = hir.Module(
        name="mymod",
        statements=[
            hir.Assignment(
                lvalue=real3,
                value=hir.FunctionCall(
                    function=builtins.real_addition, arguments=(real1, real2)
                ),
            )
        ],
    )
    compiled = CompiledModule.from_hir(module)
    compiled.vars["real1"] = 1
    compiled.vars["real2"] = 2
    compiled.run_analog()
    assert compiled.vars["real3"] == 1 + 2
    compiled.vars["real1"] = 8
    compiled.vars["real2"] = 9
    compiled.run_analog()
    assert compiled.vars["real3"] == 8 + 9


def test_from_hir_block():
    module = hir.Module(
        name="mymod",
        statements=[
            hir.Block(
                [
                    hir.Assignment(
                        lvalue=real3,
                        value=hir.FunctionCall(
                            function=builtins.real_addition, arguments=(real1, real2)
                        ),
                    ),
                    hir.Assignment(
                        lvalue=real2,
                        value=hir.FunctionCall(
                            function=builtins.real_addition, arguments=(real1, real3)
                        ),
                    ),
                ]
            )
        ],
    )
    compiled = CompiledModule.from_hir(module)
    compiled.vars["real1"] = 1
    compiled.vars["real2"] = 2
    compiled.run_analog()
    assert compiled.vars["real3"] == 1 + 2
    assert compiled.vars["real2"] == 1 + 2 + 1


def test_from_hir_if():
    module = hir.Module(
        name="mymod",
        statements=[
            hir.If(
                condition=real1,
                then=hir.If(
                    condition=real2,
                    then=hir.Assignment(lvalue=real3, value=hir.Literal(3.0)),
                    else_=hir.Assignment(lvalue=real3, value=hir.Literal(1.0)),
                ),
                else_=hir.If(
                    condition=real2,
                    then=hir.Assignment(lvalue=real3, value=hir.Literal(2.0)),
                    else_=hir.Assignment(lvalue=real3, value=hir.Literal(0.0)),
                ),
            )
        ],
    )
    compiled = CompiledModule.from_hir(module)
    for x1 in [0, 1]:
        for x2 in [0, 1]:
            compiled.vars["real1"] = x1
            compiled.vars["real2"] = x2
            compiled.run_analog()
            assert compiled.vars["real3"] == x1 + 2 * x2


def test_from_source_if():
    source = DISCIPLINES + '''
    module mymod();
    real real1, real2, real3;

    analog if (real1) if (real2) real3=3 else real3=1 else if(real2) real3=2 else real3=0
    endmodule
    '''
    module = parse_source(source).modules[0]
    compiled = CompiledModule.from_hir(module)
    for x1 in [0, 1]:
        for x2 in [0, 1]:
            compiled.vars["real1"] = x1
            compiled.vars["real2"] = x2
            compiled.run_analog()
            assert compiled.vars["real3"] == x1 + 2 * x2
