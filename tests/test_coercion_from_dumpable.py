from typing import Tuple, Union

import pytest

from parametric._type_node import TypeCoercionError
from parametric._typehint_parsing import parse_typehint


def parse_and_cast_dumpable(value, typehint):
    type_node = parse_typehint("test_field", typehint)
    return type_node.from_dumpable(value)


def test_union_type():
    assert parse_and_cast_dumpable(1, str | int) == 1
    assert parse_and_cast_dumpable("1", str | int) == "1"
    assert parse_and_cast_dumpable("1", int | str) == "1"
    assert parse_and_cast_dumpable(1.5, str | float | int) == 1.5
    assert parse_and_cast_dumpable(1, str | float | int) == 1
    assert parse_and_cast_dumpable(1, float | str | int) == 1
    assert parse_and_cast_dumpable((1, 2), str | tuple[int, int] | int) == (1, 2)
    assert parse_and_cast_dumpable(None, str | None) is None
    assert parse_and_cast_dumpable(3.0, float | complex) == 3
    assert parse_and_cast_dumpable(3.0, int | float) == 3
    assert parse_and_cast_dumpable(3, int | float) == 3
    assert parse_and_cast_dumpable([1, 2], str | tuple[int, float] | int) == (1, 2)
    assert parse_and_cast_dumpable([1, 2], str | tuple[int, float] | int) == (1, 2.0)


def test_impossible_coercion():
    with pytest.raises(Exception):
        parse_and_cast_dumpable((1, 2), tuple[int, None])
    with pytest.raises(Exception):
        parse_and_cast_dumpable((1, 2), tuple[None, int])
    with pytest.raises(Exception):
        parse_and_cast_dumpable("error str", int | float)


def test_invalid_typehint():
    with pytest.raises(Exception):
        parse_and_cast_dumpable((1, 2), tuple)
    with pytest.raises(Exception):
        parse_and_cast_dumpable((1, 2), Tuple)
    with pytest.raises(Exception):
        parse_and_cast_dumpable(1, Union)


def test_bool_node_true_values():
    assert parse_and_cast_dumpable(True, bool) is True


def test_bool_node_false_values():
    assert parse_and_cast_dumpable(False, bool) is False


def test_bool_node_invalid_values():
    with pytest.raises(TypeCoercionError):
        parse_and_cast_dumpable("not_a_bool", bool)
    with pytest.raises(TypeCoercionError):
        parse_and_cast_dumpable(2, bool)
    with pytest.raises(TypeCoercionError):
        parse_and_cast_dumpable(None, bool)


if __name__ == "__main__":
    pytest.main(["--no-cov", "-v", __file__])
