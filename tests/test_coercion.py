from typing import Tuple, Union

import pytest

from parametric._type_node import ConversionReturn
from parametric._typehint_parsing import parse_typehint


def parse_and_convert(name, value, typehint):
    type_node = parse_typehint(name, typehint)
    return type_node.convert(value)


def test_union_type_prefer_no_coercion():
    assert _compare_wrangle_type_returns(
        parse_and_convert("test_field", 1, str | int),
        ConversionReturn(1, False),
    )

    assert _compare_wrangle_type_returns(
        parse_and_convert("test_field", "1", str | int),
        ConversionReturn("1", False),
    )

    assert _compare_wrangle_type_returns(
        parse_and_convert("test_field", 1.5, str | float | int),
        ConversionReturn(1.5, False),
    )

    assert _compare_wrangle_type_returns(
        parse_and_convert("test_field", 1, str | float | int),
        ConversionReturn(1, False),
    )

    assert _compare_wrangle_type_returns(
        parse_and_convert("test_field", 1, float | str | int),
        ConversionReturn(1, False),
    )

    assert _compare_wrangle_type_returns(
        parse_and_convert("test_field", (1, 2), str | tuple[int, int] | int),
        ConversionReturn((1, 2), False),
    )

    assert _compare_wrangle_type_returns(
        parse_and_convert("test_field", None, str | None),
        ConversionReturn(None, False),
    )


def test_coercion():
    assert _compare_wrangle_type_returns(
        parse_and_convert("test_field", 1, str),
        ConversionReturn("1", True),
    )

    assert _compare_wrangle_type_returns(
        parse_and_convert("test_field", "1", int),
        ConversionReturn(1, True),
    )

    assert _compare_wrangle_type_returns(
        parse_and_convert("test_field", "1.5", float),
        ConversionReturn(1.5, True),
    )


def test_impossible_coersion():
    with pytest.raises(Exception):
        parse_and_convert("test_field", (1, 2), tuple[int, None])
    with pytest.raises(Exception):
        parse_and_convert("test_field", (1, 2), tuple[None, int])


def test_invalid_tuple_typehint():
    with pytest.raises(ValueError):
        parse_and_convert("test_field", (1, 2), tuple)
    with pytest.raises(ValueError):
        parse_and_convert("test_field", (1, 2), Tuple)
    with pytest.raises(ValueError):
        parse_and_convert("test_field", 1, Union)


def _compare_wrangle_type_returns(a: ConversionReturn, b: ConversionReturn) -> bool:
    if not isinstance(a, ConversionReturn) or not isinstance(b, ConversionReturn):
        return False
    return (a.converted_value == b.converted_value) and (a.is_coerced == b.is_coerced)
