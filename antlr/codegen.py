from verilogatypes import VAType
from llvmlite import ir
from functools import singledispatchmethod, partial
import hir
from customdict import CustomDict


llvmreal = ir.DoubleType()
llvmint = ir.IntType(32)
llvmi1 = ir.IntType(1)


def vatype_to_llvmtype(vatype):
    if vatype == VAType.real:
        return llvmreal
    elif vatype == VAType.integer:
        return llvmint
    elif isinstance(vatype, hir.FunctionSignature):
        return ir.FunctionType(
            vatype_to_llvmtype(vatype.returntype),
            tuple(map(vatype_to_llvmtype, vatype.parameters)),
        )
    else:
        raise Exception(vatype)


class CodegenContext:
    def __init__(self):
        self.irmodule = ir.Module(name=__file__)
        self.builder = None
        # Need a way to store compiled symbols (HIR functions or variables)
        # which compares identity and not equality
        self.compiled = CustomDict(key=id)

    def declare_builtins(self):
        # Declare LLVM intrinsics as extern
        intrinsic_names = {
            hir.sin: "llvm.sin.f64",
            hir.pow_: "llvm.pow.f64",
        }
        for vafunc, name in intrinsic_names.items():
            functype = vatype_to_llvmtype(vafunc.type)
            llvmfunc = ir.Function(self.irmodule, functype, name=name)
            self.compiled[vafunc] = llvmfunc

    @classmethod
    def expression_to_llvm_module_ir(cls, expression, funcname):
        codegen = cls()
        codegen.declare_builtins()
        functype = ir.FunctionType(vatype_to_llvmtype(expression.type), ())
        func = ir.Function(codegen.irmodule, functype, name=funcname)
        block = func.append_basic_block(name="entry")
        codegen.builder = ir.IRBuilder(block)
        codegen.builder.ret(codegen.expression_to_ir(expression))
        return codegen.irmodule

    @singledispatchmethod
    def expression_to_ir(self, expression: hir.Expression):
        raise NotImplementedError(type(expression))

    @expression_to_ir.register
    def _(self, literal: hir.Literal):
        return ir.Constant(vatype_to_llvmtype(literal.type), literal.value)

    @expression_to_ir.register
    def _(self, funcall: hir.FunctionCall):
        func = funcall.function
        args = [self.expression_to_ir(arg) for arg in funcall.arguments]
        instructions = {
            hir.integer_addition: self.builder.add,
            hir.integer_subtraction: self.builder.sub,
            hir.integer_product: self.builder.mul,
            hir.integer_division: self.builder.sdiv,
            hir.real_addition: self.builder.fadd,
            hir.real_subtraction: self.builder.fsub,
            hir.real_product: self.builder.fmul,
            hir.real_division: self.builder.fdiv,
            hir.cast_int_to_real: partial(self.builder.sitofp, typ=llvmreal),
            hir.cast_real_to_int: partial(self.builder.fptosi, typ=llvmint),
        }
        if func in instructions:
            return instructions[func](*args)
        logical_instructions = {
            hir.integer_equality: partial(self.builder.icmp_signed, cmpop="=="),
            hir.integer_inequality: partial(self.builder.icmp_signed, cmpop="!="),
            hir.real_equality: partial(self.builder.fcmp_ordered, cmpop="=="),
            hir.real_inequality: partial(self.builder.fcmp_ordered, cmpop="!="),
        }
        if func in logical_instructions:
            i1_result = logical_instructions[func](lhs=args[0], rhs=args[1])
            return self.builder.zext(i1_result, llvmint)
        if func in self.compiled:
            return self.builder.call(self.compiled[func], args)
        else:
            raise NotImplementedError(func)

    @expression_to_ir.register
    def _(self, variable: hir.Variable):
        pointer = self.variable_to_ir(variable)
        return self.builder.load(pointer)

    @classmethod
    def module_to_llvm_module_ir(cls, module):
        codegen = cls()
        codegen.declare_builtins()
        functype = ir.FunctionType(ir.VoidType(), ())
        func = ir.Function(codegen.irmodule, functype, name="run_analog")
        block = func.append_basic_block(name="entry")
        codegen.builder = ir.IRBuilder(block)
        for statement in module.statements:
            codegen.statement_to_ir(statement)
        codegen.builder.ret_void()
        return codegen

    def variable_to_ir(self, variable):
        if variable not in self.compiled:
            irvar = ir.GlobalVariable(
                self.irmodule, vatype_to_llvmtype(variable.type), variable.name
            )
            irvar.initializer = ir.Constant(vatype_to_llvmtype(variable.type), 0)
            self.compiled[variable] = irvar
        return self.compiled[variable]

    @singledispatchmethod
    def statement_to_ir(self, statement: hir.Statement):
        raise NotImplementedError(type(statement))

    @statement_to_ir.register
    def _(self, assignment: hir.Assignment):
        value = self.expression_to_ir(assignment.value)
        lvalue = self.variable_to_ir(assignment.lvalue)
        self.builder.store(value, lvalue)

    @statement_to_ir.register
    def _(self, block: hir.Block):
        for statement in block.statements:
            self.statement_to_ir(statement)

    @statement_to_ir.register
    def _(self, if_: hir.If):
        inequality = {
            VAType.integer: hir.integer_inequality,
            VAType.real: hir.real_inequality,
        }[if_.condition.type]
        zero = hir.Literal({VAType.integer: 0, VAType.real: 0.0}[if_.condition.type])
        condition_hir = hir.FunctionCall(inequality, (if_.condition, zero))
        condition_ir = self.builder.trunc(self.expression_to_ir(condition_hir), llvmi1)
        with self.builder.if_else(condition_ir) as (then, otherwise):
            with then:
                if if_.then is not None:
                    self.statement_to_ir(if_.then)
            with otherwise:
                if if_.else_ is not None:
                    self.statement_to_ir(if_.else_)
