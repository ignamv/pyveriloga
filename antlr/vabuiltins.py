from dataclasses import replace
from hir import FunctionSignature, Function, Variable, Literal
import keyword
from verilogatypes import VAType

binary_int_type = FunctionSignature(
    returntype=VAType.integer, parameters=(VAType.integer, VAType.integer)
)
binary_real_type = FunctionSignature(
    returntype=VAType.real, parameters=(VAType.real, VAType.real)
)
unary_real_type = FunctionSignature(returntype=VAType.real, parameters=(VAType.real,))

builtins_list = [
    replace(symbol, name="builtin." + symbol.name)
    for symbol in [
        Function(
            name="cast_int_to_real",
            type_=FunctionSignature(returntype=VAType.real, parameters=(VAType.integer,)),
        ),
        Function(
            "cast_real_to_int",
            type_=FunctionSignature(returntype=VAType.integer, parameters=(VAType.real,)),
        ),
        Function(name="integer_product", type_=binary_int_type),
        Function(name="real_product", type_=binary_real_type),
        Function(name="integer_addition", type_=binary_int_type),
        Function(name="real_addition", type_=binary_real_type),
        Function(name="integer_division", type_=binary_int_type),
        Function(name="real_division", type_=binary_real_type),
        Function(name="integer_subtraction", type_=binary_int_type),
        Function(name="real_subtraction", type_=binary_real_type),
        Function(
            name="real_equality",
            type_=FunctionSignature(
                returntype=VAType.integer, parameters=(VAType.real, VAType.real,)
            ),
        ),
        Function(
            name="real_inequality",
            type_=FunctionSignature(
                returntype=VAType.integer, parameters=(VAType.real, VAType.real)
            ),
        ),
        Function(name="integer_equality", type_=binary_int_type),
        Function(name="integer_inequality", type_=binary_int_type),
    ]
]
builtins_list.extend(
    [
        Function(name="sin", type_=unary_real_type),
        Function(name="pow", type_=binary_real_type),
        Variable(name="$temperature", type_=VAType.real, initializer=Literal(25)),
    ]
)


class Builtins:
    def __init__(self):
        self.symbols = {symbol.name: symbol for symbol in builtins_list}
        # Shortcut to common builtins
        for symbol in builtins_list:
            name = symbol.name.rpartition('.')[2]
            if keyword.iskeyword(name):
                name = name + '_'
            setattr(self, name, symbol)

    def __getitem__(self, name):
        return self.symbols[name]
builtins = Builtins()
