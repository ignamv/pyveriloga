from llvmlite import ir
from verilogatypes import realtype, integertype
from parser import Int, Float, Identifier, UnaryOp, BinaryOp, Function, FunctionCall, FunctionSignature, AnalogSequence, VariableAssignment, InitializedVariable
from dataclasses import dataclass, replace


def calculate_expression_type(expression, context):
    if isinstance(expression, (Int, Float)):
        return expression.type
    if isinstance(expression, Identifier):
        return context[expression.name].type
    if isinstance(expression, UnaryOp):
        return resolve_expression_tree_type(expression.child, context)
    if isinstance(expression, BinaryOp):
        childcontext = resolve_expression_tree_type(
            expression.left, context
        ), resolve_expression_tree_type(expression.right, context)
        if any(childtype == realtype for childtype in childcontext):
            return realtype
        assert all(childtype == integertype for childtype in childcontext)
        return integertype
    if isinstance(expression, FunctionCall):
        function = context[expression.name]
        assert isinstance(function, Function)
        # Check call arguments
        assert len(expression.arguments) == len(function.signature.parameters)
        # TODO: check argument types
        return function.signature.returntype
    raise NotImplementedError(expression)


def resolve_expression_tree_type(expression, context):
    ret = calculate_expression_type(expression, context)
    expression.type = ret
    return ret


def unaryop_to_llvm(expression, builder, context):
    operator = expression.operator
    child = expression_to_llvm_ir_inner(expression.child, builder, context)
    if operator == "-":
        return builder.fsub(ir.Constant(expression.type.llvmtype, 0), child)
    raise NotImplementedError(operator)


def ensure_real(value, builder):
    if value.type == realtype.llvmtype:
        return value
    return builder.sitofp(value, realtype.llvmtype)


def binaryop_to_llvm(expression, builder, context):
    operator = expression.operator
    left = expression_to_llvm_ir_inner(expression.left, builder, context)
    right = expression_to_llvm_ir_inner(expression.right, builder, context)
    sametype_operators = {
        "*": (builder.fmul, builder.mul),
        "/": (builder.fdiv, builder.sdiv),
        "+": (builder.fadd, builder.add),
        "-": (builder.fsub, builder.sub),
    }
    if operator in sametype_operators:
        realinstruction, intinstruction = sametype_operators[operator]
        if expression.type == realtype:
            return realinstruction(
                ensure_real(left, builder), ensure_real(right, builder)
            )
        else:
            return intinstruction(left, right)

    raise NotImplementedError(operator)


def cast(expression, type_, builder, context):
    inner = expression_to_llvm_ir_inner(expression, builder, context)
    if expression.type == type_:
        return inner
    if type_ == realtype:
        assert expression.type == integertype
        return builder.sitofp(inner, type_.llvmtype)
    elif type_ == integertype:
        assert expression.type == realtype
        return builder.fptosi(inner, type_.llvmtype)
    else:
        raise Exception(type_)


def functioncall_to_llvm(funcall, builder, context):
    func = context[funcall.name]
    assert isinstance(func, Function)
    arguments = [cast(arg, type_, builder, context)
            for arg, type_ in zip(funcall.arguments, func.signature.parameters)]
    return builder.call(func.compiled, arguments)


def readvariable(variable, builder):
    return builder.load(variable.compiled)


def expression_to_llvm_ir_inner(expression, builder, context):
    if isinstance(expression, (Int, Float)):
        return ir.Constant(expression.type.llvmtype, expression.value)
    if isinstance(expression, UnaryOp):
        return unaryop_to_llvm(expression, builder, context)
    if isinstance(expression, BinaryOp):
        return binaryop_to_llvm(expression, builder, context)
    if isinstance(expression, FunctionCall):
        return functioncall_to_llvm(expression, builder, context)
    if isinstance(expression, InitializedVariable):
        return readvariable(expression, builder)
    raise NotImplementedError(type(expression))


def expression_to_llvm_function(module, expression, type_, context):
    functype = ir.FunctionType(type_.llvmtype, ())
    func = ir.Function(module, functype, name="funcname")
    block = func.append_basic_block(name="entry")
    builder = ir.IRBuilder(block)
    # a, b = func.args
    result = expression_to_llvm_ir_inner(expression, builder, context)
    builder.ret(result)
    return func


def expression_to_llvm_module_ir(expression, type_, context):
    context = build_default_global_context()
    # TODO: use given context
    module = ir.Module(name=__file__)
    for reference in context.values():
        assert isinstance(reference, IntrinsicFunction)
        signature = reference.signature
        reference.compiled = ir.Function(
            module,
            ir.FunctionType(
                signature.returntype.llvmtype,
                tuple(type_.llvmtype for type_ in signature.parameters),
            ),
            reference.intrinsicname,
        )
    expression_to_llvm_function(module, expression, type_, context)
    return str(module)


@dataclass
class IntrinsicFunction(Function):
    intrinsicname: str = None


def build_default_global_context():
    ret = {
        "sin": IntrinsicFunction("sin", FunctionSignature(realtype, [realtype]), intrinsicname="llvm.sin.f64"),
        "pow": IntrinsicFunction("pow", FunctionSignature(realtype, [realtype, realtype]), intrinsicname="llvm.pow.f64"),
    }
    return ret


def resolve_expression(expression, module):
    if isinstance(expression, Identifier):
        return module.variables[expression.name]
    if isinstance(expression, (Float, Int)):
        return expression
    if isinstance(expression, UnaryOp):
        return replace(expression, child=resolve_expression(expression.child))
    if isinstance(expression, BinaryOp):
        return replace(expression, 
                left=resolve_expression(expression.left),
                right=resolve_expression(expression.right),
        )
    else:
        raise Exception(expression)



def resolve_analog_sequence(analog_sequence, module):
    for statement in analog_sequence.statements:
        if isinstance(statement, VariableAssignment):
            # TODO: look at analog block locals
            lvalue = module.variables[statement.lvalue]
            value = resolve_expression(statement.value, module)
            yield replace(statement, lvalue=lvalue, value=value)
        else:
            raise Exception(statement)


def compile_analog(analog_content, module, irmodule, name):
    assert isinstance(analog_content, AnalogSequence)
    statements = resolve_analog_sequence(analog_content, module)
    functype = ir.FunctionType(ir.VoidType(), ())
    func = ir.Function(irmodule, functype, name=name)
    block = func.append_basic_block(name="entry")
    builder = ir.IRBuilder(block)
    for statement in statements:
        if isinstance(statement, VariableAssignment):
            builder.store(statement.value, expression_to_llvm_ir_inner(statement.lvalue, builder, {}))
        else:
            raise Exception(statement)
    return func

def module_to_llvm_ir(module):
    context = build_default_global_context()
    # TODO: use given context
    irmodule = ir.Module(name=__file__)
    for var in module.variables:
        # TODO: use initializer
        var.compiled = ir.GlobalVariable(irmodule, var.type.llvmtype, var.name)
    for ii, analog in enumerate(module.analogs):
        name = f'analog{ii}'
        analog.compiled = compile_analog(analog.content, module, irmodule, name)

    return str(module), module
