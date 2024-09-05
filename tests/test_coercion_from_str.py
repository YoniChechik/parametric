import pytest

from parametric._typehint_parsing import parse_typehint


def parse_and_cast_from_str(value, typehint):
    type_node = parse_typehint("test_field", typehint)
    return type_node.from_str(value)


def test_union_type():
    assert parse_and_cast_from_str("1", str | int) == 1
    assert parse_and_cast_from_str("1", str | int) == 1
    assert parse_and_cast_from_str("1.5", str | float | int) == 1.5
    assert parse_and_cast_from_str("1", str | float | int) == 1
    assert parse_and_cast_from_str("1", float | str | int) == 1
    assert parse_and_cast_from_str("None", str | None) is None
    assert parse_and_cast_from_str("3.0", float | complex) == 3
    assert parse_and_cast_from_str("3.0", int | float) == 3
    assert parse_and_cast_from_str("3", int | float) == 3
    # TODO handle tuples
    # assert parse_and_cast_from_str("(1, 2)", str | tuple[int, int] | int) == (1, 2)
    # assert parse_and_cast_from_str("[1, 2]", str | tuple[int, float] | int) == (1, 2)
    # assert parse_and_cast_from_str("[1, 2]", str | tuple[int, str] | int) == (1, "2")
    # assert parse_and_cast_from_str('("some", "str")', str | tuple[int, str] | int) == "('some', 'str')"


def test_coercion():
    assert parse_and_cast_from_str("1", str) == "1"
    assert parse_and_cast_from_str("1", int) == 1
    assert parse_and_cast_from_str("1.5", float) == 1.5


def test_bool_node_true_values():
    assert parse_and_cast_from_str("true", bool) is True
    assert parse_and_cast_from_str("True", bool) is True
    assert parse_and_cast_from_str("TRUE", bool) is True
    assert parse_and_cast_from_str("yes", bool) is True


def test_bool_node_false_values():
    assert parse_and_cast_from_str("false", bool) is False
    assert parse_and_cast_from_str("False", bool) is False
    assert parse_and_cast_from_str("FALSE", bool) is False
    assert parse_and_cast_from_str("no", bool) is False
    assert parse_and_cast_from_str("NO", bool) is False


if __name__ == "__main__":
    pytest.main(["--no-cov", "-v", __file__])
