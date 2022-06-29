import pytest
from compiler import expression_to_function, CompiledModule
from codegen import resolve_expression_tree_type, build_default_global_context
from parser import (
    BinaryOp,
    Identifier,
    Int,
    Float,
    UnaryOp,
    InitializedVariable,
    FunctionCall,
    Function,
    FunctionSignature,
    parse,
)
from verilogatypes import realtype, integertype


@pytest.mark.parametrize(
    "expression,expected",
    [
        (Int(3), 3),
        (Float(3.2), 3.2),
        (UnaryOp("-", Float(3.2)), -3.2),
        (BinaryOp("*", Float(3.2), Float(2.0)), 6.4),
        (BinaryOp("*", Int(4), Int(2)), 8),
        (BinaryOp("*", Float(3.2), Int(2)), 6.4),
        (BinaryOp("/", Float(3.2), Int(2)), 1.6),
        (BinaryOp("/", Int(7), Int(2)), 3),
        (BinaryOp("/", Float(7.2), Float(2.0)), 3.6),
        (BinaryOp("+", Int(7), Int(2)), 9),
        (BinaryOp("-", Int(7), Int(2)), 5),
        (FunctionCall("sin", [Float(1.0)]), 0.8414709848078965),
        (FunctionCall("sin", [Int(1)]), 0.8414709848078965),
        (FunctionCall("pow", [Float(2.0), Float(3.5)]), 11.313708498984761),
    ],
)
def test_expression_to_function(expression, expected):
    context = build_default_global_context()
    func = expression_to_function(expression, context)
    assert func() == expected


@pytest.mark.parametrize(
    "expression,expectedtype",
    [
        (BinaryOp("/", Float(3.2), Int(2)), realtype),
        (BinaryOp("+", Int(3), Int(2)), integertype),
        (Identifier("realvar"), realtype),
        (Identifier("intvar"), integertype),
        (FunctionCall("sin", [Float(3.14)]), realtype),
    ],
)
def test_resolve_type(expression, expectedtype):
    context = build_default_global_context()
    context.update({
        "realvar": InitializedVariable("realvar", realtype, 1.5),
        "intvar": InitializedVariable("intvar", integertype, 5),
        "sin": Function("sin", FunctionSignature(realtype, [realtype])),
    })
    assert resolve_expression_tree_type(expression, context) == expectedtype


def test_compile_module():
    module = parse('''
module modname(p1);
inout p1;
real globalreal1, globalreal2;
analog begin
  globalreal1 = 3.5;
  globalreal2 = globalreal1 * 2;
end
endmodule
''', 'start_module')
    compiled_module = CompiledModule.compile(module)
    compiled_module.analogs[0]()
    assert compiled_module.vars['globalreal2'] == 7.0
