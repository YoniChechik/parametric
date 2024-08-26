from pathlib import Path
from typing import Tuple, Union

import pytest

from parametric._type_node import TypeCoercionError
from parametric._typehint_parsing import parse_typehint


def parse_and_cast_strict(value, typehint):
    type_node = parse_typehint("test_field", typehint)
    return type_node.cast_python_strict(value)


def test_union_type_strict():
    # These should succeed because the input matches one of the types exactly
    assert parse_and_cast_strict(1, str | int) == 1
    assert parse_and_cast_strict("1", str | int) == "1"
    assert parse_and_cast_strict(3.0, float | complex) == 3.0
    assert parse_and_cast_strict((1, 2), tuple[int, int]) == (1, 2)
    assert parse_and_cast_strict(None, type(None)) is None

    # These should fail because none of the types in the union match the input exactly
    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict(1.5, int | str)  # Should fail because 1.5 is not exactly int or str

    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict("1.5", float | int)  # Should fail because "1.5" is not exactly float or int

    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict(
            (1, 2), tuple[int, float]
        )  # Should fail because the tuple's second element is not a float

    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict((1, 2), tuple[float, int])  # Should fail because the tuple's first element is not a float


def test_strict_coercion():
    assert parse_and_cast_strict(1, int) == 1
    assert parse_and_cast_strict("1", str) == "1"
    assert parse_and_cast_strict(1.5, float) == 1.5

    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict(1, str)  # Should fail because strict mode does not allow type coercion

    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict("1", int)  # Should fail because strict mode does not allow type coercion


def test_impossible_coercion_strict():
    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict((1, 2), tuple[int, type(None)])

    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict((1, 2), tuple[type(None), int])

    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict("error str", int | float)


def test_invalid_typehint_strict():
    with pytest.raises(Exception):
        parse_and_cast_strict((1, 2), tuple)
    with pytest.raises(Exception):
        parse_and_cast_strict((1, 2), Tuple)
    with pytest.raises(Exception):
        parse_and_cast_strict(1, Union)


def test_union_type_error_on_str_path_union_strict():
    with pytest.raises(TypeError, match="Union with both `str` and `pathlib.Path` is not allowed."):
        parse_and_cast_strict("some_string", str | Path)


def test_bool_node_true_values_strict():
    assert parse_and_cast_strict(True, bool) is True

    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict("true", bool)  # Should fail in strict mode
    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict(1, bool)  # Should fail in strict mode


def test_bool_node_false_values_strict():
    assert parse_and_cast_strict(False, bool) is False

    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict("false", bool)  # Should fail in strict mode
    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict(0, bool)  # Should fail in strict mode
    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict(-1, bool)  # Should fail in strict mode


def test_bool_node_invalid_values_strict():
    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict("not_a_bool", bool)
    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict(2, bool)
    with pytest.raises(TypeCoercionError):
        parse_and_cast_strict(None, bool)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
