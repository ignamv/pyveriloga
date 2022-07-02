import pytest
import parsetree as pt
import hir
from verilogatypes import realtype, integertype


def generate_literal(value, cls):
    if isinstance(value, float):
        return cls(value=value, type=realtype)
    if isinstance(value, int):
        return cls(value=value, type=integertype)
    raise Exception(type(value))


def pt_literal(value):
    return generate_literal(value, pt.Literal)


def hir_literal(value):
    return generate_literal(value, hir.Literal)


test_symboltable = {
    "realvar": hir.Variable(name="realvar", type=realtype, initializer=None),
    "real_to_real_func": hir.Function(
        type=hir.FunctionSignature(returntype=realtype, parameters=[realtype])
    ),
    "int_to_real_func": hir.Function(
        type=hir.FunctionSignature(returntype=realtype, parameters=[integertype])
    ),
}


@pytest.mark.parametrize(
    "parsetree_in,hir_out",
    [
        (pt_literal(3), hir_literal(3)),
        (pt_literal(3.5), hir_literal(3.5)),
        (pt.Identifier(name="realvar"), test_symboltable["realvar"]),
        (
            pt.FunctionCall(
                name="*",
                arguments=[
                    pt_literal(2),
                    pt_literal(3),
                ],
            ),
            hir.FunctionCall(
                function=hir.integer_product,
                arguments=[
                    hir_literal(2),
                    hir_literal(3),
                ],
            ),
        ),
        (
            pt.FunctionCall(
                name="*",
                arguments=[
                    pt_literal(2),
                    pt_literal(3.5),
                ],
            ),
            hir.FunctionCall(
                function=hir.real_product,
                arguments=[
                    hir.FunctionCall(
                        function=hir.cast_int_to_real, arguments=[hir_literal(2)]
                    ),
                    hir_literal(3.5),
                ],
            ),
        ),
        (
            pt.FunctionCall(
                name="+",
                arguments=[
                    pt_literal(2),
                    pt_literal(3),
                ],
            ),
            hir.FunctionCall(
                function=hir.integer_addition,
                arguments=[
                    hir_literal(2),
                    hir_literal(3),
                ],
            ),
        ),
        (
            pt.FunctionCall(
                name="+",
                arguments=[
                    pt_literal(2),
                    pt_literal(3.5),
                ],
            ),
            hir.FunctionCall(
                function=hir.real_addition,
                arguments=[
                    hir.FunctionCall(
                        function=hir.cast_int_to_real, arguments=[hir_literal(2)]
                    ),
                    hir_literal(3.5),
                ],
            ),
        ),
        (
            pt.FunctionCall(
                name="*",
                arguments=[
                    pt_literal(3.5),
                    pt.FunctionCall(
                        name="+",
                        arguments=[
                            pt_literal(2),
                            pt_literal(6),
                        ],
                    ),
                ],
            ),
            hir.FunctionCall(
                function=hir.real_addition,
                arguments=[
                    hir_literal(3.5),
                    hir.FunctionCall(
                        function=hir.cast_int_to_real,
                        arguments=[
                            hir.FunctionCall(
                                function=hir.integer_addition,
                                arguments=[
                                    hir_literal(2),
                                    hir_literal(6),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ),
        (
            pt.FunctionCall(name="real_to_real_func", arguments=[pt_literal(3.5)]),
            hir.FunctionCall(
                function=test_symboltable["real_to_real_func"],
                arguments=[hir_literal(3.5)],
            ),
        ),
        (
            pt.FunctionCall(name="real_to_real_func", arguments=[pt_literal(3)]),
            hir.FunctionCall(
                function=test_symboltable["real_to_real_func"],
                arguments=[
                    hir.FunctionCall(
                        function=hir.cast_int_to_real, arguments=[hir_literal(3)]
                    )
                ],
            ),
        ),
        (
            pt.FunctionCall(name="int_to_real_func", arguments=[pt_literal(3)]),
            hir.FunctionCall(
                function=test_symboltable["int_to_real_func"],
                arguments=[hir_literal(3)],
            ),
        ),
        (
            pt.FunctionCall(name="int_to_real_func", arguments=[pt_literal(3.5)]),
            hir.FunctionCall(
                function=test_symboltable["int_to_real_func"],
                arguments=[
                    hir.FunctionCall(
                        function=hir.cast_real_to_int, arguments=[hir_literal(3.5)]
                    )
                ],
            ),
        ),
    ],
)
def test_resolve_expression(parsetree_in, hir_out):
    assert parsetree_in.resolve(test_symboltable) == hir_out


test_natures = {
    "Current": hir.Nature(name="Current", access="I", units="A", abstol=1e-12),
    "Voltage": hir.Nature(name="Voltage", access="V", units="V", abstol=1e-6),
}
test_disciplines = {
    "electrical": hir.Discipline(
        name="electrical",
        domain="continuous",
        potential=test_natures["Voltage"],
        flow=test_natures["Current"],
    ),
}


@pytest.mark.parametrize(
    "port_or_net,expected",
    [
        (
            pt.Net(name="p1", discipline="electrical"),
            hir.Net(name="p1", discipline=test_disciplines["electrical"]),
        ),
        (
            pt.Port(name="p1", discipline="electrical", direction="inout"),
            hir.Port(
                name="p1", discipline=test_disciplines["electrical"], direction="inout"
            ),
        ),
    ],
)
def test_resolve_nature(port_or_net, expected):
    assert port_or_net.resolve(test_disciplines) == expected


# def test_resolve_module():
# module = pt.Module(
# name='modname',
# variables=Variables({
#'realglobal': pt.Variable(name='realglobal', type=realtype, initializer=None),
#'intglobal': pt.Variable(name='intglobal', type=integertype, initializer=None),
# }),


def test_resolve_variables():
    variables = pt.Variables(
        [
            pt.Variable(name="v1", type=integertype, initializer=pt_literal(1)),
            pt.Variable(name="v2", type=integertype, initializer=pt_literal(2)),
            pt.Variable(
                name="v3",
                type=integertype,
                initializer=pt.FunctionCall(
                    name="+", arguments=[pt.Identifier("v1"), pt.Identifier("v2")]
                ),
            ),
        ]
    )
    v1 = hir.Variable(name="v1", type=integertype, initializer=hir_literal(1))
    v2 = hir.Variable(name="v2", type=integertype, initializer=hir_literal(2))
    v3 = hir.Variable(
        name="v3",
        type=integertype,
        initializer=hir.FunctionCall(hir.integer_addition, arguments=[v1, v2]),
    )
    v1global = hir.Variable(name="v1", type=integertype, initializer=hir_literal(3))
    v4global = hir.Variable(name="v2", type=integertype, initializer=hir_literal(4))
    expected_variables = hir.Variables(
        [
            v1,
            v2,
            v3,
        ]
    )
    input_symboltable = {"v1": v1global, "v4": v4global}
    expected_symboltable = {"v1": v1, "v2": v2, "v3": v3, "v4": v4global}
    actual_variables, actual_symboltable = variables.resolve(input_symboltable)
    assert actual_variables == expected_variables
    assert actual_symboltable == expected_symboltable


test_statement_symboltable = {
    var.name: var
    for var in [
        hir.Variable(name="realvar1", type=realtype, initializer=None),
        hir.Variable(name="realvar2", type=realtype, initializer=None),
        hir.Variable(name="intvar1", type=integertype, initializer=None),
    ]
}


test_resolve_statement_local = pt.Variable(
    name="realvar1", type=realtype, initializer=None
)
test_resolve_statement_local_resolved = hir.Variable(
    name="realvar1", type=realtype, initializer=None
)


@pytest.mark.parametrize(
    "statement,expected",
    [
        (
            pt.Assignment(lvalue="realvar1", value=pt.Identifier("realvar2")),
            hir.Assignment(
                lvalue=test_statement_symboltable["realvar1"],
                value=test_statement_symboltable["realvar2"],
            ),
        ),
        (
            pt.Assignment(lvalue="realvar1", value=pt.Identifier("intvar1")),
            hir.Assignment(
                lvalue=test_statement_symboltable["realvar1"],
                value=hir.FunctionCall(
                    function=hir.cast_int_to_real,
                    arguments=[test_statement_symboltable["intvar1"]],
                ),
            ),
        ),
        (
            pt.Block(
                variables=pt.Variables([test_resolve_statement_local]),
                statements=[
                    pt.Assignment(lvalue="realvar2", value=pt.Identifier("realvar1")),
                    pt.Assignment(lvalue="realvar1", value=pt.Identifier("realvar2")),
                ],
            ),
            hir.Block(
                variables=hir.Variables([test_resolve_statement_local_resolved]),
                statements=[
                    hir.Assignment(
                        lvalue=test_statement_symboltable["realvar2"],
                        value=test_statement_symboltable["realvar1"],
                    ),
                    hir.Assignment(
                        lvalue=test_statement_symboltable["realvar1"],
                        value=test_statement_symboltable["realvar2"],
                    ),
                ],
            ),
        ),
    ],
)
def test_resolve_statement(statement, expected):
    assert statement.resolve(test_statement_symboltable) == expected
