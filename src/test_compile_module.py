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
from itertools import product


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
        vars_[ii] = codegen.variables[hirvar] = compiledvar
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
    mod = CompiledModule(run_analog, {"a": pointer_a, "b": pointer_b}, parameters={})
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
        variables=[real1, real2, real3],
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
        variables=[real1,real2,real3],
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
        variables=[real1,real2,real3],
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


def test_from_source_parameter():
    source = (
        DISCIPLINES
        + """
    module mymod();
    parameter real par1 = 2.5;
    parameter integer par2 = 4;
    real out1;
    integer out2;

    analog begin
        out1 = par1 + par2;
        out2 = par1 - par2;
    end

    endmodule
    """
    )
    module = parse_source(source).modules[0]
    compiled = CompiledModule.from_hir(module)
    compiled.parameters["par1"] = 4.5
    compiled.parameters["par2"] = 7
    compiled.run_analog()
    assert compiled.vars["out1"] == 11.5
    assert compiled.vars["out2"] == -2


def test_from_source_if():
    source = (
        DISCIPLINES
        + """
    module mymod();
    real real1, real2, real3;

    analog if (real1) if (real2) real3=3; else real3=1; else if(real2) real3=2; else real3=0;
    endmodule
    """
    )
    module = parse_source(source).modules[0]
    compiled = CompiledModule.from_hir(module)
    for x1 in [0, 1]:
        for x2 in [0, 1]:
            compiled.vars["real1"] = x1
            compiled.vars["real2"] = x2
            compiled.run_analog()
            assert compiled.vars["real3"] == x1 + 2 * x2


def test_analogcontribution():
    source = (
        DISCIPLINES
        + """
    module mymod(net1, net2);
    inout electrical net1, net2;

    analog I(net1) <+ 3.5;
    analog I(net2, net1) <+ 4.5;
    endmodule
    """
    )
    module = parse_source(source).modules[0]
    compiled = CompiledModule.from_hir(module)
    for _ in range(2):
        compiled.run_analog()
        assert compiled.net_flow['net1'] == -1
        assert compiled.net_flow['net2'] == 4.5


def test_analogprobe():
    source = (
        DISCIPLINES
        + """
    module mymod(net1, net2, net3);
    inout electrical net1, net2, net3;

    analog begin
        I(net1) <+ V(net1, net2);
        I(net2) <+ -V(net2);
        V(net3, net2) <+ I(net3, net2);
        V(net1) <+ I(net1);
    end

    endmodule
    """
    )
    module = parse_source(source).modules[0]
    compiled = CompiledModule.from_hir(module)
    for _ in range(2):
        compiled.net_potential['net1'] = 3
        compiled.net_potential['net2'] = 7
        compiled.branch_flow["net3","net2"] = 5
        compiled.branch_flow["net1",None] = 6
        compiled.run_analog()
        assert compiled.net_flow['net1'] == -4
        assert compiled.net_flow['net2'] == -7
        assert compiled.branch_potential["net3","net2"] == 5
        assert compiled.branch_potential["net1",None] == 6


def test_resistor():
    source = (
        DISCIPLINES
        + """
    module mymod(net1, net2);
    inout electrical net1, net2;
    parameter real R=1;

    analog begin
        I(net1, net2) <+ V(net1, net2) / R;
    end

    endmodule
    """
    )
    module = parse_source(source).modules[0]
    compiled = CompiledModule.from_hir(module)
    for r, i, j in product([0.1, 2e3], range(4), range(4)):
        compiled.parameters["R"] = r
        v1 = 2 + i * 0.1
        v2 = 7 - i * 0.7
        compiled.net_potential['net1'] = v1
        compiled.net_potential['net2'] = v2
        compiled.run_analog()
        assert compiled.net_flow['net1'] == (v1 - v2) / r
        assert compiled.net_flow['net2'] == -(v1 - v2) / r


def test_compile_bsimbulk():
    module = parse_source(filename="../inputfiles/dump/bsimbulk_without_functions.va", include_path=["../include"]).modules[0]
