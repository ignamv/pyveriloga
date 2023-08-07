from verilogatypes import VAType
from llvmlite import ir
from functools import singledispatchmethod, partial
import hir
from vabuiltins import builtins
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
        # Dicts which look up based on identity and not equality
        # Compiled functions
        self.functions = CustomDict(key=id)
        # Compiled variables
        self.variables = CustomDict(key=id)
        # Global variables set by simulator with net potentials
        self.net_potential = CustomDict(key=id)
        # Global variables set by module with net flow contributions
        self.net_flow = CustomDict(key=id)
        # Global variables set by simulator with branch flows
        # self.branch_flow = CustomDict(key=id) # TODO
        # Global variables set by module with branch potentials
        # self.branch_potential = CustomDict(key=id) # TODO

    def declare_builtins(self):
        # Declare LLVM intrinsics as extern
        intrinsic_names = {
            "llvm.sin.f64": builtins.sin,
            "llvm.pow.f64": builtins.pow,
        }
        for name, vafunc in intrinsic_names.items():
            functype = vatype_to_llvmtype(vafunc.type_)
            llvmfunc = ir.Function(self.irmodule, functype, name=name)
            self.functions[vafunc] = llvmfunc

    @classmethod
    def expression_to_llvm_module_ir(cls, expression, funcname):
        codegen = cls()
        codegen.declare_builtins()
        functype = ir.FunctionType(vatype_to_llvmtype(expression.type_), ())
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
        return ir.Constant(vatype_to_llvmtype(literal.type_), literal.value)

    @expression_to_ir.register
    def _(self, funcall: hir.FunctionCall):
        func = funcall.function
        if func is builtins.potential:
            branch, = funcall.arguments
            pot1 = self.builder.load(self.net_potential[branch.net1])
            if branch.net2 is not None:
                pot2 = self.builder.load(self.net_potential[branch.net2])
                return self.builder.fsub(pot1, pot2)
            else:
                return pot1
        if func is builtins.flow:
            branch, = funcall.arguments
            return self.branch_flow[branch]
        args = [self.expression_to_ir(arg) for arg in funcall.arguments]
        instructions = {
            builtins.integer_addition: self.builder.add,
            builtins.integer_subtraction: self.builder.sub,
            builtins.integer_product: self.builder.mul,
            builtins.integer_division: self.builder.sdiv,
            builtins.real_addition: self.builder.fadd,
            builtins.real_subtraction: self.builder.fsub,
            builtins.real_product: self.builder.fmul,
            builtins.real_division: self.builder.fdiv,
            builtins.cast_int_to_real: partial(self.builder.sitofp, typ=llvmreal),
            builtins.cast_real_to_int: partial(self.builder.fptosi, typ=llvmint),
        }
        if func in instructions:
            return instructions[func](*args)
        logical_instructions = {
            builtins.integer_equality: partial(self.builder.icmp_signed, cmpop="=="),
            builtins.integer_inequality: partial(self.builder.icmp_signed, cmpop="!="),
            builtins.real_equality: partial(self.builder.fcmp_ordered, cmpop="=="),
            builtins.real_inequality: partial(self.builder.fcmp_ordered, cmpop="!="),
        }
        if func in logical_instructions:
            i1_result = logical_instructions[func](lhs=args[0], rhs=args[1])
            return self.builder.zext(i1_result, llvmint)
        if func in self.functions:
            return self.builder.call(self.functions[func], args)
        else:
            raise NotImplementedError(func)

    @expression_to_ir.register
    def _(self, variable: hir.Variable):
        return self.builder.load(self.variables[variable])

    @classmethod
    def module_to_llvm_module_ir(cls, module):
        codegen = cls()
        codegen.declare_builtins()
        functype = ir.FunctionType(ir.VoidType(), ())
        func = ir.Function(codegen.irmodule, functype, name="run_analog")
        for variable in module.variables:
            irvar = ir.GlobalVariable(
                codegen.irmodule, vatype_to_llvmtype(variable.type_), variable.name
            )
            irvar.initializer = ir.Constant(vatype_to_llvmtype(variable.type_), 0)
            codegen.variables[variable] = irvar
        for net in module.nets:
            irvar = ir.GlobalVariable(
                codegen.irmodule, vatype_to_llvmtype(VAType.real), '__net_potential_' + net.name
            )
            irvar.initializer = ir.Constant(vatype_to_llvmtype(VAType.real), 0)
            codegen.net_potential[net] = irvar
            irvar = ir.GlobalVariable(
                codegen.irmodule, vatype_to_llvmtype(VAType.real), '__net_flow_' + net.name
            )
            irvar.initializer = ir.Constant(vatype_to_llvmtype(VAType.real), 0)
            codegen.net_flow[net] = irvar
        block = func.append_basic_block(name="entry")
        codegen.builder = ir.IRBuilder(block)
        # Set all outputs to 0 at the beginning
        for var in codegen.net_flow.values():
            codegen.builder.store(ir.Constant(vatype_to_llvmtype(VAType.real), 0), var)
        for statement in module.statements:
            codegen.statement_to_ir(statement)
        codegen.builder.ret_void()
        return codegen

    @singledispatchmethod
    def statement_to_ir(self, statement: hir.Statement):
        raise NotImplementedError(type(statement))

    @statement_to_ir.register
    def _(self, assignment: hir.Assignment):
        value = self.expression_to_ir(assignment.value)
        self.builder.store(value, self.variables[assignment.lvalue])

    @statement_to_ir.register
    def _(self, analogcontribution: hir.AnalogContribution):
        contribution = self.expression_to_ir(analogcontribution.value)
        if analogcontribution.type_ == 'flow':
            for net, sign in [(analogcontribution.branch.net1, 1), (analogcontribution.branch.net2, -1)]:
                if sign == -1 and net is None:
                    break
                lvalue = self.net_flow[net]
                oldvalue = self.builder.load(lvalue)
                if sign == 1:
                    newvalue = self.builder.fadd(oldvalue, contribution)
                else:
                    newvalue = self.builder.fsub(oldvalue, contribution)
                self.builder.store(newvalue, lvalue)
        else:
            raise NotImplementedError(analogcontribution.type_)

    @statement_to_ir.register
    def _(self, block: hir.Block):
        for statement in block.statements:
            self.statement_to_ir(statement)

    @statement_to_ir.register
    def _(self, if_: hir.If):
        inequality = {
            VAType.integer: builtins.integer_inequality,
            VAType.real: builtins.real_inequality,
        }[if_.condition.type_]
        zero = hir.Literal({VAType.integer: 0, VAType.real: 0.0}[if_.condition.type_])
        condition_hir = hir.FunctionCall(inequality, (if_.condition, zero))
        condition_ir = self.builder.trunc(self.expression_to_ir(condition_hir), llvmi1)
        with self.builder.if_else(condition_ir) as (then, otherwise):
            with then:
                if if_.then is not None:
                    self.statement_to_ir(if_.then)
            with otherwise:
                if if_.else_ is not None:
                    self.statement_to_ir(if_.else_)
