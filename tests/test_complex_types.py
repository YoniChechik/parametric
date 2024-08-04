from typing import Optional, Tuple, Union

import pytest

from parametric._base_params import BaseParams


class MyParamsOld(BaseParams):
    nested_tuple: Tuple[Tuple[int, str], Tuple[float, str]] = ((1, "a"), (3.14, "b"))
    optional_tuple: Optional[Tuple[int, int, int]] = (1, 2, 3)
    union_field: Union[int, float] = 42
    tuple_of_int_or_str: Tuple[Union[int, str], ...] = ("key1", 1)


# Testing complex types with new type hints (Python 3.10+)
class MyParamsNew(BaseParams):
    nested_tuple: tuple[tuple[int, str], tuple[float, str]] = ((1, "a"), (3.14, "b"))
    optional_tuple: tuple[int, int, int] | None = (1, 2, 3)
    union_field: int | float = 42
    tuple_of_int_or_str: tuple[int | str, ...] = ("key1", 1)


@pytest.mark.parametrize("params_class", [MyParamsNew, MyParamsOld])
def test_params_scheme_complex_types(params_class):
    params: MyParamsNew | MyParamsOld = params_class()

    # Check initial state
    assert params.nested_tuple == ((1, "a"), (3.14, "b"))
    assert params.optional_tuple == (1, 2, 3)
    assert params.union_field == 42
    assert params.tuple_of_int_or_str == ("key1", 1)

    # Override some values and freeze
    params.optional_tuple = None
    params.union_field = 3.14
    params.freeze()

    # Convert to dict
    params_dict = params.to_dict()
    assert params_dict["nested_tuple"] == ((1, "a"), (3.14, "b"))
    assert params_dict["optional_tuple"] is None
    assert params_dict["union_field"] == 3.14
    assert params_dict["tuple_of_int_or_str"] == ("key1", 1)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
