import pytest
import math
from compile_expression import expression_to_pythonfunc
import hir
from vabuiltins import builtins


@pytest.mark.parametrize(
    "expression,expected",
    [
        (hir.Literal(3), 3),
        (hir.Literal(3.2), 3.2),
        (
            hir.FunctionCall(
                builtins["builtin.integer_subtraction"],
                (hir.Literal(0), hir.Literal(3)),
            ),
            -3,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.integer_addition"], (hir.Literal(1), hir.Literal(3))
            ),
            4,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.integer_addition"],
                (
                    hir.Literal(1),
                    hir.FunctionCall(
                        builtins["builtin.cast_real_to_int"], (hir.Literal(3.0),)
                    ),
                ),
            ),
            4,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.real_subtraction"],
                (hir.Literal(0.5), hir.Literal(3.0)),
            ),
            -2.5,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.real_subtraction"],
                (
                    hir.Literal(0.5),
                    hir.FunctionCall(
                        builtins["builtin.cast_int_to_real"], (hir.Literal(3),)
                    ),
                ),
            ),
            -2.5,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.real_addition"], (hir.Literal(1.5), hir.Literal(3.0))
            ),
            4.5,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.integer_division"], (hir.Literal(6), hir.Literal(-3))
            ),
            -2,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.integer_product"], (hir.Literal(2), hir.Literal(3))
            ),
            6,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.real_division"], (hir.Literal(-0.5), hir.Literal(2.5))
            ),
            -0.2,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.real_product"], (hir.Literal(2.5), hir.Literal(-3.0))
            ),
            -7.5,
        ),
        (hir.FunctionCall(builtins["sin"], (hir.Literal(1.0),)), math.sin(1.0)),
        (
            hir.FunctionCall(builtins["pow"], (hir.Literal(2.0), hir.Literal(3.5))),
            math.pow(2.0, 3.5),
        ),
        (
            hir.FunctionCall(
                builtins["builtin.integer_equality"], (hir.Literal(3), hir.Literal(3))
            ),
            1,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.integer_equality"], (hir.Literal(3), hir.Literal(8))
            ),
            0,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.real_equality"], (hir.Literal(3.5), hir.Literal(3.5))
            ),
            1,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.real_equality"], (hir.Literal(3.3), hir.Literal(3.9))
            ),
            0,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.integer_inequality"], (hir.Literal(3), hir.Literal(3))
            ),
            0,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.integer_inequality"], (hir.Literal(3), hir.Literal(8))
            ),
            1,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.real_inequality"],
                (hir.Literal(3.5), hir.Literal(3.5)),
            ),
            0,
        ),
        (
            hir.FunctionCall(
                builtins["builtin.real_inequality"],
                (hir.Literal(3.3), hir.Literal(3.9)),
            ),
            1,
        ),
    ],
)
def test_compile_expression(expression, expected):
    func = expression_to_pythonfunc(expression)
    actual = func()
    assert type(actual) == type(expected)
    assert actual == expected
