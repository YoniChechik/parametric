from typing import Tuple, Union

import pytest

from parametric._base_params import BaseParams, wrangle_type


class MyParamsNew(BaseParams):
    nested_tuple: tuple[tuple[int, str], tuple[float, str]] = ((1, "a"), (3.14, "b"))
    optional_tuple: tuple[int, int, int] | None = (1, 2, 3)
    union_field: int | float = 42
    tuple_of_int_or_str: tuple[int | str, ...] = ("key1", 1)


def test_invalid_overrides():
    params = MyParamsNew()

    # Attempt to override with invalid type should raise an error
    with pytest.raises(ValueError):
        params.override_from_dict({"nested_tuple": ((1, "a"), "not a tuple")})

    with pytest.raises(ValueError):
        params.override_from_dict({"nested_tuple": (("not an int", "a"), (3.14, "b"))})

    with pytest.raises(ValueError):
        params.override_from_dict({"optional_tuple": "not a tuple"})

    with pytest.raises(ValueError):
        params.override_from_dict({"union_field": "not an int or float"})


def test_to_dict_without_freeze():
    params = MyParamsNew()

    # Attempt to call to_dict without freezing should raise an error
    with pytest.raises(RuntimeError):
        params.to_dict()


def test_empty_field_error_on_freeze():
    class CustomParamsScheme(BaseParams):
        mandatory_field: int

    params = CustomParamsScheme()

    # Attempt to freeze with an unset mandatory field should raise an error
    with pytest.raises(ValueError):
        params.freeze()


def test_change_after_freeze():
    params = MyParamsNew()
    params.nested_tuple = ((1, "c"), (3.14, "d"))

    params.freeze()

    with pytest.raises(BaseException):
        params.nested_tuple = ((2, "xxx"), (2, "xxx"))


def test_invalid_tuple_typehint():
    with pytest.raises(ValueError):
        wrangle_type("test_field", (1, 2), tuple)
    with pytest.raises(ValueError):
        wrangle_type("test_field", (1, 2), Tuple)
    with pytest.raises(ValueError):
        wrangle_type("test_field", 1, Union)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
