from dataclasses import replace
from hir import FunctionSignature, Function, Variable, Literal
from verilogatypes import VAType

binary_int_type = FunctionSignature(
    returntype=VAType.integer, parameters=[VAType.integer, VAType.integer]
)
binary_real_type = FunctionSignature(
    returntype=VAType.real, parameters=[VAType.real, VAType.real]
)
unary_real_type = FunctionSignature(returntype=VAType.real, parameters=[VAType.real])

builtins_list = [
    replace(symbol, name="builtin." + symbol.name)
    for symbol in [
        Function(
            name="cast_int_to_real",
            type=FunctionSignature(returntype=VAType.real, parameters=[VAType.integer]),
        ),
        Function(
            "cast_real_to_int",
            type=FunctionSignature(returntype=VAType.integer, parameters=[VAType.real]),
        ),
        Function(name="integer_product", type=binary_int_type),
        Function(name="real_product", type=binary_real_type),
        Function(name="integer_addition", type=binary_int_type),
        Function(name="real_addition", type=binary_real_type),
        Function(name="integer_division", type=binary_int_type),
        Function(name="real_division", type=binary_real_type),
        Function(name="integer_subtraction", type=binary_int_type),
        Function(name="real_subtraction", type=binary_real_type),
        Function(
            name="real_equality",
            type=FunctionSignature(
                returntype=VAType.integer, parameters=[VAType.real, VAType.real]
            ),
        ),
        Function(
            name="real_inequality",
            type=FunctionSignature(
                returntype=VAType.integer, parameters=[VAType.real, VAType.real]
            ),
        ),
        Function(name="integer_equality", type=binary_int_type),
        Function(name="integer_inequality", type=binary_int_type),
    ]
]
builtins_list.extend(
    [
        Function(name="sin", type=unary_real_type),
        Function(name="pow", type=binary_real_type),
        Variable(name="$temperature", type=VAType.real, initializer=Literal(25)),
    ]
)

builtins = {symbol.name: symbol for symbol in builtins_list}
