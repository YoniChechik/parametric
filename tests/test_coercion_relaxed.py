from pathlib import Path
from typing import Tuple, Union

import pytest

from parametric._type_node import TypeCoercionError
from parametric._typehint_parsing import parse_typehint


def parse_and_cast_relaxed(value, typehint):
    type_node = parse_typehint("test_field", typehint)
    return type_node.cast_python_relaxed(value)


def test_union_type():
    assert parse_and_cast_relaxed(1, str | int) == 1
    assert parse_and_cast_relaxed("1", str | int) == 1
    assert parse_and_cast_relaxed(1.5, str | float | int) == 1.5
    assert parse_and_cast_relaxed(1, str | float | int) == 1
    assert parse_and_cast_relaxed(1, float | str | int) == 1
    assert parse_and_cast_relaxed((1, 2), str | tuple[int, int] | int) == (1, 2)
    assert parse_and_cast_relaxed(None, str | None) is None
    assert parse_and_cast_relaxed(3.0, float | complex) == 3
    assert parse_and_cast_relaxed(3.0, int | float) == 3
    assert parse_and_cast_relaxed(3, int | float) == 3
    assert parse_and_cast_relaxed((1, 2), str | tuple[int, float] | int) == (1, 2)
    assert parse_and_cast_relaxed((1, 2), str | tuple[int, str] | int) == (1, "2")
    assert parse_and_cast_relaxed(("some", "str"), str | tuple[int, str] | int) == "('some', 'str')"


def test_coercion():
    assert parse_and_cast_relaxed(1, str) == "1"
    assert parse_and_cast_relaxed("1", int) == 1
    assert parse_and_cast_relaxed("1.5", float) == 1.5


def test_impossible_coercion():
    with pytest.raises(Exception):
        parse_and_cast_relaxed((1, 2), tuple[int, None])
    with pytest.raises(Exception):
        parse_and_cast_relaxed((1, 2), tuple[None, int])
    with pytest.raises(Exception):
        parse_and_cast_relaxed("error str", int | float)


def test_invalid_typehint():
    with pytest.raises(Exception):
        parse_and_cast_relaxed((1, 2), tuple)
    with pytest.raises(Exception):
        parse_and_cast_relaxed((1, 2), Tuple)
    with pytest.raises(Exception):
        parse_and_cast_relaxed(1, Union)


def test_union_type_error_on_str_path_union():
    with pytest.raises(TypeError, match="Union with both `str` and `pathlib.Path` is not allowed."):
        parse_and_cast_relaxed("some_string", str | Path)


def test_bool_node_true_values():
    assert parse_and_cast_relaxed(True, bool) is True
    assert parse_and_cast_relaxed("true", bool) is True
    assert parse_and_cast_relaxed("True", bool) is True
    assert parse_and_cast_relaxed("TRUE", bool) is True
    assert parse_and_cast_relaxed("yes", bool) is True
    assert parse_and_cast_relaxed(1, bool) is True


def test_bool_node_false_values():
    assert parse_and_cast_relaxed(False, bool) is False
    assert parse_and_cast_relaxed("false", bool) is False
    assert parse_and_cast_relaxed("False", bool) is False
    assert parse_and_cast_relaxed("FALSE", bool) is False
    assert parse_and_cast_relaxed("no", bool) is False
    assert parse_and_cast_relaxed("NO", bool) is False
    assert parse_and_cast_relaxed(0, bool) is False
    assert parse_and_cast_relaxed(-1, bool) is False


def test_bool_node_invalid_values():
    with pytest.raises(TypeCoercionError):
        parse_and_cast_relaxed("not_a_bool", bool)
    with pytest.raises(TypeCoercionError):
        parse_and_cast_relaxed(2, bool)
    with pytest.raises(TypeCoercionError):
        parse_and_cast_relaxed(None, bool)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
