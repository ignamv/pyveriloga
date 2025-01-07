from verilogatypes import VAType
from llvmlite import ir
import hir
from compiler import compile_ir, get_engine, vatype_to_ctype
from codegen import CodegenContext
from ctypes import POINTER, cast

def make_pointer_to_global(vatype, name):
    address = get_engine().get_global_value_address(name)
    type_ = POINTER(vatype_to_ctype(vatype))
    return cast(address, type_)

class CompiledModule:
    def __init__(
            self,
            run_analog,
            variables,
            parameters,
            net_potential=None,
            net_flow=None,
            branch_potential=None,
            branch_flow=None,
        ):
        if net_potential is None:
            net_potential = {}
        self.net_potential = self.Vars(net_potential)
        if net_flow is None:
            net_flow = {}
        self.net_flow = self.Vars(net_flow)
        self.branch_potential = self.Vars(branch_potential or {})
        self.branch_flow = self.Vars(branch_flow or {})
        self.vars = self.Vars(variables)
        self.parameters = self.Vars(parameters)
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
        engine = get_engine()

        func_ptr = engine.get_function_address("run_analog")
        cfunctype = vatype_to_ctype(
            hir.FunctionSignature(returntype=VAType.void, parameters=[])
        )
        run_analog = cfunctype(func_ptr)

        # TODO: choose only exported variables
        variable_pointers = {
            variable.name: make_pointer_to_global(variable.type_, ir_variable.name)
            for variable, ir_variable in codegen.variables.items()
        }
        parameters = {
            parameter.name: make_pointer_to_global(parameter.type_, ir_variable.name)
            for parameter, ir_variable in codegen.parameters.items()
        }
        net_potential = {
            net.name: make_pointer_to_global(VAType.real, variable.name)
            for net, variable in codegen.net_potential.items()
        }
        net_flow = {
            net.name: make_pointer_to_global(VAType.real, variable.name)
            for net, variable in codegen.net_flow.items()
        }
        branch_potential = {
            (branch.net1.name, branch.net2.name if branch.net2 is not None else None):
            make_pointer_to_global(VAType.real, variable.name)
            for branch, variable in codegen.branch_potential.items()
        }
        branch_flow = {
            (branch.net1.name, branch.net2.name if branch.net2 is not None else None):
            make_pointer_to_global(VAType.real, variable.name)
            for branch, variable in codegen.branch_flow.items()
        }
        return cls(
            run_analog=run_analog,
            variables=variable_pointers,
            parameters=parameters,
            net_potential=net_potential,
            net_flow=net_flow,
            branch_potential=branch_potential,
            branch_flow=branch_flow,
        )
